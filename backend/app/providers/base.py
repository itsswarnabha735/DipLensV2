from abc import ABC, abstractmethod
from typing import List, Dict
from app.models import Bar


class DataProvider(ABC):
    """Base interface for market data providers"""
    
    @abstractmethod
    def get_bars(
        self, 
        symbol: str, 
        interval: str, 
        lookback: str
    ) -> List[Bar]:
        """
        Fetch OHLCV bars for a symbol
        
        Args:
            symbol: Ticker symbol (e.g., RELIANCE.NS)
            interval: Time interval (1m, 5m, 15m, 1h, 1d)
            lookback: Lookback period (1d, 5d, 1mo, etc.)
        
        Returns:
            List of normalized Bar objects
        """
        pass
    
    @abstractmethod
    def get_constraints(self) -> Dict:
        """
        Get provider-specific constraints
        
        Returns:
            Dictionary with limits and constraints
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
