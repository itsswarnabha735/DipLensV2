"""
NSE (National Stock Exchange of India) Data Provider

Uses nsepython library to fetch real market data for Indian stocks.
"""

from typing import List, Dict
import datetime as dt
from app.providers.base import DataProvider
from app.models import Bar
import logging

logger = logging.getLogger(__name__)

try:
    from nsepython import equity_history
    NSEPY_AVAILABLE = True
except ImportError:
    NSEPY_AVAILABLE = False
    logger.warning("nsepython not installed. Indian stock data will not be available.")


class NSEProvider(DataProvider):
    """NSE data provider for Indian stocks"""
    
    @property
    def name(self) -> str:
        return "nse"
    
    def _clean_symbol(self, symbol: str) -> str:
        """Remove .NS or .BSE suffix from symbol"""
        if symbol.endswith('.NS'):
            return symbol[:-3]
        elif symbol.endswith('.BSE'):
            return symbol[:-4]
        return symbol
    
    def _parse_lookback_days(self, lookback: str) -> int:
        """Convert lookback string to number of days"""
        lookback_map = {
           '1d': 1,
            '5d': 5,
            '1mo': 30,
            '3mo': 90,
            '6mo': 180,
            '1y': 365,
            '2y': 730,
        }
        return lookback_map.get(lookback, 365)
    
    def get_bars(self, symbol: str, interval: str, lookback: str) -> List[Bar]:
        """
        Fetch bars from NSE for Indian stocks
        
        Note: nsepython limitations:
        - Only supports daily data (interval parameter ignored)
        - Limited to NSE-listed stocks
        - May have delays in data availability
        """
        if not NSEPY_AVAILABLE:
            logger.error("nsepython not available. Cannot fetch Indian stock data.")
            return []
        
        # Only handle .NS stocks (NSE)
        if not symbol.endswith('.NS'):
            return []
        
        try:
            # Clean symbol
            clean_symbol = self._clean_symbol(symbol)
            
            # Calculate date range
            days = self._parse_lookback_days(lookback)
            end_date = dt.datetime.now()
            start_date = end_date - dt.timedelta(days=days)
            
            # Format dates for nsepython (dd-mm-yyyy)
            start_str = start_date.strftime('%d-%m-%Y')
            end_str = end_date.strftime('%d-%m-%Y')
            
            logger.info(f"Fetching NSE data for {clean_symbol} from {start_str} to {end_str}")
            
            # Use nsepython's equity_history function
            data = equity_history(clean_symbol, "EQ", start_str, end_str)
            
            if data is None or (hasattr(data, 'empty') and data.empty):
                logger.warning(f"No NSE data available for {clean_symbol}")
                return []
            
            # Convert DataFrame to Bar objects
            bars = []
            for _, row in data.iterrows():
                try:
                    # nsepython returns columns: CH_TIMESTAMP, CH_SYMBOL, CH_SERIES, etc.
                    date_str = row['CH_TIMESTAMP']  # Can be 'YYYY-MM-DD' or 'DD-MMM-YYYY'
                    
                    # Parse date - try both formats
                    try:
                        # Try YYYY-MM-DD first (newer format)
                        date_obj = dt.datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        # Try DD-MMM-YYYY format
                        date_obj = dt.datetime.strptime(date_str, '%d-%b-%Y')
                    
                    timestamp = date_obj.replace(tzinfo=dt.timezone.utc)
                    
                    bar = Bar(
                        t=timestamp.isoformat(),
                        o=float(row['CH_OPENING_PRICE']),
                        h=float(row['CH_TRADE_HIGH_PRICE']),
                        l=float(row['CH_TRADE_LOW_PRICE']),
                        c=float(row['CH_CLOSING_PRICE']),
                        v=int(row['CH_TOT_TRADED_QTY'])
                    )
                    bars.append(bar)
                except Exception as e:
                    logger.debug(f"Skipping row due to parse error: {e}")
                    continue
            
            # Sort by date (oldest first)
            bars.sort(key=lambda x: x.t)
            
            # Try to get the LATEST LIVE QUOTE to append/update
            try:
                from nsepython import nse_quote
                quote = nse_quote(clean_symbol)
                
                # Extract price and time
                current_price = quote.get('underlyingValue')
                timestamp_str = quote.get('fut_timestamp') # e.g. "21-Nov-2025 11:51:49"
                
                if current_price and timestamp_str:
                    # Parse timestamp
                    # Format: 21-Nov-2025 11:51:49
                    latest_dt = dt.datetime.strptime(timestamp_str, '%d-%b-%Y %H:%M:%S')
                    latest_ts = latest_dt.replace(tzinfo=dt.timezone.utc)
                    
                    # Create a bar for the latest quote
                    # We use the current price for OHLC because it's a snapshot
                    latest_bar = Bar(
                        t=latest_ts.isoformat(),
                        o=float(current_price),
                        h=float(current_price),
                        l=float(current_price),
                        c=float(current_price),
                        v=0 # Volume not always available in this field
                    )
                    
                    # Check if we should append or replace
                    if bars and bars[-1].t.split('T')[0] == latest_ts.isoformat().split('T')[0]:
                        # Same day, update the last bar's close to current price
                        # But keeping it as a separate "latest" point is often better for charts
                        # to show the specific time.
                        # Let's append it.
                        bars.append(latest_bar)
                    else:
                        bars.append(latest_bar)
                        
                    logger.info(f"Added live quote for {clean_symbol}: {current_price} at {timestamp_str}")
                    
            except Exception as e:
                logger.warning(f"Failed to fetch live quote for {clean_symbol}: {e}")
            
            logger.info(f"NSE returned {len(bars)} bars for {clean_symbol}")
            return bars
            
        except Exception as e:
            logger.error(f"NSE fetch failed for {symbol}: {e}")
            return []
    
    def get_constraints(self) -> Dict:
        """Get NSE provider constraints"""
        return {
            "provider": "nse",
            "supported_intervals": ["1d"],  # nsepython only supports daily data
            "supported_markets": ["NSE"],
            "notes": "Only supports NSE-listed stocks with .NS suffix. Daily data only.",
            "available": NSEPY_AVAILABLE
        }


# Global NSE provider instance
nse_provider = NSEProvider()
