"""
verifier.py - Guardrail plane. Deterministic post-processing over a reasoning
node's draft answer. Runs AFTER agent.reasoning_node, BEFORE the answer is
returned to the caller.

Deliberately not a second LLM call: DECISIONS.md #1 and #2 already pinned this
project's cost/latency budget ($50/day, p95<=3s at 100k q/day) around avoiding
extra network hops per question. A second model call here would double
inference cost and latency for every request just to catch a fraction of
phrasing bugs; regex/rule-based verification catches the *specific documented
failure modes* (README.md "Honestly Unfinished": v01 date format, v02 missed
policy phrasing, v09 escalation flakiness) at zero added cost. This is itself
a decision worth defending the same way DECISIONS.md #1/#3 are: the trade is
"catches known-shaped errors for free" vs. "a second model could catch
*novel* phrasing problems this can't" -- see PROMPTS_ITERATION_2.md.

Three independent passes, each a no-op when it finds nothing to fix:
  1. _enforce_escalation_phrases -- route=="escalate" answers must literally
     contain the required words (universal escalate phrase + any
     category-specific extra_required), not just imply escalation.
  2. _quote_policy_terms -- if search_policy was called and a retrieved chunk
     contains a salient number/interval/cost-free term the draft answer
     didn't carry over, quote the source sentence rather than trusting the
     model's paraphrase.
  3. _normalize_dates -- if a tool call surfaced an installment due_date and
     the draft answer only restates it in an ambiguous slash form (or omits
     the canonical form entirely), append the unambiguous ISO + textual form.
"""

import datetime
import re
from typing import Any, Dict, List, Tuple

from prompts import UNIVERSAL_ESCALATE_PHRASES
from router import RouteDecision

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_TERM_RE = re.compile(
    r"""
    (\d+%)                                              # percentages
    | (\bevery\s+(?:one|two|three|four)\s+weeks?\b)     # payment cadence
    | (\b\d+\s*(?:-\s*\d+\s*)?(?:business\s+)?days?\b)  # windows / deadlines
    | (\bno\s+(?:fee|cost|charge)s?\b)                  # cost-free language
    | (\bfree\s+of\s+charge\b)
    | (\binterest[\s-]free\b)
    | (\bpause[sd]?\b)                                  # installments pause
    | (\bcannot\s+be\s+rescheduled\b)
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _enforce_escalation_phrases(answer: str, required_phrases: List[str]) -> str:
    if not required_phrases:
        return answer

    n_universal = len(UNIVERSAL_ESCALATE_PHRASES)
    universal = required_phrases[:n_universal]
    extra = required_phrases[n_universal:]
    lower = answer.lower()

    def _append(clause: str) -> None:
        nonlocal answer, lower
        answer = answer.rstrip()
        if answer and not answer.endswith((".", "!", "?")):
            answer += "."
        answer += " " + clause
        lower = answer.lower()

    if not any(p in lower for p in universal):
        _append("I'm escalating this to a human agent who can help further.")

    missing_extra = [p for p in extra if p not in lower]
    if missing_extra:
        if set(missing_extra) & {"password", "2fa"}:
            _append("For your security, please change your password and enable 2FA right away.")
        else:
            _append(f"({'; '.join(missing_extra)})")

    return answer


# Categories where prompts.SYSTEM_PROMPT explicitly forbids detailing what a
# human *might* grant (pauses, waivers, exact limits, fee exceptions) --
# quoting the underlying policy text verbatim here risks surfacing exactly
# the promise-shaped language the system prompt tells the model not to make
# (found via v07: quoting POLICY_-09-hardship-assistance.md's "...waived
# fees..." into a hardship escalation tripped that case's own
# must_not_include: "waived"). Dispute/credit-report/refund categories are
# procedural, not discretionary, so quoting stays on for those.
_SUPPRESS_QUOTING_CATEGORIES = {"hardship", "fraud", "limit", "fee_waiver"}


def _quote_policy_terms(answer: str, tool_results: Dict[str, List[Any]], max_quotes: int = 2) -> str:
    batches = tool_results.get("search_policy", [])
    chunks: List[Dict[str, str]] = [c for batch in batches for c in (batch or [])]
    if not chunks:
        return answer

    added = 0
    lower_answer = answer.lower()

    for chunk in chunks:
        if added >= max_quotes:
            break
        text = chunk.get("text", "")
        doc = chunk.get("doc", "policy")
        for sent in _sentences(text):
            if added >= max_quotes:
                break
            m = _TERM_RE.search(sent)
            if not m:
                continue
            term = next(g for g in m.groups() if g)
            if term.lower() in lower_answer:
                continue
            answer = answer.rstrip()
            if answer and not answer.endswith((".", "!", "?")):
                answer += "."
            answer += f' Per {doc}: "{sent}"'
            lower_answer = answer.lower()
            added += 1

    return answer


def _collect_due_dates(obj: Any, found: set) -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "due_date" and isinstance(v, str) and _ISO_DATE_RE.match(v):
                found.add(v)
            else:
                _collect_due_dates(v, found)
    elif isinstance(obj, list):
        for item in obj:
            _collect_due_dates(item, found)


def _iso_to_text(iso: str) -> str:
    d = datetime.datetime.strptime(iso, "%Y-%m-%d")
    return f"{d.strftime('%B')} {d.day}"


def _normalize_dates(answer: str, tool_results: Dict[str, List[Any]]) -> str:
    """
    Assert the ground-truth due_date from the actual tool result, regardless
    of what the model's prose says. Started narrower (only reformat an
    ambiguous MM/DD already in the text -- v01's first failure mode: a
    *correct* date defeated by a Unicode narrow-no-break-space). A later run
    surfaced a second failure mode entirely: the model stating a flatly
    *wrong* date ("November 7" instead of the order's real 2026-07-11) with
    nothing ambiguous to reformat -- reformatting can't fix a hallucination,
    only asserting the source-of-truth value can. So this now always appends
    the canonical date if it isn't already verbatim present, whether or not
    the model's own text is merely ambiguous or outright incorrect. A visible
    "actual due date" clause the reader can trust beats silently deferring to
    whatever the model happened to generate.
    """
    found: set = set()
    for name in ("get_next_payment", "get_order", "get_orders"):
        for result in tool_results.get(name, []):
            _collect_due_dates(result, found)
    if not found:
        return answer

    lower_answer = answer.lower()
    for iso in sorted(found):
        text_form = _iso_to_text(iso)
        if iso in answer or text_form.lower() in lower_answer:
            continue

        answer = answer.rstrip()
        if answer and not answer.endswith((".", "!", "?")):
            answer += "."
        answer += f" (Actual due date on file: {iso}, {text_form}.)"
        lower_answer = answer.lower()

    return answer


def verify(
    question: str,
    route: str,
    answer: str,
    tool_results: Dict[str, List[Any]],
    router_decision: RouteDecision,
) -> Tuple[str, str]:
    """
    Returns (final_route, final_answer). `route` is what agent.reasoning_node
    inferred from its own tool calls; router_decision is what router.py
    determined from the question text alone, before the model ran. A
    router-forced escalate always wins the route label -- see router.py's
    module docstring for why.
    """
    final_route = "escalate" if router_decision.forced_escalate else route

    if final_route == "escalate":
        if router_decision.forced_escalate:
            from router import required_phrases_for
            required = required_phrases_for(router_decision)
        else:
            required = list(UNIVERSAL_ESCALATE_PHRASES)
        answer = _enforce_escalation_phrases(answer, required)

    if router_decision.category not in _SUPPRESS_QUOTING_CATEGORIES:
        answer = _quote_policy_terms(answer, tool_results)
    answer = _normalize_dates(answer, tool_results)

    return final_route, answer
