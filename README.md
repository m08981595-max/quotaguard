# 🛡️ QuotaGuard: Local AI Token & Rate Limit Optimizer

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/downloads/)
[![Architecture: Local-First](https://img.shields.io/badge/Architecture-Local--First-orange.svg)](#)
[![Dependencies: Zero](https://img.shields.io/badge/Dependencies-Zero-success.svg)](#)

> **QuotaGuard** is a zero-dependency, local-first AI Gateway & Caching Proxy. It sits transparently between your tools (Cursor, VS Code, Python scripts, AI agents) and LLM APIs, reducing token consumption by **50% to 80%** and completely preventing **HTTP 429 Too Many Requests** errors.

---

## 🌟 Key Features

* ⚡ **Sub-Millisecond Cache Hits (0 Tokens):** Instantaneous responses from persistent SQLite cache for recurring queries and code reviews.
* 🗜️ **Smart Context Minification:** Lossless prompt and code compression reducing input tokens by 20-40% without losing semantics.
* 🚦 **Rate Limit Smoothing:** Token bucket and sliding window rate limiting that smooths API request spikes.
* 🔄 **Multi-Key Pool & Failover:** Round-robin API key rotation with automatic cooldown when any key encounters rate limits.
* 🔌 **Drop-in OpenAI Compatibility:** Works seamlessly with any tool that supports custom OpenAI `baseURL` (`http://127.0.0.1:8080/v1`).
* 🔒 **100% Private & Local:** All database records, hashes, and configurations reside solely on your device.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                 YOUR TOOLS & AGENTS                         │
│       (Cursor, VS Code, Antigravity, Python Scripts)        │
└──────────────────────────────┬──────────────────────────────┘
                               │  baseURL: http://127.0.0.1:8080/v1
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   🛡️ QuotaGuard Proxy                       │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 1. 💾 Persistent SQLite Cache (SHA-256 Hash Matching) │  │
│  │    └──> HIT: Return in < 1ms at ZERO token cost!      │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 2. 🗜️ Lossless Prompt & Context Minifier              │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 3. 🚦 Rate Limiter (Token Bucket & Smooth Sliding Win) │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ 4. 🔑 Multi-Key Pool (Round-Robin & 429 Failover)     │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
          [DeepSeek / OpenAI / Claude / Gemini / Ollama]
```

---

## 🚀 Quickstart

### 1. Installation
```bash
git clone https://github.com/m08981595-max/quotaguard.git
cd quotaguard
pip install -e .
```

### 2. Launch Local Gateway
Start the local proxy on port 8080:
```bash
quotaguard serve --port 8080
```

### 3. Check Savings Statistics
Inspect total token savings and cache hits anytime:
```bash
quotaguard stats
```
*Output:*
```text
📊 === إحصائيات التوفير في QuotaGuard ===
• إجمالي الردود المخزنة (Cache Entries): 48
• عدد مرات التوفير المباشر (Cache Hits): 112
• إجمالي التوكنز التي تم توفيرها (Tokens Saved): 348,200 Token ⚡
• مسار قاعدة البيانات: C:\Users\...\.quotaguard\cache.db
```

### 4. Test Prompt Compression
```bash
quotaguard compress "def   calculate_sum(  a, b  ) : \n\n    # calculate sum\n    return a + b"
```

---

## 💻 Python Library Usage

```python
from quotaguard import SQLiteCache, PromptCompressor

cache = SQLiteCache()
compressor = PromptCompressor()

prompt = "Analyze this database schema..."
compressed_prompt, stats = compressor.compress(prompt)
print(f"Saved {stats.saved_tokens} tokens ({stats.savings_percentage}%)")

# Check cache before calling expensive API
cached_reply = cache.get(compressed_prompt, model="deepseek-v4-pro")
if cached_reply:
    reply, saved_tokens = cached_reply
    print(f"Instant cache hit! Saved {saved_tokens} tokens.")
else:
    # Call upstream API...
    reply = "Schema looks optimal..."
    cache.set(compressed_prompt, reply, model="deepseek-v4-pro", prompt_tokens=150, response_tokens=50)
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
