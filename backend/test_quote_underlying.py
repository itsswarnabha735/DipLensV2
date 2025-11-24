from nsepython import nse_quote
import json

def check_underlying():
    symbol = "RELIANCE"
    try:
        q = nse_quote(symbol)
        print(f"Underlying Value: {q.get('underlyingValue')}")
        print(f"Info: {q.get('info')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_underlying()
