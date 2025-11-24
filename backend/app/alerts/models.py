from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class AlertCondition(str, Enum):
    DIP_GT = "dip_gt"  # Dip >= X%
    RSI_LT = "rsi_lt"  # RSI < X
    MACD_BULLISH = "macd_bullish"  # MACD Histogram > 0 and > threshold
    VOLUME_SPIKE = "volume_spike"  # Volume > X * Avg Volume
    PRE_SCORE_GT = "pre_score_gt" # Pre-Score > X

class AlertStateEnum(str, Enum):
    IDLE = "idle"
    ARMED = "armed"  # Condition met, waiting for confirmation window
    TRIGGERED = "triggered" # Alert fired
    COOLDOWN = "cooldown" # In cooldown period

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SuppressionReason(str, Enum):
    BUDGET = "budget"
    QUIET_HOURS = "quiet_hours"
    COOLDOWN = "cooldown"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    LOW_PRIORITY = "low_priority"
    BURST_ROLLUP = "burst_rollup"
    CORPORATE_ACTION = "corporate_action"
    HALT = "halt"

class AlertRule(BaseModel):
    id: str
    user_id: str = "default_user" # Single user for now
    symbol: str
    condition: AlertCondition
    threshold: float
    
    # Sensitivity & Tuning
    debounce_seconds: int = 0 # Condition must hold for X seconds
    hysteresis_reset: float = 0.0 # Value must retreat by this much to reset
    confirm_window_seconds: int = 0 # Window to look for confirmation
    
    # Noise Control
    enabled: bool = True
    cooldown_seconds: int = 3600 # 1 hour default
    priority: Priority = Priority.MEDIUM
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AlertState(BaseModel):
    rule_id: str
    symbol: str
    state: AlertStateEnum = AlertStateEnum.IDLE
    
    last_transition_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    
    # For change-of-state detection
    last_value: Optional[float] = None
    
    # For confirmation window
    first_signal_at: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True

class AlertEvent(BaseModel):
    id: str
    rule_id: str
    symbol: str
    fired_at: datetime = Field(default_factory=datetime.utcnow)
    priority: Priority
    
    # Context
    value: float
    threshold: float
    message: str
    chips: List[str] = []
    payload: Dict[str, Any] = {}
    
    # Delivery Status
    push_sent: bool = False
    digest_batch_id: Optional[str] = None

class SuppressionLog(BaseModel):
    id: str
    rule_id: str
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    reason: SuppressionReason
    meta: Dict[str, Any] = {}
