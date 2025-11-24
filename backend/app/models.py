from pydantic import BaseModel, Field
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime


class Bar(BaseModel):
    """Normalized OHLCV bar"""
    t: str = Field(..., description="Timestamp in ISO 8601 format (UTC)")
    o: float = Field(..., description="Open price")
    h: float = Field(..., description="High price")
    l: float = Field(..., description="Low price")
    c: float = Field(..., description="Close price")
    v: int = Field(..., description="Volume")


class BarsResponse(BaseModel):
    """Response for /bars endpoint"""
    symbol: str
    interval: str
    bars: List[Bar]
    asof: str = Field(..., description="Data as-of timestamp (UTC)")
    provider: str = Field(default="yahoo", description="Data provider")
    stale: bool = Field(default=False, description="Cache stale flag")


class FreshnessInfo(BaseModel):
    last_update: str
    stale: bool

class LimitationsInfo(BaseModel):
    yfinance: str
    alphavantage: str

class MetaResponse(BaseModel):
    """Response for /meta endpoint"""
    version: str = "1.0.0"
    providers: List[str] = ["yahoo", "alphavantage"]
    cache_stats: dict
    rate_limits: dict
    constraints: dict
    freshness: Optional[FreshnessInfo] = None
    limitations: Optional[LimitationsInfo] = None


class SectorMember(BaseModel):
    """Individual sector member"""
    symbol: str
    name: str
    weight_hint: Optional[float] = None


class ChecklistRequest(BaseModel):
    q1_earnings: str  # "yes", "no", "unsure"
    q2_balance_sheet: str
    q3_moat: str
    q4_management: str

class FinalScoreResponse(BaseModel):
    symbol: str
    pre_score: int
    checklist_score: int
    total_score: int
    band: str
    breakdown: Dict[str, Any]


class Sector(BaseModel):
    """Sector definition"""
    sector_id: str
    sector_name: str
    index_symbol: str
    members: List[SectorMember]


class SectorMembership(BaseModel):
    """Complete sector membership data"""
    version: str
    source: str
    sectors: List[Sector]


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    code: int


# --- Insight Generator Models ---

class PreScoreComponent(BaseModel):
    name: str
    points: int
    evidence: str

class PreScoreDetail(BaseModel):
    total: int
    components: List[PreScoreComponent]

class DerivedFeatures(BaseModel):
    current_price: float
    pct_below_sma50: float
    pct_above_sma200: float
    pct_above_bb_lower: float

class InsightCard(BaseModel):
    title: str
    severity: Literal["info", "warning", "critical"]
    bullets: List[str]

class ChecklistPrompt(BaseModel):
    id: str
    text: str
    scoring_rule: str

class InsightResponse(BaseModel):
    """LLM-generated Insight Response"""
    insight_version: str
    state: Literal["ready", "almost_ready", "not_ready", "insufficient_data"]
    allocation_band: Literal["full", "partial", "small", "skip"]
    pre_score: PreScoreDetail
    derived: DerivedFeatures
    insight_cards: List[InsightCard]
    callouts: Optional[List[str]] = []
    checklist_prompts: List[ChecklistPrompt]
    next_required_inputs: Optional[List[str]] = []
    disclaimer: str
