from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.dip_engine import DipEngine, DipAnalysis, DipClass
from app.providers.yahoo import yahoo_provider
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class DipAnalysisResponse(BaseModel):
    """Response model for dip analysis"""
    symbol: str
    current_price: float
    high_52w: float
    high_52w_date: str | None
    dip_pct: float
    dip_class: DipClass
    days_from_high: int | None


class DipBatchRequest(BaseModel):
    """Request model for batch dip analysis"""
    symbols: List[str]
    lookback_days: int = 365


@router.get("/{symbol}", response_model=DipAnalysisResponse)
async def analyze_dip_single(
    symbol: str,
    lookback_days: int = 365
):
    """
    Analyze dip for a single symbol
    
    - **symbol**: Ticker symbol (e.g., TCS.NS)
    - **lookback_days**: Rolling window for high calculation (default 365)
    
    Returns dip classification and 52-week high information
    """
    try:
        # Fetch daily bars for the lookback period
        bars = yahoo_provider.get_bars(symbol, "1d", f"{lookback_days}d" if lookback_days <= 30 else "1y")
        
        if not bars:
            raise HTTPException(
                status_code=400,
                detail=f"No data available for {symbol}"
            )
        
        # Extract price data
        closes = [bar.c for bar in bars]
        highs = [bar.h for bar in bars]
        dates = [bar.t for bar in bars]
        
        # Analyze dip
        analysis = DipEngine.analyze_dip(
            symbol,
            closes,
            highs,
            dates,
            lookback_days
        )
        
        return DipAnalysisResponse(
            symbol=analysis.symbol,
            current_price=analysis.current_price,
            high_52w=analysis.high_52w,
            high_52w_date=analysis.high_52w_date,
            dip_pct=analysis.dip_pct,
            dip_class=analysis.dip_class,
            days_from_high=analysis.days_from_high
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing dip for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch", response_model=List[DipAnalysisResponse])
async def analyze_dips_batch(request: DipBatchRequest):
    """
    Analyze dips for multiple symbols in batch
    
    - **symbols**: List of ticker symbols
    - **lookback_days**: Rolling window (default 365)
    
    Returns dip analysis for each symbol
    """
    results = []
    
    for symbol in request.symbols:
        try:
            bars = yahoo_provider.get_bars(symbol, "1d", f"{request.lookback_days}d" if request.lookback_days <= 30 else "1y")
            
            if not bars:
                # Return zero values for symbols with no data
                results.append(DipAnalysisResponse(
                    symbol=symbol,
                    current_price=0.0,
                    high_52w=0.0,
                    high_52w_date=None,
                    dip_pct=0.0,
                    dip_class=DipClass.NONE,
                    days_from_high=None
                ))
                continue
            
            closes = [bar.c for bar in bars]
            highs = [bar.h for bar in bars]
            dates = [bar.t for bar in bars]
            
            analysis = DipEngine.analyze_dip(
                symbol,
                closes,
                highs,
                dates,
                request.lookback_days
            )
            
            results.append(DipAnalysisResponse(
                symbol=analysis.symbol,
                current_price=analysis.current_price,
                high_52w=analysis.high_52w,
                high_52w_date=analysis.high_52w_date,
                dip_pct=analysis.dip_pct,
                dip_class=analysis.dip_class,
                days_from_high=analysis.days_from_high
            ))
            
        except Exception as e:
            logger.error(f"Error in batch dip analysis for {symbol}: {e}")
            results.append(DipAnalysisResponse(
                symbol=symbol,
                current_price=0.0,
                high_52w=0.0,
                high_52w_date=None,
                dip_pct=0.0,
                dip_class=DipClass.NONE,
                days_from_high=None
            ))
    
    return results
