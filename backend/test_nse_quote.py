from nsepython import nse_quote
import json

def test_nse_quote():
    symbol = "RELIANCE"
    print(f"Testing nse_quote for {symbol}...")
    try:
        quote = nse_quote(symbol)
        print("Result: SUCCESS")
        print(json.dumps(quote, indent=2))
    except Exception as e:
        print(f"Result: FAILED. Error: {e}")

if __name__ == "__main__":
    test_nse_quote()
