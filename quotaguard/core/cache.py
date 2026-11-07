"""
QuotaGuard SQLite Caching Engine
================================
Zero-dependency persistent local cache delivering sub-millisecond 0-token responses.
"""

import os
import time
import json
import sqlite3
import hashlib
from typing import Optional, Dict, Any, Tuple

DEFAULT_DB_PATH = os.path.expanduser("~/.quotaguard/cache.db")

class SQLiteCache:
    def __init__(self, db_path: Optional[str] = None, default_ttl: int = 86400 * 7):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.default_ttl = default_ttl
        self._mem_conn = None
        if self.db_path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:")
        else:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _get_connection(self):
        if self._mem_conn:
            return self._mem_conn
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        conn = self._get_connection()
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS response_cache (
                cache_key TEXT PRIMARY KEY,
                model TEXT,
                prompt TEXT,
                response TEXT,
                prompt_tokens INTEGER,
                response_tokens INTEGER,
                hits INTEGER DEFAULT 0,
                created_at REAL,
                last_accessed REAL,
                expires_at REAL
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_expires ON response_cache (expires_at);")
        conn.commit()
        if not self._mem_conn:
            conn.close()

    @staticmethod
    def generate_key(prompt_or_messages: Any, model: str = "") -> str:
        """Create a stable SHA-256 key from request content and model."""
        if isinstance(prompt_or_messages, (list, dict)):
            raw = json.dumps(prompt_or_messages, sort_keys=True)
        else:
            raw = str(prompt_or_messages).strip()
        combined = f"{model}:{raw}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def get(self, prompt_or_messages: Any, model: str = "") -> Optional[Tuple[str, int]]:
        """Retrieve cached response and saved tokens if found and not expired."""
        key = self.generate_key(prompt_or_messages, model)
        now = time.time()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT response, prompt_tokens, response_tokens, expires_at
                FROM response_cache
                WHERE cache_key = ?
            """, (key,))
            row = cursor.fetchone()
            if not row:
                return None

            response, p_tokens, r_tokens, expires_at = row
            if expires_at and now > expires_at:
                cursor.execute("DELETE FROM response_cache WHERE cache_key = ?", (key,))
                conn.commit()
                return None

            # Increment hits & update last accessed
            cursor.execute("""
                UPDATE response_cache
                SET hits = hits + 1, last_accessed = ?
                WHERE cache_key = ?
            """, (now, key))
            conn.commit()

            saved_tokens = (p_tokens or 0) + (r_tokens or 0)
            return response, saved_tokens
        finally:
            if not self._mem_conn:
                conn.close()

    def set(self, prompt_or_messages: Any, response: str, model: str = "", prompt_tokens: int = 0, response_tokens: int = 0, ttl: Optional[int] = None) -> str:
        """Store a new model completion in cache."""
        key = self.generate_key(prompt_or_messages, model)
        now = time.time()
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        expires_at = now + ttl_seconds if ttl_seconds > 0 else 0

        raw_prompt = json.dumps(prompt_or_messages, ensure_ascii=False) if isinstance(prompt_or_messages, (list, dict)) else str(prompt_or_messages)

        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO response_cache
                (cache_key, model, prompt, response, prompt_tokens, response_tokens, hits, created_at, last_accessed, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (key, model, raw_prompt, response, prompt_tokens, response_tokens, now, now, expires_at))
            conn.commit()
            return key
        finally:
            if not self._mem_conn:
                conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Aggregate total cache hits and saved token metrics."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(hits), 0) FROM response_cache;")
            entries, total_hits = cursor.fetchone()

            cursor.execute("""
                SELECT COALESCE(SUM(hits * (prompt_tokens + response_tokens)), 0)
                FROM response_cache;
            """)
            tokens_saved = cursor.fetchone()[0]

            return {
                "total_cached_entries": entries,
                "total_cache_hits": total_hits,
                "total_tokens_saved": tokens_saved,
                "database_path": self.db_path
            }
        finally:
            if not self._mem_conn:
                conn.close()

    def clear(self) -> None:
        """Clear all cached entries."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM response_cache;")
            conn.commit()
        finally:
            if not self._mem_conn:
                conn.close()
