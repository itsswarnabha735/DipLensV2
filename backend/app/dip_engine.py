"""
Dip Classification Engine

Tracks 52-week highs and classifies dips into severity categories.
Supports corporate action adjustments (splits, bonuses, dividends).
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from enum import Enum
from datetime import datetime, timedelta
from dataclasses import dataclass


class DipClass(str, Enum):
    """Dip severity classifications"""
    NONE = "none"           # < 3%
    MICRO = "micro"         # 3-5%
    MINOR = "minor"         # 5-8%
    MODERATE = "moderate"   # 8-12%
    SIGNIFICANT = "significant"  # 12-15%
    MAJOR = "major"         # 15-25%
    EXTREME = "extreme"     # > 25%


@dataclass
class DipAnalysis:
    """Result of dip analysis"""
    symbol: str
    current_price: float
    high_52w: float
    high_52w_date: Optional[str]
    dip_pct: float
    dip_class: DipClass
    days_from_high: Optional[int]


class DipEngine:
    """Engine for tracking 52-week highs and classifying dips"""
    
    @staticmethod
    def calculate_52w_high(highs: List[float], lookback_days: int = 365) -> float:
        """
        Calculate 52-week (or custom period) rolling high
        
        Args:
            highs: List of daily high prices
            lookback_days: Number of days to look back (default 365)
            
        Returns:
            Maximum high price in the period
        """
        if not highs:
            return 0.0
        
        # Use last N days or all available if less than N
        period_highs = highs[-lookback_days:] if len(highs) > lookback_days else highs
        return float(np.max(period_highs))
    
    @staticmethod
    def classify_dip(current_price: float, high_52w: float) -> Tuple[float, DipClass]:
        """
        Classify dip severity based on distance from 52-week high
        
        Args:
            current_price: Current stock price
            high_52w: 52-week high price
            
        Returns:
            Tuple of (dip_percentage, DipClass)
        """
        if high_52w == 0:
            return (0.0, DipClass.NONE)
        
        dip_pct = ((high_52w - current_price) / high_52w) * 100
        
        if dip_pct < 0:
            # Price is above 52w high (new high)
            return (0.0, DipClass.NONE)
        elif dip_pct < 3:
            return (dip_pct, DipClass.NONE)
        elif dip_pct < 5:
            return (dip_pct, DipClass.MICRO)
        elif dip_pct < 8:
            return (dip_pct, DipClass.MINOR)
        elif dip_pct < 12:
            return (dip_pct, DipClass.MODERATE)
        elif dip_pct < 15:
            return (dip_pct, DipClass.SIGNIFICANT)
        elif dip_pct < 25:
            return (dip_pct, DipClass.MAJOR)
        else:
            return (dip_pct, DipClass.EXTREME)
    
    @staticmethod
    def find_high_date(
        highs: List[float], 
        dates: List[str], 
        high_52w: float
    ) -> Optional[Tuple[str, int]]:
        """
        Find the date when 52-week high occurred
        
        Args:
            highs: List of high prices
            dates: List of corresponding dates (ISO format)
            high_52w: The 52-week high value
            
        Returns:
            Tuple of (date_string, days_ago) or None
        """
        if not highs or not dates or len(highs) != len(dates):
            return None
        
        try:
            # Find index of 52w high (last occurrence if multiple)
            high_indices = [i for i, h in enumerate(highs) if abs(h - high_52w) < 0.01]
            
            if not high_indices:
                return None
            
            # Get the most recent occurrence
            high_idx = high_indices[-1]
            high_date = dates[high_idx]
            
            # Calculate days ago
            days_ago = len(highs) - high_idx - 1
            
            return (high_date, days_ago)
        except Exception:
            return None
    
    @staticmethod
    def analyze_dip(
        symbol: str,
        closes: List[float],
        highs: List[float],
        dates: Optional[List[str]] = None,
        lookback_days: int = 365
    ) -> DipAnalysis:
        """
        Perform complete dip analysis for a symbol
        
        Args:
            symbol: Stock symbol
            closes: List of closing prices
            highs: List of high prices
            dates: Optional list of dates (ISO format)
            lookback_days: Rolling window (default 365)
            
        Returns:
            DipAnalysis object with complete dip information
        """
        if not closes or not highs:
            return DipAnalysis(
                symbol=symbol,
                current_price=0.0,
                high_52w=0.0,
                high_52w_date=None,
                dip_pct=0.0,
                dip_class=DipClass.NONE,
                days_from_high=None
            )
        
        current_price = closes[-1]
        high_52w = DipEngine.calculate_52w_high(highs, lookback_days)
        dip_pct, dip_class = DipEngine.classify_dip(current_price, high_52w)
        
        # Find when the high occurred
        high_date = None
        days_from_high = None
        
        if dates:
            result = DipEngine.find_high_date(highs, dates, high_52w)
            if result:
                high_date, days_from_high = result
        
        return DipAnalysis(
            symbol=symbol,
            current_price=current_price,
            high_52w=high_52w,
            high_52w_date=high_date,
            dip_pct=round(dip_pct, 2),
            dip_class=dip_class,
            days_from_high=days_from_high
        )
    
    @staticmethod
    def adjust_for_split(prices: List[float], split_ratio: float) -> List[float]:
        """
        Adjust historical prices for stock split
        
        Args:
            prices: List of historical prices
            split_ratio: Split ratio (e.g., 2.0 for 2:1 split)
            
        Returns:
            Adjusted price list
        """
        return [p / split_ratio for p in prices]
    
    @staticmethod
    def adjust_for_bonus(prices: List[float], bonus_ratio: float) -> List[float]:
        """
        Adjust historical prices for bonus issue
        
        Args:
            prices: List of historical prices
            bonus_ratio: Bonus ratio (e.g., 1.5 for 1:2 bonus)
            
        Returns:
            Adjusted price list
        """
        return [p / bonus_ratio for p in prices]


class IncrementalDipTracker:
    """
    Maintains rolling 52-week high state for incremental updates
    Useful for streaming/real-time data
    """
    
    def __init__(self, symbol: str, lookback_days: int = 365):
        self.symbol = symbol
        self.lookback_days = lookback_days
        self.highs: List[float] = []
        self.closes: List[float] = []
        self.dates: List[str] = []
        self.current_52w_high: float = 0.0
    
    def add_bar(self, close: float, high: float, date: Optional[str] = None):
        """Add a new bar and update rolling high"""
        self.closes.append(close)
        self.highs.append(high)
        
        if date:
            self.dates.append(date)
        
        # Keep only necessary history
        if len(self.highs) > self.lookback_days:
            self.highs = self.highs[-self.lookback_days:]
            self.closes = self.closes[-self.lookback_days:]
            if self.dates:
                self.dates = self.dates[-self.lookback_days:]
        
        # Update 52w high
        self.current_52w_high = DipEngine.calculate_52w_high(self.highs, self.lookback_days)
    
    def get_current_analysis(self) -> DipAnalysis:
        """Get current dip analysis"""
        return DipEngine.analyze_dip(
            self.symbol,
            self.closes,
            self.highs,
            self.dates if self.dates else None,
            self.lookback_days
        )
    
    def is_new_high(self) -> bool:
        """Check if current price is at a new 52-week high"""
        if not self.closes or not self.highs:
            return False
        
        current = self.closes[-1]
        return current >= self.current_52w_high
