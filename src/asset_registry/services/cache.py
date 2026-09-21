from __future__ import annotations

import threading
import time
from typing import Any


class SummaryCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._value: Any = None
        self._expires_at: float = 0.0

    def get(self) -> Any | None:
        with self._lock:
            if self._value is None:
                return None
            if time.monotonic() >= self._expires_at:
                self._value = None
                return None
            return self._value

    def set(self, value: Any, ttl_seconds: int) -> None:
        with self._lock:
            self._value = value
            self._expires_at = time.monotonic() + ttl_seconds

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


summary_cache = SummaryCache()
