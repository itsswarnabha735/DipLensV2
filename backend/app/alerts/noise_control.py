import redis
from datetime import datetime, time
from typing import Optional
from app.config import settings
from app.alerts.models import AlertRule, SuppressionReason

class NoiseControl:
    def __init__(self):
        try:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            self.redis.ping()
        except Exception:
            self.redis = None
            
        # Default Limits
        self.DAILY_USER_CAP = 5
        self.DAILY_SYMBOL_CAP = 2
        
        # Quiet Hours (Hardcoded for now, could be in user settings)
        self.QUIET_START = time(22, 0) # 10 PM
        self.QUIET_END = time(8, 0)   # 8 AM

    def is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        if self.QUIET_START < self.QUIET_END:
            return self.QUIET_START <= now <= self.QUIET_END
        else: # Crosses midnight
            return now >= self.QUIET_START or now <= self.QUIET_END

    def check_budget(self, user_id: str, symbol: str) -> Optional[SuppressionReason]:
        """Check if alert budget is exceeded"""
        if not self.redis:
            return None
            
        today = datetime.utcnow().strftime("%Y%m%d")
        user_key = f"budget:user:{user_id}:{today}"
        symbol_key = f"budget:symbol:{user_id}:{symbol}:{today}"
        
        # Check User Cap
        user_count = int(self.redis.get(user_key) or 0)
        if user_count >= self.DAILY_USER_CAP:
            return SuppressionReason.BUDGET
            
        # Check Symbol Cap
        symbol_count = int(self.redis.get(symbol_key) or 0)
        if symbol_count >= self.DAILY_SYMBOL_CAP:
            return SuppressionReason.BUDGET
            
        return None

    def consume_budget(self, user_id: str, symbol: str):
        """Increment budget counters"""
        if not self.redis:
            return
            
        today = datetime.utcnow().strftime("%Y%m%d")
        user_key = f"budget:user:{user_id}:{today}"
        symbol_key = f"budget:symbol:{user_id}:{symbol}:{today}"
        
        pipe = self.redis.pipeline()
        pipe.incr(user_key)
        pipe.expire(user_key, 86400)
        pipe.incr(symbol_key)
        pipe.expire(symbol_key, 86400)
        pipe.execute()
