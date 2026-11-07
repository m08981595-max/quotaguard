"""
QuotaGuard SQLite Caching Engine with Semantic Matching
======================================================
Combines exact SHA-256 instant hashing with vectorized Cosine Similarity
semantic caching for rephrased queries.
"""

import os
import time
import json
import sqlite3
import hashlib
from typing import Optional, Dict, Any, Tuple
from .semantic import extract_ngrams, compute_cosine_similarity

def get_default_db_path() -> str:
    env_path = os.environ.get("QUOTAGUARD_DB_PATH")
    if env_path:
        return env_path
    if os.path.exists(r"D:\QuotaGuard"):
        return r"D:\QuotaGuard\data\cache.db"
    return os.path.join(os.path.expanduser("~"), ".quotaguard", "data", "cache.db")

DEFAULT_DB_PATH = get_default_db_path()

class SQLiteCache:
    def __init__(self, db_path: Optional[str] = None, default_ttl: int = 86400 * 7, semantic_threshold: float = 0.85):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.default_ttl = default_ttl
        self.semantic_threshold = semantic_threshold
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
        conn.execute("CREATE INDEX IF NOT EXISTS idx_model ON response_cache (model);")
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

    def get(self, prompt_or_messages: Any, model: str = "", enable_semantic: bool = True) -> Optional[Tuple[str, int, str]]:
        """
        Retrieve cached response.
        Returns: Tuple of (response_text, saved_tokens, match_type: 'exact'|'semantic') or None.
        """
        key = self.generate_key(prompt_or_messages, model)
        now = time.time()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()

            # Step 1: Exact Match Lookup (O(1))
            cursor.execute("""
                SELECT response, prompt_tokens, response_tokens, expires_at
                FROM response_cache
                WHERE cache_key = ?
            """, (key,))
            row = cursor.fetchone()
            if row:
                response, p_tokens, r_tokens, expires_at = row
                if not (expires_at and now > expires_at):
                    cursor.execute("""
                        UPDATE response_cache
                        SET hits = hits + 1, last_accessed = ?
                        WHERE cache_key = ?
                    """, (now, key))
                    conn.commit()
                    saved = (p_tokens or 0) + (r_tokens or 0)
                    return response, saved, "exact"

            # Step 2: Semantic Matching Lookup (Cosine Similarity)
            if enable_semantic:
                target_text = json.dumps(prompt_or_messages, ensure_ascii=False) if isinstance(prompt_or_messages, (list, dict)) else str(prompt_or_messages)
                target_vec = extract_ngrams(target_text)

                # Fetch candidate prompts for this model
                cursor.execute("""
                    SELECT cache_key, prompt, response, prompt_tokens, response_tokens, expires_at
                    FROM response_cache
                    WHERE model = ? AND (expires_at = 0 OR expires_at > ?)
                    ORDER BY hits DESC, last_accessed DESC LIMIT 150
                """, (model, now))
                candidates = cursor.fetchall()

                best_match = None
                best_score = 0.0

                for c_key, c_prompt, c_response, c_pt, c_rt, _ in candidates:
                    cand_vec = extract_ngrams(c_prompt)
                    score = compute_cosine_similarity(target_vec, cand_vec)
                    if score > best_score:
                        best_score = score
                        best_match = (c_key, c_response, (c_pt or 0) + (c_rt or 0))

                if best_match and best_score >= self.semantic_threshold:
                    matched_key, matched_resp, saved_tok = best_match
                    cursor.execute("""
                        UPDATE response_cache
                        SET hits = hits + 1, last_accessed = ?
                        WHERE cache_key = ?
                    """, (now, matched_key))
                    conn.commit()
                    return matched_resp, saved_tok, f"semantic_{best_score:.2f}"

            return None
        finally:
            if not self._mem_conn:
                conn.close()

    def set(self, prompt_or_messages: Any, response: str, model: str = "", prompt_tokens: int = 0, response_tokens: int = 0, ttl: Optional[int] = None) -> str:
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
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM response_cache;")
            conn.commit()
        finally:
            if not self._mem_conn:
                conn.close()
