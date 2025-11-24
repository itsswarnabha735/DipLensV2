from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from app.models import InsightResponse, PreScoreDetail, DerivedFeatures, PreScoreComponent
from app.llm_orchestrator import LLMOrchestrator
from app.scoring_engine import ScoringEngine, PreScore
from app.indicators import IncrementalIndicators
from app.dip_engine import DipEngine
from app.providers.yahoo import yahoo_provider
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
llm_orchestrator = LLMOrchestrator()
scoring_engine = ScoringEngine()

# Mock data store for demo purposes - in real app this would be DB/Cache
# We need to fetch the latest data for the symbol to compute the pre-score
# For this implementation, we will assume the frontend passes the necessary data 
# or we fetch it from our internal services. 
# To keep it simple and aligned with the PRD "Inputs" section, 
# we might need a service that aggregates this. 
# For now, I'll create an endpoint that accepts the raw data or just the symbol 
# and fetches/computes internally.

@router.get("/{symbol}/latest", response_model=InsightResponse)
async def get_latest_insight(symbol: str):
    """
    Generates or retrieves the latest insight for a ticker using real market data.
    """
    try:
        # 1. Fetch Historical Bars
        from app.providers.nse import nse_provider
        from app.indicators import IndicatorEngine
        
        logger.info(f"Fetching real data for {symbol}")
        
        # Try NSE first for Indian stocks, fallback to Yahoo
        bars = nse_provider.get_bars(symbol, "1d", "1y")
        if not bars:
            logger.info(f"NSE returned no data for {symbol}, trying Yahoo")
            bars = yahoo_provider.get_bars(symbol, "1d", "1y")
        
        if not bars or len(bars) < 50:
            raise HTTPException(
                status_code=404,
                detail=f"Insufficient historical data for {symbol}. Need at least 50 days."
            )
        
        # 2. Extract price data
        closes = [bar.c for bar in bars]
        volumes = [bar.v for bar in bars]
        highs = [bar.h for bar in bars]
        lows = [bar.l for bar in bars]
        
        current_price = closes[-1]
        
        # 3. Calculate Indicators
        logger.info(f"Calculating indicators for {symbol}")
        indicators = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, lows)
        
        # 4. Calculate Dip Analysis
        from app.dip_engine import DipEngine
        dip_engine = DipEngine()
        
        # Get 52-week high
        week_52_high = max(highs[-252:]) if len(highs) >= 252 else max(highs)
        dip_pct = ((week_52_high - current_price) / week_52_high) * 100
        
        dip_analysis = {
            'dip_pct': dip_pct,
            'week_52_high': week_52_high
        }
        
        # 5. Calculate Pre-Score
        logger.info(f"Calculating pre-score for {symbol}")
        volume_data = {
            'current_volume': volumes[-1] if volumes else 0,
            'volume_avg': indicators.get('volume_avg', 0)
        }
        
        pre_score = scoring_engine.calculate_pre_score(
            symbol=symbol,
            current_price=current_price,
            indicators=indicators,
            dip_analysis=dip_analysis,
            volume_data=volume_data
        )
        
        # 6. Convert PreScore to PreScoreDetail with evidence
        def create_evidence(name: str, indicators: Dict, current_price: float, dip_pct: float) -> str:
            """Create evidence string for each scoring component"""
            if "Dip" in name:
                return f"{dip_pct:.2f}% from 52-week high"
            elif "RSI" in name:
                rsi = indicators.get('rsi', 0)
                if rsi < 30:
                    return f"RSI {rsi:.2f} (oversold, high volatility)"
                elif 30 <= rsi <= 40:
                    return f"RSI {rsi:.2f} (weak/near-oversold)"
                return f"RSI {rsi:.2f}"
            elif "MACD" in name:
                macd = indicators.get('macd', {})
                histogram = macd.get('histogram', 0)
                macd_line = macd.get('macd', 0)
                signal = macd.get('signal', 0)
                if macd_line > signal:
                    return f"MACD {macd_line:.2f} > Signal {signal:.2f} (bullish)"
                elif histogram > 0:
                    return f"Histogram {histogram:.2f} (rising)"
                return f"Histogram {histogram:.2f} (bearish)"
            elif "200-DMA" in name or "SMA200" in name:
                sma200 = indicators.get('sma200', 0)
                pct = ((current_price - sma200) / sma200) * 100
                if current_price >= sma200:
                    return f"Price ₹{current_price:.2f} vs SMA200 ₹{sma200:.2f} (+{pct:.2f}%)"
                else:
                    return f"Price ₹{current_price:.2f} testing SMA200 ₹{sma200:.2f} ({pct:.2f}%)"
            elif "Bollinger" in name or "band" in name.lower():
                bb = indicators.get('bollinger', {})
                lower = bb.get('lower', 0)
                pct = ((current_price - lower) / lower) * 100
                return f"{pct:.2f}% above lower band ₹{lower:.2f}"
            elif "Volume" in name or "Vol" in name:
                vol_avg = indicators.get('volume_avg', 0)
                current_vol = volumes[-1] if volumes else 0
                if vol_avg > 0:
                    ratio = current_vol / vol_avg
                    return f"Volume {current_vol:,.0f} vs avg {vol_avg:,.0f} ({ratio:.2f}x)"
                return f"Volume data available, avg {vol_avg:,.0f}"
            return ""
        
        components = []
        
        # Map scoring criteria to components with points
        criteria = [
            ("Dip 8–15%", 2 if 8 <= dip_pct <= 15 else 0),
            ("RSI 30–40", 2 if indicators.get('rsi') and 30 <= indicators['rsi'] <= 40 else 0),
            ("MACD bullish", 2 if indicators.get('macd', {}).get('histogram', 0) > 0 or indicators.get('macd', {}).get('macd', 0) > indicators.get('macd', {}).get('signal', 0) else 0),
            ("Above 200-DMA", 2 if indicators.get('sma200') and current_price >= indicators['sma200'] * 0.97 else 0),
            ("Near lower Bollinger", 2 if indicators.get('bollinger', {}).get('lower') and current_price <= indicators['bollinger']['lower'] * 1.02 else 0),
            ("Volume spike", 2 if volume_data['volume_avg'] > 0 and volume_data['current_volume'] / volume_data['volume_avg'] >= 1.5 else 0)
        ]
        
        for name, points in criteria:
            evidence = create_evidence(name, indicators, current_price, dip_pct)
            components.append(PreScoreComponent(name=name, points=points, evidence=evidence))
        
        pre_score_detail = PreScoreDetail(
            total=pre_score.pre_score,
            components=components
        )
        
        # 7. Calculate Derived Features
        sma50 = indicators.get('sma50', current_price)
        sma200 = indicators.get('sma200', current_price)
        bb_lower = indicators.get('bollinger', {}).get('lower', current_price)
        
        derived = DerivedFeatures(
            current_price=current_price,
            pct_below_sma50=((sma50 - current_price) / sma50 * 100) if sma50 > 0 else 0,
            pct_above_sma200=((current_price - sma200) / sma200 * 100) if sma200 > 0 else 0,
            pct_above_bb_lower=((current_price - bb_lower) / bb_lower * 100) if bb_lower > 0 else 0
        )
        
        # 8. Identify missing inputs
        missing_inputs = []
        if not volumes or volumes[-1] == 0:
            missing_inputs.append("today_volume")
        if not indicators.get('macd'):
            missing_inputs.append("macd_data")
        
        # 9. Generate Insight via LLM
        logger.info(f"Generating LLM insight for {symbol}")
        insight = llm_orchestrator.generate_insight(
            symbol=symbol,
            pre_score=pre_score_detail,
            derived=derived,
            missing_inputs=missing_inputs
        )
        
        return insight
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"LLM configuration error: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to generate insight for {symbol}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate insight: {str(e)}")

