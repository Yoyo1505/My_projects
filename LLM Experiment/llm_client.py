"""
llm_client.py - Model plane. Single choke point for every LLM call the graph makes.

Extracted from agent.py so every node (reasoning, and any future node) talks to
the model the same way: same endpoint selection, same timeout/keep_alive knobs,
same error shape. Local Ollama (http://localhost:11434) is the no-key fallback;
Ollama Cloud (OLLAMA_API_KEY set) is used when available -- see DECISIONS.md #2
for why the cloud pivot happened (local CPU inference was 15+ min/batch).
"""

import json
import os
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


class LLMError(Exception):
    """Raised when the model endpoint is unreachable or returns an error."""


# Ollama Cloud's gpt-oss:20b renders "typographic" whitespace inside its own
# output -- U+202F (narrow no-break space) between "July" and "11" in a date,
# U+00A0 between a number and its unit, etc. Invisible in a terminal, but it
# silently defeats every plain-ASCII regex check downstream (eval.py's
# must_include patterns, verifier.py's term matching). Discovered via v01:
# the model wrote a fully correct "July 11, 2026" that failed the golden check
# only because "July" and "11" were joined by U+202F, not a plain space.
_SPACE_LIKE_CODEPOINTS = [
    0x00A0, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006,
    0x2007, 0x2008, 0x2009, 0x200A, 0x202F, 0x205F, 0x3000,
]
_ZERO_WIDTH_CODEPOINTS = [0x200B, 0x200C, 0x200D, 0xFEFF]
_WS_TABLE = {cp: " " for cp in _SPACE_LIKE_CODEPOINTS}
_WS_TABLE.update({cp: "" for cp in _ZERO_WIDTH_CODEPOINTS})

# Same failure mode, different character class: "typographic" quotes/dashes
# (found via v04 -- the model wrote "can't" with U+2019, and the golden
# regex's plain ASCII "can't" silently missed it, same as v01's date bug).
_PUNCT_TABLE = {
    0x2018: "'", 0x2019: "'",  # single quotes -> '
    0x201C: '"', 0x201D: '"',  # double quotes -> "
    0x2013: "-", 0x2014: "-",  # en/em dash -> -
}
_WS_TABLE.update(_PUNCT_TABLE)


def normalize_text(text: str) -> str:
    """Collapse non-ASCII whitespace/zero-width/typographic-punctuation chars to plain ASCII equivalents."""
    return text.translate(_WS_TABLE)


def _endpoint() -> Dict[str, Any]:
    api_key = os.environ.get("OLLAMA_API_KEY")
    if api_key:
        return {
            "url": "https://ollama.com/api/chat",
            "model": os.environ.get("OLLAMA_MODEL", "gpt-oss:20b"),
            "headers": {"Authorization": f"Bearer {api_key}"},
        }
    return {
        "url": "http://localhost:11434/api/chat",
        "model": os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
        "headers": {},
    }


def chat(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    One chat turn. Returns the raw `message` object from the Ollama /api/chat
    response (has `content` and, if the model used one, `tool_calls`).

    Raises LLMError on any transport/HTTP failure -- callers decide how to
    degrade (agent.py's reasoning_node turns this into a route="policy" error
    answer rather than crashing the batch).
    """
    ep = _endpoint()
    payload = {
        "model": model or ep["model"],
        "messages": messages,
        "stream": False,
        "keep_alive": "30m",
    }
    if tools:
        payload["tools"] = tools

    req = urllib.request.Request(
        ep["url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **ep["headers"]},
    )

    timeout_s = int(os.environ.get("OLLAMA_TIMEOUT_S", "60"))
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise LLMError(
            f"Ollama API returned HTTP {e.code} ({e.reason}). "
            f"Ensure model '{payload['model']}' is available. {err_body}"
        ) from e
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        raise LLMError(
            f"Unable to reach {ep['url']}. "
            f"Ensure Ollama is running and model '{payload['model']}' is available."
        ) from e

    return response_data.get("message", {})
