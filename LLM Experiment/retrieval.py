"""
Lightweight lexical search over POLICY_*.md files.

No embedding API: 12 short docs do not justify the cost or the extra network hop
against the take-home's 100k q/day, ~$50/day, p95 ≤ 3s constraint. BM25 is
in-process and sub-millisecond. rank_bm25 is not assumed; this is pure Python.
"""

from __future__ import annotations

import math
import os
import re
from typing import Dict, List, Optional, Tuple

# Module-level cache: chunks + the BM25 index built from them.
_CHUNKS: Optional[List[Dict[str, str]]] = None
_INDEX: Optional["_BM25Index"] = None
_LOADED_DIR: Optional[str] = None

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_H2_RE = re.compile(r"^##\s+(.+?)\s*$")
_H1_RE = re.compile(r"^#\s+(.+?)\s*$")

# Common function words. Kept small so domain terms ("pay", "fee", "limit") stay.
_STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "was", "were", "be", "been", "being", "it", "its", "this", "that", "with",
    "at", "by", "from", "as", "if", "but", "not", "no", "so", "do", "does",
    "did", "my", "your", "our", "their", "i", "you", "we", "they", "me",
    "can", "will", "just", "how", "what", "when", "where", "why", "who",
    "about", "into", "than", "then", "also", "any", "all", "each",
}

# Shopper phrasing → extra query tokens. The policy docs are formal; tickets are not.
_QUERY_EXPANSION = {
    "push": ("reschedule", "rescheduling"),
    "postpone": ("reschedule", "rescheduling"),
    "defer": ("reschedule", "rescheduling"),
    "move": ("reschedule",),
    "later": ("reschedule",),
    "missed": ("failed", "failure"),
    "late": ("failed", "overdue"),
    "bounced": ("failed", "failure"),
    "money": ("refund", "return"),
    "return": ("refund", "returns"),
    "returned": ("refund",),
    "shipped": ("dispute", "received"),
    "received": ("dispute",),
    "missing": ("dispute", "shipped"),
    "wrong": ("dispute",),
    "job": ("hardship",),
    "unemployed": ("hardship",),
    "laid": ("hardship",),
    "afford": ("hardship",),
    "broke": ("hardship",),
    "disaster": ("hardship",),
    "medical": ("hardship",),
    "limit": ("spending", "limits", "decline"),
    "limits": ("spending", "decline"),
    "declined": ("limit", "limits", "spending"),
    "decline": ("limit", "limits"),
    "unauthorized": ("fraud",),
    "stolen": ("fraud",),
    "hacked": ("fraud", "takeover"),
    "takeover": ("fraud",),
    "interest": ("fee", "fees"),
    "reactivate": ("reactivation", "deactivated"),
    "deactivated": ("reactivation",),
    "virtual": ("card",),
    "bureau": ("credit", "reporting"),
    "score": ("credit", "reporting"),
}

# Extra indexed terms (not returned) so informal queries still hit the right file.
_DOC_ALIASES = {
    "payment-schedules": (
        "pay in 4 pay-in-4 payin4 installment plan how it works "
        "25 percent every two weeks schedule next payment"
    ),
    "rescheduling": (
        "push back move date postpone defer later change due date "
        "reschedule rescheduling"
    ),
    "failed": (
        "missed payment late overdue retry bounced failed installment "
        "cannot reschedule repay"
    ),
    "refunds": (
        "return money back where is my money approved return refund timeline"
    ),
    "disputes": (
        "never shipped not received wrong item not as described missing "
        "package item not received file dispute"
    ),
    "reactivation": "reactivate deactivated unlock account reactivation fee",
    "splitwave-boost": "credit bureau report credit score splitwave boost enrolled reporting",
    "virtual": "virtual card apple pay google pay preload declined card",
    "hardship": (
        "lost job unemployed medical disaster laid off "
        "broke hardship assistance pause waive"
    ),
    "fees": "interest charge fee cost waive discount on time no interest",
    "security": (
        "fraud stolen hacked unauthorized did not place never ordered "
        "takeover 2fa password unrecognized"
    ),
    "merchants": (
        "spending limit credit limit declined order spending power exact "
        "limit decline reason"
    ),
}


def _stem(word: str) -> str:
    """Very light stemmer so reschedule/rescheduling and decline/declined match."""
    if len(word) <= 3:
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("es") and len(word) > 4 and word[-3] in "sxz":
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        word = word[:-1]
    if word.endswith("ing") and len(word) > 5:
        word = word[:-3]
        if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "aeiou":
            word = word[:-1]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
        if len(word) > 3 and word[-1] == word[-2] and word[-1] not in "aeiou":
            word = word[:-1]
    if word.endswith("e") and len(word) > 4:
        word = word[:-1]
    return word


def _tokenize(text: str) -> List[str]:
    tokens: List[str] = []
    for raw in _TOKEN_RE.findall(text.lower().replace("'", "")):
        if raw in _STOPWORDS or len(raw) < 2:
            continue
        tokens.append(_stem(raw))
    return tokens


def _expand_query(tokens: List[str]) -> List[str]:
    """Add stemmed synonym tokens. Original tokens stay first (same BM25 weight)."""
    extra: List[str] = []
    seen = set(tokens)
    # Expand from the unstemmed surface forms we still have as stems; also
    # check the raw synonym table keys against the stem set.
    for key, syns in _QUERY_EXPANSION.items():
        key_stem = _stem(key)
        if key_stem in seen or key in seen:
            for syn in syns:
                for piece in _tokenize(syn):
                    if piece not in seen:
                        extra.append(piece)
                        seen.add(piece)
    return tokens + extra


def _aliases_for(filename: str) -> str:
    lower = filename.lower()
    parts: List[str] = []
    for key, aliases in _DOC_ALIASES.items():
        if key in lower:
            parts.append(aliases)
    return " ".join(parts)


def _h1_title(content: str, filename: str) -> str:
    for line in content.splitlines():
        m = _H1_RE.match(line)
        if m:
            return m.group(1).strip()
    return os.path.splitext(filename)[0]


def _chunk_markdown(filename: str, content: str) -> List[Dict[str, str]]:
    """Split on ## headers. Docs with only a # title become a single chunk."""
    lines = content.splitlines()
    h1 = _h1_title(content, filename)
    h2_indexes = [i for i, line in enumerate(lines) if _H2_RE.match(line)]

    if not h2_indexes:
        text = content.strip()
        if not text:
            return []
        return [{"doc": filename, "section": h1, "text": text}]

    chunks: List[Dict[str, str]] = []
    preamble = "\n".join(lines[: h2_indexes[0]]).strip()
    if preamble:
        chunks.append({"doc": filename, "section": h1, "text": preamble})

    for idx, start in enumerate(h2_indexes):
        end = h2_indexes[idx + 1] if idx + 1 < len(h2_indexes) else len(lines)
        heading = _H2_RE.match(lines[start]).group(1).strip()
        text = "\n".join(lines[start:end]).strip()
        if text:
            chunks.append({"doc": filename, "section": heading, "text": text})
    return chunks


def _resolve_policy_dir(policy_dir: str) -> str:
    """Prefer the given dir; fall back to this module's directory."""
    if os.path.isdir(policy_dir):
        matches = [
            n for n in os.listdir(policy_dir)
            if n.startswith("POLICY_") and n.endswith(".md")
        ]
        if matches:
            return os.path.abspath(policy_dir)
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(here):
        matches = [
            n for n in os.listdir(here)
            if n.startswith("POLICY_") and n.endswith(".md")
        ]
        if matches:
            return here
    return os.path.abspath(policy_dir)


class _BM25Index:
    """Okapi BM25 over an in-memory tokenized corpus."""

    def __init__(self, corpus: List[List[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.n = len(corpus)
        self.doc_len = [len(doc) for doc in corpus]
        self.avgdl = (sum(self.doc_len) / self.n) if self.n else 0.0
        self.tf: List[Dict[str, int]] = []
        df: Dict[str, int] = {}
        for doc in corpus:
            counts: Dict[str, int] = {}
            for tok in doc:
                counts[tok] = counts.get(tok, 0) + 1
            self.tf.append(counts)
            for tok in counts:
                df[tok] = df.get(tok, 0) + 1
        self.idf = {
            tok: math.log(1.0 + (self.n - freq + 0.5) / (freq + 0.5))
            for tok, freq in df.items()
        }

    def scores(self, query: List[str]) -> List[float]:
        out = [0.0] * self.n
        if not query or self.avgdl == 0:
            return out
        for i, tfmap in enumerate(self.tf):
            dl = self.doc_len[i]
            s = 0.0
            for tok in query:
                tf = tfmap.get(tok)
                if not tf:
                    continue
                idf = self.idf.get(tok, 0.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
                s += idf * (tf * (self.k1 + 1.0)) / denom
            out[i] = s
        return out


def _build_index(chunks: List[Dict[str, str]]) -> _BM25Index:
    corpus: List[List[str]] = []
    for chunk in chunks:
        # Searchable text includes heading + filename + aliases; returned text does not.
        searchable = " ".join(
            [
                chunk["section"],
                chunk["text"],
                chunk["doc"].replace("_", " ").replace("-", " "),
                _aliases_for(chunk["doc"]),
            ]
        )
        corpus.append(_tokenize(searchable))
    return _BM25Index(corpus)


def load_policies(policy_dir: str = ".") -> List[Dict[str, str]]:
    """
    Load POLICY_*.md files and chunk them on ## headers.

    Returns list[{"doc": filename, "section": str, "text": str}].
    Cached in module state; a different policy_dir rebuilds the cache.
    """
    global _CHUNKS, _INDEX, _LOADED_DIR

    resolved = _resolve_policy_dir(policy_dir)
    if _CHUNKS is not None and _LOADED_DIR == resolved:
        return _CHUNKS

    chunks: List[Dict[str, str]] = []
    try:
        names = sorted(os.listdir(resolved))
    except OSError:
        names = []

    for name in names:
        if not (name.startswith("POLICY_") and name.endswith(".md")):
            continue
        path = os.path.join(resolved, name)
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue
        chunks.extend(_chunk_markdown(name, content))

    _CHUNKS = chunks
    _INDEX = _build_index(chunks) if chunks else None
    _LOADED_DIR = resolved
    return _CHUNKS


def search_policy(query: str, k: int = 3) -> List[Dict[str, str]]:
    """
    Top-k policy chunks for query.

    Returns list[{"doc": filename, "text": str}] ordered by BM25 score, highest first.
    """
    chunks = load_policies()
    if not chunks or k <= 0:
        return []

    tokens = _expand_query(_tokenize(query or ""))
    if not tokens or _INDEX is None:
        # No usable query: return the first k chunks as a stable fallback.
        return [{"doc": c["doc"], "text": c["text"]} for c in chunks[:k]]

    scored: List[Tuple[float, int]] = []
    for i, score in enumerate(_INDEX.scores(tokens)):
        if score > 0:
            scored.append((score, i))
    scored.sort(key=lambda item: (-item[0], item[1]))

    results: List[Dict[str, str]] = []
    for _, idx in scored[:k]:
        chunk = chunks[idx]
        results.append({"doc": chunk["doc"], "text": chunk["text"]})
    return results
