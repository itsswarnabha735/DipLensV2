"""
Pydantic models for LLM-Assisted Fundamentals Checklist.

This module defines the request/response schemas for fundamentals suggestions
powered by Gemini with Google Search grounding.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime


class Citation(BaseModel):
    """Source citation from grounded search results"""
    url: str = Field(..., description="Source URL")
    title: str = Field(..., description="Source title/headline")
    published_at: Optional[str] = Field(None, description="Publication timestamp (ISO 8601)")
    snippet: Optional[str] = Field(None, description="Relevant excerpt from source")


class QuestionSuggestion(BaseModel):
    """LLM suggestion for a single fundamentals question"""
    rec: str = Field(..., description="Recommendation (categorical answer)")
    confidence: Literal["High", "Medium", "Low"] = Field(..., description="Confidence level based on evidence quality")
    reasons: List[str] = Field(..., min_length=2, max_length=3, description="2-3 evidence-based reasons")
    citations: List[Citation] = Field(..., min_length=1, max_length=3, description="1-3 source citations")


class Q1Suggestion(QuestionSuggestion):
    """Q1: Dip cause classification"""
    rec: Literal["Macro", "Sector", "CompanySpecific", "Unknown"] = Field(
        ..., 
        description="Dip cause: Macro/Sector/CompanySpecific/Unknown"
    )


class Q2Suggestion(QuestionSuggestion):
    """Q2: Earnings resilience"""
    rec: Literal["Yes", "No", "Unsure"] = Field(
        ..., 
        description="Are revenue & profit intact? Yes/No/Unsure"
    )


class Q3Suggestion(QuestionSuggestion):
    """Q3: Management/guidance quality"""
    rec: Literal["NoneObserved", "NegativeObserved", "Unsure"] = Field(
        ..., 
        description="Any negative guidance or management exits? NoneObserved/NegativeObserved/Unsure"
    )


class Q4Suggestion(QuestionSuggestion):
    """Q4: Support level proximity"""
    rec: Literal["LikelySupport", "NotNear", "Unsure"] = Field(
        ..., 
        description="Is price near support zone? LikelySupport/NotNear/Unsure"
    )


class FundamentalsSuggestionRequest(BaseModel):
    """Request for fundamentals suggestions"""
    symbol: str = Field(..., description="Stock symbol (e.g., AXISBANK.NS)")
    as_of: str = Field(..., description="Timestamp of request (ISO 8601)")
    features: Dict[str, Any] = Field(..., description="Technical features (dip%, sector move, RSI, etc.)")
    grounding: Dict[str, bool] = Field(
        default={"google_search": True},
        description="Grounding configuration"
    )


class FundamentalsSuggestionResponse(BaseModel):
    """Response with LLM-generated fundamentals suggestions"""
    q1: Q1Suggestion = Field(..., description="Q1: Dip cause")
    q2: Q2Suggestion = Field(..., description="Q2: Earnings resilience")
    q3: Q3Suggestion = Field(..., description="Q3: Management/guidance")
    q4: Q4Suggestion = Field(..., description="Q4: Support level")
    summary: str = Field(
        ..., 
        min_length=50, 
        max_length=800,
        description="3-5 sentence summary"
    )
    generated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    model_version: str = Field(default="gemini-2.0-flash-grounded-v1")
    cache_key: Optional[str] = Field(None, description="Cache key for this response")


class ValidationResult(BaseModel):
    """Result of validation gate check"""
    valid: bool = Field(..., description="Whether validation passed")
    error_message: Optional[str] = Field(None, description="Error message if validation failed")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")


class ConfidenceMetrics(BaseModel):
    """Metrics for confidence assessment"""
    citation_count: int = Field(..., description="Total citations provided")
    recent_citation_count: int = Field(..., description="Citations within recency window")
    source_diversity: float = Field(..., ge=0.0, le=1.0, description="Diversity of source domains (0-1)")
    conflicting_signals: bool = Field(default=False, description="Whether conflicting evidence detected")


class FundamentalsCache(BaseModel):
    """Cache entry for fundamentals suggestions"""
    symbol: str
    response: FundamentalsSuggestionResponse
    created_at: datetime
    ttl_seconds: int = 90
    
    def is_expired(self) -> bool:
        """Check if cache entry is expired"""
        from datetime import datetime, timedelta
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
