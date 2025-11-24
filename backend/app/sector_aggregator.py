"""
Sector Aggregation Engine

Computes sector-level synthetic lines and breadth metrics from constituent stocks.
"""

import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime
from app.indicators import IndicatorEngine
from app.dip_engine import DipEngine


@dataclass
class SectorSnapshot:
    """Sector state at a point in time"""
    sector_id: str
    sector_name: str
    ts: str  # ISO timestamp
    dip_pct: float
    rsi40_breadth: float      # % with RSI < 40
    sma200_up_breadth: float  # % at/above SMA200
    lowerband_breadth: float  # % within +2% of lower Bollinger
    constituents_count: int
    avg_volume_ratio: float   # Average volume vs 20-day avg


class SectorAggregator:
    """Aggregates constituent data into sector-level metrics"""
    
    @staticmethod
    def calculate_weighted_return(
        prices: List[float],
        weights: List[float]
    ) -> float:
        """
        Calculate weighted normalized return
        
        Args:
            prices: List of current prices
            weights: List of weight hints (must sum to 1.0)
            
        Returns:
            Weighted return percentage
        """
        if not prices or not weights or len(prices) != len(weights):
            return 0.0
        
        # Normalize weights if they don't sum to 1
        weight_sum = sum(weights)
        if weight_sum > 0:
            weights = [w / weight_sum for w in weights]
        
        # Simple weighted average (can be enhanced with returns calculation)
        weighted_avg = sum(p * w for p, w in zip(prices, weights))
        
        return weighted_avg
    
    @staticmethod
    def calculate_rsi40_breadth(rsi_values: List[Optional[float]]) -> float:
        """
        Calculate percentage of stocks with RSI < 40
        
        Args:
            rsi_values: List of RSI values (None for unavailable)
            
        Returns:
            Percentage (0-1) of stocks with RSI < 40
        """
        valid_values = [rsi for rsi in rsi_values if rsi is not None]
        
        if not valid_values:
            return 0.0
        
        below_40 = sum(1 for rsi in valid_values if rsi < 40)
        return below_40 / len(valid_values)
    
    @staticmethod
    def calculate_sma200_up_breadth(
        current_prices: List[float],
        sma200_values: List[Optional[float]]
    ) -> float:
        """
        Calculate percentage of stocks at or above SMA200
        
        Args:
            current_prices: List of current prices
            sma200_values: List of SMA200 values
            
        Returns:
            Percentage (0-1) of stocks above SMA200
        """
        if len(current_prices) != len(sma200_values):
            return 0.0
        
        valid_pairs = [
            (price, sma) 
            for price, sma in zip(current_prices, sma200_values) 
            if sma is not None and price > 0
        ]
        
        if not valid_pairs:
            return 0.0
        
        above_sma = sum(1 for price, sma in valid_pairs if price >= sma)
        return above_sma / len(valid_pairs)
    
    @staticmethod
    def calculate_lowerband_breadth(
        current_prices: List[float],
        bollinger_bands: List[Optional[Dict[str, float]]]
    ) -> float:
        """
        Calculate percentage of stocks within +2% of lower Bollinger band
        
        Args:
            current_prices: List of current prices
            bollinger_bands: List of Bollinger band dicts with 'lower' key
            
        Returns:
            Percentage (0-1) of stocks near lower band
        """
        if len(current_prices) != len(bollinger_bands):
            return 0.0
        
        valid_pairs = [
            (price, bb) 
            for price, bb in zip(current_prices, bollinger_bands) 
            if bb is not None and 'lower' in bb and price > 0
        ]
        
        if not valid_pairs:
            return 0.0
        
        near_lower = 0
        for price, bb in valid_pairs:
            lower = bb['lower']
            threshold = lower * 1.02  # Within +2% of lower band
            if price <= threshold:
                near_lower += 1
        
        return near_lower / len(valid_pairs)
    
    @staticmethod
    def calculate_avg_volume_ratio(
        current_volumes: List[int],
        avg_volumes: List[Optional[float]]
    ) -> float:
        """
        Calculate average volume ratio (current vs 20-day avg)
        
        Args:
            current_volumes: List of current volumes
            avg_volumes: List of 20-day average volumes
            
        Returns:
            Average volume ratio
        """
        if len(current_volumes) != len(avg_volumes):
            return 1.0
        
        valid_pairs = [
            (curr, avg) 
            for curr, avg in zip(current_volumes, avg_volumes) 
            if avg is not None and avg > 0
        ]
        
        if not valid_pairs:
            return 1.0
        
        ratios = [curr / avg for curr, avg in valid_pairs]
        return float(np.mean(ratios))
    
    @staticmethod
    def compute_sector_snapshot(
        sector_id: str,
        sector_name: str,
        member_data: List[Dict],
        weights: Optional[List[float]] = None
    ) -> SectorSnapshot:
        """
        Compute comprehensive sector snapshot from member data
        
        Args:
            sector_id: Sector identifier
            sector_name: Sector display name
            member_data: List of dicts with member indicators and prices
            weights: Optional weight hints for constituents
            
        Returns:
            SectorSnapshot object
        """
        n = len(member_data)
        
        if n == 0:
            return SectorSnapshot(
                sector_id=sector_id,
                sector_name=sector_name,
                ts=datetime.utcnow().isoformat(),
                dip_pct=0.0,
                rsi40_breadth=0.0,
                sma200_up_breadth=0.0,
                lowerband_breadth=0.0,
                constituents_count=0,
                avg_volume_ratio=1.0
            )
        
        # Extract data from members
        current_prices = [m.get('current_price', 0) for m in member_data]
        rsi_values = [m.get('rsi') for m in member_data]
        sma200_values = [m.get('sma200') for m in member_data]
        bollinger_bands = [m.get('bollinger') for m in member_data]
        current_volumes = [m.get('current_volume', 0) for m in member_data]
        avg_volumes = [m.get('volume_avg') for m in member_data]
        dip_pcts = [m.get('dip_pct', 0) for m in member_data]
        
        # Use equal weights if not provided
        if not weights or len(weights) != n:
            weights = [1.0 / n] * n
        
        # Calculate breadth metrics
        rsi40_breadth = SectorAggregator.calculate_rsi40_breadth(rsi_values)
        sma200_up_breadth = SectorAggregator.calculate_sma200_up_breadth(
            current_prices, sma200_values
        )
        lowerband_breadth = SectorAggregator.calculate_lowerband_breadth(
            current_prices, bollinger_bands
        )
        avg_volume_ratio = SectorAggregator.calculate_avg_volume_ratio(
            current_volumes, avg_volumes
        )
        
        # Calculate weighted average dip
        weighted_dip = sum(dip * w for dip, w in zip(dip_pcts, weights))
        
        return SectorSnapshot(
            sector_id=sector_id,
            sector_name=sector_name,
            ts=datetime.utcnow().isoformat(),
            dip_pct=round(weighted_dip, 2),
            rsi40_breadth=round(rsi40_breadth, 4),
            sma200_up_breadth=round(sma200_up_breadth, 4),
            lowerband_breadth=round(lowerband_breadth, 4),
            constituents_count=n,
            avg_volume_ratio=round(avg_volume_ratio, 2)
        )
