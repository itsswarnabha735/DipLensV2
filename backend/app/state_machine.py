"""
Sector State Machine

Manages sector states (NORMAL/WATCH/ALERT/COOLDOWN) with hysteresis to avoid flapping.
Emits events on state transitions.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import time


class SectorState(str, Enum):
    """Sector monitoring states"""
    NORMAL = "normal"
    WATCH = "watch"
    ALERT = "alert"
    COOLDOWN = "cooldown"


@dataclass
class StateThresholds:
    """Configurable thresholds for state transitions"""
    # Entry thresholds
    watch_dip_min: float = 5.0          # Min dip % for WATCH
    watch_rsi40_breadth_min: float = 0.35   # Min RSI<40 breadth
    
    alert_dip_min: float = 8.0          # Min dip % for ALERT
    alert_rsi40_breadth_min: float = 0.45   # Min RSI<40 breadth
    alert_down_breadth_min: float = 0.55    # Alternative: down breadth
    
    # Exit thresholds (hysteresis - less strict)
    watch_exit_dip: float = 4.0
    watch_exit_rsi40: float = 0.33
    
    alert_exit_dip: float = 7.0
    alert_exit_rsi40: float = 0.43
    
    # Cooldown settings
    cooldown_duration_seconds: int = 1800  # 30 minutes
    
    # Re-alert triggers (during cooldown)
    dip_worsen_threshold: float = 2.0      # +2% dip deepening
    breadth_worsen_threshold: float = 0.10  # +10pp breadth increase


@dataclass
class SectorEvent:
    """Event emitted on state change"""
    event_id: str
    sector_id: str
    ts: datetime
    previous_state: SectorState
    new_state: SectorState
    metrics_snapshot: Dict
    trigger_reason: str


@dataclass
class SectorStateRecord:
    """Tracks current state and history for a sector"""
    sector_id: str
    current_state: SectorState
    last_transition: datetime
    cooldown_until: Optional[datetime]
    last_alert_metrics: Optional[Dict]  # For worsen detection
    state_history: List[SectorEvent]


class SectorStateMachine:
    """Manages sector state transitions with hysteresis"""
    
    def __init__(self, thresholds: Optional[StateThresholds] = None):
        self.thresholds = thresholds or StateThresholds()
        self.sector_states: Dict[str, SectorStateRecord] = {}
    
    def _meets_watch_criteria(self, metrics: Dict) -> bool:
        """Check if metrics meet WATCH state criteria"""
        dip_pct = metrics.get('dip_pct', 0)
        rsi40_breadth = metrics.get('rsi40_breadth', 0)
        
        return (
            dip_pct >= self.thresholds.watch_dip_min and
            rsi40_breadth >= self.thresholds.watch_rsi40_breadth_min
        )
    
    def _meets_alert_criteria(self, metrics: Dict) -> bool:
        """Check if metrics meet ALERT state criteria"""
        dip_pct = metrics.get('dip_pct', 0)
        rsi40_breadth = metrics.get('rsi40_breadth', 0)
        lowerband_breadth = metrics.get('lowerband_breadth', 0)
        
        # ALERT: dip ≥ 8% AND (rsi40 ≥ 45% OR down_breadth ≥ 55%)
        # Using lowerband_breadth as proxy for "down_breadth"
        return (
            dip_pct >= self.thresholds.alert_dip_min and
            (rsi40_breadth >= self.thresholds.alert_rsi40_breadth_min or
             lowerband_breadth >= self.thresholds.alert_down_breadth_min)
        )
    
    def _should_exit_watch(self, metrics: Dict) -> bool:
        """Check if should exit WATCH state (hysteresis)"""
        dip_pct = metrics.get('dip_pct', 0)
        rsi40_breadth = metrics.get('rsi40_breadth', 0)
        
        return (
            dip_pct < self.thresholds.watch_exit_dip or
            rsi40_breadth < self.thresholds.watch_exit_rsi40
        )
    
    def _should_exit_alert(self, metrics: Dict) -> bool:
        """Check if should exit ALERT state (hysteresis)"""
        dip_pct = metrics.get('dip_pct', 0)
        rsi40_breadth = metrics.get('rsi40_breadth', 0)
        
        return (
            dip_pct < self.thresholds.alert_exit_dip or
            rsi40_breadth < self.thresholds.alert_exit_rsi40
        )
    
    def _check_worsen_conditions(self, current_metrics: Dict, last_metrics: Optional[Dict]) -> bool:
        """Check if conditions worsened enough to re-alert during cooldown"""
        if not last_metrics:
            return False
        
        current_dip = current_metrics.get('dip_pct', 0)
        last_dip = last_metrics.get('dip_pct', 0)
        dip_deepened = current_dip - last_dip
        
        current_breadth = current_metrics.get('rsi40_breadth', 0)
        last_breadth = last_metrics.get('rsi40_breadth', 0)
        breadth_increased = current_breadth - last_breadth
        
        return (
            dip_deepened >= self.thresholds.dip_worsen_threshold or
            breadth_increased >= self.thresholds.breadth_worsen_threshold
        )
    
    def update_state(
        self, 
        sector_id: str, 
        metrics: Dict
    ) -> Optional[SectorEvent]:
        """
        Update sector state based on current metrics
        
        Args:
            sector_id: Sector identifier
            metrics: Current sector metrics (dip_pct, breadths, etc.)
            
        Returns:
            SectorEvent if state changed, None otherwise
        """
        now = datetime.utcnow()
        
        # Initialize state record if new sector
        if sector_id not in self.sector_states:
            self.sector_states[sector_id] = SectorStateRecord(
                sector_id=sector_id,
                current_state=SectorState.NORMAL,
                last_transition=now,
                cooldown_until=None,
                last_alert_metrics=None,
                state_history=[]
            )
        
        record = self.sector_states[sector_id]
        current_state = record.current_state
        new_state = current_state
        trigger_reason = ""
        
        # State transition logic
        if current_state == SectorState.NORMAL:
            if self._meets_alert_criteria(metrics):
                new_state = SectorState.ALERT
                trigger_reason = "Alert criteria met"
            elif self._meets_watch_criteria(metrics):
                new_state = SectorState.WATCH
                trigger_reason = "Watch criteria met"
        
        elif current_state == SectorState.WATCH:
            if self._meets_alert_criteria(metrics):
                new_state = SectorState.ALERT
                trigger_reason = "Escalated from WATCH to ALERT"
            elif self._should_exit_watch(metrics):
                new_state = SectorState.NORMAL
                trigger_reason = "Watch criteria no longer met"
        
        elif current_state == SectorState.ALERT:
            if self._should_exit_alert(metrics):
                # Enter cooldown instead of going directly to NORMAL
                new_state = SectorState.COOLDOWN
                record.cooldown_until = now + timedelta(seconds=self.thresholds.cooldown_duration_seconds)
                record.last_alert_metrics = metrics.copy()
                trigger_reason = "Alert ended, entering cooldown"
        
        elif current_state == SectorState.COOLDOWN:
            # Check if cooldown expired
            if record.cooldown_until and now >= record.cooldown_until:
                new_state = SectorState.NORMAL
                trigger_reason = "Cooldown expired"
            # Check worsen conditions for re-alert
            elif self._check_worsen_conditions(metrics, record.last_alert_metrics):
                new_state = SectorState.ALERT
                trigger_reason = "Conditions worsened during cooldown"
        
        # Emit event if state changed
        if new_state != current_state:
            event = SectorEvent(
                event_id=f"{sector_id}_{int(time.time())}",
                sector_id=sector_id,
                ts=now,
                previous_state=current_state,
                new_state=new_state,
                metrics_snapshot=metrics.copy(),
                trigger_reason=trigger_reason
            )
            
            # Update record
            record.current_state = new_state
            record.last_transition = now
            record.state_history.append(event)
            
            # Keep only last 100 events per sector
            if len(record.state_history) > 100:
                record.state_history = record.state_history[-100:]
            
            return event
        
        return None
    
    def get_current_state(self, sector_id: str) -> SectorState:
        """Get current state for a sector"""
        if sector_id in self.sector_states:
            return self.sector_states[sector_id].current_state
        return SectorState.NORMAL
    
    def get_state_history(self, sector_id: str, limit: int = 10) -> List[SectorEvent]:
        """Get recent state history for a sector"""
        if sector_id in self.sector_states:
            history = self.sector_states[sector_id].state_history
            return history[-limit:] if len(history) > limit else history
        return []
