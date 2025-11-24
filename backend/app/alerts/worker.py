import asyncio
import logging
from typing import List, Dict
from datetime import datetime

from app.alerts.models import AlertRule
from app.alerts.storage import AlertStorage
from app.alerts.engine import AlertEngine
from app.providers.yahoo import yahoo_provider
from app.dip_engine import DipEngine
from app.indicators import IndicatorEngine

logger = logging.getLogger(__name__)

async def process_alerts_for_symbol(symbol: str, rules: List[AlertRule], engine: AlertEngine):
    try:
        # 1. Fetch Data (Blocking call to Yahoo/NSE)
        # We need enough history for Dip (52w) and Indicators (RSI/MACD)
        # Run in executor to avoid blocking the loop if this is called from async context
        # But here we are likely running in a thread from APScheduler, so blocking is fine-ish
        # unless we want to parallelize symbols.
        
        # For MVP, sequential per symbol is safer for rate limits.
        bars = yahoo_provider.get_bars(symbol, "1d", "1y")
        
        if not bars or len(bars) < 50:
            logger.warning(f"Insufficient data for {symbol}")
            return

        # Extract arrays
        closes = [bar.c for bar in bars]
        highs = [bar.h for bar in bars]
        lows = [bar.l for bar in bars]
        volumes = [bar.v for bar in bars]
        dates = [bar.t for bar in bars]

        # 2. Calculate Metrics
        # Dip
        dip = DipEngine.analyze_dip(symbol, closes, highs, dates, 365)
        
        # Indicators
        inds = IndicatorEngine.calculate_all_indicators(closes, volumes, highs, lows)
        
        # 3. Construct Market Data Context
        market_data = {
            "dip_percent": dip.dip_pct,
            "rsi": inds["rsi"],
            "macd_hist": inds["macd"]["histogram"],
            "volume": volumes[-1],
            "avg_volume": inds["volume_avg"],
            "price": closes[-1]
        }
        
        # 4. Evaluate Rules
        for rule in rules:
            await engine.evaluate_rule(rule, market_data)
            
    except Exception as e:
        logger.error(f"Error processing alerts for {symbol}: {e}")

def check_alerts_cycle():
    """
    Main entry point for the background job.
    """
    logger.info("Starting alert evaluation cycle...")
    start_time = datetime.now()
    
    storage = AlertStorage()
    engine = AlertEngine()
    
    # 1. Get all active rules
    rules = storage.get_rules()
    if not rules:
        logger.info("No active alert rules.")
        return

    # 2. Group by symbol
    rules_by_symbol: Dict[str, List[AlertRule]] = {}
    for rule in rules:
        if not rule.enabled:
            continue
        if rule.symbol not in rules_by_symbol:
            rules_by_symbol[rule.symbol] = []
        rules_by_symbol[rule.symbol].append(rule)
        
    logger.info(f"Processing {len(rules_by_symbol)} symbols with {len(rules)} active rules.")

    # 3. Process each symbol
    # We use asyncio.run to execute the async processing logic
    async def _run_batch():
        tasks = []
        for symbol, symbol_rules in rules_by_symbol.items():
            tasks.append(process_alerts_for_symbol(symbol, symbol_rules, engine))
        await asyncio.gather(*tasks)

    try:
        asyncio.run(_run_batch())
    except Exception as e:
        logger.error(f"Error in alert evaluation cycle: {e}")
        
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"Alert evaluation cycle completed in {duration:.2f}s")
