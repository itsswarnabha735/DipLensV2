from fastapi import APIRouter, HTTPException
from typing import Dict, Optional, Any
from app.providers.yahoo import yahoo_provider
from app.dip_engine import DipEngine, DipClass
from app.indicators import IndicatorEngine
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{symbol}/full-analysis")
async def get_full_analysis(symbol: str, lookback: str = "1y"):
    """
    Get complete stock analysis in a single call:
    - Historical Bars (OHLCV)
    - Dip Analysis
    - Technical Indicators
    """
    try:
        # 1. Fetch Data ONCE
        bars = yahoo_provider.get_bars(symbol, "1d", lookback)
        
        if not bars:
            raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
            
        # Extract arrays for calculations
        closes = [bar.c for bar in bars]
        highs = [bar.h for bar in bars]
        lows = [bar.l for bar in bars]
        volumes = [bar.v for bar in bars]
        dates = [bar.t for bar in bars]
        
        # 2. Calculate Dip Analysis (in-memory)
        dip_analysis = DipEngine.analyze_dip(
            symbol, closes, highs, dates, 365
        )
        
        # 3. Calculate Indicators (in-memory)
        indicators = IndicatorEngine.calculate_all_indicators(
            closes, volumes, highs, lows
        )
        
        # 4. Return Unified Response
        return {
            "symbol": symbol,
            "bars": bars,
            "dip_analysis": {
                "symbol": dip_analysis.symbol,
                "current_price": dip_analysis.current_price,
                "high_52w": dip_analysis.high_52w,
                "high_52w_date": dip_analysis.high_52w_date,
                "dip_pct": dip_analysis.dip_pct,
                "dip_class": dip_analysis.dip_class,
                "days_from_high": dip_analysis.days_from_high
            },
            "indicators": {
                "rsi": indicators["rsi"],
                "macd": indicators["macd"],
                "sma50": indicators["sma50"],
                "sma200": indicators["sma200"],
                "bollinger": indicators["bollinger"],
                "volume_avg": indicators["volume_avg"]
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in full analysis for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
