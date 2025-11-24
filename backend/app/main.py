from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import bars, dips, indicators, sectors, sector_snapshots, stock, suggestions, scores, insights, fundamentals
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="DipLens Data Provider",
    description="Market data API for DipLens v2 - provides OHLCV bars and sector membership",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize background jobs on startup"""
    logger.info("Application startup - initializing background jobs...")
    try:
        from app.background_worker import start_background_jobs
        start_background_jobs()
        logger.info("Background jobs started successfully")
    except Exception as e:
        logger.error(f"Failed to start background jobs: {e}", exc_info=True)

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup background jobs on shutdown"""
    logger.info("Application shutdown - stopping background jobs...")
    try:
        from app.background_worker import stop_background_jobs
        stop_background_jobs()
        logger.info("Background jobs stopped successfully")
    except Exception as e:
        logger.error(f"Failed to stop background jobs: {e}", exc_info=True)


#Include routers
app.include_router(bars.router, tags=["Market Data"])
app.include_router(sectors.router, prefix="/sectors", tags=["Sectors"])
app.include_router(sector_snapshots.router, tags=["Sector Snapshots"])  # Routes already have /sectors prefix
app.include_router(suggestions.router, prefix="/sectors", tags=["Suggestions"])
app.include_router(indicators.router, prefix="/indicators", tags=["Indicators"])
app.include_router(dips.router, prefix="/dips", tags=["Dips"])
app.include_router(scores.router, prefix="/sectors", tags=["Scores"])
app.include_router(stock.router, prefix="/stock", tags=["stock"])
app.include_router(insights.router, prefix="/insights", tags=["Insights"])
app.include_router(fundamentals.router, tags=["Fundamentals"])
from app.routers import alerts
app.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])

@app.get("/")
async def root():
    """Root endpoint - health check"""
    return {
        "service": "DipLens Data Provider",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "bars": "/bars",
            "meta": "/meta",
            "sectors": "/sectors",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
