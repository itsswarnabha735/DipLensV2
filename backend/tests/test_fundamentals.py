"""
Unit tests for fundamentals models and validation.
"""

import pytest
from datetime import datetime, timedelta
from app.fundamentals_models import (
    Citation,
    Q1Suggestion,
    Q2Suggestion,
    Q3Suggestion,
    Q4Suggestion,
    FundamentalsSuggestionResponse,
    ValidationResult
)
from app.fundamentals_validator import FundamentalsValidator


class TestFundamentalsModels:
    """Test Pydantic models for fundamentals"""
    
    def test_citation_model(self):
        """Test Citation model"""
        citation = Citation(
            url="https://example.com/article",
            title="Test Article",
            published_at="2025-11-20T10:00:00Z",
            snippet="This is a test snippet."
        )
        assert citation.url == "https://example.com/article"
        assert citation.title == "Test Article"
    
    def test_q1_suggestion_valid_enum(self):
        """Test Q1 suggestion with valid enum values"""
        q1 = Q1Suggestion(
            rec="Macro",
            confidence="High",
            reasons=["Market-wide selloff", "Sector underperformance"],
            citations=[
                Citation(url="https://example.com", title="Market News")
            ]
        )
        assert q1.rec == "Macro"
        assert q1.confidence == "High"
    
    def test_q2_suggestion_valid_enum(self):
        """Test Q2 suggestion with valid enum values"""
        q2 = Q2Suggestion(
            rec="Yes",
            confidence="Medium",
            reasons=["Revenue up 10% YoY", "Margins stable"],
            citations=[
                Citation(url="https://example.com", title="Earnings Report")
            ]
        )
        assert q2.rec == "Yes"
    
    def test_full_response_structure(self):
        """Test complete FundamentalsSuggestionResponse"""
        response = FundamentalsSuggestionResponse(
            q1=Q1Suggestion(
                rec="Sector",
                confidence="High",
                reasons=["Banking sector down 5%", "No company-specific news"],
                citations=[Citation(url="https://example.com", title="Sector News")]
            ),
            q2=Q2Suggestion(
                rec="Yes",
                confidence="Medium",
                reasons=["Q2 revenue growth positive", "Margins stable at 15%"],
                citations=[Citation(url="https://example.com", title="Earnings")]
            ),
            q3=Q3Suggestion(
                rec="NoneObserved",
                confidence="High",
                reasons=["No management changes", "Guidance maintained"],
                citations=[Citation(url="https://example.com", title="Corporate News")]
            ),
            q4=Q4Suggestion(
                rec="LikelySupport",
                confidence="Medium",
                reasons=["Price at 200-DMA", "Historical support level"],
                citations=[Citation(url="https://example.com", title="Technical Analysis")]
            ),
            summary="Stock dip appears sector-driven with intact fundamentals and near support.",
            generated_at=datetime.now().isoformat()
        )
        
        assert response.q1.rec == "Sector"
        assert response.q2.rec == "Yes"
        assert response.q3.rec == "NoneObserved"
        assert response.q4.rec == "LikelySupport"
        assert len(response.summary) > 50


class TestFundamentalsValidator:
    """Test validation gates"""
    
    def setup_method(self):
        """Setup validator"""
        self.validator = FundamentalsValidator(max_citation_age_days=7)
    
    def test_valid_response_passes(self):
        """Test that a valid response passes all gates"""
        response = FundamentalsSuggestionResponse(
            q1=Q1Suggestion(
                rec="Macro",
                confidence="High",
                reasons=["Global market selloff", "Fed rate concerns"],
                citations=[
                    Citation(
                        url="https://example.com/news1",
                        title="Market Selloff",
                        published_at=(datetime.now() - timedelta(days=2)).isoformat()
                    )
                ]
            ),
            q2=Q2Suggestion(
                rec="Yes",
                confidence="High",
                reasons=["Strong Q2 results", "Revenue up 15%"],
                citations=[
                    Citation(url="https://example.com/earnings", title="Earnings Report")
                ]
            ),
            q3=Q3Suggestion(
                rec="NoneObserved",
                confidence="High",
                reasons=["No recent management changes", "Guidance reiterated"],
                citations=[
                    Citation(
                        url="https://example.com/corporate",
                        title="Corporate Updates",
                        published_at=(datetime.now() - timedelta(days=1)).isoformat()
                    )
                ]
            ),
            q4=Q4Suggestion(
                rec="LikelySupport",
                confidence="Medium",
                reasons=["Near 200-DMA", "Historical support zone"],
                citations=[
                    Citation(url="https://example.com/tech", title="Technical View")
                ]
            ),
            summary="Stock appears to be caught in broader market selloff with fundamentals intact.",
            generated_at=datetime.now().isoformat()
        )
        
        result = self.validator.validate_all(response)
        assert result.valid is True
    
    def test_missing_citations_fails(self):
        """Test that missing citations cause validation failure"""
        from pydantic import ValidationError
        # This should fail Pydantic validation due to empty citations
        with pytest.raises(ValidationError) as exc_info:
            Q2Suggestion(
                rec="Yes",
                confidence="High",
                reasons=["Revenue up", "Margins improved"],
                citations=[]  # No citations!
            )
        
        # Check that citations error is included
        errors = str(exc_info.value)
        assert "citations" in errors
    
    def test_recency_check(self):
        """Test recency scoring"""
        recent_citation = Citation(
            url="https://example.com",
            title="Recent News",
            published_at=(datetime.now() - timedelta(days=3)).isoformat()
        )
        
        old_citation = Citation(
            url="https://example.com",
            title="Old News",
            published_at=(datetime.now() - timedelta(days=30)).isoformat()
        )
        
        # All recent
        score = self.validator._check_recency([recent_citation, recent_citation])
        assert score == 1.0
        
        # Mixed
        score = self.validator._check_recency([recent_citation, old_citation])
        assert score == 0.5
        
        # All old
        score = self.validator._check_recency([old_citation, old_citation])
        assert score == 0.0
    
    def test_safety_filter_blocks_prohibited_terms(self):
        """Test that safety filter blocks investment advice"""
        response = FundamentalsSuggestionResponse(
            q1=Q1Suggestion(
                rec="Macro",
                confidence="High",
                reasons=["You should BUY this stock now", "Strong growth ahead"],  # Prohibited!
                citations=[Citation(url="https://example.com", title="News")]
            ),
            q2=Q2Suggestion(
                rec="Yes",
                confidence="High",
                reasons=["Good results", "Revenue growth strong"],
                citations=[Citation(url="https://example.com", title="News")]
            ),
            q3=Q3Suggestion(
                rec="NoneObserved",
                confidence="High",
                reasons=["No issues", "Guidance maintained"],
                citations=[Citation(url="https://example.com", title="News")]
            ),
            q4=Q4Suggestion(
                rec="LikelySupport",
                confidence="Medium",
                reasons=["At support", "Volume spike"],
                citations=[Citation(url="https://example.com", title="News")]
            ),
            summary="This test summary is long enough to meet the minimum fifty character requirement for validation.",
            generated_at=datetime.now().isoformat()
        )
        
        valid, error = self.validator._enforce_safety(response)
        assert valid is False
        assert "prohibited term" in error.lower()
    
    def test_invalid_url_format_fails(self):
        """Test that invalid URL formats are caught"""
        q_bad = Q1Suggestion(
            rec="Macro",
            confidence="High",
            reasons=["Test reason one", "Test reason two"],
            citations=[
                Citation(url="not-a-valid-url", title="Bad URL")  # Invalid!
            ]
        )
        
        valid, error = self.validator._validate_citations(q_bad, "Q1")
        assert valid is False
        assert "invalid url format" in error.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
