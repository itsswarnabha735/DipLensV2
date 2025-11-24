from nsepython import nse_quote

def check_timestamps():
    symbol = "RELIANCE"
    try:
        q = nse_quote(symbol)
        print(f"Future Timestamp: {q.get('fut_timestamp')}")
        print(f"Option Timestamp: {q.get('opt_timestamp')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_timestamps()
