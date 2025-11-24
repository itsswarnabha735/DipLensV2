import os
import time
import random

# Configure SSL certificates for curl_cffi (used by yfinance 0.2.66+)
try:
    import certifi
    os.environ['CURL_CA_BUNDLE'] = certifi.where()
    os.environ['SSL_CERT_FILE'] = certifi.where()
except ImportError:
    # Fallback: disable SSL verification if certifi is not available
    # WARNING: This should not be used in production
    os.environ['CURL_CA_BUNDLE'] = ''
    os.environ['SSL_CERT_FILE'] = ''

import yfinance as yf
from typing import List, Dict
from datetime import datetime, timezone
from app.providers.base import DataProvider
from app.models import Bar
import ssl
import urllib3
import requests

# DEVELOPMENT ONLY: Disable SSL verification to work around macOS certificate issues
# WARNING: This should not be used in production
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Monkeypatch requests to force verify=False and set User-Agent
_original_request = requests.Session.request

def _insecure_request(self, method, url, *args, **kwargs):
    kwargs['verify'] = False
    
    # Ensure headers exist
    if 'headers' not in kwargs:
        kwargs['headers'] = {}
        
    # Set browser-like User-Agent if not present
    if 'User-Agent' not in kwargs['headers']:
        kwargs['headers']['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        
    return _original_request(self, method, url, *args, **kwargs)

requests.Session.request = _insecure_request


class YahooFinanceProvider(DataProvider):
    """Yahoo Finance data provider using yfinance"""
    
    @property
    def name(self) -> str:
        return "yahoo"
    
    def _parse_period(self, lookback: str) -> str:
        """Convert lookback to yfinance period format"""
        # yfinance supports: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max
        lookback_map = {
            "1d": "1d",
            "5d": "5d",
            "1mo": "1mo",
            "3mo": "3mo",
            "6mo": "6mo",
            "1y": "1y",
        }
        return lookback_map.get(lookback, "1d")
    
    def _parse_interval(self, interval: str) -> str:
        """Validate and normalize interval"""
        # yfinance supports: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        valid_intervals = ["1m", "5m", "15m", "30m", "1h", "1d"]
        if interval not in valid_intervals:
            raise ValueError(f"Invalid interval: {interval}")
        return interval
    
    def get_bars(self, symbol: str, interval: str, lookback: str) -> List[Bar]:
        """
        Fetch bars from Yahoo Finance with automatic Alpha Vantage fallback
        
        Note: yfinance has limitations:
        - 1m data: max 7 days
        - Intraday data: max ~60 days
        - If Yahoo Finance fails, automatically tries Alpha Vantage
        """
        # Add small delay to avoid rate limiting
        time.sleep(0.5 + random.random() * 0.5)  # 0.5-1.0 second delay
        
        max_retries = 2  # Reduced retries since we have fallback
        yahoo_failed = False
        
        # OPTIMIZATION: Skip Yahoo entirely for Indian stocks (.NS)
        # Yahoo is unreliable/blocked for these, so go straight to NSE provider
        if symbol.endswith('.NS'):
            print(f"Skipping Yahoo for {symbol} (Indian stock), going straight to NSE...")
            yahoo_failed = True
        else:
            for attempt in range(max_retries):
                try:
                    period = self._parse_period(lookback)
                    interval_parsed = self._parse_interval(interval)
                    
                    ticker = yf.Ticker(symbol)
                    df = ticker.history(period=period, interval=interval_parsed)
                    
                    if df.empty:
                        yahoo_failed = True
                        break
                    
                    bars = self._process_dataframe(df)
                    if bars:  # Successfully got data
                        return bars
                    else:
                        yahoo_failed = True
                        break
                
                except Exception as e:
                    error_msg = str(e).lower()
                    logger.warning(f"Yahoo fetch failed for {symbol} (attempt {attempt+1}): {e}")
                    
                    # Treat ANY error as a potential reason to fail and retry/fallback
                    # especially "expecting value" (json error) or "no price data"
                    if attempt < max_retries - 1:
                        wait_time = 1 + attempt
                        time.sleep(wait_time)
                    else:
                        yahoo_failed = True
                        break
                    print(f"Yahoo error for {symbol}, retry {attempt + 1}/{max_retries}")
                    time.sleep(wait_time)
                else:
                    yahoo_failed = True
        
        
        # Try fallback providers if Yahoo failed
        if yahoo_failed:
            # For Indian stocks (.NS), try NSE provider first
            if symbol.endswith('.NS'):
                print(f"Yahoo Finance unavailable for {symbol}, trying NSE provider...")
                try:
                    from app.providers.nse import nse_provider
                    bars = nse_provider.get_bars(symbol, interval, lookback)
                    if bars:
                        print(f"✓ NSE provided {len(bars)} bars for {symbol}")
                        return bars
                except Exception as nse_error:
                    print(f"NSE provider failed for {symbol}: {nse_error}")
            
            # For US stocks (or if NSE failed), try Alpha Vantage
            print(f"Trying Alpha Vantage for {symbol}...")
            try:
                from app.providers.alphavantage import alphavantage_provider
                bars = alphavantage_provider.get_bars(symbol, interval, lookback)
                if bars:
                    print(f"✓ Alpha Vantage provided {len(bars)} bars for {symbol}")
                    return bars
            except Exception as av_error:
                print(f"Alpha Vantage also failed for {symbol}: {av_error}")
        
        return []
    
    def get_bars_batch(self, symbols: List[str], interval: str, lookback: str) -> Dict[str, List[Bar]]:
        """
        Fetch bars for multiple symbols in batch
        """
        results = {}
        if not symbols:
            return results
            
        try:
            period = self._parse_period(lookback)
            interval_parsed = self._parse_interval(interval)
            
            # yfinance download for batch
            # group_by='ticker' makes it easier to iterate
            df = yf.download(
                tickers=" ".join(symbols),
                period=period,
                interval=interval_parsed,
                group_by='ticker',
                threads=True,
                progress=False
            )
            
            if df.empty:
                return results
                
            # If only one symbol, structure is different (no top-level ticker index)
            if len(symbols) == 1:
                symbol = symbols[0]
                # Re-use single fetch logic or wrap
                results[symbol] = self._process_dataframe(df)
                return results
            
            # Process multi-index dataframe
            for symbol in symbols:
                try:
                    # Access data for specific ticker
                    # yfinance might drop symbols if no data, so check
                    if symbol in df.columns.levels[0]: # Check if symbol is in top level
                        symbol_df = df[symbol]
                        results[symbol] = self._process_dataframe(symbol_df)
                    else:
                        # Fallback or empty
                        results[symbol] = []
                except Exception as e:
                    print(f"Error processing batch data for {symbol}: {e}")
                    results[symbol] = []
                    
        except Exception as e:
            print(f"Batch download failed: {e}")
            # Fallback to sequential? Or just return empty
            
        return results

    def _process_dataframe(self, df) -> List[Bar]:
        """Helper to convert DF to Bars"""
        bars = []
        if df.empty:
            return bars
            
        for timestamp, row in df.iterrows():
            try:
                # Skip rows with NaN
                if row.isnull().any():
                    continue
                    
                # Convert timestamp
                if hasattr(timestamp, 'tz_localize'):
                    if timestamp.tz is None:
                        timestamp = timestamp.tz_localize('UTC')
                    else:
                        timestamp = timestamp.tz_convert('UTC')
                
                bar = Bar(
                    t=timestamp.isoformat(),
                    o=float(row['Open']),
                    h=float(row['High']),
                    l=float(row['Low']),
                    c=float(row['Close']),
                    v=int(row['Volume'])
                )
                bars.append(bar)
            except Exception:
                continue
        return bars

    def get_constraints(self) -> Dict:
        """Get Yahoo Finance constraints"""
        return {
            "provider": "yahoo",
            "intraday_1m_max_days": 7,
            "intraday_max_days": 60,
            "supported_intervals": ["1m", "5m", "15m", "30m", "1h", "1d"],
            "supported_lookbacks": ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
            "notes": "1m data limited to 7 days, intraday data limited to ~60 days"
        }


# Global provider instance
yahoo_provider = YahooFinanceProvider()
