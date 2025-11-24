"""
Suggestion Bundle Emitter

Creates and persists suggestion bundles based on sector events.
Handles deduplication and cooldowns.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from app.candidate_ranker import RankedCandidate
from app.state_machine import SectorEvent, SectorState
import json
import logging

logger = logging.getLogger(__name__)

@dataclass
class SuggestionBundle:
    """A bundle of suggested candidates for a sector event"""
    bundle_id: str
    event_id: str
    sector_id: str
    ts: str  # ISO timestamp
    candidates: List[RankedCandidate]
    severity_tags: List[str]
    
    def to_dict(self):
        return {
            "bundle_id": self.bundle_id,
            "event_id": self.event_id,
            "sector_id": self.sector_id,
            "ts": self.ts,
            "candidates": [asdict(c) for c in self.candidates],
            "severity_tags": self.severity_tags
        }


class SuggestionEmitter:
    """Manages creation and storage of suggestion bundles"""
    
    def __init__(self):
        # In-memory storage for now (could be Redis/DB)
        self.bundles: Dict[str, List[SuggestionBundle]] = {}  # sector_id -> list of bundles
        self.last_bundle_ts: Dict[str, datetime] = {}  # sector_id -> last bundle time
        
        # Config
        self.bundle_cooldown_minutes = 30
    
    def _generate_severity_tags(self, event: SectorEvent) -> List[str]:
        """Generate tags based on event metrics"""
        tags = []
        metrics = event.metrics_snapshot
        
        dip_pct = metrics.get('dip_pct', 0)
        if dip_pct > 15:
            tags.append("dip_severity: major")
        elif dip_pct > 10:
            tags.append("dip_severity: moderate")
            
        rsi_breadth = metrics.get('rsi40_breadth', 0)
        if rsi_breadth > 0.6:
            tags.append("breadth: high")
            
        return tags

    def _should_emit_bundle(self, sector_id: str, event: SectorEvent) -> bool:
        """Check if we should emit a new bundle (cooldown check)"""
        # Always emit if it's a new ALERT state transition
        if event.new_state == SectorState.ALERT and event.previous_state != SectorState.ALERT:
            return True
            
        # If already in ALERT (e.g. worsen condition), check cooldown
        last_ts = self.last_bundle_ts.get(sector_id)
        if last_ts:
            elapsed = datetime.utcnow() - last_ts
            if elapsed < timedelta(minutes=self.bundle_cooldown_minutes):
                # Unless it's a "worsen" trigger which forces re-emit
                if "worsen" in event.trigger_reason.lower():
                    return True
                return False
                
        return True

    def create_bundle(
        self,
        event: SectorEvent,
        ranked_candidates: List[RankedCandidate]
    ) -> Optional[SuggestionBundle]:
        """
        Create and store a suggestion bundle if conditions met
        """
        if not self._should_emit_bundle(event.sector_id, event):
            return None
            
        if not ranked_candidates:
            return None
            
        now = datetime.utcnow()
        bundle_id = f"bundle_{event.sector_id}_{int(now.timestamp())}"
        
        bundle = SuggestionBundle(
            bundle_id=bundle_id,
            event_id=event.event_id,
            sector_id=event.sector_id,
            ts=now.isoformat(),
            candidates=ranked_candidates,
            severity_tags=self._generate_severity_tags(event)
        )
        
        # Store
        if event.sector_id not in self.bundles:
            self.bundles[event.sector_id] = []
        self.bundles[event.sector_id].append(bundle)
        
        # Keep history limited
        if len(self.bundles[event.sector_id]) > 20:
            self.bundles[event.sector_id] = self.bundles[event.sector_id][-20:]
            
        self.last_bundle_ts[event.sector_id] = now
        
        logger.info(f"Created suggestion bundle {bundle_id} for {event.sector_id} with {len(ranked_candidates)} candidates")
        return bundle

    def get_latest_bundle(self, sector_id: str) -> Optional[SuggestionBundle]:
        """Get the most recent bundle for a sector"""
        bundles = self.bundles.get(sector_id)
        if bundles:
            return bundles[-1]
        return None
