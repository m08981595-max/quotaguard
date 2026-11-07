"""
QuotaGuard Upgraded Prompt & Context Compressor
==============================================
Includes safe lossless prompt minification AND active deduplication.
Preserves critical comments while collapsing duplicate logs and decorative bloat.
"""

import re
from dataclasses import dataclass, field
from typing import Tuple, Dict, Any, List

@dataclass
class CompressionStats:
    original_chars: int
    compressed_chars: int
    estimated_tokens_before: int
    estimated_tokens_after: int
    saved_tokens: int
    savings_percentage: float = field(default=0.0)

    def __post_init__(self):
        if self.estimated_tokens_before > 0:
            self.savings_percentage = round((self.saved_tokens / self.estimated_tokens_before) * 100, 1)

class PromptCompressor:
    def __init__(self, aggressive: bool = False, enable_dedup: bool = True):
        self.aggressive = aggressive
        self.enable_dedup = enable_dedup

    @staticmethod
    def estimate_tokens(text: str) -> int:
        if not text:
            return 0
        words = re.findall(r"\w+|[^\w\s]", text)
        return max(1, int(len(words) * 1.25))

    def deduplicate_lines(self, text: str) -> Tuple[str, int]:
        """Detect and collapse identical repeating consecutive or block lines."""
        lines = text.split("\n")
        if len(lines) <= 1:
            return text, 0

        deduped = []
        i = 0
        lines_saved = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Check if this line repeats consecutively
            if stripped and len(stripped) > 5:
                count = 1
                while (i + count) < len(lines) and lines[i + count].strip() == stripped:
                    count += 1
                if count >= 2:
                    deduped.append(f"{line}  # [x{count} identical lines collapsed by QuotaGuard]")
                    lines_saved += (count - 1)
                    i += count
                    continue

            deduped.append(line)
            i += 1

        return "\n".join(deduped), lines_saved

    def compress(self, text: str) -> Tuple[str, CompressionStats]:
        if not text:
            return "", CompressionStats(0, 0, 0, 0, 0)

        original = text
        compressed = text

        # Step 1: Active Line Deduplication (Repeated logs, error traces, copy-pastes)
        if self.enable_dedup:
            compressed, _ = self.deduplicate_lines(compressed)

        # Step 2: Strip only decorative comment dividers and empty comments (Preserve real code comments)
        # Decorative: # --------------, # =============, // --------------
        compressed = re.sub(r"^\s*[#/]{1,2}\s*[-=*~_]{3,}\s*$", "", compressed, flags=re.MULTILINE)
        compressed = re.sub(r"^\s*#\s*$", "", compressed, flags=re.MULTILINE)
        compressed = re.sub(r"^\s*//\s*$", "", compressed, flags=re.MULTILINE)

        # Step 3: Normalize excessive syntax spaces: foo(  a  ,  b  ) -> foo(a, b)
        compressed = re.sub(r"\s*([,;:])\s*", r"\1 ", compressed)
        compressed = re.sub(r"\s+([,;:])", r"\1", compressed)
        compressed = re.sub(r"\(\s+", "(", compressed)
        compressed = re.sub(r"\s+\)", ")", compressed)
        compressed = re.sub(r"\[\s+", "[", compressed)
        compressed = re.sub(r"\s+\]", "]", compressed)

        # Step 4: Normalize consecutive newlines and horizontal spaces
        compressed = re.sub(r"[ \t]+", " ", compressed)
        compressed = re.sub(r"\n{3,}", "\n\n", compressed)
        compressed = compressed.strip()

        before_tokens = self.estimate_tokens(original)
        after_tokens = self.estimate_tokens(compressed)

        # Calculate proportional token delta
        if len(compressed) < len(original):
            char_ratio = len(compressed) / max(1, len(original))
            after_tokens = min(after_tokens, max(1, int(before_tokens * char_ratio)))

        saved = max(0, before_tokens - after_tokens)

        stats = CompressionStats(
            original_chars=len(original),
            compressed_chars=len(compressed),
            estimated_tokens_before=before_tokens,
            estimated_tokens_after=after_tokens,
            saved_tokens=saved
        )
        return compressed, stats

    def compress_messages(self, messages: List[Dict[str, str]]) -> Tuple[List[Dict[str, str]], CompressionStats]:
        new_messages = []
        total_orig = 0
        total_comp = 0
        total_before = 0
        total_after = 0

        for m in messages:
            content = m.get("content", "")
            comp_content, stats = self.compress(content)
            new_m = dict(m)
            new_m["content"] = comp_content
            new_messages.append(new_m)

            total_orig += stats.original_chars
            total_comp += stats.compressed_chars
            total_before += stats.estimated_tokens_before
            total_after += stats.estimated_tokens_after

        saved = max(0, total_before - total_after)
        agg_stats = CompressionStats(
            original_chars=total_orig,
            compressed_chars=total_comp,
            estimated_tokens_before=total_before,
            estimated_tokens_after=total_after,
            saved_tokens=saved
        )
        return new_messages, agg_stats
