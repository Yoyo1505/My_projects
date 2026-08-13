"""
graph.py - Control plane entry point: the multi-node graph across planes that
replaced the original submission's single flat tool-calling loop.

    question, user_id
          |
          v
    +-----------+     control plane
    | router.py |     deterministic hint match on the raw question text.
    +-----------+     Forces route="escalate" for known-shaped asks
          |            (fraud/hardship/limit/dispute/fee-waiver/injection)
          |            independent of what the model decides to do --
          |            closes the v09 flakiness named in README.md.
          v
    +----------------+   specialist plane, backed by the model plane
    | agent.py       |   (llm_client.py -> Ollama local/cloud). Tool calls
    | reasoning_node |   inside this node hit the data plane:
    +----------------+     orders_store.py  (authorization-guarded lookups)
          |                retrieval.py     (BM25 policy search)
          v
    +-------------+     guardrail plane. Deterministic (no 2nd model call --
    | verifier.py |     see verifier.py's docstring for why). Enforces
    +-------------+     escalation phrasing, quotes policy terms the draft
          |              answer dropped, disambiguates dates.
          v
    {route, answer}

Each plane only talks to the plane below it -- router.py and verifier.py
don't know about each other, agent.py doesn't import either. That one-way
dependency is what makes this a graph instead of one big function: any node
can be swapped (e.g. verifier.py rebuilt by Grok Build CLI, see
PROMPTS_ITERATION_2.md) without the others needing to change.
"""

from typing import Dict

import router
from agent import reasoning_node
from verifier import verify


def run(question: str, user_id: str) -> Dict[str, str]:
    decision = router.classify(question)

    system_note = ""
    preloaded: Dict[str, list] = {}
    if decision.forced_escalate:
        system_note = (
            f"ROUTER NOTE: this message matched the '{decision.category}' "
            f"escalation category (phrase: '{decision.matched_phrase}'). "
            f"You must call escalate() with a reason. Still call any order/"
            f"policy tools needed so your answer explains real context "
            f"(e.g. dispute windows, order status) -- explaining is fine, "
            f"taking the action itself is not."
        )
    elif router.likely_needs_order_lookup(question):
        order = router.find_referenced_order(question, user_id)
        if order is not None:
            preloaded = {"get_order": [order]}
        system_note = (
            "ROUTER NOTE: this question references policy applying to a "
            "specific order. You MUST also call search_policy before "
            "answering -- do not answer from policy text alone, and apply "
            "it to the order data provided."
        )

    result = reasoning_node(question, user_id, system_note=system_note, preloaded=preloaded)

    final_route, final_answer = verify(
        question=question,
        route=result["route"],
        answer=result["answer"],
        tool_results=result["tool_results"],
        router_decision=decision,
    )

    return {"route": final_route, "answer": final_answer}
