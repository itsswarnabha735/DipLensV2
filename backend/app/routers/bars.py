from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from app.models import BarsResponse, MetaResponse, ErrorResponse
from app.providers.yahoo import yahoo_provider
from app.providers.alphavantage import alphavantage_provider
from app.cache import cache
from typing import Literal
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Track consecutive failures for auto-fallback
failure_tracker = {}


@router.get("/bars", response_model=BarsResponse)
async def get_bars(
    symbol: str = Query(..., description="Ticker symbol (e.g., RELIANCE.NS)"),
    interval: Literal["1m", "5m", "15m", "30m", "1h", "1d"] = Query("1m", description="Time interval"),
    lookback: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y"] = Query("1d", description="Lookback period")
):
    """
    Get OHLCV bars for a symbol
    
    - **symbol**: Ticker symbol (e.g., RELIANCE.NS, ^NSEBANK)
    - **interval**: Time interval (1m, 5m, 15m, 30m, 1h, 1d)
    - **lookback**: How far back to fetch (1d, 5d, 1mo, 3mo, 6mo, 1y)
    
    Returns normalized bars with timestamps in UTC ISO 8601 format.
    Auto-switches to Alpha Vantage fallback after 2 consecutive Yahoo failures.
    """
    try:
        # Check cache first
        cached_data = cache.get(symbol, interval, lookback)
        if cached_data and not cached_data.get("stale", False):
            return BarsResponse(**cached_data)
        
        bars = []
        provider_name = "yahoo"

        # Try primary provider (Yahoo)
        try:
            bars = yahoo_provider.get_bars(symbol, interval, lookback)
            if bars:
                # Reset failure tracker on success
                if symbol in failure_tracker:
                    del failure_tracker[symbol]
            else:
                logger.warning(f"Yahoo Finance returned no bars for {symbol}. Trying fallback.")
                raise ValueError("Yahoo Finance returned no data.") # Force fallback
        except Exception as yahoo_error:
            logger.warning(f"Yahoo Finance failed for {symbol}: {yahoo_error}")
            
            # Track consecutive failures
            failure_tracker[symbol] = failure_tracker.get(symbol, 0) + 1
            
            if failure_tracker[symbol] >= 2:
                logger.info(f"Switching to Alpha Vantage fallback for {symbol}")
                try:
                    bars = alphavantage_provider.get_bars(symbol, interval, lookback)
                    provider_name = "alphavantage"
                    logger.info(f"Alpha Vantage fallback successful for {symbol}")
                except Exception as av_error:
                    logger.error(f"Alpha Vantage fallback also failed: {av_error}")
                    raise HTTPException(
                        status_code=503,
                        detail=f"Both providers failed. Yahoo: {str(yahoo_error)}, AlphaVantage: {str(av_error)}"
                    )
            else:
                # Still within tolerance, return Yahoo error
                raise yahoo_error
        
        # Prepare response
        response_data = {
            "symbol": symbol,
            "interval": interval,
            "bars": [bar.model_dump() for bar in bars],
            "asof": datetime.now(timezone.utc).isoformat(),
            "provider": provider_name,
            "stale": False
        }
        
        # Cache the result
        cache.set(symbol, interval, lookback, response_data)
        
        return BarsResponse(**response_data)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bars: {str(e)}")


@router.get("/bars/fallback", response_model=BarsResponse)
async def get_bars_fallback(
    symbol: str = Query(..., description="Ticker symbol"),
    interval: Literal["1m", "5m", "15m", "30m", "1h", "1d"] = Query("5m", description="Time interval"),
    lookback: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y"] = Query("1d", description="Lookback period")
):
    """
    Explicitly use Alpha Vantage fallback provider
    
    Use this endpoint to force Alpha Vantage instead of Yahoo Finance.
    Subject to Alpha Vantage rate limits (5 req/min, 500/day).
    """
    try:
        bars = alphavantage_provider.get_bars(symbol, interval, lookback)
        
        response_data = {
            "symbol": symbol,
            "interval": interval,
            "bars": [bar.model_dump() for bar in bars],
            "asof": datetime.now(timezone.utc).isoformat(),
            "provider": "alphavantage",
            "stale": False
        }
        
        return BarsResponse(**response_data)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alpha Vantage failed: {str(e)}")


@router.get("/bars/meta", response_model=MetaResponse)
async def get_meta():
    """
    Get metadata about the data provider
    
    Returns information about:
    - Available providers
    - Cache statistics
    - Rate limits
    - Provider-specific constraints
    """
    return MetaResponse(
        version="1.0.0",
        providers=["yahoo", "alphavantage"],
        cache_stats=cache.get_stats(),
        rate_limits={
            "yahoo": "~60/min (soft limit)",
            "alphavantage": {
                "per_minute": 5,
                "daily": alphavantage_provider.bucket.get_stats()
            }
        },
        constraints={
            "yahoo": yahoo_provider.get_constraints(),
            "alphavantage": alphavantage_provider.get_constraints()
        },
        freshness={
            "last_update": datetime.now(timezone.utc).isoformat(),
            "stale": False
        },
        limitations={
            "yfinance": "1m data limited to 7 days",
            "alphavantage": "5 req/min, 500/day"
        }
    )
