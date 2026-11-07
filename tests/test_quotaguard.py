import unittest
from quotaguard.core.compressor import PromptCompressor
from quotaguard.core.cache import SQLiteCache
from quotaguard.core.rate_limiter import RateLimiter
from quotaguard.core.key_pool import KeyPool
from quotaguard.core.semantic import extract_ngrams, compute_cosine_similarity
from quotaguard.core.router import SmartRouter, TaskClassifier, TaskType

class TestQuotaGuard(unittest.TestCase):
    def test_compression(self):
        comp = PromptCompressor(aggressive=False, enable_dedup=True)
        raw = "def   foo (  a ,  b  ) : \n\n\n    # -------------------\n    # Keep this meaningful comment\n    return a + b"
        result, stats = comp.compress(raw)
        self.assertLess(stats.compressed_chars, stats.original_chars)
        self.assertIn("# Keep this meaningful comment", result)
        self.assertNotIn("# -------------------", result)
        self.assertGreater(stats.savings_percentage, 0.0)

    def test_deduplication(self):
        comp = PromptCompressor(enable_dedup=True)
        raw = "Error 404: Not Found\nError 404: Not Found\nError 404: Not Found\nProceed to home."
        result, stats = comp.compress(raw)
        self.assertIn("[x3 identical lines collapsed by QuotaGuard]", result)
        self.assertEqual(result.count("Error 404: Not Found"), 1)

    def test_cache_hit_and_stats(self):
        cache = SQLiteCache(":memory:")
        prompt = "What is Python?"
        response = "Python is a high-level programming language."
        
        # Miss first
        self.assertIsNone(cache.get(prompt, model="test-model"))
        
        # Set
        cache.set(prompt, response, model="test-model", prompt_tokens=10, response_tokens=20)
        
        # Exact Hit second
        cached_resp, saved_tokens, match_type = cache.get(prompt, model="test-model")
        self.assertEqual(cached_resp, response)
        self.assertEqual(saved_tokens, 30)
        self.assertEqual(match_type, "exact")

        # Verify stats
        stats = cache.get_stats()
        self.assertEqual(stats["total_cached_entries"], 1)
        self.assertEqual(stats["total_cache_hits"], 1)
        self.assertEqual(stats["total_tokens_saved"], 30)

    def test_semantic_cache_hit(self):
        cache = SQLiteCache(":memory:", semantic_threshold=0.80)
        q1 = "ما هي عاصمة اليابان؟"
        ans = "طوكيو"
        cache.set(q1, ans, model="test-model", prompt_tokens=15, response_tokens=5)

        # Rephrased variation
        q2 = "ما هي عاصمة دولة اليابان؟"
        res = cache.get(q2, model="test-model", enable_semantic=True)
        self.assertIsNotNone(res)
        cached_ans, saved, match_type = res
        self.assertEqual(cached_ans, ans)
        self.assertTrue(match_type.startswith("semantic_"))

    def test_smart_router_and_task_classification(self):
        router = SmartRouter()
        
        # Code audit classification
        code_prompt = "def broken_fn():\n    return 1 / 0\n# debug this error traceback"
        model, task_type = router.route(code_prompt)
        self.assertEqual(task_type, TaskType.CODE_AUDIT)
        self.assertEqual(model, "free/qwen-3.8-max")

        # Reasoning heavy classification
        reasoning_prompt = "Compare the architectural trade-offs and scalability between Raft and Paxos consensus algorithms."
        model, task_type = router.route(reasoning_prompt)
        self.assertEqual(task_type, TaskType.REASONING_HEAVY)
        self.assertEqual(model, "free/deepseek-v4-pro-0813")

        # Fast QA classification
        qa_prompt = "What is the capital of France?"
        model, task_type = router.route(qa_prompt)
        self.assertEqual(task_type, TaskType.FAST_QA)
        self.assertEqual(model, "free/deepseek-v4.1-flash")

    def test_key_pool(self):
        pool = KeyPool(["key1", "key2"])
        k1 = pool.get_active_key()
        k2 = pool.get_active_key()
        self.assertNotEqual(k1, k2)
        pool.mark_rate_limited("key1")
        self.assertEqual(pool.get_active_key(), "key2")

if __name__ == "__main__":
    unittest.main()
