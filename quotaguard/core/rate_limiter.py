"""
QuotaGuard Rate Limiter
=======================
Sliding window & token bucket rate limiter to prevent HTTP 429 Too Many Requests.
"""

import time
from collections import deque
from typing import Optional

class RateLimiter:
    def __init__(self, max_requests_per_minute: int = 60, min_interval_seconds: float = 0.5):
        self.max_rpm = max_requests_per_minute
        self.min_interval = min_interval_seconds
        self.timestamps = deque()
        self.last_request_time = 0.0

    def acquire(self, wait: bool = True) -> bool:
        """Acquire permission to send a request, pausing if near the limit."""
        now = time.time()

        # Enforce minimum spacing between calls
        elapsed_since_last = now - self.last_request_time
        if elapsed_since_last < self.min_interval:
            if wait:
                time.sleep(self.min_interval - elapsed_since_last)
                now = time.time()
            else:
                return False

        # Expire timestamps older than 60 seconds
        cutoff = now - 60.0
        while self.timestamps and self.timestamps[0] < cutoff:
            self.timestamps.popleft()

        # Check RPM threshold
        if len(self.timestamps) >= self.max_rpm:
            if wait:
                sleep_time = 60.0 - (now - self.timestamps[0]) + 0.1
                if sleep_time > 0:
                    time.sleep(sleep_time)
                now = time.time()
                while self.timestamps and self.timestamps[0] < (now - 60.0):
                    self.timestamps.popleft()
            else:
                return False

        self.timestamps.append(now)
        self.last_request_time = now
        return True
