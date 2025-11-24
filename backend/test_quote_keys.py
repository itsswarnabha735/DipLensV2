from nsepython import nse_quote
import json

def dump_quote_keys():
    symbol = "RELIANCE"
    try:
        q = nse_quote(symbol)
        print(f"Keys: {list(q.keys())}")
        # Print first level of data to see structure
        # print(json.dumps(q, indent=2)[:1000]) 
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_quote_keys()
