from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
import uuid
import logging

from app.alerts.models import AlertRule, AlertState, SuppressionLog, AlertCondition, Priority
from app.alerts.storage import AlertStorage
from app.alerts.engine import AlertEngine

router = APIRouter()
logger = logging.getLogger(__name__)

# Dependencies
def get_storage():
    return AlertStorage()

def get_engine():
    return AlertEngine()

@router.post("/", response_model=AlertRule)
async def create_alert(
    rule: AlertRule,
    storage: AlertStorage = Depends(get_storage)
):
    """Create a new alert rule"""
    # Ensure ID is generated if not provided
    if not rule.id:
        rule.id = str(uuid.uuid4())
        
    try:
        storage.create_rule(rule)
        return rule
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[AlertRule])
async def list_alerts(
    user_id: Optional[str] = None,
    symbol: Optional[str] = None,
    storage: AlertStorage = Depends(get_storage)
):
    """List alert rules with optional filtering"""
    return storage.get_rules(user_id=user_id, symbol=symbol)

@router.delete("/{rule_id}")
async def delete_alert(
    rule_id: str,
    storage: AlertStorage = Depends(get_storage)
):
    """Delete an alert rule"""
    try:
        storage.delete_rule(rule_id)
        return {"status": "success", "id": rule_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{rule_id}/logs", response_model=List[SuppressionLog])
async def get_alert_logs(
    rule_id: str,
    limit: int = 50,
    storage: AlertStorage = Depends(get_storage)
):
    """Get suppression logs for a specific rule"""
    return storage.get_logs(rule_id, limit)

@router.get("/states", response_model=List[dict])
async def get_alert_states(
    storage: AlertStorage = Depends(get_storage)
):
    """Get current state for all alerts"""
    rules = storage.get_rules()
    states = []
    for rule in rules:
        state = storage.get_state(rule.id, rule.symbol)
        states.append({
            "rule_id": rule.id,
            "symbol": rule.symbol,
            "state": state.state,
            "last_triggered": state.last_triggered_at,
            "last_transition": state.last_transition_at
        })
    return states

@router.post("/simulate")
async def simulate_alert_check(
    symbol: str,
    dip_percent: float = Query(..., description="Simulated Dip %"),
    rsi: float = Query(100.0, description="Simulated RSI"),
    engine: AlertEngine = Depends(get_engine),
    storage: AlertStorage = Depends(get_storage)
):
    """
    Manually trigger the alert engine for a specific symbol with simulated data.
    Useful for testing without waiting for real market data.
    """
    # 1. Get all rules for this symbol
    rules = storage.get_rules(symbol=symbol)
    
    if not rules:
        return {"status": "no_rules_found", "symbol": symbol}
        
    # 2. Construct simulated market data
    market_data = {
        "dip_percent": dip_percent,
        "rsi": rsi,
        "volume": 1000000,
        "avg_volume": 500000,
        "macd_hist": 0.5 # Default positive
    }
    
    # 3. Evaluate each rule
    results = []
    for rule in rules:
        await engine.evaluate_rule(rule, market_data)
        # Fetch updated state
        state = storage.get_state(rule.id, symbol)
        results.append({
            "rule_id": rule.id,
            "condition": rule.condition,
            "new_state": state.state,
            "last_transition": state.last_transition_at
        })
        
    return {
        "status": "evaluated",
        "symbol": symbol,
        "simulated_data": market_data,
        "results": results
    }
