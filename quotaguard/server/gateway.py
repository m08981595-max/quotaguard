"""
QuotaGuard Local AI Gateway / Proxy Server
===========================================
Drop-in OpenAI-compatible proxy running on standard library http.server.
Intercepts completions, compresses context, consults SQLite cache, and forwards requests.
"""

import sys
import json
import time
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Any, Optional

from ..core.compressor import PromptCompressor
from ..core.cache import SQLiteCache
from ..core.rate_limiter import RateLimiter

class QuotaGuardHandler(BaseHTTPRequestHandler):
    compressor = PromptCompressor()
    cache = SQLiteCache()
    limiter = RateLimiter(max_requests_per_minute=120)
    upstream_url = "https://api.apinex.bond/v1"
    upstream_api_key = ""

    def log_message(self, format, *args):
        # Clean terminal logging
        sys.stdout.write(f"[QuotaGuard Gateway] {args[0]} {args[1]} - {args[2]}\n")

    def _send_json(self, status: int, data: Dict[str, Any]):
        response_bytes = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(response_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def do_GET(self):
        if self.path == "/v1/models":
            self._send_json(200, {
                "object": "list",
                "data": [
                    {"id": "free/deepseek-v4-pro-0813", "object": "model", "owned_by": "quotaguard"},
                    {"id": "free/deepseek-v4.1-flash", "object": "model", "owned_by": "quotaguard"}
                ]
            })
            return

        if self.path == "/v1/stats" or self.path == "/stats":
            self._send_json(200, self.cache.get_stats())
            return

        self._send_json(200, {
            "name": "QuotaGuard Local AI Proxy",
            "status": "online",
            "stats": self.cache.get_stats()
        })

    def do_POST(self):
        if not self.path.startswith("/v1/chat/completions"):
            self._send_json(404, {"error": "Not Found"})
            return

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        messages = body.get("messages", [])
        model = body.get("model", "free/deepseek-v4-pro-0813")

        # Step 1: Check Cache (0 Tokens)
        cached_result = self.cache.get(messages, model=model)
        if cached_result:
            reply_text, tokens_saved = cached_result
            sys.stdout.write(f"[QuotaGuard] ⚡ CACHE HIT! Saved {tokens_saved} tokens (0ms)\n")
            self._send_json(200, {
                "id": "chatcmpl-cached",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": reply_text},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "quotaguard_saved_tokens": tokens_saved
                }
            })
            return

        # Step 2: Prompt Compression
        compressed_msgs, stats = self.compressor.compress_messages(messages)
        body["messages"] = compressed_msgs
        if stats.saved_tokens > 0:
            sys.stdout.write(f"[QuotaGuard] 🗜️ Compressed Prompt: saved ~{stats.saved_tokens} tokens ({stats.savings_percentage}% reduction)\n")

        # Step 3: Rate Limiter Smooth
        self.limiter.acquire(wait=True)

        # Step 4: Upstream Dispatch
        auth_header = self.headers.get("Authorization", "")
        if not auth_header and self.upstream_api_key:
            auth_header = f"Bearer {self.upstream_api_key}"

        upstream_endpoint = f"{self.upstream_url.rstrip('/')}/chat/completions"
        req = urllib.request.Request(
            upstream_endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": auth_header,
                "Content-Type": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as upstream_res:
                raw_response = upstream_res.read().decode("utf-8")
                res_json = json.loads(raw_response)
                reply_content = res_json["choices"][0]["message"]["content"]

                # Cache completion for future queries
                p_tokens = res_json.get("usage", {}).get("prompt_tokens", stats.estimated_tokens_after)
                r_tokens = res_json.get("usage", {}).get("completion_tokens", self.compressor.estimate_tokens(reply_content))
                self.cache.set(messages, reply_content, model=model, prompt_tokens=p_tokens, response_tokens=r_tokens)

                self._send_json(upstream_res.status, res_json)
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8", errors="ignore")
            self._send_json(e.code, {"error": err_msg})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

def start_server(port: int = 8080, upstream_url: Optional[str] = None, upstream_key: Optional[str] = None):
    if upstream_url:
        QuotaGuardHandler.upstream_url = upstream_url
    if upstream_key:
        QuotaGuardHandler.upstream_api_key = upstream_key

    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, QuotaGuardHandler)
    print(f"\n🛡️ QuotaGuard Gateway running on http://127.0.0.1:{port}")
    print(f"📡 Upstream: {QuotaGuardHandler.upstream_url}")
    print(f"📊 Stats endpoint: http://127.0.0.1:{port}/stats")
    print("Press Ctrl+C to stop.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping QuotaGuard server...")
        httpd.server_close()
