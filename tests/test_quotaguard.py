import unittest
from quotaguard.core.compressor import PromptCompressor
from quotaguard.core.cache import SQLiteCache
from quotaguard.core.rate_limiter import RateLimiter
from quotaguard.core.key_pool import KeyPool

class TestQuotaGuard(unittest.TestCase):
    def test_compression(self):
        comp = PromptCompressor()
        raw = "def   foo (  a ,  b  ) : \n\n\n    # useless comment\n    return a + b"
        result, stats = comp.compress(raw)
        self.assertLess(stats.compressed_chars, stats.original_chars)
        self.assertGreater(stats.savings_percentage, 0.0)

    def test_cache_hit_and_stats(self):
        cache = SQLiteCache(":memory:")
        prompt = "What is Python?"
        response = "Python is a high-level programming language."
        
        # Miss first
        self.assertIsNone(cache.get(prompt, model="test-model"))
        
        # Set
        cache.set(prompt, response, model="test-model", prompt_tokens=10, response_tokens=20)
        
        # Hit second
        cached_resp, saved_tokens = cache.get(prompt, model="test-model")
        self.assertEqual(cached_resp, response)
        self.assertEqual(saved_tokens, 30)

        # Verify stats
        stats = cache.get_stats()
        self.assertEqual(stats["total_cached_entries"], 1)
        self.assertEqual(stats["total_cache_hits"], 1)
        self.assertEqual(stats["total_tokens_saved"], 30)

    def test_key_pool(self):
        pool = KeyPool(["key1", "key2"])
        k1 = pool.get_active_key()
        k2 = pool.get_active_key()
        self.assertNotEqual(k1, k2)
        pool.mark_rate_limited("key1")
        self.assertEqual(pool.get_active_key(), "key2")

if __name__ == "__main__":
    unittest.main()
