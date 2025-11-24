"""
Mock Data Provider for Development

Generates realistic OHLCV data for testing when Yahoo Finance is unavailable.
"""

import random
from typing import List, Dict
from datetime import datetime, timedelta, timezone
from app.providers.base import DataProvider
from app.models import Bar
import numpy as np


class MockDataProvider(DataProvider):
    """Mock data provider that generates realistic stock data"""
    
    @property
    def name(self) -> str:
        return "mock"
    
    def _generate_realistic_ohlcv(
        self, 
        symbol: str, 
        base_price: float,
        num_bars: int,
        interval_minutes: int = 1440  # Default to daily
    ) -> List[Bar]:
        """Generate realistic OHLCV data with trends and volatility"""
        
        bars = []
        current_price = base_price
        current_time = datetime.now(timezone.utc) - timedelta(minutes=interval_minutes * num_bars)
        
        # Use symbol hash for reproducible randomness
        seed = hash(symbol) % 10000
        rng = np.random.RandomState(seed)
        
        # Generate trend and volatility based on symbol
        daily_volatility = 0.02 + rng.random() * 0.01  # 2-3% daily volatility
        trend = (rng.random() - 0.5) * 0.001  # Small upward/downward trend
        
        for i in range(num_bars):
            # Add some trend and random walk
            price_change = rng.normal(trend, daily_volatility)
            current_price *= (1 + price_change)
            
            # Generate OHLC from close
            daily_range = current_price * (0.01 + rng.random() * 0.02)  # 1-3% intraday range
            
            high = current_price + rng.random() * daily_range * 0.7
            low = current_price - rng.random() * daily_range * 0.7
            open_price = low + rng.random() * (high - low)
            close = current_price
            
            # Ensure OHLC relationships are valid
            high = max(high, open_price, close)
            low = min(low, open_price, close)
            
            # Generate volume (higher volume on larger price moves)
            base_volume = 1_000_000 + rng.randint(0, 500_000)
            volume_multiplier = 1 + abs(price_change) * 10
            volume = int(base_volume * volume_multiplier)
            
            bar = Bar(
                t=current_time.isoformat(),
                o=round(open_price, 2),
                h=round(high, 2),
                l=round(low, 2),
                c=round(close, 2),
                v=volume
            )
            bars.append(bar)
            
            current_time += timedelta(minutes=interval_minutes)
        
        return bars
    
    def _get_base_price(self, symbol: str) -> float:
        """Get a base price for a symbol based on its name"""
        # Use known prices for common stocks
        known_prices = {
            'AAPL': 180.0,
            'RELIANCE.NS': 2500.0,
            'TCS.NS': 3500.0,
            'INFY.NS': 1500.0,
            'HDFC.NS': 1600.0,
            'ICICIBANK.NS': 950.0,
            'LT.NS': 3200.0,
            'ETERNAL.NS': 450.0,
            'PAYTM.NS': 650.0,
        }
        
        # Return known price or generate one based on symbol hash
        if symbol in known_prices:
            return known_prices[symbol]
        
        # Generate price based on symbol hash
        seed = hash(symbol) % 10000
        return 100 + (seed % 900)  # Price between 100-1000
    
    def _parse_lookback_to_bars( self, lookback: str, interval: str) -> int:
        """Convert lookback period to number of bars"""
        # Map interval to minutes
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 1440,
        }.get(interval, 1440)
        
        # Map lookback to total minutes
        lookback_minutes = {
            '1d': 1440,
            '5d': 1440 * 5,
            '1mo': 1440 * 30,
            '3mo': 1440 * 90,
            '6mo': 1440 * 180,
            '1y': 1440 * 365,
            '2y': 1440 * 730,
        }.get(lookback, 1440 * 30)
        
        # Calculate number of bars
        num_bars = lookback_minutes // interval_minutes
        
        # Cap at reasonable limits
        return min(num_bars, 1000)
    
    def get_bars(self, symbol: str, interval: str, lookback: str) -> List[Bar]:
        """Generate mock bars for a symbol"""
        base_price = self._get_base_price(symbol)
        num_bars = self._parse_lookback_to_bars(lookback, interval)
        
        interval_minutes = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '1d': 1440,
        }.get(interval, 1440)
        
        return self._generate_realistic_ohlcv(symbol, base_price, num_bars, interval_minutes)
    
    def get_bars_batch(self, symbols: List[str], interval: str, lookback: str) -> Dict[str, List[Bar]]:
        """Generate mock bars for multiple symbols"""
        results = {}
        for symbol in symbols:
            results[symbol] = self.get_bars(symbol, interval, lookback)
        return results
    
    def get_constraints(self) -> Dict:
        """Get mock provider constraints"""
        return {
            "provider": "mock",
            "unlimited": True,
            "note": "Mock data for development/testing only"
        }


# Global mock provider instance
mock_provider = MockDataProvider()
