"""
QuotaGuard Multi-Key Pool
=========================
Round-robin API key manager with automatic fallback and cooldown on rate limits.
"""

import time
from typing import List, Optional, Dict

class KeyPool:
    def __init__(self, keys: Optional[List[str]] = None, cooldown_seconds: int = 60):
        self.keys = keys or []
        self.cooldown = cooldown_seconds
        self.cooldowns: Dict[str, float] = {}
        self.index = 0

    def add_key(self, key: str):
        if key and key not in self.keys:
            self.keys.append(key)

    def get_active_key(self) -> Optional[str]:
        """Return the next available healthy key."""
        if not self.keys:
            return None

        now = time.time()
        # Clean expired cooldowns
        for k, expire_t in list(self.cooldowns.items()):
            if now >= expire_t:
                del self.cooldowns[k]

        available = [k for k in self.keys if k not in self.cooldowns]
        if not available:
            # All keys cooling down; return earliest to recover
            earliest = min(self.cooldowns.items(), key=lambda x: x[1])[0]
            return earliest

        self.index = self.index % len(available)
        selected = available[self.index]
        self.index = (self.index + 1) % len(available)
        return selected

    def mark_rate_limited(self, key: str):
        """Put a key into cooldown when HTTP 429 occurs."""
        self.cooldowns[key] = time.time() + self.cooldown
