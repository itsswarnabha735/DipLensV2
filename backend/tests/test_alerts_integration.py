import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.alerts.models import AlertCondition, AlertStateEnum
import uuid

client = TestClient(app)

def test_create_and_trigger_alert():
    # 1. Create Rule
    rule_data = {
        "id": str(uuid.uuid4()),
        "symbol": "TEST_STOCK",
        "condition": "dip_gt",
        "threshold": 5.0,
        "enabled": True,
        "debounce_seconds": 0,
        "priority": "high"
    }
    
    response = client.post("/alerts/", json=rule_data)
    assert response.status_code == 200
    created_rule = response.json()
    assert created_rule["symbol"] == "TEST_STOCK"
    
    # 2. Simulate Trigger (Dip 6% > 5%)
    # First trigger -> Should fire
    response = client.post("/alerts/simulate?symbol=TEST_STOCK&dip_percent=6.0")
    assert response.status_code == 200
    result = response.json()
    
    assert result["status"] == "evaluated"
    rule_result = result["results"][0]
    assert rule_result["new_state"] == "triggered"
    
    # 3. Simulate Trigger Again (Dip 7% > 5%)
    # Should stay TRIGGERED (or move to COOLDOWN if configured, but here we just check state persistence)
    # Actually, the engine transitions to TRIGGERED, then if we check again it might stay TRIGGERED or go to COOLDOWN if we implemented auto-cooldown logic in the engine loop.
    # In my engine implementation:
    # If TRIGGERED: checks _should_reset. If not reset, it stays TRIGGERED.
    # Wait, my engine implementation:
    # if state.state == AlertStateEnum.TRIGGERED:
    #    if self._should_reset(rule, current_value):
    #         self._transition(state, AlertStateEnum.COOLDOWN, "Entering cooldown")
    
    # So if we send 7% (still > 5%), it should NOT reset, so it stays TRIGGERED.
    
    response = client.post("/alerts/simulate?symbol=TEST_STOCK&dip_percent=7.0")
    result = response.json()
    rule_result = result["results"][0]
    assert rule_result["new_state"] == "triggered"
    
    # 4. Simulate Reset (Dip 2% < 5%)
    # Should transition to COOLDOWN (because _should_reset returns True)
    response = client.post("/alerts/simulate?symbol=TEST_STOCK&dip_percent=2.0")
    result = response.json()
    rule_result = result["results"][0]
    assert rule_result["new_state"] == "cooldown"

    # 5. Clean up
    client.delete(f"/alerts/{created_rule['id']}")

def test_debounce_logic():
    # 1. Create Rule with Debounce
    rule_data = {
        "id": str(uuid.uuid4()),
        "symbol": "DEBOUNCE_STOCK",
        "condition": "dip_gt",
        "threshold": 5.0,
        "debounce_seconds": 10, # 10s debounce
        "enabled": True
    }
    client.post("/alerts/", json=rule_data)
    
    # 2. Trigger First Time
    response = client.post("/alerts/simulate?symbol=DEBOUNCE_STOCK&dip_percent=6.0")
    result = response.json()
    assert result["results"][0]["new_state"] == "armed" # Should be ARMED, not TRIGGERED
    
    # 3. Trigger Immediately Again
    response = client.post("/alerts/simulate?symbol=DEBOUNCE_STOCK&dip_percent=6.0")
    result = response.json()
    assert result["results"][0]["new_state"] == "armed" # Still ARMED
    
    # Clean up
    client.delete(f"/alerts/{rule_data['id']}")
