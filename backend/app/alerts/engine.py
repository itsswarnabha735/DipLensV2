import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

from app.alerts.models import (
    AlertRule, AlertState, AlertStateEnum, AlertEvent, 
    AlertCondition, Priority, SuppressionReason, SuppressionLog
)
from app.alerts.storage import AlertStorage
from app.alerts.notifications import NotificationService
from app.alerts.noise_control import NoiseControl

logger = logging.getLogger(__name__)

class AlertEngine:
    def __init__(self):
        self.storage = AlertStorage()
        self.notifier = NotificationService()
        self.noise_control = NoiseControl()
        
    async def evaluate_rule(self, rule: AlertRule, market_data: Dict):
        """
        Evaluate a single rule against current market data.
        Handles state transitions, debounce, hysteresis, and confirmation.
        """
        state = self.storage.get_state(rule.id, rule.symbol)
        now = datetime.utcnow()
        
        # 1. Check Cooldown
        if state.state == AlertStateEnum.COOLDOWN:
            if state.cooldown_until and now >= state.cooldown_until:
                self._transition(state, AlertStateEnum.IDLE, "Cooldown ended")
            else:
                return # Still in cooldown

        # 2. Evaluate Condition
        is_met, current_value = self._check_condition(rule, market_data)
        
        # 3. State Machine
        if state.state == AlertStateEnum.IDLE:
            if is_met:
                # ALRT-05: Change-of-State (False -> True)
                # ALRT-06: Debounce / "For" Duration
                if rule.debounce_seconds > 0:
                    # Move to ARMED, wait for debounce
                    self._transition(state, AlertStateEnum.ARMED, "Condition met, starting debounce")
                    state.first_signal_at = now
                else:
                    # Immediate Trigger
                    await self._trigger_alert(rule, state, current_value)
                    
        elif state.state == AlertStateEnum.ARMED:
            if is_met:
                # Check if debounce period passed
                if state.first_signal_at and (now - state.first_signal_at).total_seconds() >= rule.debounce_seconds:
                    await self._trigger_alert(rule, state, current_value)
            else:
                # Condition lost during debounce
                self._transition(state, AlertStateEnum.IDLE, "Condition lost during debounce")
                
        elif state.state == AlertStateEnum.TRIGGERED:
            # ALRT-07: Hysteresis Reset
            # Check if we should exit TRIGGERED state (reset)
            if self._should_reset(rule, current_value):
                 # Enter Cooldown
                 cooldown_until = now + timedelta(seconds=rule.cooldown_seconds)
                 state.cooldown_until = cooldown_until
                 self._transition(state, AlertStateEnum.COOLDOWN, "Entering cooldown")
        
        # Persist State
        state.last_value = current_value
        self.storage.save_state(state)

    def _check_condition(self, rule: AlertRule, data: Dict) -> (bool, float):
        """Check if rule condition is met based on type"""
        val = 0.0
        met = False
        
        try:
            if rule.condition == AlertCondition.DIP_GT:
                val = data.get('dip_percent', 0)
                met = val >= rule.threshold
                
            elif rule.condition == AlertCondition.RSI_LT:
                val = data.get('rsi', 100)
                met = val < rule.threshold
                
            elif rule.condition == AlertCondition.MACD_BULLISH:
                # Assuming data has macd_hist
                val = data.get('macd_hist', 0)
                met = val > 0 and val > rule.threshold
                
            elif rule.condition == AlertCondition.VOLUME_SPIKE:
                vol = data.get('volume', 0)
                avg_vol = data.get('avg_volume', 1)
                val = vol / avg_vol if avg_vol > 0 else 0
                met = val >= rule.threshold
                
        except Exception as e:
            logger.error(f"Error checking condition {rule.condition}: {e}")
            
        return met, val

    def _should_reset(self, rule: AlertRule, current_value: float) -> bool:
        """Check hysteresis reset condition"""
        # If hysteresis_reset is 0, reset immediately when condition is false
        if rule.hysteresis_reset == 0:
            # Re-evaluate condition logic inversely
            # For DIP_GT (>= 8%), reset if < 8%
            if rule.condition == AlertCondition.DIP_GT:
                return current_value < rule.threshold
            elif rule.condition == AlertCondition.RSI_LT:
                return current_value >= rule.threshold
            # ... others
            return True
            
        # With Hysteresis band
        # e.g. Trigger at 8%, Reset at 6% (hysteresis=2%)
        if rule.condition == AlertCondition.DIP_GT:
            return current_value < (rule.threshold - rule.hysteresis_reset)
        elif rule.condition == AlertCondition.RSI_LT:
            return current_value > (rule.threshold + rule.hysteresis_reset)
            
        return True

    def _transition(self, state: AlertState, new_state: AlertStateEnum, reason: str):
        """Update state transition metadata"""
        state.state = new_state
        state.last_transition_at = datetime.utcnow()
        logger.info(f"Rule {state.rule_id} transition: {new_state} ({reason})")

    async def _trigger_alert(self, rule: AlertRule, state: AlertState, value: float):
        """Handle alert triggering: Noise Control -> Dedupe -> Notify"""
        
        # 1. Noise Control Checks
        suppression_reason = None
        
        # Quiet Hours
        if self.noise_control.is_quiet_hours() and rule.priority != Priority.HIGH:
            suppression_reason = SuppressionReason.QUIET_HOURS
            
        # Budget
        if not suppression_reason:
            suppression_reason = self.noise_control.check_budget(rule.user_id, rule.symbol)
            
        # Log Suppression if any
        if suppression_reason:
            self._log_suppression(rule, suppression_reason)
            # Even if suppressed, we transition state to avoid re-evaluating immediately
            self._transition(state, AlertStateEnum.TRIGGERED, f"Triggered but suppressed: {suppression_reason}")
            state.last_triggered_at = datetime.utcnow()
            return

        # 2. Create Event
        event = AlertEvent(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            symbol=rule.symbol,
            priority=rule.priority,
            value=value,
            threshold=rule.threshold,
            message=self._format_message(rule, value),
            chips=[f"{rule.condition.value} {value:.2f}"],
            payload={"value": value}
        )
        
        # 3. Send Notification
        success = await self.notifier.dispatch(event)
        event.push_sent = success
        
        # 4. Update State & Budget
        self.noise_control.consume_budget(rule.user_id, rule.symbol)
        self._transition(state, AlertStateEnum.TRIGGERED, "Alert fired")
        state.last_triggered_at = datetime.utcnow()
        
        logger.info(f"Alert Fired: {rule.symbol} - {event.message}")

    def _format_message(self, rule: AlertRule, value: float) -> str:
        if rule.condition == AlertCondition.DIP_GT:
            return f"Dip reached {value:.1f}% (Threshold: {rule.threshold}%)"
        elif rule.condition == AlertCondition.RSI_LT:
            return f"RSI dropped to {value:.1f} (Threshold: {rule.threshold})"
        return f"Alert triggered: {rule.condition} = {value:.2f}"

    def _log_suppression(self, rule: AlertRule, reason: SuppressionReason):
        log = SuppressionLog(
            id=str(uuid.uuid4()),
            rule_id=rule.id,
            symbol=rule.symbol,
            reason=reason
        )
        self.storage.log_suppression(log)
