from typing import Any, Optional
import json
from redis import Redis
from datetime import timedelta

class RedisCache:
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_client = Redis(host=host, port=port, db=db, decode_responses=True)
        self.default_ttl = timedelta(hours=1)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        data = self.redis_client.get(key)
        if data:
            return json.loads(data)
        return None

    def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Set value in cache with optional TTL"""
        try:
            serialized_value = json.dumps(value)
            if ttl is None:
                ttl = self.default_ttl
            return self.redis_client.setex(key, ttl, serialized_value)
        except Exception:
            return False

    def delete(self, key: str) -> bool:
        """Delete value from cache"""
        return bool(self.redis_client.delete(key))

    def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern"""
        keys = self.redis_client.keys(pattern)
        if keys:
            return self.redis_client.delete(*keys)
        return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        return bool(self.redis_client.exists(key)) 