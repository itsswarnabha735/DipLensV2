from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict
from dataclasses import asdict
from pydantic import BaseModel
from app.routers.sectors import load_sector_data
from app.providers.nse import nse_provider
from app.indicators import IndicatorEngine
from app.dip_engine import DipEngine
from app.scoring_engine import ScoringEngine, PreScore
from app.candidate_ranker import CandidateRanker, RankedCandidate
from app.suggestion_emitter import SuggestionEmitter, SuggestionBundle
from app.state_machine import SectorStateMachine, SectorState, SectorEvent
from app.routers.sector_snapshots import get_sector_snapshot
import logging
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize singletons (in a real app, use dependency injection)
scoring_engine = ScoringEngine()
state_machine = SectorStateMachine()
suggestion_emitter = SuggestionEmitter()

# Global cache for candidates (similar to sector_snapshots cache)
_candidates_cache: Dict[str, List['CandidateResponse']] = {}
_candidates_cache_timestamp: Dict[str, float] = {}
CANDIDATES_CACHE_TTL_SECONDS = 900  # 15 minutes

import time


class CandidateResponse(BaseModel):
    symbol: str
    rank: int
    pre_score: int
    reasons: List[str]
    flags: List[str]
    distance_to_sma200_pct: float
    distance_to_lower_band_pct: float
    adtv: float


class SuggestionBundleResponse(BaseModel):
    bundle_id: str
    event_id: str
    sector_id: str
    ts: str
    candidates: List[CandidateResponse]
    severity_tags: List[str]


@router.get("/{sector_id}/candidates", response_model=List[CandidateResponse])
async def get_sector_candidates(
    sector_id: str,
    limit: int = 12
):
    """
    Get ranked candidates for a sector
    
    Calculates Pre-Scores and ranks candidates based on:
    1. Pre-Score (0-12)
    2. Technical proximity (SMA200, Bollinger)
    3. Liquidity
    """
    global _candidates_cache, _candidates_cache_timestamp
    
    # Check cache first
    current_time = time.time()
    if sector_id in _candidates_cache:
        cache_age = current_time - _candidates_cache_timestamp.get(sector_id, 0)
        if cache_age < CANDIDATES_CACHE_TTL_SECONDS:
            logger.info(f"Returning cached candidates for {sector_id} (age: {cache_age:.0f}s)")
            cached = _candidates_cache[sector_id]
            return cached[:limit]
    
    # Cache miss or stale - compute fresh
    logger.info(f"Computing fresh candidates for {sector_id} (cache miss/stale)")
    try:
        candidates = await _compute_sector_candidates(sector_id)
        
        # Update cache
        _candidates_cache[sector_id] = candidates
        _candidates_cache_timestamp[sector_id] = current_time
        logger.info(f"Cached {len(candidates)} candidates for {sector_id}")
        
        return candidates[:limit]
    except Exception as e:
        logger.error(f"Error computing candidates for {sector_id}: {e}")
        raise


async def _compute_sector_candidates(sector_id: str) -> List[CandidateResponse]:
    """
    Internal function to compute candidates (extracted for caching)
    """
    try:
        # 1. Load sector members
        sector_data = load_sector_data()
        sector = next((s for s in sector_data.sectors if s.sector_id == sector_id), None)
        if not sector:
            raise HTTPException(status_code=404, detail=f"Sector {sector_id} not found")
            
        member_symbols = [m.symbol for m in sector.members]
        
        # 2. Fetch data for all members (batch)
        # Fetch data for all members using NSE provider (individual calls)
        logger.info(f"Fetching data for {len(member_symbols)} symbols using NSE provider")
        all_bars = {}
        
        for symbol in member_symbols:
            try:
                bars = nse_provider.get_bars(symbol, "1d", "30d")
                if bars:
                    all_bars[symbol] = bars
                    logger.debug(f"Fetched {len(bars)} bars for {symbol}")
            except Exception as e:
                logger.error(f"NSE fetch failed for {symbol}: {e}")
                continue
        
        logger.info(f"Successfully fetched bars for {len(all_bars)}/{len(member_symbols)} symbols")
        
        candidates_data = []
        
        for symbol in member_symbols:
            try:
                bars = all_bars.get(symbol, [])
                
                if not bars:
                    continue
                    
                closes = [bar.c for bar in bars]
                highs = [bar.h for bar in bars]
                volumes = [bar.v for bar in bars]
                dates = [bar.t for bar in bars]
                
                # Calculate metrics
                indicators = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, highs)
                dip_analysis = DipEngine.analyze_dip(symbol, closes, highs, dates)
                
                # Estimate ADTV (last 20 days)
                recent_volumes = volumes[-20:]
                recent_closes = closes[-20:]
                adtv = sum(v * c for v, c in zip(recent_volumes, recent_closes)) / len(recent_volumes) if recent_volumes else 0
                
                # Pre-score calculation happens inside ranker preparation or here
                # Let's do it here to pass PreScore object
                pre_score = scoring_engine.calculate_pre_score(
                    symbol,
                    closes[-1],
                    indicators,
                    asdict(dip_analysis) if hasattr(dip_analysis, 'dip_pct') else {'dip_pct': dip_analysis.dip_pct}, # Handle dataclass vs dict
                    {'current_volume': volumes[-1], 'volume_avg': indicators.get('volume_avg')}
                )
                
                candidates_data.append({
                    'symbol': symbol,
                    'pre_score': pre_score,
                    'current_price': closes[-1],
                    'indicators': indicators,
                    'adtv': adtv
                })
                
            except Exception as e:
                logger.error(f"Error processing candidate {symbol}: {e}")
                continue
        
        # 3. Rank candidates
        ranked = CandidateRanker.rank_candidates(candidates_data, limit)
        
        return [
            CandidateResponse(
                symbol=c.symbol,
                rank=c.rank,
                pre_score=c.pre_score,
                reasons=c.reasons,
                flags=c.flags,
                distance_to_sma200_pct=c.distance_to_sma200_pct,
                distance_to_lower_band_pct=c.distance_to_lower_band_pct,
                adtv=c.adtv
            )
            for c in ranked
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting candidates for {sector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{sector_id}/event", response_model=Optional[SuggestionBundleResponse])
async def get_sector_event(sector_id: str):
    """
    Get the latest event and suggestion bundle for a sector
    
    Triggers state machine update and bundle generation if needed.
    """
    try:
        # 1. Get current snapshot
        # Note: In a real background worker, this would be pushed. 
        # Here we pull on demand.
        snapshot_resp = await get_sector_snapshot(sector_id)
        snapshot_dict = snapshot_resp.model_dump()
        
        # 2. Update state machine
        event = state_machine.update_state(sector_id, snapshot_dict)
        
        # 3. If event occurred or we need a bundle for current state
        current_state = state_machine.get_current_state(sector_id)
        
        # If we are in ALERT state, we should ensure we have a bundle
        latest_bundle = suggestion_emitter.get_latest_bundle(sector_id)
        
        if event or (current_state == SectorState.ALERT and not latest_bundle):
            # Generate candidates
            candidates = await get_sector_candidates(sector_id, limit=12)
            
            # Convert response models back to RankedCandidate objects
            ranked_objs = [
                RankedCandidate(
                    symbol=c.symbol,
                    rank=c.rank,
                    pre_score=c.pre_score,
                    reasons=c.reasons,
                    flags=c.flags,
                    distance_to_sma200_pct=c.distance_to_sma200_pct,
                    distance_to_lower_band_pct=c.distance_to_lower_band_pct,
                    adtv=c.adtv
                )
                for c in candidates
            ]
            
            # Create pseudo-event if none exists but we are in ALERT
            if not event and current_state == SectorState.ALERT:
                from datetime import datetime
                import time
                event = SectorEvent(
                    event_id=f"poll_{sector_id}_{int(time.time())}",
                    sector_id=sector_id,
                    ts=datetime.utcnow(),
                    previous_state=SectorState.ALERT, # No change
                    new_state=SectorState.ALERT,
                    metrics_snapshot=snapshot_dict,
                    trigger_reason="Poll update"
                )
            
            if event:
                new_bundle = suggestion_emitter.create_bundle(event, ranked_objs)
                if new_bundle:
                    latest_bundle = new_bundle
        
        if latest_bundle:
            return SuggestionBundleResponse(
                bundle_id=latest_bundle.bundle_id,
                event_id=latest_bundle.event_id,
                sector_id=latest_bundle.sector_id,
                ts=latest_bundle.ts,
                candidates=[
                    CandidateResponse(
                        symbol=c.symbol,
                        rank=c.rank,
                        pre_score=c.pre_score,
                        reasons=c.reasons,
                        flags=c.flags,
                        distance_to_sma200_pct=c.distance_to_sma200_pct,
                        distance_to_lower_band_pct=c.distance_to_lower_band_pct,
                        adtv=c.adtv
                    )
                    for c in latest_bundle.candidates
                ],
                severity_tags=latest_bundle.severity_tags
            )
            
        return None
        
    except Exception as e:
        logger.error(f"Error getting sector event for {sector_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _update_candidates_cache():
    """
    Internal function to update candidates cache for all sectors.
    Called by background worker.
    """
    global _candidates_cache, _candidates_cache_timestamp
    
    try:
        import asyncio
        from app.routers.sectors import load_sector_data
        
        logger.info("Updating candidates cache for all sectors...")
        sector_data = load_sector_data()
        
        current_time = time.time()
        
        # Create event loop for async calls
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for sector in sector_data.sectors:
            try:
                logger.info(f"Computing candidates for {sector.sector_id}...")
                candidates = loop.run_until_complete(_compute_sector_candidates(sector.sector_id))
                
                # Update cache
                _candidates_cache[sector.sector_id] = candidates
                _candidates_cache_timestamp[sector.sector_id] = current_time
                logger.info(f"Cached {len(candidates)} candidates for {sector.sector_id}")
                
            except Exception as e:
                logger.error(f"Failed to update candidates cache for {sector.sector_id}: {e}")
                continue
        
        logger.info(f"Candidates cache updated for {len(_candidates_cache)} sectors")
        
    except Exception as e:
        logger.error(f"Error updating candidates cache: {e}", exc_info=True)
