from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict
from app.indicators import IndicatorEngine
from app.providers.yahoo import yahoo_provider
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class IndicatorBatchRequest(BaseModel):
    """Request model for batch indicator calculation"""
    symbols: List[str]
    interval: str = "1d"
    lookback: str = "1y"


class IndicatorResponse(BaseModel):
    """Response model for indicators"""
    symbol: str
    rsi: float | None
    macd: Dict[str, float] | None
    sma50: float | None
    sma200: float | None
    bollinger: Dict[str, float] | None
    volume_avg: float | None
    error: str | None = None


@router.post("/batch", response_model=List[IndicatorResponse])
async def calculate_indicators_batch(request: IndicatorBatchRequest = Body(...)):
    """
    Calculate technical indicators for multiple symbols in batch
    
    - **symbols**: List of ticker symbols
    - **interval**: Time interval (default: 1d)
    - **lookback**: Historical period (default: 1y)
    
    Returns RSI(14), MACD(12,26,9), SMA50, SMA200, Bollinger(20,2), VolAvg20
    """
    results = []
    
    for symbol in request.symbols:
        try:
            # Fetch historical bars
            bars = yahoo_provider.get_bars(symbol, request.interval, request.lookback)
            
            if not bars or len(bars) < 200:
                results.append(IndicatorResponse(
                    symbol=symbol,
                    rsi=None,
                    macd=None,
                    sma50=None,
                    sma200=None,
                    bollinger=None,
                    volume_avg=None,
                    error=f"Insufficient data: {len(bars)} bars"
                ))
                continue
            
            # Extract price and volume data
            closes = [bar.c for bar in bars]
            volumes = [bar.v for bar in bars]
            highs = [bar.h for bar in bars]
            lows = [bar.l for bar in bars]
            
            # Calculate all indicators
            indicators = IndicatorEngine.calculate_all_indicators(
                closes, volumes, highs, lows
            )
            
            results.append(IndicatorResponse(
                symbol=symbol,
                rsi=indicators["rsi"],
                macd=indicators["macd"],
                sma50=indicators["sma50"],
                sma200=indicators["sma200"],
                bollinger=indicators["bollinger"],
                volume_avg=indicators["volume_avg"],
                error=None
            ))
            
            logger.info(f"Calculated indicators for {symbol}")
            
        except Exception as e:
            logger.error(f"Error calculating indicators for {symbol}: {e}")
            results.append(IndicatorResponse(
                symbol=symbol,
                rsi=None,
                macd=None,
                sma50=None,
                sma200=None,
                bollinger=None,
                volume_avg=None,
                error=str(e)
            ))
    
    return results


@router.get("/{symbol}", response_model=IndicatorResponse)
async def calculate_indicators_single(
    symbol: str,
    interval: str = "1d",
    lookback: str = "1y"
):
    """
    Calculate technical indicators for a single symbol
    
    - **symbol**: Ticker symbol
    - **interval**: Time interval (default: 1d)
    - **lookback**: Historical period (default: 1y)
    """
    try:
        bars = yahoo_provider.get_bars(symbol, interval, lookback)
        
        if not bars or len(bars) < 200:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient data for {symbol}: {len(bars) if bars else 0} bars (need 200+)"
            )
        
        closes = [bar.c for bar in bars]
        volumes = [bar.v for bar in bars]
        highs = [bar.h for bar in bars]
        lows = [bar.l for bar in bars]
        
        indicators = IndicatorEngine.calculate_all_indicators(
            closes, volumes, highs, lows
        )
        
        return IndicatorResponse(
            symbol=symbol,
            rsi=indicators["rsi"],
            macd=indicators["macd"],
            sma50=indicators["sma50"],
            sma200=indicators["sma200"],
            bollinger=indicators["bollinger"],
            volume_avg=indicators["volume_avg"],
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
