"""
Fundamentals suggestions API endpoint.

Provides LLM-powered, grounded suggestions for fundamentals checklist questions.
"""

import logging
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from datetime import datetime, timedelta
from app.fundamentals_models import FundamentalsSuggestionResponse, FundamentalsCache
from app.fundamentals_validator import FundamentalsValidator
from app.llm_orchestrator import LLMOrchestrator
from app.dip_engine import DipEngine
from app.indicators import IndicatorEngine
from app.sector_aggregator import SectorAggregator
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
llm_orchestrator = LLMOrchestrator()
validator = FundamentalsValidator(max_citation_age_days=getattr(settings, 'fundamentals_max_citation_age_days', 7))

# Simple in-memory cache (for production, use Redis)
_fundamentals_cache: Dict[str, FundamentalsCache] = {}


@router.get("/fundamentals/{symbol}/suggestions", response_model=FundamentalsSuggestionResponse)
async def get_fundamentals_suggestions(symbol: str):
    """
    Generate LLM-powered fundamentals suggestions with Google Search grounding.
    
    Process:
    1. Check cache (TTL: 90s by default)
    2. Fetch real-time market data (dip%, sector move, indicators)
    3. Generate suggestions via Gemini with grounding
    4. Validate response through runtime gates
    5. Cache and return
    
    Args:
        symbol: Stock symbol (e.g., AXISBANK.NS)
    
    Returns:
        FundamentalsSuggestionResponse with grounded suggestions for Q1-Q4
    """
    try:
        # 1. Check cache
        cache_key = f"fundamentals:{symbol}"
        if cache_key in _fundamentals_cache:
            cached = _fundamentals_cache[cache_key]
            if not cached.is_expired():
                logger.info(f"Returning cached fundamentals suggestions for {symbol}")
                return cached.response
            else:
                # Remove expired entry
                del _fundamentals_cache[cache_key]
        
        logger.info(f"Cache miss - generating fresh fundamentals suggestions for {symbol}")
        
        # 2. Fetch real-time market data
        features = await _fetch_features(symbol)
        
        # 3. Generate suggestions via LLM
        suggestions = llm_orchestrator.generate_fundamentals_suggestions(
            symbol=symbol,
            features=features
        )
        
        # 4. Validate response
        validation_result = validator.validate_all(suggestions)
        
        if not validation_result.valid:
            logger.error(f"Validation failed for {symbol}: {validation_result.error_message}")
            raise HTTPException(
                status_code=500,
                detail=f"Generated suggestions failed validation: {validation_result.error_message}"
            )
        
        if validation_result.warnings:
            logger.warning(f"Validation warnings for {symbol}: {validation_result.warnings}")
            # Continue anyway - warnings are non-fatal
        
        # 5. Cache the result
        cache_ttl = getattr(settings, 'fundamentals_cache_ttl', 90)
        _fundamentals_cache[cache_key] = FundamentalsCache(
            symbol=symbol,
            response=suggestions,
            created_at=datetime.now(),
            ttl_seconds=cache_ttl
        )
        
        logger.info(f"Successfully generated and cached fundamentals suggestions for {symbol}")
        return suggestions
        
    except ValueError as e:
        # LLM configuration error
        logger.error(f"LLM configuration error for {symbol}: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Failed to generate fundamentals suggestions for {symbol}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate fundamentals suggestions: {str(e)}"
        )


async def _fetch_features(symbol: str) -> Dict[str, Any]:
    """
    Fetch all required features for fundamentals suggestion generation.
    
    Returns dict with:
    - dip_pct: Percentage dip from 52-week high
    - sector_move_pct: Sector benchmark movement
    - breadth_down_pct: Market breadth
    - rsi: RSI indicator
    - macd: MACD signal
    - near_sma200: Boolean, price near 200-DMA
    - support_zone: List of support levels
    """
    from app.providers.nse import nse_provider
    from app.providers.yahoo import yahoo_provider
    
    try:
        # Fetch historical bars
        logger.info(f"Fetching bars for {symbol} to calculate features")
        bars = nse_provider.get_bars(symbol, "1d", "1y")
        if not bars:
            logger.info(f"NSE returned no data, trying Yahoo for {symbol}")
            bars = yahoo_provider.get_bars(symbol, "1d", "1y")
        
        if not bars or len(bars) < 50:
            raise ValueError(f"Insufficient historical data for {symbol}")
        
        # Extract price data
        closes = [bar.c for bar in bars]
        volumes = [bar.v for bar in bars]
        highs = [bar.h for bar in bars]
        lows = [bar.l for bar in bars]
        
        current_price = closes[-1]
        
        # Calculate indicators
        logger.info(f"Calculating indicators for {symbol}")
        indicators = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, lows)
        
        # Calculate dip analysis
        week_52_high = max(highs[-252:]) if len(highs) >= 252 else max(highs)
        dip_pct = ((week_52_high - current_price) / week_52_high) * 100
        
        # Get sector data (if available)
        sector_move_pct = 0.0
        breadth_down_pct = 50.0  # Default neutral
        
        try:
            # Try to get sector info
            sector_agg = SectorAggregator()
            # This is simplified - in production would look up symbol's sector
            # and fetch actual sector movement and breadth
            logger.info(f"Sector data fetch skipped for MVP - using defaults")
        except Exception as e:
            logger.warning(f"Could not fetch sector data for {symbol}: {e}")
        
        # Calculate support zones (simple: recent lows with high volume)
        support_zone = []
        try:
            # Find local lows in last 3 months
            recent_lows = lows[-60:] if len(lows) >= 60 else lows
            sorted_lows = sorted(recent_lows)[:3]  # 3 lowest points
            support_zone = [round(low, 2) for low in sorted_lows]
        except Exception as e:
            logger.warning(f"Could not calculate support zones for {symbol}: {e}")
        
        # Build features dict
        features = {
            'dip_pct': round(dip_pct, 2),
            'sector_move_pct': sector_move_pct,
            'breadth_down_pct': breadth_down_pct,
            'rsi': indicators.get('rsi', 50),
            'macd': 'bullish' if indicators.get('macd', {}).get('histogram', 0) > 0 else 'bearish',
            'near_sma200': bool(
                indicators.get('sma200') and 
                current_price >= indicators['sma200'] * 0.97
            ),
            'support_zone': support_zone,
            'current_price': current_price
        }
        
        logger.info(f"Features calculated for {symbol}: dip={dip_pct:.1f}%, RSI={features['rsi']:.0f}")
        return features
        
    except Exception as e:
        logger.error(f"Failed to fetch features for {symbol}: {e}", exc_info=True)
        raise


@router.delete("/fundamentals/cache")
async def clear_fundamentals_cache():
    """Clear the fundamentals suggestions cache (admin endpoint)"""
    global _fundamentals_cache
    count = len(_fundamentals_cache)
    _fundamentals_cache.clear()
    logger.info(f"Cleared {count} entries from fundamentals cache")
    return {"status": "success", "cleared": count}
