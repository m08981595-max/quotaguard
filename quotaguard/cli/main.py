#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
QuotaGuard CLI: Local AI Token & Rate Limit Optimizer
"""

import os
import sys
import argparse
from ..core.cache import SQLiteCache
from ..core.compressor import PromptCompressor
from ..server.gateway import start_server

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    parser = argparse.ArgumentParser(description="QuotaGuard: Local AI Token & Rate Limit Optimizer")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # serve command
    serve_parser = subparsers.add_parser("serve", help="Start the local AI Gateway proxy server")
    serve_parser.add_argument("--port", "-p", type=int, default=8080, help="Port to listen on (default: 8080)")
    serve_parser.add_argument("--upstream", "-u", default="https://api.apinex.bond/v1", help="Upstream API base URL")

    # stats command
    subparsers.add_parser("stats", help="Display token savings and cache statistics")

    # clear-cache command
    subparsers.add_parser("clear-cache", help="Flush the local SQLite response cache")

    # compress command
    comp_parser = subparsers.add_parser("compress", help="Test compression on a prompt or file")
    comp_parser.add_argument("text", nargs="*", help="Text to compress")
    comp_parser.add_argument("--file", "-f", help="File to compress")

    args = parser.parse_args()

    if args.command == "serve":
        # Auto-detect API key from ~/.dsh
        creds_file = os.path.expanduser("~/.dsh/.credentials.yaml")
        api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        if os.path.exists(creds_file) and not api_key:
            try:
                with open(creds_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        if "APINEX_API_KEY:" in line or "FREE2_API_KEY:" in line:
                            api_key = line.split(":", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass
        start_server(port=args.port, upstream_url=args.upstream, upstream_key=api_key)
        return

    if args.command == "stats":
        cache = SQLiteCache()
        stats = cache.get_stats()
        print("\n📊 === إحصائيات التوفير في QuotaGuard ===")
        print(f"• إجمالي الردود المخزنة (Cache Entries): {stats['total_cached_entries']}")
        print(f"• عدد مرات التوفير المباشر (Cache Hits): {stats['total_cache_hits']}")
        print(f"• إجمالي التوكنز التي تم توفيرها (Tokens Saved): {stats['total_tokens_saved']:,} Token ⚡")
        print(f"• مسار قاعدة البيانات: {stats['database_path']}\n")
        return

    if args.command == "clear-cache":
        cache = SQLiteCache()
        cache.clear()
        print("\n✅ تم مسح الذاكرة المؤقتة (Cache) لـ QuotaGuard بنجاح.\n")
        return

    if args.command == "compress":
        compressor = PromptCompressor()
        input_text = " ".join(args.text)
        if args.file and os.path.exists(args.file):
            with open(args.file, "r", encoding="utf-8", errors="ignore") as f:
                input_text = f.read()

        if not input_text:
            print("يرجى إدخال نص أو تحديد ملف للضغط.")
            return

        comp_text, s = compressor.compress(input_text)
        print("\n🗜️ === نتيجة ضغط الـ Prompt ===")
        print(f"• الحجم الأصلي: {s.original_chars} حرف (~{s.estimated_tokens_before} توكن)")
        print(f"• الحجم المضغوط: {s.compressed_chars} حرف (~{s.estimated_tokens_after} توكن)")
        print(f"• التوفير: {s.saved_tokens} توكن بنسبة ({s.savings_percentage}%)\n")
        print("--- النص بعد الضغط ---")
        print(comp_text[:300] + ("..." if len(comp_text) > 300 else ""))
        return

    parser.print_help()

if __name__ == "__main__":
    main()
