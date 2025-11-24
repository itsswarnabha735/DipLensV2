import time
import requests
from typing import List, Dict, Optional
from app.providers.base import DataProvider
from app.models import Bar
from app.config import settings
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""
    
    def __init__(self, tokens_per_minute: int, daily_limit: int):
        self.tokens_per_minute = tokens_per_minute
        self.daily_limit = daily_limit
        self.tokens = tokens_per_minute
        self.daily_tokens = daily_limit
        self.last_refill = time.time()
        self.daily_refill = time.time()
        
    def consume(self) -> bool:
        """Try to consume a token. Returns True if successful."""
        now = time.time()
        
        # Refill per-minute tokens
        elapsed = now - self.last_refill
        if elapsed >= 60:
            self.tokens = self.tokens_per_minute
            self.last_refill = now
        
        # Refill daily tokens
        daily_elapsed = now - self.daily_refill
        if daily_elapsed >= 86400:  # 24 hours
            self.daily_tokens = self.daily_limit
            self.daily_refill = now
        
        # Check if we have tokens
        if self.tokens > 0 and self.daily_tokens > 0:
            self.tokens -= 1
            self.daily_tokens -= 1
            return True
        return False
    
    def get_stats(self) -> Dict:
        """Get current token bucket stats"""
        return {
            "tokens_remaining": self.tokens,
            "tokens_per_minute": self.tokens_per_minute,
            "daily_tokens_remaining": self.daily_tokens,
            "daily_limit": self.daily_limit
        }


class AlphaVantageProvider(DataProvider):
    """Alpha Vantage data provider as fallback"""
    
    def __init__(self):
        self.api_key = settings.alpha_vantage_api_key
        self.base_url = "https://www.alphavantage.co/query"
        self.bucket = TokenBucket(tokens_per_minute=5, daily_limit=500)
        
    @property
    def name(self) -> str:
        return "alphavantage"
    
    def _convert_symbol(self, symbol: str) -> str:
        """Convert NSE/BSE symbol to Alpha Vantage format"""
        # Alpha Vantage doesn't directly support NSE with .NS suffix
        # For Indian stocks, need to use different format or BSE
        # For now, just remove the suffix
        if symbol.endswith('.NS') or symbol.endswith('.BSE'):
            return symbol.split('.')[0]
        return symbol
    
    def _parse_interval(self, interval: str) -> str:
        """Convert interval to Alpha Vantage format"""
        interval_map = {
            "1m": "1min",
            "5m": "5min",
            "15m": "15min",
            "30m": "30min",
            "1h": "60min",
            "1d": "daily"
        }
        return interval_map.get(interval, "daily")
    
    def get_bars(self, symbol: str, interval: str, lookback: str) -> List[Bar]:
        """
        Fetch bars from Alpha Vantage
        
        Note: Alpha Vantage has strict rate limits:
        - 5 requests per minute
        - 500 requests per day (free tier)
        - Indian stocks (.NS, .BSE) are NOT supported in free tier
        """
        # Check if this is an Indian stock
        if symbol.endswith('.NS') or symbol.endswith('.BSE'):
            logger.warning(f"Alpha Vantage free tier doesn't support Indian stocks: {symbol}")
            logger.info(f"Suggestion: Try US stocks (AAPL, MSFT, GOOGL) or upgrade to Alpha Vantage premium")
            return []  # Return empty to avoid wasting API quota
        
        # Check token bucket
        if not self.bucket.consume():
            logger.warning("Alpha Vantage rate limit exceeded")
            raise Exception("Rate limit exceeded. Try again later.")
        
        try:
            av_symbol = self._convert_symbol(symbol)
            av_interval = self._parse_interval(interval)
            
            # Choose appropriate function
            if interval == "1d":
                function = "TIME_SERIES_DAILY"
                params = {
                    "function": function,
                    "symbol": av_symbol,
                    "apikey": self.api_key,
                    "outputsize": "full"  # Get full dataset (up to 20 years daily)
                }
            else:
                function = "TIME_SERIES_INTRADAY"
                params = {
                    "function": function,
                    "symbol": av_symbol,
                    "interval": av_interval,
                    "apikey": self.api_key,
                    "outputsize": "full"  # Get full dataset for intraday
                }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check for API error messages
            if "Error Message" in data:
                logger.error(f"Alpha Vantage error: {data['Error Message']}")
                raise Exception(data["Error Message"])
            
            if "Note" in data:
                logger.warning(f"Alpha Vantage note: {data['Note']}")
                raise Exception("API rate limit reached")
            
            # Parse time series data
            bars = []
            time_series_key = None
            
            # Find the time series key
            for key in data.keys():
                if "Time Series" in key:
                    time_series_key = key
                    break
            
            if not time_series_key or time_series_key not in data:
                logger.warning(f"No time series data for {symbol}")
                return []
            
            time_series = data[time_series_key]
            
            for timestamp_str, values in time_series.items():
                try:
                    # Parse timestamp
                    timestamp = datetime.fromisoformat(timestamp_str)
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    bar = Bar(
                        t=timestamp.isoformat(),
                        o=float(values.get("1. open", 0)),
                        h=float(values.get("2. high", 0)),
                        l=float(values.get("3. low", 0)),
                        c=float(values.get("4. close", 0)),
                        v=int(values.get("5. volume", 0))
                    )
                    bars.append(bar)
                except Exception as e:
                    logger.error(f"Error parsing bar data: {e}")
                    continue
            
            # Sort by timestamp (oldest first)
            bars.sort(key=lambda x: x.t)
            
            logger.info(f"Alpha Vantage returned {len(bars)} bars for {symbol}")
            return bars
            
        except requests.RequestException as e:
            logger.error(f"Alpha Vantage request failed: {e}")
            raise Exception(f"Failed to fetch data from Alpha Vantage: {str(e)}")
    
    def get_constraints(self) -> Dict:
        """Get Alpha Vantage constraints"""
        return {
            "provider": "alphavantage",
            "rate_limit_per_minute": 5,
            "daily_limit": 500,
            "supported_intervals": ["1m", "5m", "15m", "30m", "1h", "1d"],
            "notes": "Free tier limited to 5 requests/min and 500/day",
            "token_stats": self.bucket.get_stats()
        }


# Global provider instance
alphavantage_provider = AlphaVantageProvider()
