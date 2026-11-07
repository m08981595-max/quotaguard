"""
QuotaGuard Semantic Caching Engine (Numpy Vectorized)
====================================================
Sub-millisecond semantic similarity matching using character/word n-gram TF vectors
and cosine similarity. Matches rephrased queries without downloading heavy external models.
"""

import re
import math
import numpy as np
from typing import List, Dict, Tuple, Optional

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

def extract_ngrams(text: str, n_word: int = 1, n_char: int = 3) -> Dict[str, float]:
    """Generate normalized word and character n-gram frequencies."""
    normalized = normalize_text(text)
    if not normalized:
        return {}

    freqs = {}
    words = normalized.split()
    
    # Word n-grams
    for w in words:
        freqs[f"w:{w}"] = freqs.get(f"w:{w}", 0.0) + 1.0

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

def compute_cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse feature dicts."""
    if not vec1 or not vec2:
        return 0.0
    common_keys = set(vec1.keys()) & set(vec2.keys())
    if not common_keys:
        return 0.0
    score = sum(vec1[k] * vec2[k] for k in common_keys)
    return float(np.clip(score, 0.0, 1.0))
