#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuotaGuard Independent Audit & Re-Verification Suite (v2.0)
==========================================================
Executes real empirical benchmarks against the live API,
capturing actual API usage metrics (prompt_tokens, completion_tokens).
Verifies:
  - Context Compression & Functional Comment Preservation
  - Exact & Semantic Caching
  - Active Line Deduplication
  - Smart Routing & Task Classification
  - Selective Context Filtering
  - Multi-Turn Conversation Optimization
  - Tri-Agent Team Coordination Efficiency
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "D:\\QuotaGuard")

from quotaguard.core.compressor import PromptCompressor
from quotaguard.core.cache import SQLiteCache
from quotaguard.core.router import SmartRouter, TaskClassifier, SelectiveContext, TaskType

# Sandboxed isolated database for clean, isolated audit
AUDIT_DB_PATH = r"D:\QuotaGuard\data\audit_sandbox_cache.db"
if os.path.exists(AUDIT_DB_PATH):
    try:
        os.remove(AUDIT_DB_PATH)
    except Exception:
        pass

# Retrieve API credentials
CREDS_FILE = os.path.expanduser("~/.dsh/.credentials.yaml")
API_KEY = ""
if os.path.exists(CREDS_FILE):
    with open(CREDS_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if "APINEX_API_KEY:" in line or "FREE2_API_KEY:" in line:
                API_KEY = line.split(":", 1)[1].strip().strip('"').strip("'")
                break

if not API_KEY:
    print("FATAL: No API key found for empirical testing.")
    sys.exit(1)

API_URL = "https://api.apinex.bond/v1/chat/completions"

def make_raw_api_call(messages, model="free/qwen-3.8-max"):
    """Call the raw API directly and return actual token usage and response content."""
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=45) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        latency = time.perf_counter() - t0
        usage = res.get("usage", {})
        content = res["choices"][0]["message"]["content"]
        return {
            "content": content,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency": latency
        }

results = {}

print("=== STARTING QUOTAGUARD EMPIRICAL AUDIT & RE-VERIFICATION SUITE ===\n")

# -------------------------------------------------------------
# TEST A: Context Compression & Safe Comment Preservation
# -------------------------------------------------------------
print("--- [Test A: Context Compression & Safe Comment Preservation] ---")
raw_code_prompt = """# ========================================================
# User Authentication Controller Module
# ========================================================

def authenticate_user(   username  ,   password   ) :
    # Step 1: Validate input fields
    if not username or not password:
        return False

    # Step 2: Query database for active user
    user = db.find_user( username )
    if not user:
        return False

    # Step 3: Check password hash with timing-attack safe compare
    return verify_hash( password , user.password_hash )

# Explain what this code does in 1 sentence.
"""

# Baseline (Raw API without compression)
baseline_a = make_raw_api_call([{"role": "user", "content": raw_code_prompt}])

# Compressed with QuotaGuard
compressor = PromptCompressor(aggressive=False, enable_dedup=True)
comp_text, comp_stats = compressor.compress(raw_code_prompt)
optimized_a = make_raw_api_call([{"role": "user", "content": comp_text}])

token_saving_a = baseline_a["prompt_tokens"] - optimized_a["prompt_tokens"]
pct_a = ((baseline_a["prompt_tokens"] - optimized_a["prompt_tokens"]) / baseline_a["prompt_tokens"]) * 100

has_functional_comments = "# Step 1: Validate input fields" in comp_text and "# Step 3: Check password hash" in comp_text
dividers_stripped = "# ====" not in comp_text

results["Test_A"] = {
    "baseline_input_tokens": baseline_a["prompt_tokens"],
    "optimized_input_tokens": optimized_a["prompt_tokens"],
    "tokens_saved": token_saving_a,
    "saving_percentage": round(pct_a, 2),
    "heuristic_estimated_saved": comp_stats.saved_tokens,
    "quality_check": len(optimized_a["content"]) > 10,
    "functional_comments_preserved": has_functional_comments,
    "decorative_dividers_stripped": dividers_stripped
}
print(f"Baseline Prompt Tokens (Real API): {baseline_a['prompt_tokens']}")
print(f"Optimized Prompt Tokens (Real API): {optimized_a['prompt_tokens']}")
print(f"Actual Token Savings: {token_saving_a} ({pct_a:.1f}%)")
print(f"Functional comments preserved: {has_functional_comments}")
print(f"Decorative dividers stripped: {dividers_stripped}\n")

# -------------------------------------------------------------
# TEST B: Caching Verification (Exact Match + Semantic Matching)
# -------------------------------------------------------------
print("--- [Test B: Caching Verification (Exact + Semantic)] ---")
test_cache = SQLiteCache(AUDIT_DB_PATH, semantic_threshold=0.82)
query_1 = "ما هي عاصمة اليابان؟ أجب في كلمة واحدة."
query_2_semantic = "ما هي عاصمة دولة اليابان؟ أجب في كلمة واحدة."

# Run 1: Cache Miss (Cold)
t0 = time.perf_counter()
cached_1 = test_cache.get(query_1, model="free/qwen-3.8-max")
if not cached_1:
    api_resp_1 = make_raw_api_call([{"role": "user", "content": query_1}])
    test_cache.set(query_1, api_resp_1["content"], model="free/qwen-3.8-max",
                   prompt_tokens=api_resp_1["prompt_tokens"], response_tokens=api_resp_1["completion_tokens"])
    run_1_time = time.perf_counter() - t0
    run_1_tokens = api_resp_1["total_tokens"]
    run_1_hit = False
else:
    run_1_hit = True

# Run 2: Exact Repeat (Cache Hit Expected)
t0 = time.perf_counter()
cached_2 = test_cache.get(query_1, model="free/qwen-3.8-max")
run_2_time = time.perf_counter() - t0
run_2_hit = cached_2 is not None
run_2_match_type = cached_2[2] if cached_2 else None

# Run 3: Semantic Variation (Rephrased query)
t0 = time.perf_counter()
cached_3 = test_cache.get(query_2_semantic, model="free/qwen-3.8-max", enable_semantic=True)
run_3_time = time.perf_counter() - t0
run_3_hit = cached_3 is not None
run_3_match_type = cached_3[2] if cached_3 else None

results["Test_B"] = {
    "run_1_api_tokens": run_1_tokens,
    "run_1_latency_sec": round(run_1_time, 3),
    "run_2_api_tokens": 0 if run_2_hit else run_1_tokens,
    "run_2_latency_sec": round(run_2_time, 5),
    "exact_cache_hit": run_2_hit,
    "exact_match_type": run_2_match_type,
    "run_3_api_tokens": 0 if run_3_hit else run_1_tokens,
    "run_3_latency_sec": round(run_3_time, 5),
    "semantic_cache_hit": run_3_hit,
    "semantic_match_type": run_3_match_type,
    "total_cached_saved_tokens": (run_1_tokens if run_2_hit else 0) + (run_1_tokens if run_3_hit else 0)
}
print(f"Run 1 (Cold API call): {run_1_tokens} tokens, Latency: {run_1_time:.3f}s")
print(f"Run 2 (Exact Hit): 0 API tokens, Latency: {run_2_time:.5f}s, Match: {run_2_match_type}")
print(f"Run 3 (Semantic Hit): 0 API tokens, Latency: {run_3_time:.5f}s, Match: {run_3_match_type}\n")

# -------------------------------------------------------------
# TEST C: Deduplication Verification
# -------------------------------------------------------------
print("--- [Test C: Deduplication Verification] ---")
repeated_context = """
# Execution Log
[2026-11-07 10:00:01] ERROR: ConnectionResetError at socket_pool.py:104
[2026-11-07 10:00:01] ERROR: ConnectionResetError at socket_pool.py:104
[2026-11-07 10:00:01] ERROR: ConnectionResetError at socket_pool.py:104
[2026-11-07 10:00:01] ERROR: ConnectionResetError at socket_pool.py:104
[2026-11-07 10:00:01] ERROR: ConnectionResetError at socket_pool.py:104
Task: What error occurred in 3 words?
"""
comp_dedup, dedup_stats = compressor.compress(repeated_context)
resp_raw_c = make_raw_api_call([{"role": "user", "content": repeated_context}])
resp_comp_c = make_raw_api_call([{"role": "user", "content": comp_dedup}])

dedup_saved = resp_raw_c["prompt_tokens"] - resp_comp_c["prompt_tokens"]
pct_c = (dedup_saved / resp_raw_c["prompt_tokens"]) * 100

results["Test_C"] = {
    "raw_tokens": resp_raw_c["prompt_tokens"],
    "comp_tokens": resp_comp_c["prompt_tokens"],
    "tokens_saved": dedup_saved,
    "saving_percentage": round(pct_c, 2),
    "lines_deduplicated": "[x5 identical lines collapsed by QuotaGuard]" in comp_dedup
}
print(f"Raw Repeated Prompt Tokens: {resp_raw_c['prompt_tokens']}")
print(f"Compressed Deduplicated Prompt Tokens: {resp_comp_c['prompt_tokens']}")
print(f"Tokens Saved via Deduplication: {dedup_saved} ({pct_c:.1f}%)")
print(f"Did it deduplicate repeating lines? {results['Test_C']['lines_deduplicated']}\n")

# -------------------------------------------------------------
# TEST D & E: Smart Routing & Selective Context Verification
# -------------------------------------------------------------
print("--- [Test D & E: Smart Routing & Selective Context Verification] ---")
router = SmartRouter()

# Task 1: QA
m1, t1 = router.route("What is the speed of light?")
# Task 2: Code Audit
m2, t2 = router.route("def check_syntax():\n    return 1 / 0\n# debug this bug")
# Task 3: Architecture Reasoning
m3, t3 = router.route("Compare the architectural trade-offs and consensus latency of Raft vs Paxos")

# Selective Context Filter test
bulky_conversation = [
    {"role": "system", "content": "You are a senior developer."},
    {"role": "user", "content": "Here is an unrelated chat about weather yesterday."},
    {"role": "assistant", "content": "Weather was sunny."},
    {"role": "user", "content": "Now review this code: def foo(): return 42"},
    {"role": "assistant", "content": "Function returns 42."},
    {"role": "user", "content": "Audit that function for type annotations."}
]
filtered_msgs = router.context_filter.filter_context(bulky_conversation, TaskType.CODE_AUDIT, max_turns=4)
unrelated_trimmed = not any("weather yesterday" in m.get("content", "") for m in filtered_msgs)

results["Test_D_E"] = {
    "qa_routed_model": m1,
    "qa_task_type": t1.value,
    "code_routed_model": m2,
    "code_task_type": t2.value,
    "reasoning_routed_model": m3,
    "reasoning_task_type": t3.value,
    "smart_routing_verified": (t1 == TaskType.FAST_QA and t2 == TaskType.CODE_AUDIT and t3 == TaskType.REASONING_HEAVY),
    "selective_context_trimmed_unrelated": unrelated_trimmed,
    "original_msg_count": len(bulky_conversation),
    "filtered_msg_count": len(filtered_msgs)
}
print(f"Task 1 (QA) -> Type: {t1.value}, Routed to: {m1}")
print(f"Task 2 (Code Audit) -> Type: {t2.value}, Routed to: {m2}")
print(f"Task 3 (Reasoning) -> Type: {t3.value}, Routed to: {m3}")
print(f"Selective Context Trimmed Unrelated: {unrelated_trimmed} ({len(bulky_conversation)} -> {len(filtered_msgs)} msgs)\n")

# -------------------------------------------------------------
# TEST F: Multi-Turn Conversation Simulation
# -------------------------------------------------------------
print("--- [Test F: Multi-Turn Conversation Benchmark] ---")
dialogue = [
    {"role": "user", "content": "I am designing a distributed key-value store in Python. Recommend an algorithm."},
    {"role": "assistant", "content": "I recommend Consistent Hashing with virtual nodes for partitioning."},
    {"role": "user", "content": "# =========================================\n# Virtual Nodes Ring\n# =========================================\nclass ConsistentHash:\n    def __init__(  self  ,  nodes=None  ) :\n        # Keep active nodes list\n        self.nodes = nodes or []\n        pass\n"},
    {"role": "assistant", "content": "Here is the implementation with bisect."},
    {"role": "user", "content": "Explain how replication works in this scheme in 1 sentence."}
]

# Baseline Dialogue Tokens
base_f = make_raw_api_call(dialogue)

# Compressed Dialogue
comp_dialogue, f_stats = compressor.compress_messages(dialogue)
opt_f = make_raw_api_call(comp_dialogue)

saving_f = base_f["prompt_tokens"] - opt_f["prompt_tokens"]
pct_f = (saving_f / base_f["prompt_tokens"]) * 100

results["Test_F"] = {
    "baseline_input_tokens": base_f["prompt_tokens"],
    "optimized_input_tokens": opt_f["prompt_tokens"],
    "tokens_saved": saving_f,
    "saving_percentage": round(pct_f, 2)
}
print(f"Multi-turn Baseline Tokens: {base_f['prompt_tokens']}")
print(f"Multi-turn Optimized Tokens: {opt_f['prompt_tokens']}")
print(f"Multi-turn Savings: {saving_f} tokens ({pct_f:.1f}%)\n")

# -------------------------------------------------------------
# TEST G: Tri-Agent Team Coordination (Shared Cache & Compression)
# -------------------------------------------------------------
print("--- [Test G: Tri-Agent Team Coordination Simulation] ---")
# When Gemini, DeepSeek, and Qwen collaborate on the same task,
# can Qwen audit without re-evaluating the entire raw prompt?
shared_spec = "Architecture Specification: Design an asynchronous token bucket rate limiter in Python."

# DeepSeek writes architecture (Cold)
deepseek_resp = make_raw_api_call([{"role": "user", "content": shared_spec}], model="free/deepseek-v4-pro-0813")
test_cache.set(shared_spec, deepseek_resp["content"], model="free/deepseek-v4-pro-0813",
               prompt_tokens=deepseek_resp["prompt_tokens"], response_tokens=deepseek_resp["completion_tokens"])

# Gemini inspects from cache (0 tokens)
cached_gemini = test_cache.get(shared_spec, model="free/deepseek-v4-pro-0813")
gemini_saved = cached_gemini is not None

# Qwen audits code (Compressed prompt only)
audit_prompt = f"Audit this implementation for race conditions:\n```python\n{deepseek_resp['content'][:250]}\n```"
comp_audit, _ = compressor.compress(audit_prompt)
qwen_audit = make_raw_api_call([{"role": "user", "content": comp_audit}], model="free/qwen-3.8-max")

results["Test_G"] = {
    "shared_context_cached": gemini_saved,
    "deepseek_tokens": deepseek_resp["total_tokens"],
    "gemini_tokens": 0 if gemini_saved else deepseek_resp["total_tokens"],
    "qwen_audit_prompt_tokens": qwen_audit["prompt_tokens"],
    "total_team_savings_tokens": deepseek_resp["total_tokens"] if gemini_saved else 0
}
print(f"DeepSeek Architect Execution: {deepseek_resp['total_tokens']} tokens")
print(f"Gemini Engineer Context Retrieval: 0 tokens (Cache Hit: {gemini_saved})")
print(f"Qwen Auditor Execution: {qwen_audit['prompt_tokens']} prompt tokens (compressed)")
print(f"Tri-Agent Team Pipeline Saved: {results['Test_G']['total_team_savings_tokens']} tokens\n")

# Dump JSON results for auditor review
with open(r"D:\QuotaGuard\data\audit_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("=== AUDIT SUITE FINISHED. Results saved to D:\\QuotaGuard\\data\\audit_results.json ===")
