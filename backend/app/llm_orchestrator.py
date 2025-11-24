import json
import logging
import google.generativeai as genai
from typing import Optional, Dict, Any
from app.config import settings
from app.models import InsightResponse, PreScoreDetail, DerivedFeatures

logger = logging.getLogger(__name__)

class LLMOrchestrator:
    """
    Orchestrates interactions with Gemini for Insight Generation and Fundamentals Suggestions.
    Enforces strict JSON schema and handles grounding for evidence-based suggestions.
    """

    def __init__(self):
        if settings.gemini_api_key:
            masked_key = settings.gemini_api_key[:4] + "..." + settings.gemini_api_key[-4:] if len(settings.gemini_api_key) > 8 else "INVALID"
            logger.info(f"LLMOrchestrator initialized with API Key: {masked_key}")
            try:
                genai.configure(api_key=settings.gemini_api_key)
                
                # Model for insight generation (existing)
                self.model = genai.GenerativeModel('gemini-2.0-flash',
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # Configure grounded model for fundamentals suggestions (with Google Search)
                self.grounded_model = genai.GenerativeModel(
                    'gemini-2.0-flash',
                    generation_config={"response_mime_type": "application/json"}
                )
                logger.info("Grounded Gemini model (gemini-2.0-flash) configured for fundamentals suggestions.")
                
                logger.info("Gemini models configured successfully (insight + grounded fundamentals).")
            except Exception as e:
                logger.error(f"Failed to configure Gemini: {e}")
                self.model = None
                self.grounded_model = None
        else:
            logger.warning("Gemini API key not found in settings. LLM features will be disabled.")
            self.model = None
            self.grounded_model = None

    def generate_insight(
        self,
        symbol: str,
        pre_score: PreScoreDetail,
        derived: DerivedFeatures,
        missing_inputs: list[str]
    ) -> InsightResponse:
        """
        Generates a user-facing insight card from technical data.
        """
        if not self.model:
            logger.error("LLM model not configured. Cannot generate insight.")
            raise ValueError("LLM model not configured. Please set GEMINI_API_KEY.")

        prompt = self._construct_prompt(symbol, pre_score, derived, missing_inputs)
        logger.info(f"Sending prompt to Gemini for {symbol}...")
        
        try:
            response = self.model.generate_content(prompt)
            logger.info("Received response from Gemini.")
            insight_response = InsightResponse.model_validate_json(response.text)
            
            # FORCE OVERWRITE: Ensure checklist prompts are exactly as specified
            insight_response.checklist_prompts = [
                {"id": "q1_earnings", "text": "Is the dip primarily macro/sector‑driven (not company‑specific)?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q2_balance_sheet", "text": "Are revenue and profit broadly intact in the latest results?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q3_moat", "text": "Any negative guidance or key mgmt exits recently?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q4_management", "text": "Is the stock near horizontal support you recognize?", "scoring_rule": "+2 yes / 0 unsure / 0 no"}
            ]
            
            return insight_response
        except Exception as e:
            logger.error(f"LLM Generation failed: {e}")
            raise e

    def _construct_prompt(
        self,
        symbol: str,
        pre_score: PreScoreDetail,
        derived: DerivedFeatures,
        missing_inputs: list[str]
    ) -> str:
        """Constructs the prompt for Gemini with explicit JSON schema."""
        
        # Get the JSON schema from the Pydantic model
        schema = InsightResponse.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        system_instruction = f"""
You are a compliance-aware technical-analysis explainer for the 'Dip Lens' app.
Convert the provided technical metrics into a JSON response that STRICTLY matches this schema:

{schema_str}

CRITICAL RULES:
1. Output ONLY valid JSON matching the exact schema above
2. ALL fields must be present and of the correct type
3. 'severity' for insight_cards must be one of: "info", "warning", "critical"
4. 'checklist_prompts' must be an array of objects with id, text, and scoring_rule fields
5. Never use "buy", "sell", or "guarantee" in any text
6. Use only the provided evidence - do not hallucinate news or fundamentals
7. Keep insight_cards bullets under 140 characters each
8. Generate exactly 4 checklist prompts about: Macro, Results/Earnings, Management, Support levels
        """
        
        user_content = f"""
Analyze {symbol}:

PRE-SCORE: {pre_score.total}/12
Components: {json.dumps([c.model_dump() for c in pre_score.components])}

DERIVED METRICS:
- Current Price: ₹{derived.current_price:.2f}
- % Below SMA50: {derived.pct_below_sma50:.2f}%
- % Above SMA200: {derived.pct_above_sma200:.2f}%  
- % Above BB Lower: {derived.pct_above_bb_lower:.2f}%

MISSING INPUTS: {missing_inputs if missing_inputs else "None"}

Generate the complete JSON response now. Remember to include ALL required fields from the schema.
        """
        
        return system_instruction + "\n\n" + user_content

    def _deterministic_fallback(
        self,
        symbol: str,
        pre_score: PreScoreDetail,
        derived: DerivedFeatures,
        missing_inputs: list[str]
    ) -> InsightResponse:
        """
        Fallback generator if LLM fails or is unconfigured.
        Constructs a basic valid response from rules.
        """
        
        # Logic to build simple cards based on score
        main_card_bullets = []
        for comp in pre_score.components:
            if comp.points > 0:
                main_card_bullets.append(f"{comp.name}: {comp.evidence}")
        
        if not main_card_bullets:
            main_card_bullets.append("No significant technical signals detected yet.")

        cards = [
            {
                "title": f"Technical Setup: {pre_score.total}/12 Score",
                "severity": "info" if pre_score.total < 8 else "warning",
                "bullets": main_card_bullets[:3] 
            }
        ]

        return InsightResponse(
            insight_version="v1.0-fallback",
            state="ready" if not missing_inputs else "insufficient_data",
            allocation_band="partial" if pre_score.total >= 8 else "skip", # Simplified logic
            pre_score=pre_score,
            derived=derived,
            insight_cards=cards,
            checklist_prompts=[
                {"id": "q1_earnings", "text": "Is the dip primarily macro/sector‑driven (not company‑specific)?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q2_balance_sheet", "text": "Are revenue and profit broadly intact in the latest results?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q3_moat", "text": "Any negative guidance or key mgmt exits recently?", "scoring_rule": "+2 yes / 0 unsure / -2 no"},
                {"id": "q4_management", "text": "Is the stock near horizontal support you recognize?", "scoring_rule": "+2 yes / 0 unsure / 0 no"}
            ],
            next_required_inputs=missing_inputs,
            disclaimer="Educational only. Not investment advice."
        )

    def generate_fundamentals_suggestions(
        self,
        symbol: str,
        features: Dict[str, Any]
    ):
        """
        Generate grounded fundamentals suggestions using Gemini with Google Search.
        
        Args:
            symbol: Stock symbol (e.g., AXISBANK.NS)
            features: Technical features dict containing:
                - dip_pct: Percentage dip from 52-week high
                - sector_move_pct: Sector benchmark movement
                - breadth_down_pct: Market breadth (% stocks down)
                - rsi: RSI indicator value
                - macd: MACD histogram signal
                - near_sma200: Boolean, price near 200-day SMA
                - support_zone: List of support price levels
        
        Returns:
            FundamentalsSuggestionResponse with grounded suggestions
        """
        from app.fundamentals_models import FundamentalsSuggestionResponse
        from datetime import datetime
        
        if not self.grounded_model:
            logger.error("Grounded model not configured. Cannot generate fundamentals suggestions.")
            raise ValueError("Grounded model not configured. Please set GEMINI_API_KEY.")
        
        prompt = self._construct_fundamentals_prompt(symbol, features)
        logger.info(f"Generating grounded fundamentals suggestions for {symbol}...")
        
        try:
            response = self.grounded_model.generate_content(prompt)
            logger.info(f"Received grounded response for {symbol}.")
            
            # Parse and validate JSON
            result = FundamentalsSuggestionResponse.model_validate_json(response.text)
            
            # Add metadata
            result.generated_at = datetime.now().isoformat()
            result.cache_key = f"fundamentals:{symbol}:{datetime.now().strftime('%Y%m%d%H%M')}"
            
            return result
            
        except Exception as e:
            logger.error(f"Fundamentals suggestion generation failed for {symbol}: {e}", exc_info=True)
            raise e
    
    def _construct_fundamentals_prompt(
        self,
        symbol: str,
        features: Dict[str, Any]
    ) -> str:
        """
        Construct prompt for fundamentals suggestions with explicit JSON schema.
        Uses Google Search grounding to fetch recent news, filings, and analyst reports.
        """
        from app.fundamentals_models import FundamentalsSuggestionResponse
        
        # Get JSON schema
        schema = FundamentalsSuggestionResponse.model_json_schema()
        schema_str = json.dumps(schema, indent=2)
        
        system_instruction = f"""
You are a compliance-aware fundamentals analyst for the DipLens app. Your job is to help users evaluate whether a stock dip is worth investigating.

CRITICAL RULES:
1. Ground EVERY factual claim in citations from Google Search
2. If insufficient evidence exists, answer "Unsure" or "Unknown" and explain the gap
3. Output ONLY valid JSON matching this exact schema:

{schema_str}

4. For each question (Q1-Q4):
   - Provide 2-3 evidence-based reasons
   - Include 1-3 source citations with URLs, titles, and publish dates
   - Assign confidence: High (≥2 recent, consistent sources), Medium (some evidence), Low (sparse/stale)
5. For Q1 and Q3, prefer sources published within the last 7 days
6. NEVER use "buy", "sell", "price target", or "guarantee" in any text
7. Summary should be 3-5 sentences tying Q1-Q4 together, highlighting uncertainties

"""
        
        user_content = f"""
Analyze {symbol} for fundamentals checklist:

TECHNICAL CONTEXT:
- Dip: {features.get('dip_pct', 0):.1f}% from 52-week high
- Sector move: {features.get('sector_move_pct', 0):.1f}%
- Market breadth (% down): {features.get('breadth_down_pct', 50)}%
- RSI: {features.get('rsi', 50):.0f}
- MACD: {features.get('macd', 'neutral')}
- Near 200-DMA: {features.get('near_sma200', False)}
- Support zone: {features.get('support_zone', [])}

QUESTIONS TO ANSWER:

Q1 - Dip Cause:
Is the dip primarily macro/sector-driven (not company-specific)?
- Search for: recent news on {symbol}, sector performance, market trends
- Look for: company-specific negatives vs broad market sell-off
- Answer: "Macro" | "Sector" | "CompanySpecific" | "Unknown"

Q2 - Earnings Resilience:
Are revenue and profit broadly intact in latest results?
- Search for: latest earnings report for {symbol}, revenue growth, profit margins
- Look for: YoY/QoQ revenue and profit trends
- Answer: "Yes" | "No" | "Unsure"

Q3 - Management/Guidance:
Any negative guidance or key management exits recently?
- Search for: management changes at {symbol}, guidance updates, corporate announcements
- Look for: CEO/CFO exits, guidance cuts, restructuring
- Answer: "NoneObserved" | "NegativeObserved" | "Unsure"

Q4 - Support Level:
Is price near a recognized support zone?
- Technical context shows support zone around {features.get('support_zone', [])}
- Search for: analyst price targets for {symbol}, historical support levels
- Answer: "LikelySupport" | "NotNear" | "Unsure"

Generate the complete JSON response now.
"""
        
        return system_instruction + "\n\n" + user_content

