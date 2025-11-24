"""
Candidate Ranking Engine

Ranks candidates for a sector based on Pre-Score and secondary factors.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass
from app.scoring_engine import PreScore

@dataclass
class RankedCandidate:
    """A ranked candidate with score and ranking details"""
    symbol: str
    rank: int
    pre_score: int
    reasons: List[str]
    flags: List[str]
    
    # Ranking metrics for debugging/transparency
    distance_to_sma200_pct: float
    distance_to_lower_band_pct: float
    adtv: float


class CandidateRanker:
    """Ranks candidates based on multi-factor criteria"""
    
    @staticmethod
    def calculate_ranking_score(
        pre_score: int,
        current_price: float,
        sma200: Optional[float],
        lower_band: Optional[float],
        adtv: float
    ) -> float:
        """
        Calculate a sortable score. Higher is better.
        
        Primary: Pre-Score (weighted heavily)
        Secondary: Proximity to SMA200 (if holding)
        Tertiary: Proximity to Lower Band
        Quaternary: Liquidity (log scale)
        """
        # Base score from Pre-Score (0-12) -> scaled to 1000-2200
        total_score = pre_score * 100.0
        
        # Secondary: Distance to SMA200 (closer is better if price >= SMA200)
        # If price < SMA200, it's resistance, so maybe less valuable? 
        # Requirement: "closer is better, if holding"
        if sma200 and current_price > 0:
            dist_pct = abs(current_price - sma200) / sma200
            # Cap distance penalty at 10%
            dist_factor = max(0, 0.10 - dist_pct) * 100  # 0-10 points
            if current_price >= sma200:
                total_score += dist_factor
        
        # Tertiary: Proximity to Lower Band (closer is better)
        if lower_band and current_price > 0:
            dist_pct = abs(current_price - lower_band) / lower_band
            # Cap distance penalty at 10%
            dist_factor = max(0, 0.10 - dist_pct) * 50  # 0-5 points
            total_score += dist_factor
            
        # Tiebreaker: ADTV (add tiny fraction)
        # 1M ADTV -> 0.000001 points
        total_score += (adtv / 1_000_000_000_000)
        
        return total_score

    @staticmethod
    def rank_candidates(
        candidates: List[Dict],
        limit: int = 12
    ) -> List[RankedCandidate]:
        """
        Rank a list of candidate dictionaries.
        
        Args:
            candidates: List of dicts containing:
                - symbol
                - pre_score (PreScore object)
                - current_price
                - indicators (dict with sma200, bollinger)
                - adtv
                
        Returns:
            List of RankedCandidate objects, sorted by rank
        """
        scored_candidates = []
        
        for cand in candidates:
            pre_score_obj: PreScore = cand.get('pre_score')
            if not pre_score_obj or pre_score_obj.pre_score == 0:
                continue
                
            current_price = cand.get('current_price', 0)
            indicators = cand.get('indicators', {})
            adtv = cand.get('adtv', 0)
            
            sma200 = indicators.get('sma200')
            bollinger = indicators.get('bollinger')
            lower_band = bollinger.get('lower') if bollinger else None
            
            # Calculate sort score
            sort_score = CandidateRanker.calculate_ranking_score(
                pre_score_obj.pre_score,
                current_price,
                sma200,
                lower_band,
                adtv
            )
            
            # Calculate display metrics
            dist_sma = 0.0
            if sma200 and current_price > 0:
                dist_sma = (current_price - sma200) / sma200 * 100
                
            dist_lower = 0.0
            if lower_band and current_price > 0:
                dist_lower = (current_price - lower_band) / lower_band * 100
            
            scored_candidates.append({
                'candidate': cand,
                'sort_score': sort_score,
                'metrics': {
                    'dist_sma': dist_sma,
                    'dist_lower': dist_lower
                }
            })
            
        # Sort by score descending
        scored_candidates.sort(key=lambda x: x['sort_score'], reverse=True)
        
        # Take top N
        top_candidates = scored_candidates[:limit]
        
        # Convert to RankedCandidate objects
        result = []
        for i, item in enumerate(top_candidates):
            cand = item['candidate']
            pre_score_obj = cand['pre_score']
            metrics = item['metrics']
            
            result.append(RankedCandidate(
                symbol=pre_score_obj.symbol,
                rank=i + 1,
                pre_score=pre_score_obj.pre_score,
                reasons=pre_score_obj.reasons,
                flags=pre_score_obj.flags,
                distance_to_sma200_pct=metrics['dist_sma'],
                distance_to_lower_band_pct=metrics['dist_lower'],
                adtv=cand.get('adtv', 0)
            ))
            
        return result
