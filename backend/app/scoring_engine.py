"""
Stock Scoring Engine

Scores individual stocks (Pre-Score 0-12) based on technical criteria.
Includes filtering for quality candidates.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from app.dip_engine import DipClass


@dataclass
class ScoringFilters:
    """Configurable filters for candidate stocks"""
    min_adtv: float = 1_000_000  # Min 20-day average daily traded value
    min_price: float = 50.0       # Min stock price
    exclude_asm: bool = True      # Exclude ASM/surveillance stocks
    

@dataclass
class PreScore:
    """Pre-score result for a stock"""
    symbol: str
    pre_score: int  # 0-12
    reasons: List[str]
    flags: List[str]  # Warnings like "volatility_risk"


class ScoringEngine:
    """Scores stocks based on technical criteria (0-12 scale)"""
    
    def __init__(self, filters: Optional[ScoringFilters] = None):
        self.filters = filters or ScoringFilters()
    
    def passes_filters(
        self,
        symbol: str,
        current_price: float,
        adtv: float,
        is_asm: bool = False
    ) -> tuple[bool, Optional[str]]:
        """
        Check if stock passes basic filters
        
        Returns:
            (passes, reason) - reason provided if failed
        """
        if current_price < self.filters.min_price:
            return (False, f"Price {current_price} below min {self.filters.min_price}")
        
        if adtv < self.filters.min_adtv:
            return (False, f"ADTV {adtv:,.0f} below min {self.filters.min_adtv:,.0f}")
        
        if self.filters.exclude_asm and is_asm:
            return (False, "Stock in ASM/surveillance")
        
        return (True, None)
    
    def calculate_pre_score(
        self,
        symbol: str,
        current_price: float,
        indicators: Dict,
        dip_analysis: Dict,
        volume_data: Dict
    ) -> PreScore:
        """
        Calculate pre-score (0-12) based on technical criteria
        
        Scoring rules (each +2):
        1. Dip 8-15%
        2. RSI 30-40 (or <30 with volatility flag)
        3. MACD bullish/rising histogram
        4. At/above or testing SMA200
        5. Near/touching lower Bollinger
        6. Volume spike ≥1.5× avg20
        
        Args:
            symbol: Stock symbol
            current_price: Current price
            indicators: Dict with rsi, macd, sma200, bollinger
            dip_analysis: Dict with dip_pct, dip_class
            volume_data: Dict with current_volume, volume_avg
            
        Returns:
            PreScore object
        """
        score = 0
        reasons = []
        flags = []
        
        # 1. Dip 8-15% (+2)
        dip_pct = dip_analysis.get('dip_pct', 0)
        if 8 <= dip_pct <= 15:
            score += 2
            reasons.append(f"Dip {dip_pct:.1f}% (+2)")
        
        # 2. RSI 30-40 (+2), or <30 with volatility flag
        rsi = indicators.get('rsi')
        if rsi is not None:
            if 30 <= rsi <= 40:
                score += 2
                reasons.append(f"RSI {rsi:.0f} (+2)")
            elif rsi < 30:
                score += 2
                reasons.append(f"RSI {rsi:.0f} (+2)")
                flags.append("volatility_risk")
        
        # 3. MACD bullish/rising histogram (+2)
        macd = indicators.get('macd')
        if macd and isinstance(macd, dict):
            histogram = macd.get('histogram', 0)
            macd_line = macd.get('macd', 0)
            signal = macd.get('signal', 0)
            
            # Bullish: MACD above signal, or rising histogram (positive)
            if macd_line > signal or histogram > 0:
                score += 2
                reasons.append("MACD ↑ (+2)")
        
        # 4. At/above or testing SMA200 (+2)
        sma200 = indicators.get('sma200')
        if sma200 is not None and current_price > 0:
            # "Testing" = within 3% below SMA200
            testing_range = sma200 * 0.97
            if current_price >= sma200 or current_price >= testing_range:
                score += 2
                if current_price >= sma200:
                    reasons.append("Holding SMA200 (+2)")
                else:
                    reasons.append("Testing SMA200 (+2)")
        
        # 5. Near/touching lower Bollinger (+2)
        bollinger = indicators.get('bollinger')
        if bollinger and isinstance(bollinger, dict):
            lower_band = bollinger.get('lower')
            if lower_band and current_price > 0:
                # Within +2% of lower band
                threshold = lower_band * 1.02
                if current_price <= threshold:
                    score += 2
                    reasons.append("Lower band touch (+2)")
        
        # 6. Volume spike ≥1.5× avg20 (+2)
        current_volume = volume_data.get('current_volume', 0)
        volume_avg = volume_data.get('volume_avg', 0)
        if volume_avg and volume_avg > 0:
            volume_ratio = current_volume / volume_avg
            if volume_ratio >= 1.5:
                score += 2
                reasons.append(f"Vol {volume_ratio:.1f}× (+2)")
        
        return PreScore(
            symbol=symbol,
            pre_score=score,
            reasons=reasons,
            flags=flags
        )
    
    def score_stock_batch(
        self,
        stocks_data: List[Dict]
    ) -> List[PreScore]:
        """
        Score multiple stocks at once
        
        Args:
            stocks_data: List of dicts with all required data per stock
            
        Returns:
            List of PreScore objects
        """
        results = []
        
        for stock in stocks_data:
            symbol = stock.get('symbol', 'UNKNOWN')
            current_price = stock.get('current_price', 0)
            adtv = stock.get('adtv', 0)
            is_asm = stock.get('is_asm', False)
            
            # Check filters
            passes, reason = self.passes_filters(symbol, current_price, adtv, is_asm)
            if not passes:
                # Return zero score for filtered stocks
                results.append(PreScore(
                    symbol=symbol,
                    pre_score=0,
                    reasons=[f"Filtered: {reason}"],
                    flags=["filtered"]
                ))
                continue
            
            # Calculate score
            pre_score = self.calculate_pre_score(
                symbol,
                current_price,
                stock.get('indicators', {}),
                stock.get('dip_analysis', {}),
                stock.get('volume_data', {})
            )
            results.append(pre_score)
        
        return results
