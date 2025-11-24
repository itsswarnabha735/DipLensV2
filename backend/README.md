# DipLens Data Provider Backend

Python FastAPI microservice for market data and sector membership.

## Setup

1. **Install Python 3.9+**

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

4. **Install Redis** (for caching):
```bash
# macOS
brew install redis
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

5. **Configure environment:**
```bash
cp env.example .env
# Edit .env and add your Alpha Vantage API key (optional, for fallback)
```

## Running the Service

**Development mode:**
```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

**Or using Python:**
```bash
cd backend
python -m app.main
```

**Access the API:**
- API docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

## API Endpoints

### GET /bars
Fetch OHLCV bars for a symbol

**Parameters:**
- `symbol` (required): Ticker symbol (e.g., RELIANCE.NS, ^NSEBANK)
- `interval` (optional): 1m, 5m, 15m, 30m, 1h, 1d (default: 1m)
- `lookback` (optional): 1d, 5d, 1mo, 3mo, 6mo, 1y (default: 1d)

**Example:**
```bash
curl "http://localhost:8000/bars?symbol=RELIANCE.NS&interval=1m&lookback=1d"
```

### GET /meta
Get metadata about the service (cache stats, rate limits, constraints)

```bash
curl http://localhost:8000/meta
```

## Testing

```bash
# Run tests
pytest backend/tests/

# Run with coverage
pytest --cov=app backend/tests/
```

## Architecture

```
backend/
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Settings
│   ├── models.py         # Pydantic models
│   ├── cache.py          # Redis cache
│   ├── routers/
│   │   └── bars.py       # /bars endpoints
│   └── providers/
│       ├── base.py       # Provider interface
│       └── yahoo.py      # Yahoo Finance
├── requirements.txt
└── README.md
```

## Notes

- **Yahoo Finance Limits**: 1m data limited to 7 days, intraday to ~60 days
- **Caching**: 30-second TTL (configurable in .env)
- **CORS**: Configured for http://localhost:3000 (Next.js frontend)
