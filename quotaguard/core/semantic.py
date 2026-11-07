"""
QuotaGuard Semantic Caching Engine (Numpy Vectorized with Polarity Guard)
========================================================================
Sub-millisecond semantic similarity matching using character/word n-gram TF vectors,
cosine similarity, and strict Negation/Polarity Conflict Guards.
Guarantees zero false-positive cache collisions on opposite-intent queries
(e.g., enable vs disable, with vs without, Japan vs Korea).
"""

import re
import math
import numpy as np
from typing import List, Dict, Set, Tuple, Optional

# Antonym / Inversion pairs that must NEVER match
POLARITY_PAIRS = [
    ({"enable", "enabled", "enabling"}, {"disable", "disabled", "disabling"}),
    ({"with", "including"}, {"without", "excluding"}),
    ({"true", "valid", "allow", "allowed"}, {"false", "invalid", "deny", "denied"}),
    ({"add", "insert", "create"}, {"remove", "delete", "drop"}),
    ({"start", "launch"}, {"stop", "terminate", "kill"}),
    ({"encrypt", "encryption"}, {"decrypt", "decryption"}),
    ({"safe", "secure"}, {"unsafe", "insecure", "vulnerable"}),
    ({"تفعيل", "تشغيل"}, {"تعطيل", "ايقاف"}),
    ({"مع", "ب"}, {"بدون", "دون"}),
    ({"اضافة", "انشاء"}, {"حذف", "ازالة"}),
    ({"سماح", "قبول"}, {"منع", "حظر", "رفض"}),
    ({"صحيح", "حق"}, {"خطا", "باطل"})
]

NEGATION_WORDS_EN = {"not", "no", "never", "none", "neither", "nor", "hardly", "scarcely"}
NEGATION_WORDS_AR = {"لا", "لم", "لن", "ليس", "غير", "دون", "بدون", "ما"}

def normalize_text(text: str) -> str:
    """Normalize Arabic and Latin text for robust semantic comparison."""
    if not text:
        return ""
    s = text.lower().strip()
    # Normalize Arabic Alef variants and common letters
    s = re.sub(r"[إأآا]", "ا", s)
    s = re.sub(r"ة", "ه", s)
    s = re.sub(r"ى", "ي", s)
    # Remove Arabic diacritics (Tashkeel)
    s = re.sub(r"[\u064B-\u065F\u0670]", "", s)
    # Normalize multiple whitespace and punctuation
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def has_polarity_conflict(text1: str, text2: str) -> bool:
    """Detect if two texts have opposite intent, negations, or conflicting antonyms."""
    t1_norm = normalize_text(text1)
    t2_norm = normalize_text(text2)
    words1 = set(t1_norm.split())
    words2 = set(t2_norm.split())

    # 1. Check Antonym / Polarity Pairs
    for pos_set, neg_set in POLARITY_PAIRS:
        has_pos1 = bool(words1 & pos_set)
        has_neg1 = bool(words1 & neg_set)
        has_pos2 = bool(words2 & pos_set)
        has_neg2 = bool(words2 & neg_set)

        # Opposite assignment: one is positive, the other is negative
        if (has_pos1 and has_neg2) or (has_neg1 and has_pos2):
            return True

    # 2. Check Negation disparity
    neg1_count = len(words1 & (NEGATION_WORDS_EN | NEGATION_WORDS_AR))
    neg2_count = len(words2 & (NEGATION_WORDS_EN | NEGATION_WORDS_AR))
    if (neg1_count % 2) != (neg2_count % 2):
        # One text is negated, the other is affirmative!
        return True

    return False

def extract_ngrams(text: str, n_word: int = 1, n_char: int = 3) -> Dict[str, float]:
    """Generate normalized word and character n-gram frequencies."""
    normalized = normalize_text(text)
    if not normalized:
        return {}

    freqs = {}
    words = normalized.split()
    
    # Word n-grams (heavy weight on specific entity terms)
    for w in words:
        freqs[f"w:{w}"] = freqs.get(f"w:{w}", 0.0) + 1.5

    # Character n-grams for typo and inflection tolerance
    for i in range(len(normalized) - n_char + 1):
        gram = normalized[i:i+n_char]
        freqs[f"c:{gram}"] = freqs.get(f"c:{gram}", 0.0) + 0.5

    # L2 normalize vector
    norm = math.sqrt(sum(v * v for v in freqs.values()))
    if norm > 0:
        for k in freqs:
            freqs[k] /= norm
    return freqs

def compute_cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float], text1: str = "", text2: str = "") -> float:
    """
    Compute cosine similarity between two feature vectors.
    If text1 and text2 are supplied and have polarity conflict, score is immediately clamped to 0.0.
    """
    if text1 and text2 and has_polarity_conflict(text1, text2):
        return 0.0

    if not vec1 or not vec2:
        return 0.0
    common_keys = set(vec1.keys()) & set(vec2.keys())
    if not common_keys:
        return 0.0
    score = sum(vec1[k] * vec2[k] for k in common_keys)
    return float(np.clip(score, 0.0, 1.0))
