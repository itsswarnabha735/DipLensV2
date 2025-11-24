import yfinance as yf
import time

def test_yahoo():
    symbol = "RELIANCE.NS"
    print(f"Testing yfinance for {symbol}...")
    try:
        # Try to fetch 1-minute data for the last 1 day
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d", interval="1m")
        
        if hist.empty:
            print("Result: EMPTY DataFrame")
        else:
            print(f"Result: SUCCESS. Got {len(hist)} bars.")
            print(hist.tail())
            
    except Exception as e:
        print(f"Result: FAILED. Error: {e}")

if __name__ == "__main__":
    test_yahoo()
