import redis
import json
import time
from typing import Optional, Dict
from app.config import settings


class CacheManager:
    """Redis-based cache manager with TTL support"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
        except redis.ConnectionError:
            print("Warning: Redis not available, running without cache")
            self.redis_client = None
            self.enabled = False
        
        self.stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0
        }
    
    def _make_key(self, symbol: str, interval: str, lookback: str) -> str:
        """Generate cache key"""
        return f"bars:{symbol}:{interval}:{lookback}"
    
    def get(self, symbol: str, interval: str, lookback: str) -> Optional[Dict]:
        """Get cached bars data"""
        if not self.enabled:
            return None
        
        key = self._make_key(symbol, interval, lookback)
        try:
            data = self.redis_client.get(key)
            if data:
                self.stats["hits"] += 1
                result = json.loads(data)
                # Check if stale
                cache_time = result.get("cached_at", 0)
                age = time.time() - cache_time
                result["stale"] = age > settings.cache_ttl_seconds
                return result
            else:
                self.stats["misses"] += 1
                return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    def set(self, symbol: str, interval: str, lookback: str, data: Dict, ttl: Optional[int] = None):
        """Set cached bars data with TTL"""
        if not self.enabled:
            return
        
        key = self._make_key(symbol, interval, lookback)
        ttl = ttl or settings.cache_ttl_seconds
        
        try:
            data["cached_at"] = time.time()
            self.redis_client.setex(key, ttl, json.dumps(data))
            self.stats["sets"] += 1
        except Exception as e:
            print(f"Cache set error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "enabled": self.enabled,
            "hits": self.stats["hits"],
            "misses": self.stats["misses"],
            "sets": self.stats["sets"],
            "hit_rate_percent": round(hit_rate, 2)
        }


# Global cache instance
cache = CacheManager()
