import sqlite3
import json
import redis
from typing import List, Optional, Dict
from datetime import datetime
from app.config import settings
from app.alerts.models import AlertRule, AlertState, AlertEvent, SuppressionLog, AlertStateEnum

class AlertStorage:
    def __init__(self, db_path: str = "alerts.db"):
        self.db_path = db_path
        self._init_sqlite()
        self._init_redis()

    def _init_sqlite(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_rules (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    symbol TEXT,
                    condition TEXT,
                    threshold REAL,
                    debounce_seconds INTEGER,
                    hysteresis_reset REAL,
                    confirm_window_seconds INTEGER,
                    enabled BOOLEAN,
                    cooldown_seconds INTEGER,
                    priority TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS suppression_logs (
                    id TEXT PRIMARY KEY,
                    rule_id TEXT,
                    symbol TEXT,
                    timestamp TEXT,
                    reason TEXT,
                    meta TEXT
                )
            """)

    _local_state_cache = {}

    def _init_redis(self):
        try:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            self.redis.ping()
        except Exception as e:
            print(f"Redis connection failed: {e}")
            self.redis = None

    # --- Rules (SQLite) ---

    def create_rule(self, rule: AlertRule):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO alert_rules VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    rule.id, rule.user_id, rule.symbol, rule.condition, rule.threshold,
                    rule.debounce_seconds, rule.hysteresis_reset, rule.confirm_window_seconds,
                    rule.enabled, rule.cooldown_seconds, rule.priority,
                    rule.created_at.isoformat(), rule.updated_at.isoformat()
                )
            )

    def get_rules(self, user_id: Optional[str] = None, symbol: Optional[str] = None) -> List[AlertRule]:
        query = "SELECT * FROM alert_rules WHERE 1=1"
        params = []
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)
            
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [
                AlertRule(
                    id=row['id'],
                    user_id=row['user_id'],
                    symbol=row['symbol'],
                    condition=row['condition'],
                    threshold=row['threshold'],
                    debounce_seconds=row['debounce_seconds'],
                    hysteresis_reset=row['hysteresis_reset'],
                    confirm_window_seconds=row['confirm_window_seconds'],
                    enabled=bool(row['enabled']),
                    cooldown_seconds=row['cooldown_seconds'],
                    priority=row['priority'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ) for row in rows
            ]

    def delete_rule(self, rule_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM alert_rules WHERE id = ?", (rule_id,))
            
    # --- State (Redis / Local) ---
    
    def _state_key(self, rule_id: str) -> str:
        return f"alert:state:{rule_id}"

    def get_state(self, rule_id: str, symbol: str) -> AlertState:
        key = self._state_key(rule_id)
        
        if self.redis:
            data = self.redis.get(key)
            if data:
                return AlertState.model_validate_json(data)
        elif key in self._local_state_cache:
            return self._local_state_cache[key]
                
        return AlertState(rule_id=rule_id, symbol=symbol)

    def save_state(self, state: AlertState):
        key = self._state_key(state.rule_id)
        
        if self.redis:
            self.redis.set(key, state.model_dump_json())
        else:
            self._local_state_cache[key] = state

    # --- Logs (SQLite) ---
    
    def log_suppression(self, log: SuppressionLog):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO suppression_logs VALUES (?, ?, ?, ?, ?, ?)",
                (log.id, log.rule_id, log.symbol, log.timestamp.isoformat(), log.reason, json.dumps(log.meta))
            )

    def get_logs(self, rule_id: str, limit: int = 50) -> List[SuppressionLog]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM suppression_logs WHERE rule_id = ? ORDER BY timestamp DESC LIMIT ?",
                (rule_id, limit)
            )
            return [
                SuppressionLog(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    symbol=row['symbol'],
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    reason=row['reason'],
                    meta=json.loads(row['meta'])
                ) for row in cursor.fetchall()
            ]
