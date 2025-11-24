from nsepython import nse_quote
import json

def check_quote_values():
    symbol = "RELIANCE"
    try:
        q = nse_quote(symbol)
        # Print key fields
        print(f"Symbol: {symbol}")
        print(f"Price: {q.get('priceInfo', {}).get('lastPrice')}")
        print(f"Time: {q.get('metadata', {}).get('lastUpdateTime')}")
        print(f"Date: {q.get('metadata', {}).get('tradingDate')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_quote_values()
