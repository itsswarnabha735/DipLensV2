"""
Indicator Calculation Engine

Provides vectorized technical indicator calculations with incremental update support.
All indicators use numpy/pandas for performance.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class IndicatorEngine:
    """Core indicator calculation engine with streaming support"""
    
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> Optional[float]:
        """
        Calculate RSI (Relative Strength Index)
        
        Args:
            closes: List of closing prices
            period: RSI period (default 14)
            
        Returns:
            Current RSI value (0-100) or None if insufficient data
        """
        if len(closes) < period + 1:
            return None
        
        closes_arr = np.array(closes)
        deltas = np.diff(closes_arr)
        
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        # Use EMA for gains and losses
        avg_gain = pd.Series(gains).ewm(span=period, adjust=False).mean().iloc[-1]
        avg_loss = pd.Series(losses).ewm(span=period, adjust=False).mean().iloc[-1]
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
    
    @staticmethod
    def calculate_macd(
        closes: List[float], 
        fast: int = 12, 
        slow: int = 26, 
        signal: int = 9
    ) -> Optional[Dict[str, float]]:
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            closes: List of closing prices
            fast: Fast EMA period (default 12)
            slow: Slow EMA period (default 26)
            signal: Signal line period (default 9)
            
        Returns:
            Dict with macd, signal, histogram or None if insufficient data
        """
        if len(closes) < slow + signal:
            return None
        
        closes_series = pd.Series(closes)
        
        ema_fast = closes_series.ewm(span=fast, adjust=False).mean()
        ema_slow = closes_series.ewm(span=slow, adjust=False).mean()
        
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return {
            "macd": float(macd_line.iloc[-1]),
            "signal": float(signal_line.iloc[-1]),
            "histogram": float(histogram.iloc[-1])
        }
    
    @staticmethod
    def calculate_sma(closes: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average
        
        Args:
            closes: List of closing prices
            period: SMA period
            
        Returns:
            Current SMA value or None if insufficient data
        """
        if len(closes) < period:
            return None
        
        return float(np.mean(closes[-period:]))
    
    @staticmethod
    def calculate_bollinger_bands(
        closes: List[float], 
        period: int = 20, 
        std_dev: float = 2.0
    ) -> Optional[Dict[str, float]]:
        """
        Calculate Bollinger Bands
        
        Args:
            closes: List of closing prices
            period: Moving average period (default 20)
            std_dev: Standard deviation multiplier (default 2.0)
            
        Returns:
            Dict with upper, middle, lower bands or None if insufficient data
        """
        if len(closes) < period:
            return None
        
        closes_arr = np.array(closes[-period:])
        
        middle_band = np.mean(closes_arr)
        std = np.std(closes_arr)
        
        upper_band = middle_band + (std_dev * std)
        lower_band = middle_band - (std_dev * std)
        
        return {
            "upper": float(upper_band),
            "middle": float(middle_band),
            "lower": float(lower_band)
        }
    
    @staticmethod
    def calculate_volume_avg(volumes: List[int], period: int = 20) -> Optional[float]:
        """
        Calculate Average Volume
        
        Args:
            volumes: List of volume values
            period: Average period (default 20)
            
        Returns:
            Average volume or None if insufficient data
        """
        if len(volumes) < period:
            return None
        
        return float(np.mean(volumes[-period:]))
    
    @staticmethod
    def calculate_all_indicators(
        closes: List[float],
        volumes: List[int],
        highs: Optional[List[float]] = None,
        lows: Optional[List[float]] = None
    ) -> Dict[str, any]:
        """
        Calculate all indicators at once for efficiency
        
        Args:
            closes: List of closing prices
            volumes: List of volumes
            highs: Optional list of high prices
            lows: Optional list of low prices
            
        Returns:
            Dict with all calculated indicators
        """
        result = {
            "rsi": IndicatorEngine.calculate_rsi(closes),
            "macd": IndicatorEngine.calculate_macd(closes),
            "sma50": IndicatorEngine.calculate_sma(closes, 50),
            "sma200": IndicatorEngine.calculate_sma(closes, 200),
            "bollinger": IndicatorEngine.calculate_bollinger_bands(closes),
            "volume_avg": IndicatorEngine.calculate_volume_avg(volumes)
        }
        
        return result


class IncrementalIndicators:
    """
    Maintains indicator state for incremental updates
    Useful for streaming data without full recalculation
    """
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.closes: List[float] = []
        self.volumes: List[int] = []
        self.highs: List[float] = []
        self.lows: List[float] = []
        self.last_update: Optional[datetime] = None
        
        # EMA state for incremental RSI
        self.rsi_avg_gain: Optional[float] = None
        self.rsi_avg_loss: Optional[float] = None
        
        # EMA state for incremental MACD
        self.ema_fast: Optional[float] = None
        self.ema_slow: Optional[float] = None
        self.macd_signal: Optional[float] = None
    
    def add_bar(self, close: float, volume: int, high: float, low: float):
        """Add a new bar and update indicators incrementally"""
        self.closes.append(close)
        self.volumes.append(volume)
        self.highs.append(high)
        self.lows.append(low)
        self.last_update = datetime.now()
        
        # Keep only necessary history (365 days for year-long indicators)
        max_len = 365
        if len(self.closes) > max_len:
            self.closes = self.closes[-max_len:]
            self.volumes = self.volumes[-max_len:]
            self.highs = self.highs[-max_len:]
            self.lows = self.lows[-max_len:]
    
    def get_current_indicators(self) -> Dict[str, any]:
        """Get current indicator values"""
        return IndicatorEngine.calculate_all_indicators(
            self.closes, 
            self.volumes,
            self.highs,
            self.lows
        )
    
    def update_incremental_rsi(self, new_close: float, period: int = 14) -> Optional[float]:
        """
        Incrementally update RSI using EMA state
        Much faster than recalculating from scratch
        """
        if len(self.closes) < 2:
            return None
        
        delta = new_close - self.closes[-1]
        gain = max(delta, 0)
        loss = max(-delta, 0)
        
        alpha = 1 / period
        
        if self.rsi_avg_gain is None:
            # Initialize on first calculation
            return IndicatorEngine.calculate_rsi(self.closes, period)
        
        # Incremental EMA update
        self.rsi_avg_gain = alpha * gain + (1 - alpha) * self.rsi_avg_gain
        self.rsi_avg_loss = alpha * loss + (1 - alpha) * self.rsi_avg_loss
        
        if self.rsi_avg_loss == 0:
            return 100.0
        
        rs = self.rsi_avg_gain / self.rsi_avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return float(rsi)
