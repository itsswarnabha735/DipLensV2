from fastapi import APIRouter, HTTPException, Depends
from app.models import ChecklistRequest, FinalScoreResponse
from app.scoring_engine import ScoringEngine
from app.routers.suggestions import scoring_engine
from app.indicators import IndicatorEngine
from app.dip_engine import DipEngine
from app.providers.yahoo import yahoo_provider
from typing import Dict, Any
from dataclasses import asdict

router = APIRouter()

def get_scoring_engine_dep():
    return scoring_engine

def calculate_checklist_score(checklist: ChecklistRequest) -> int:
    score = 0
    
    # Q1: Strong earnings trajectory?
    if checklist.q1_earnings == "yes": score += 2
    elif checklist.q1_earnings == "no": score -= 2
    
    # Q2: Healthy balance sheet?
    if checklist.q2_balance_sheet == "yes": score += 2
    elif checklist.q2_balance_sheet == "no": score -= 2
    
    # Q3: Competitive moat?
    if checklist.q3_moat == "yes": score += 2
    elif checklist.q3_moat == "no": score -= 2
    
    # Q4: Management quality?
    if checklist.q4_management == "yes": score += 2
    # No penalty for management "no", just 0
    
    return score

def determine_band(total_score: int) -> str:
    if total_score >= 21: return "Very High Conviction"
    if total_score >= 15: return "High Conviction"
    if total_score >= 9: return "Medium Conviction"
    return "Low Conviction"

@router.post("/{symbol}/checklist", response_model=FinalScoreResponse)
async def submit_checklist(
    symbol: str, 
    checklist: ChecklistRequest,
    engine: ScoringEngine = Depends(get_scoring_engine_dep)
):
    try:
        # Fetch data
        bars = yahoo_provider.get_bars(symbol, "1d", "2y")
        
        if not bars:
             # Fallback if data fails completely
             pre_score = 0
             pre_score_result = None
        else:
            closes = [b.c for b in bars]
            highs = [b.h for b in bars]
            volumes = [b.v for b in bars]
            dates = [b.t for b in bars]
            
            # Calculate Indicators
            # IndicatorEngine.calculate_all_indicators expects (closes, volumes, highs, lows)
            # We passed highs twice in suggestions.py, let's follow that or fix it.
            # suggestions.py: IndicatorEngine.calculate_all_indicators(closes, volumes, highs, highs)
            # Let's use lows if available. Bar has l.
            lows = [b.l for b in bars]
            indicators = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, lows)
            
            # Calculate Dip
            dip_analysis = DipEngine.analyze_dip(symbol, closes, highs, dates)
            
            # Calculate Pre-Score
            # calculate_pre_score(self, symbol, current_price, indicators, dip_analysis, market_data)
            pre_score_result = engine.calculate_pre_score(
                symbol,
                closes[-1],
                indicators,
                asdict(dip_analysis),
                {'current_volume': volumes[-1], 'volume_avg': indicators.get('volume_avg')}
            )
            pre_score = pre_score_result.score
        
    except Exception as e:
        print(f"Error calculating pre-score for {symbol}: {e}")
        pre_score = 0
        pre_score_result = None

    # 2. Calculate Checklist Score
    checklist_score = calculate_checklist_score(checklist)
    
    # 3. Total Score
    total_score = pre_score + checklist_score
    
    # 4. Determine Band
    band = determine_band(total_score)
    
    return FinalScoreResponse(
        symbol=symbol,
        pre_score=pre_score,
        checklist_score=checklist_score,
        total_score=total_score,
        band=band,
        breakdown={
            "pre_score_reasons": pre_score_result.reasons if pre_score_result else [],
            "checklist": checklist.dict()
        }
    )
