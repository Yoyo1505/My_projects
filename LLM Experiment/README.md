# SplitWave Support Agent

An LLM-powered customer support assistant for SplitWave (Buy Now, Pay Later) shoppers. It handles policy inquiries, order & payment status lookups, and human support escalations while enforcing structural data guardrails.

---

## Prerequisites

1. **Ollama**: Download and run [Ollama](https://ollama.com/) locally (`http://localhost:11434`).
2. **Model**: Pull the local LLM model:
   ```bash
   ollama pull llama3.1:8b
   ```
3. **Environment Variables** (Optional):
   - `OLLAMA_MODEL`: Target Ollama model name (default: `llama3.1`).
   - `OLLAMA_TIMEOUT_S`: HTTP request timeout in seconds (default: `60`).

---

## Running the Agent & Evaluation

### Run Test Cases
Execute the standard runner contract against test cases:
```bash
python run_cases.py CASES_-_golden_visible.jsonl answers.jsonl
```

### Run Benchmark Evaluation
Evaluate generated answers against golden requirements (route accuracy, `must_include`, `must_not_include` assertions):
```bash
python eval.py CASES_-_golden_visible.jsonl answers.jsonl
```

### Run Structural Guardrail Tests
Verify cross-account authorization logic and non-existent entity handling:
```bash
python test_authorization.py
```

---

## File Layout

- **`agent.py`**: Core LLM orchestration loop, tool execution, and deterministic route inference (`policy` | `tool` | `both` | `escalate`).
- **`orders_store.py`**: Data store layer for `DATA-orders.json` enforcing function-level authorization filters.
- **`retrieval.py`**: Fast lexical BM25/keyword retrieval system over policy documentation.
- **`prompts.py`**: System prompt guidelines and escalation rules.
- **`run_cases.py`**: Standard batch evaluation CLI contract (`<input.jsonl> <output.jsonl>`).
- **`eval.py`**: Quantitative evaluation script for routes and regex assertions.
- **`test_authorization.py`**: Test script verifying cross-account access isolation.
- **`DATA-orders.json`**: Mock database containing user profiles, order details, and payment schedules (`today = 2026-07-01`).
- **`POLICY_-*.md`**: 12 policy documents covering payment schedules, disputes, refunds, card usage, and security.
- **`DECISIONS.md`**: Decision records (ADRs) covering retrieval approach, local inference, and structural security boundaries.
- **`PROMPTS.md`**: Record of prompts used during system development and model guidance.

*(Post-submission only — see "Post-Submission Iteration" below: `router.py`, `llm_client.py`, `verifier.py`, `graph.py`, `PROMPTS_ITERATION_2.md`, `DECISIONS_ITERATION_2.md`.)*

---

## Results

- **Run 1** (`answers_run1.jsonl`, local-infra bugs fixed, prompt not yet tuned): **4/10** on the visible golden set.
- **Run 2 / final** (`answers_run2.jsonl`, after tightening escalation + both-route rules in `prompts.py`): **7/10**.
- Earliest attempt (`answers_run0_infra_fail.jsonl`) is kept as-is: 0/10, pure infrastructure failure (wrong default model tag + a 3s client timeout copied from the *production* latency target into local dev code) — no model behavior signal in it, see `PROMPTS.md` for the diagnosis trail.

## Honestly Unfinished

- **3/10 still failing** (`v01`, `v02`, `v09` in run 2): `v01` gets the right route/amount but phrases the date as `07/11` instead of a form matching `2026-07-11|july 11`; `v02` doesn't reliably quote the exact "25%" / "every two weeks" policy language; `v09` (fraud report) intermittently routes to `policy` instead of `escalate` — the escalation rule likely needs a firmer trigger for "there's an order I never placed" phrasing specifically, not just the hint list.
- **Prompt-injection resistance** — rules are named explicitly in the system prompt, but there's no automated red-team pass proving the model refuses *novel* phrasings, only the ones anticipated.
- **Latency at scale** — even the hosted path here is a shared/dev-tier endpoint with unmeasured concurrency behavior; before trusting it at 100k req/day it needs real load testing (see `DECISIONS.md` #2).
- **No caching layer** — repeated/similar questions re-run retrieval + full model inference every time; a cache keyed on (user_id, normalized question) would cut both cost and p95 in production.
- **Single visible-set run per iteration** — only one iteration cycle fit in the time budget; a hidden-set-shaped stress test (paraphrases, more hostile inputs) is the natural next step.

---

## Post-Submission Iteration (not part of the graded submission)

Everything above this line is exactly what was sent. The take-home was
submitted; everything below is a personal follow-up pass done the same day,
kept in a separate section (and separate files) so the original artifact
isn't rewritten after the fact. See `PROMPTS_ITERATION_2.md` and
`DECISIONS_ITERATION_2.md` for the full log and decision records.

**What changed:** the single flat tool-calling loop became an explicit graph
across four planes — control (`router.py`), specialist (`agent.py`, now a
`reasoning_node`), model (`llm_client.py`), and guardrail (`verifier.py`) —
orchestrated by `graph.py`, which `run_cases.py`/`run_checkpoint.py` now
call. `orders_store.py` and `retrieval.py` (the data plane) are unchanged.
See `graph.py`'s module docstring for the diagram.

**Result:** **10/10** on the visible golden set, confirmed on two
consecutive runs (`answers_run11.jsonl`, `answers_run12.jsonl`), up from the
submitted 7/10 (`answers_run2.jsonl`). Getting there was not one clean pass —
`answers_run3.jsonl` through `answers_run10.jsonl` are kept as the real
iteration trail (6/10 → 9/10 → 8/10 → 9/10 → 7/10 → 10/10 → 10/10), each dip
a genuine new failure mode this Ollama Cloud model (`gpt-oss:20b`) produced,
not noise glossed over. Full trail, bug-by-bug, in
`PROMPTS_ITERATION_2.md`. Grok Build CLI and Gemini CLI were both
unavailable this session (Grok: billing balance exhausted; Gemini: its free
tier was deprecated mid-session) — all of this iteration was done directly
rather than blocked on either, see `PROMPTS_ITERATION_2.md` for the
handoff prompts that are still there ready to use once either is available.

All three of the original "Honestly Unfinished" failures above (v01, v02,
v09), plus one found *during* this iteration (v10), now pass:

- **v01** — two distinct bugs, found on different runs: (1) Unicode
  narrow-no-break-spaces inside the model's own output (e.g. between "July"
  and "11") silently broke plain-ASCII regex checks; (2) on a later run, the
  model stated an outright wrong date. Fixed with two layers: `llm_client
  .normalize_text()` strips typographic whitespace/punctuation (also caught
  smart quotes/apostrophes, which broke v04 the same way with `can't`), and
  `verifier.py`'s `_normalize_dates` now always asserts the ground-truth
  due date from the tool result rather than trusting the model's prose,
  which fixes both the formatting bug and the hallucination.
- **v02** — fixed by the categorized escalation hints removing routing
  ambiguity that let phrasing-only fixes regress across runs.
- **v05** — the escalation-phrase check itself was under-strict (accepted
  bare "specialist" without "human" before it, which the golden regex
  doesn't); tightened `UNIVERSAL_ESCALATE_PHRASES` in `prompts.py` to match
  what's actually graded.
- **v09** — fixed structurally: `router.py` pins `route="escalate"` for
  known fraud/hardship/limit/dispute/fee-waiver/injection phrasing before
  the model runs, instead of relying on the model reliably calling the
  `escalate()` tool every time.
- **v10** — the model doesn't reliably call an order-lookup tool for
  refund-status questions the way it does for reschedule questions, even
  when told to explicitly. Fixed structurally, not by more prompt wording:
  `router.find_referenced_order()` fetches the matching order itself
  (scoped to the authenticated user_id, same authorization guard as
  everywhere else) and hands it to the reasoning node directly — closes the
  gap the same way `orders_store.py`'s authorization filter does: don't
  rely on the model doing the right thing, make the right thing already
  true.

**Also unfinished, same as before:** no automated prompt-injection red-team
pass, no caching layer, no real load testing at 100k q/day — the guardrail
plane added this pass is deterministic specifically so it doesn't make the
cost/latency picture worse (see `DECISIONS_ITERATION_2.md` #1), but doesn't
by itself address any of these three. And two clean runs is evidence, not
proof — this model's variance across the 12 total runs this session means a
13th run failing something new would not be shocking.
