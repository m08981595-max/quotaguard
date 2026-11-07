"""
QuotaGuard: Local AI Token & Rate Limit Optimizer (v0.2.0 Verified Edition)
============================================================================
Zero-dependency local-first AI proxy and multi-tier caching engine.
Features vectorized semantic caching, active line deduplication,
smart task routing, selective context filtering, and rate limiting.
"""

__version__ = "0.2.0"
__author__ = "QuotaGuard Core Team"
__license__ = "MIT"

from .core.compressor import PromptCompressor, CompressionStats
from .core.cache import SQLiteCache
from .core.rate_limiter import RateLimiter
from .core.key_pool import KeyPool
from .core.semantic import extract_ngrams, compute_cosine_similarity
from .core.router import SmartRouter, TaskClassifier, SelectiveContext, TaskType

__all__ = [
    "PromptCompressor",
    "CompressionStats",
    "SQLiteCache",
    "RateLimiter",
    "KeyPool",
    "SmartRouter",
    "TaskClassifier",
    "SelectiveContext",
    "TaskType",
    "extract_ngrams",
    "compute_cosine_similarity",
    "__version__"
]
