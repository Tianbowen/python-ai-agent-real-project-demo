# cache/cache.py

import threading
from typing import Any, Optional
from cachetools import TTLCache

from config import SESSION_TTL_S, SESSION_MAXSIZE, logger

class SessionCache:
    """
    进程内 L1 TTL 缓存，线程安全
    存储 ConversationSession, 实现跨请求的多轮记忆
    """

    def __init__(self, maxsize: int= SESSION_MAXSIZE, ttl: int = SESSION_TTL_S):
        self._cache = TTLCache(maxsize=maxsize, ttl=ttl)
        self._lock = threading.Lock()

    def get(self, key: str, default= None) -> Any:
        with self._lock:
            return self._cache.get(key, default)
        
    def set(self, key: str, value: Any):
        with self._lock:
            self._cache[key] = value

    def delete(self, key: str):
        with self._lock:
            self._cache.pop(key, None)

# 全局单例缓存

_session_cache = SessionCache()

def get_session(session_id: str):
    return _session_cache.get(session_id)

def set_session(session_id: str, session):
    _session_cache.set(session_id, session)
        