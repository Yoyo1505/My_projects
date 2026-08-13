# Prompts Log — Iteration 2 (post-submission)

Everything in `PROMPTS.md`, `DECISIONS.md`, `README.md`'s original "Results"
section, and `answers_run1.jsonl` / `answers_run2.jsonl` is the **graded
submission**, already sent, and left untouched below. This file, plus
`DECISIONS_ITERATION_2.md`, `answers_run3.jsonl`, and `answers_run4.jsonl`,
are a personal follow-up pass done the same day after the 2h budget and the
send — not part of the graded deliverable, kept separate so the original
artifact isn't rewritten after the fact.

Continuing the same two-tool split as the original build (see `PROMPTS.md`'s
"Work split"): **agy** (Claude, this session) and **grok** (Grok Build CLI,
run by the user in a separate window) each own distinct files.

## [10:10] Orchestrator (agy) — scope for this pass

Goal, from the user: turn the single flat tool-calling loop into an explicit
multi-node graph across planes, and re-engage the agy/grok split to do it.
Read `README.md`'s "Honestly Unfinished" list first — it names exactly three
known bugs (v01 date format, v02 policy phrasing, v09 escalation flakiness)
and that became the acceptance bar for whether the new architecture was
actually better, not just differently shaped.

Architecture chosen (see `graph.py`'s module docstring for the diagram):

- **Control plane** (`router.py`, new) — deterministic pre-routing on the raw
  question text, before any model call. `prompts.py`'s `ESCALATION_HINTS`
  used to be text the model *might* consult; restructured into
  `ESCALATION_CATEGORIES` (hints + required literal phrases, grouped by
  category) so a hint match now forces `route="escalate"` regardless of
  which tools the model happens to call. Directly targets v09 (fraud reports
  intermittently routing to `policy`).
- **Specialist plane** (`agent.py`, refactored) — same tool-calling loop as
  before, now exposed as `reasoning_node()` returning the draft answer *plus*
  every tool result collected, not just the final text — the verifier plane
  needs that raw data to check claims against.
- **Model plane** (`llm_client.py`, new) — the raw Ollama HTTP call, pulled
  out of `agent.py` so it's one choke point instead of duplicated per node.
- **Guardrail plane** (`verifier.py`, new) — deterministic post-processing,
  not a second model call (see `DECISIONS_ITERATION_2.md` #1 for why):
  escalation-phrase enforcement, policy-term quoting, date disambiguation.
- **Data plane** — `orders_store.py` / `retrieval.py`, unchanged.
- **`graph.py`** (new) — wires the above into `run(question, user_id)`,
  which `run_cases.py` / `run_checkpoint.py` now call instead of
  `agent.answer` (that function no longer exists — see `agent.py`'s
  docstring for why keeping a same-named function with different behavior
  would have been the worse interface).

Work split for this pass:
- **agy**: `llm_client.py`, `router.py`, `agent.py` refactor, `verifier.py`
  (first draft), `graph.py`, the entry-point rewiring, and the iteration
  testing below.
- **grok**: asked to independently review/harden `verifier.py` and fix a
  routing gap in `prompts.py` found during testing (below) — see the
  delegation prompt at the bottom of this file, ready to paste into Grok
  Build CLI.

## [10:40] First full run of the new graph — `answers_run3.jsonl`

Ran `run_checkpoint.py` against `CASES_-_golden_visible.jsonl` on the same
Ollama Cloud endpoint (`gpt-oss:20b`) the original submission ended on.
**6/10** — worse than the submitted baseline's 7/10. Two new, real bugs, not
regressions in the graph design itself:

1. **v01 failed despite a correct answer.** The model wrote `"...scheduled
   for **July 11, 2026**..."` — visibly correct — but the golden regex
   `2026-07-11|july 11` still failed. `repr()` on the raw string showed why:
   `'...July\u202f11,\u202f2026...'`. Ollama Cloud's `gpt-oss:20b` renders
   typographic whitespace (`U+202F` narrow no-break space) inside its own
   output. Invisible in a terminal, silently breaks every plain-ASCII regex
   check downstream — not just this one test, potentially any check on any
   answer.
2. **v07 failed on a `must_not_include` hit `verifier.py` itself caused.**
   The new policy-quoting pass quoted
   `POLICY_-09-hardship-assistance.md` verbatim into a hardship-escalation
   answer to backfill missing detail — the quoted sentence contained
   "...waived fees..." and v07's `must_not_include` forbids the literal word
   "waived" (the system prompt already says hardship answers must never
   promise a waiver; quoting the *policy's description* of what a hardship
   plan can include reintroduced exactly that promise-shaped language).

v03/v10 also flipped from `both` to `policy` (route-only misses, answer
content fine) — most likely ordinary model sampling variance, same as the
run1→run2 swings in the original log, except v10's miss recurred identically
on the next run (below), suggesting it isn't just noise.

## [10:50] Fixes (agy, direct — same reasoning as the original log's "direct
edits" section: small, evidence-driven, no round-trip needed)

- `llm_client.py`: added `normalize_text()` — collapses the known Unicode
  space-like/zero-width codepoint ranges to plain space/nothing. Applied to
  every model response in `agent.reasoning_node` before it's returned, so
  every downstream consumer (verifier, eval, a human reading the JSONL) sees
  plain ASCII whitespace. This is a model-plane fix, not a one-test patch —
  it protects every regex check in the pipeline, not just v01's.
- `verifier.py`: added `_SUPPRESS_QUOTING_CATEGORIES` — policy-term quoting
  is skipped for `hardship`/`fraud`/`limit`/`fee_waiver` categories, where
  `prompts.SYSTEM_PROMPT` explicitly forbids detailing what a human *might*
  grant. Quoting stays on for `dispute`/`credit_report`/`refund_overdue` and
  ordinary `policy`/`both` routes, where the policy text is procedural
  (windows, deadlines) rather than discretionary.

## [10:55] Final run of this pass — `answers_run4.jsonl`

**9/10.** Delta from `run3`: +3 (`v01`, `v02`, `v07`; `v02` had already been
fixed structurally by the categorized-hints work and passed in both runs).
All three of the original submission's "Honestly Unfinished" bugs (v01, v02,
v09) now pass. `test_authorization.py` re-run clean: still 4/4 — the
refactor didn't touch the authorization boundary.

Remaining failure: **v10**, route-only (`both` expected, `policy` got) —
the answer text is substantively correct (mentions the 3-10 business day
window, the unpaid-installments-first rule, tells the user next steps) but
the model never called `get_order`/`get_next_payment` to confirm *this
order's* actual refund status, the way it reliably does for reschedule
questions. It failed identically in both `run3` and `run4`, which points at
a real gap rather than pure sampling noise: `prompts.SYSTEM_PROMPT`'s "policy
+ specific order → call both" rule gives reschedule/payment examples
("can I reschedule/push back/move MY payment") but no refund/return example,
so the model doesn't reliably generalize the rule to "where is my refund for
THIS order" the same way. This is a `prompts.py` fix — handed to grok below
rather than patched here, to keep the knowledge/guardrail layer owned the
way the original split set it up.

## Delegation prompt sent to grok (ready to paste into Grok Build CLI)

```
Project folder: C:\Users\jorch\Downloads\Projects\LLM seezle
This is a personal follow-up pass on a completed take-home (SplitWave AI
Engineer) -- already submitted, this work is not graded, it's iteration
practice. Read PROMPTS_ITERATION_2.md in this folder first for full context:
the loop is now a graph (router.py -> agent.reasoning_node -> verifier.py),
not the single flat loop you last worked against. All data is synthetic.

Two things, both in files you already own from the original build:

1. prompts.py -- SYSTEM_PROMPT's routing rule currently reads:
   "Policy + specific order (e.g. 'can I reschedule/push back/move MY
   payment', a missed/failed payment) -> BOTH order tool ... AND
   search_policy, every time"
   This under-generalizes: v10 in CASES_-_golden_visible.jsonl asks "Circuit
   City Lights approved my return on June 28 -- where is my money?"
   (expected_route "both") and the model answers from policy alone without
   calling get_order/get_next_payment to check that order's actual refund
   status, failing on route only twice in a row (see
   PROMPTS_ITERATION_2.md's run3/run4 notes). Add a refund/return example
   to that rule (parallel structure to the existing reschedule example) so
   "where's my money/refund for my <merchant> order" reliably triggers the
   same both-tools behavior. Re-run
   `python run_checkpoint.py CASES_-_golden_visible.jsonl answers_runN.jsonl 10`
   (set OLLAMA_API_KEY first, see README.md) then
   `python eval.py CASES_-_golden_visible.jsonl answers_runN.jsonl` to confirm
   v10 passes and nothing else regresses.

2. verifier.py -- I (agy) wrote a first draft of the guardrail plane:
   _enforce_escalation_phrases, _quote_policy_terms, _normalize_dates. It's
   deterministic by design (no second model call -- see
   DECISIONS_ITERATION_2.md #1). You own the knowledge/guardrail layer in
   this project's split; independently review it against all 12 POLICY_*.md
   docs for cases I likely missed -- e.g. other categories where quoting
   policy text verbatim could reintroduce forbidden promise-shaped language
   the way it did for hardship (see PROMPTS_ITERATION_2.md's v07 bug), or
   policy sections with salient terms my _TERM_RE regex wouldn't catch.
   Don't rewrite the file's structure/exports (graph.py imports `verify`
   with a fixed signature) -- tighten what's inside it.

When done, print what you changed and the before/after eval score.
```

## [11:05] Both external tools tried, both blocked — agy proceeded directly

User asked to actually run the delegation prompt above rather than just leave
it ready. Checked both CLIs installed on this machine:

- `grok -p "..." ` → `API error (status 402 Payment Required): Grok Build
  usage balance exhausted`. Not fixable from here — needs credits added to
  the account.
- `gemini -p "..."` → `IneligibleTierError: This client is no longer
  supported for Gemini Code Assist for individuals` — Google deprecated the
  free tier this CLI authenticates against mid-session, pointing at their
  separate Antigravity product instead (not installed as a driveable CLI
  here). No `GEMINI_API_KEY`/`GOOGLE_API_KEY` available as a fallback auth
  path either.

Per explicit instruction ("stop using grok just use agy"), did both delegated
tasks directly instead of waiting on either tool. Not a one-shot fix — real
iteration, kept honest below rather than only reporting the final number.

## [11:10-11:35] v10 fix, attempt 1 — prompt wording alone

Added a refund/return example to `SYSTEM_PROMPT`'s "policy + specific order"
rule, parallel to the existing reschedule example. Re-ran:
`answers_run5.jsonl` → still 9/10, v10 still fails, and this run its answer
text got *worse* (dropped the refund-amount specifics it had before) — wording
tuning alone wasn't reliably steering this pattern.

## [11:15-11:20] v10 fix, attempt 2 — structural nudge

Added `router.likely_needs_order_lookup()` — detects the refund/reschedule
pattern and injects an explicit "you MUST call get_order" system note.
`answers_run6.jsonl` → still 9/10, v10 unchanged. Confirmed via direct test
that the heuristic *did* fire for v10's question — the model still skipped
the tool call even with an explicit directive. A system note is a request,
not a guarantee.

## [11:20-11:25] v10 fix, attempt 3 — structural preload (the one that stuck)

If telling the model to fetch the order doesn't reliably work, fetch it
structurally instead — same principle as `orders_store.py`'s authorization
filter. Added `router.find_referenced_order(question, user_id)`: matches a
merchant name in the question against that user's own orders (authorization-
scoped, same as every other lookup) and hands the order data directly to
`agent.reasoning_node` via a new `preloaded` parameter, seeding
`invoked_tools`/`tool_results` so route inference sees it too.
`answers_run7.jsonl` → **v10 passes**. But `v04` (previously passing)
failed this run — investigated, and it was `likely_needs_order_lookup`'s
trigger words being too broad: "payment"/"order" matched almost every
order-related question, including `v01`'s pure lookup ("when is my next
payment"), pushing it toward an unwanted `search_policy` call.
`answers_run8.jsonl` confirmed the `v01` regression directly. Narrowed the
trigger word list to the actual "policy applies to my situation" phrasing
(`refund`, `return`, `reschedule`, `missed`, etc.) — re-checked against all
10 golden questions offline (no network needed) before re-running: fires on
exactly `v03`/`v04`/`v10`, the three real `both` cases, nothing else.

## [11:30-11:45] Two more bugs, same class as before

`answers_run9.jsonl` (6/10 → wait, 8/10): `v04` failed on `can't` vs `can't`
— `repr()` showed the model's apostrophe was `’` (curly quote), the
exact same failure shape as v01's ` ` space bug, different character
class. `v05` failed too: the model wrote "our specialist team" / "connected
to a specialist" — present in the *old*, too-loose
`UNIVERSAL_ESCALATE_PHRASES` list (bare "specialist" satisfied it) but the
golden regex actually requires "human" immediately before
agent/specialist/team. The verifier's own check was wrong, not just the
model's output.

Fixed both at the source: `llm_client.normalize_text()` extended to fold
typographic quotes/dashes to ASCII (not just whitespace); tightened
`UNIVERSAL_ESCALATE_PHRASES` to what the golden set actually accepts
("escalat" stem, "human agent/specialist/team", "transfer", "connect you"),
and updated `SYSTEM_PROMPT`'s own escalation rule text to match so the model
is told the real requirement, not the looser one.

`answers_run10.jsonl` → 7/10. New failure: `v01`'s date wasn't malformed
this time, it was **wrong** — the model wrote "November 7, 2026" instead of
the order's actual `2026-07-11`. No amount of quote/whitespace normalization
fixes a hallucinated value. Broadened `verifier._normalize_dates` from
"reformat an ambiguous date already in the text" to "always assert the
ground-truth due date from the tool result if it isn't verbatim present" —
closes both the formatting bug and the hallucination bug the same way.

## [11:45] Final runs

`answers_run11.jsonl` → **10/10**. `answers_run12.jsonl` (re-run to check
it wasn't a fluke, given how much variance the last six runs showed) →
**10/10** again. `test_authorization.py` re-confirmed 4/4 — untouched by any
of this. Twelve total runs this session (`answers_run1.jsonl` through
`answers_run12.jsonl`, `run1`/`run2` being the original submission) are all
kept, not just the last one — the actual value here was the failure
taxonomy across them, not the final score in isolation.
