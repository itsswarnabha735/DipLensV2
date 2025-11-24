"""
Runtime validation gates for fundamentals suggestions.

Ensures LLM outputs meet quality, safety, and grounding standards before
being returned to users.
"""

import logging
import re
from typing import List, Tuple, Optional
from datetime import datetime, timedelta
from app.fundamentals_models import (
    FundamentalsSuggestionResponse,
    QuestionSuggestion,
    Citation,
    ValidationResult,
    ConfidenceMetrics
)

logger = logging.getLogger(__name__)


class FundamentalsValidator:
    """Validates fundamentals suggestions through multiple gates"""
    
    def __init__(self, max_citation_age_days: int = 7):
        self.max_citation_age_days = max_citation_age_days
        
        # Prohibited terms for safety filter
        self.prohibited_terms = [
            r'\bbuy\b', r'\bsell\b', r'\bprice target\b', 
            r'\bguarantee\b', r'\bcertainly\b', r'\bwill reach\b',
            r'\binvestment advice\b', r'\brecommendation to\b'
        ]
    
    def validate_all(
        self, 
        response: FundamentalsSuggestionResponse
    ) -> ValidationResult:
        """
        Run all validation gates on a suggestion response.
        
        Returns ValidationResult with overall pass/fail and any warnings.
        """
        warnings = []
        
        # Gate 1: Schema validation (already done by Pydantic)
        # Just check enums are correct
        schema_valid, schema_error = self._validate_schema(response)
        if not schema_valid:
            return ValidationResult(valid=False, error_message=schema_error)
        
        # Gate 2: Citation presence
        for q_num, question in enumerate([response.q1, response.q2, response.q3, response.q4], 1):
            citation_valid, citation_error = self._validate_citations(question, f"Q{q_num}")
            if not citation_valid:
                return ValidationResult(valid=False, error_message=citation_error)
        
        # Gate 3: Recency check (Q1 and Q3 require recent sources)
        recency_warnings = []
        for q_label, question in [("Q1", response.q1), ("Q3", response.q3)]:
            recency_score = self._check_recency(question.citations)
            if recency_score < 0.5:  # Less than 50% recent citations
                recency_warnings.append(
                    f"{q_label}: Only {recency_score*100:.0f}% citations are recent (≤{self.max_citation_age_days}d)"
                )
        warnings.extend(recency_warnings)
        
        # Gate 4: Safety filter
        safety_valid, safety_error = self._enforce_safety(response)
        if not safety_valid:
            return ValidationResult(valid=False, error_message=safety_error)
        
        # Gate 5: Contradiction check (basic NLI)
        # For MVP, skip this - too complex without additional model
        # Can add in Phase 2
        
        return ValidationResult(valid=True, warnings=warnings)
    
    def _validate_schema(
        self, 
        response: FundamentalsSuggestionResponse
    ) -> Tuple[bool, Optional[str]]:
        """Validate response schema (enum values, field presence)"""
        try:
            # Check Q1 enum
            if response.q1.rec not in ["Macro", "Sector", "CompanySpecific", "Unknown"]:
                return False, f"Q1 recommendation '{response.q1.rec}' not in allowed values"
            
            # Check Q2 enum
            if response.q2.rec not in ["Yes", "No", "Unsure"]:
                return False, f"Q2 recommendation '{response.q2.rec}' not in allowed values"
            
            # Check Q3 enum
            if response.q3.rec not in ["NoneObserved", "NegativeObserved", "Unsure"]:
                return False, f"Q3 recommendation '{response.q3.rec}' not in allowed values"
            
            # Check Q4 enum
            if response.q4.rec not in ["LikelySupport", "NotNear", "Unsure"]:
                return False, f"Q4 recommendation '{response.q4.rec}' not in allowed values"
            
            # Check confidence values
            for q_num, question in enumerate([response.q1, response.q2, response.q3, response.q4], 1):
                if question.confidence not in ["High", "Medium", "Low"]:
                    return False, f"Q{q_num} confidence '{question.confidence}' not in allowed values"
            
            return True, None
            
        except Exception as e:
            return False, f"Schema validation error: {str(e)}"
    
    def _validate_citations(
        self, 
        suggestion: QuestionSuggestion,
        question_label: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate citation presence and quality.
        Require at least 1 valid citation per question.
        """
        if not suggestion.citations or len(suggestion.citations) == 0:
            return False, f"{question_label}: No citations provided (required ≥1)"
        
        # Check each citation has required fields
        for idx, citation in enumerate(suggestion.citations):
            if not citation.url:
                return False, f"{question_label}: Citation {idx+1} missing URL"
            if not citation.title:
                return False, f"{question_label}: Citation {idx+1} missing title"
            
            # Basic URL validation
            if not citation.url.startswith(('http://', 'https://')):
                return False, f"{question_label}: Citation {idx+1} has invalid URL format"
        
        return True, None
    
    def _check_recency(
        self, 
        citations: List[Citation],
        max_age_days: Optional[int] = None
    ) -> float:
        """
        Check proportion of recent citations.
        Returns score 0.0-1.0 (fraction of citations within recency window).
        """
        if max_age_days is None:
            max_age_days = self.max_citation_age_days
        
        if not citations:
            return 0.0
        
        recent_count = 0
        parseable_count = 0
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        
        for citation in citations:
            if not citation.published_at:
                # No timestamp available - can't determine recency
                continue
            
            try:
                pub_date = datetime.fromisoformat(citation.published_at.replace('Z', '+00:00'))
                parseable_count += 1
                if pub_date >= cutoff_date:
                    recent_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse citation date '{citation.published_at}': {e}")
                continue
        
        if parseable_count == 0:
            # No parseable dates - assume neutral
            return 0.5
        
        return recent_count / parseable_count
    
    def _enforce_safety(
        self, 
        response: FundamentalsSuggestionResponse
    ) -> Tuple[bool, Optional[str]]:
        """
        Safety filter: block advice language and price predictions.
        """
        # Check all text fields
        all_text = [response.summary]
        for question in [response.q1, response.q2, response.q3, response.q4]:
            all_text.extend(question.reasons)
        
        combined_text = " ".join(all_text).lower()
        
        for pattern in self.prohibited_terms:
            if re.search(pattern, combined_text, re.IGNORECASE):
                return False, f"Safety violation: prohibited term detected (matched pattern: {pattern})"
        
        return True, None
    
    def calculate_confidence_metrics(
        self, 
        suggestion: QuestionSuggestion
    ) -> ConfidenceMetrics:
        """
        Calculate metrics that inform confidence assessment.
        For telemetry and monitoring.
        """
        citation_count = len(suggestion.citations)
        recent_count = int(self._check_recency(suggestion.citations) * citation_count)
        
        # Source diversity: unique domains / total citations
        domains = set()
        for citation in suggestion.citations:
            try:
                from urllib.parse import urlparse
                domain = urlparse(citation.url).netloc
                domains.add(domain)
            except:
                pass
        
        source_diversity = len(domains) / citation_count if citation_count > 0 else 0.0
        
        return ConfidenceMetrics(
            citation_count=citation_count,
            recent_citation_count=recent_count,
            source_diversity=source_diversity,
            conflicting_signals=False  # TODO: Implement in Phase 2
        )
