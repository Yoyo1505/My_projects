"""
router.py - Control plane. Deterministic pre-routing, before any model call.

DECISIONS.md #3 established that guardrails should be structural (enforced in
code), not just prompted -- applied there to *data access* (orders_store.py).
This module applies the same principle to *escalation routing*.

Previously (agent.py in the original submission), ESCALATION_HINTS existed only
as text the model *might* read in its system prompt; the actual route label was
inferred after the fact from which tools the model happened to call. README.md's
"Honestly Unfinished" section names the resulting failure mode directly: v09
(a fraud report) intermittently routed to `policy` because the model sometimes
skipped calling escalate().

Here, a hint match is load-bearing: it pins route="escalate" before the model
turn runs, independent of the model's own tool-calling behavior. The model
reasoning node still runs afterward (graph.py) -- grounding for the escalate
answer (e.g. the dispute policy's window language) still has to come from real
tool calls, this module just makes sure the *label* can't drift from what a
known-escalate phrase demands.
"""

import re
from typing import List, NamedTuple, Optional

from prompts import ESCALATION_CATEGORIES, UNIVERSAL_ESCALATE_PHRASES

# Structural nudge (not a forced route -- see graph.py) for the "policy
# applies to a specific order" pattern the SYSTEM_PROMPT's routing rule
# already asks for but doesn't reliably get followed on refund/return
# questions (found via v10: model answered from policy alone, skipping the
# order-status lookup, twice in a row across two separate prompt wordings).
# Unlike the escalate hints, this doesn't override the final route -- it
# just makes the tool call the model should already be making more likely.
_MERCHANT_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?:\s*&?\s*[A-Z][a-z]+)+\b")

# Deliberately narrow to "does policy X apply to MY situation" phrasing, not
# any word that happens to co-occur with orders -- an earlier, broader
# version (also matching "payment"/"order") wrongly fired on v01 ("when is
# my next payment", a pure lookup with no policy question at all) and pushed
# it into an unwanted search_policy call. Scoped to the actual pattern
# SYSTEM_PROMPT's routing rule names: reschedule eligibility, refund status,
# a missed/failed payment.
_ORDER_TOPIC_WORDS = (
    "refund", "return", "reschedule", "push back", "postpone",
    "missed", "failed payment", "where is my money", "where's my money",
)


def likely_needs_order_lookup(question: str) -> bool:
    q_lower = question.lower()
    has_order_topic = any(w in q_lower for w in _ORDER_TOPIC_WORDS)
    references_specific_order = "my order" in q_lower or bool(_MERCHANT_NAME_RE.search(question))
    return has_order_topic and references_specific_order


def find_referenced_order(question: str, user_id: str):
    """
    If `question` names a merchant that matches one of user_id's own orders,
    return that order dict structurally (no model call). A hint that the
    model *should* look up an order is not the same as it reliably doing so
    (v10: even an explicit "you MUST call get_order" system note didn't
    always produce the tool call) -- this fetches the grounding data itself
    so the reasoning node can hand it to the model directly instead of
    hoping the model asks for it.
    """
    import orders_store

    m = _MERCHANT_NAME_RE.search(question)
    if not m:
        return None
    merchant_guess = m.group(0).strip().lower()

    for order in orders_store.get_orders_for_user(user_id):
        merchant = str(order.get("merchant", "")).lower()
        if merchant and (merchant in merchant_guess or merchant_guess in merchant):
            return order
    return None


class RouteDecision(NamedTuple):
    forced_escalate: bool
    category: Optional[str]
    matched_phrase: Optional[str]
    extra_required_phrases: List[str]


def classify(question: str) -> RouteDecision:
    """
    Scan `question` for a known escalation-category hint phrase.

    Longest-phrase-first matching within each category so a more specific
    hint (e.g. "why was my order declined") isn't shadowed by a shorter one
    that happens to be a substring of it.
    """
    q = question.lower()

    for category, spec in ESCALATION_CATEGORIES.items():
        hints = sorted(spec["hints"], key=len, reverse=True)
        for phrase in hints:
            if phrase in q:
                return RouteDecision(
                    forced_escalate=True,
                    category=category,
                    matched_phrase=phrase,
                    extra_required_phrases=list(spec["extra_required"]),
                )

    return RouteDecision(
        forced_escalate=False,
        category=None,
        matched_phrase=None,
        extra_required_phrases=[],
    )


def required_phrases_for(decision: RouteDecision) -> List[str]:
    """
    Every literal phrase the final answer must satisfy for a forced-escalate
    decision: the universal escalate phrase (any one of) plus every
    category-specific extra_required phrase (all of, verified individually).
    """
    if not decision.forced_escalate:
        return []
    return list(UNIVERSAL_ESCALATE_PHRASES) + list(decision.extra_required_phrases)
