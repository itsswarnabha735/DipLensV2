from fastapi import APIRouter, HTTPException
from typing import List
from pydantic import BaseModel
from app.sector_aggregator import SectorAggregator, SectorSnapshot
from app.indicators import IndicatorEngine
from app.dip_engine import DipEngine
from app.providers.nse import nse_provider  # Use NSE provider for Indian stocks
from app.routers.sectors import load_sector_data
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


class SectorSnapshotResponse(BaseModel):
    """Response model for sector snapshot"""
    sector_id: str
    sector_name: str
    ts: str
    dip_pct: float
    rsi40_breadth: float
    sma200_up_breadth: float
    lowerband_breadth: float
    constituents_count: int
    avg_volume_ratio: float


# In-memory cache for sector snapshots (must be after class definition)
_snapshot_cache: List[SectorSnapshotResponse] = []
_cache_timestamp: float = 0
CACHE_TTL_SECONDS = 900  # 15 minutes



@router.get("/sectors/{sector_id}/snapshot", response_model=SectorSnapshotResponse)
async def get_sector_snapshot(sector_id: str):
    """
    Get current sector snapshot with breadth metrics
    
    - **sector_id**: Sector identifier (e.g., nifty_bank, nifty_it)
    
    Returns sector-level aggregated metrics including:
    - Weighted average dip percentage
    - RSI < 40 breadth
    - SMA200+ breadth  
    - Lower Bollinger band breadth
    - Volume ratio
    """
    try:
        # Load sector membership
        sector_data = load_sector_data()
        sector = next((s for s in sector_data.sectors if s.sector_id == sector_id), None)
        
        if not sector:
            raise HTTPException(status_code=404, detail=f"Sector {sector_id} not found")
        
        # Fetch data for all members
        member_symbols = [m.symbol for m in sector.members]
        weights = [m.weight_hint if m.weight_hint else 1.0/len(sector.members) for m in sector.members]
        
        member_data = []
        
        # Fetch data for all members using NSE provider (individual calls)
        logger.info(f"Fetching data for {len(member_symbols)} symbols using NSE provider")
        all_bars = {}
        
        for symbol in member_symbols:
            try:
                # Use NSE provider for Indian stocks (.NS suffix)
                bars = nse_provider.get_bars(symbol, "1d", "30d")
                if bars:
                    all_bars[symbol] = bars
                    logger.debug(f"Fetched {len(bars)} bars for {symbol}")
            except Exception as e:
                logger.error(f"NSE fetch failed for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched bars for {len(all_bars)}/{len(member_symbols)} symbols")
        
        member_data = []
        
        for symbol in member_symbols:
            try:
                # Fetch bars from batch result
                bars = all_bars.get(symbol, [])
                
                if not bars:
                    continue
                
                # Extract data
                closes = [bar.c for bar in bars]
                highs = [bar.h for bar in bars]
                volumes = [bar.v for bar in bars]
                dates = [bar.t for bar in bars]
                
                # Calculate indicators
                indicators = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, highs)
                
                # Calculate dip
                dip_analysis = DipEngine.analyze_dip(symbol, closes, highs, dates)
                
                # Compile member data
                member_data.append({
                    'symbol': symbol,
                    'current_price': closes[-1] if closes else 0,
                    'current_volume': volumes[-1] if volumes else 0,
                    'rsi': indicators.get('rsi'),
                    'sma200': indicators.get('sma200'),
                    'bollinger': indicators.get('bollinger'),
                    'volume_avg': indicators.get('volume_avg'),
                    'dip_pct': dip_analysis.dip_pct
                })
                
            except Exception as e:
                logger.error(f"Error processing data for {symbol}: {e}")
                continue
        
        if not member_data:
            raise HTTPException(
                status_code=503,
                detail=f"Could not fetch data for any members of {sector_id}"
            )
        
        # Compute sector snapshot
        snapshot = SectorAggregator.compute_sector_snapshot(
            sector_id,
            sector.sector_name,
            member_data,
            weights
        )
        
        return SectorSnapshotResponse(
            sector_id=snapshot.sector_id,
            sector_name=snapshot.sector_name,
            ts=snapshot.ts,
            dip_pct=snapshot.dip_pct,
            rsi40_breadth=snapshot.rsi40_breadth,
            sma200_up_breadth=snapshot.sma200_up_breadth,
            lowerband_breadth=snapshot.lowerband_breadth,
            constituents_count=snapshot.constituents_count,
            avg_volume_ratio=snapshot.avg_volume_ratio
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing sector snapshot: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _update_snapshot_cache() -> List[SectorSnapshotResponse]:
    """
    Internal function to update the snapshot cache.
    Called by background worker and on-demand when cache is stale.
    """
    global _snapshot_cache, _cache_timestamp
    
    try:
        import time
        from datetime import datetime
        
        logger.info("Updating sector snapshot cache...")
        sector_data = load_sector_data()
        results = []
        
        for sector in sector_data.sectors:
            try:
                # Use synchronous version - we'll make this work in async context
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                snapshot_response = loop.run_until_complete(get_sector_snapshot(sector.sector_id))
                results.append(snapshot_response)
            except Exception as e:
                logger.error(f"Error getting snapshot for {sector.sector_id}: {e}")
                # Add empty snapshot
                results.append(SectorSnapshotResponse(
                    sector_id=sector.sector_id,
                    sector_name=sector.sector_name,
                    ts="",
                    dip_pct=0.0,
                    rsi40_breadth=0.0,
                    sma200_up_breadth=0.0,
                    lowerband_breadth=0.0,
                    constituents_count=0,
                    avg_volume_ratio=1.0
                ))
        
        _snapshot_cache = results
        _cache_timestamp = time.time()
        logger.info(f"Sector snapshot cache updated with {len(results)} sectors")
        
        return results
        
    except Exception as e:
        logger.error(f"Error updating snapshot cache: {e}", exc_info=True)
        raise


@router.post("/sectors/refresh-cache")
async def trigger_cache_refresh():
    """
    Manually trigger sector cache refresh (snapshots + candidates).
    
    This runs in the background and returns immediately.
    Use when you want fresh sector data without automatic background updates.
    """
    import threading
    
    def refresh_all():
        try:
            logger.info("Manual cache refresh triggered...")
            _update_snapshot_cache()
            logger.info("Manual cache refresh completed")
        except Exception as e:
            logger.error(f"Manual cache refresh failed: {e}", exc_info=True)
    
    thread = threading.Thread(target=refresh_all, name="ManualCacheRefresh", daemon=True)
    thread.start()
    
    return {
        "status": "started",
        "message": "Sector cache refresh started in background. This may take 3-4 minutes.",
        "estimated_time_seconds": 240
    }


# async def get_all_sector_snapshots() -> List[SectorSnapshotResponse]: cache on error


@router.get("/sectors/snapshots", response_model=List[SectorSnapshotResponse])
async def get_all_sector_snapshots():
    """
    Get snapshots for all sectors
    
    Returns aggregated metrics for all available sectors.
    This can be used for the Sector Radar view.
    
    Uses in-memory cache with 15-minute TTL for performance.
    """
    global _snapshot_cache, _cache_timestamp
    
    try:
        import time
        
        # Check if cache is valid
        cache_age = time.time() - _cache_timestamp
        
        if _snapshot_cache and cache_age < CACHE_TTL_SECONDS:
            logger.debug(f"Returning cached sector snapshots (age: {cache_age:.0f}s)")
            return _snapshot_cache
        
        # Cache is stale or empty, update it
        logger.info(f"Cache miss or stale (age: {cache_age:.0f}s), fetching fresh sector snapshots...")
        
        # For async context, we need to fetch sectors properly
        sector_data = load_sector_data()
        results = []
        
        for sector in sector_data.sectors:
            try:
                snapshot_response = await get_sector_snapshot(sector.sector_id)
                results.append(snapshot_response)
            except Exception as e:
                logger.error(f"Error getting snapshot for {sector.sector_id}: {e}")
                # Add empty snapshot
                results.append(SectorSnapshotResponse(
                    sector_id=sector.sector_id,
                    sector_name=sector.sector_name,
                    ts="",
                    dip_pct=0.0,
                    rsi40_breadth=0.0,
                    sma200_up_breadth=0.0,
                    lowerband_breadth=0.0,
                    constituents_count=0,
                    avg_volume_ratio=1.0
                ))
        
        # Update cache
        _snapshot_cache = results
        _cache_timestamp = time.time()
        logger.info(f"Sector snapshot cache updated with {len(results)} sectors")
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting all sector snapshots: {e}")
        raise HTTPException(status_code=500, detail=str(e))
