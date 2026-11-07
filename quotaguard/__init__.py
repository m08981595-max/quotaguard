"""
QuotaGuard: Local AI Token & Rate Limit Optimizer
==================================================
Zero-dependency, local-first proxy and caching engine saving 50-80% of AI tokens
and preventing HTTP 429 rate limit errors for autonomous agents.
"""

__version__ = "0.1.0"
__author__ = "QuotaGuard Core Team"
__license__ = "MIT"

from .core.compressor import PromptCompressor, CompressionStats
from .core.cache import SQLiteCache
from .core.rate_limiter import RateLimiter
from .core.key_pool import KeyPool

__all__ = ["PromptCompressor", "CompressionStats", "SQLiteCache", "RateLimiter", "KeyPool", "__version__"]
