# Prompts Log

All times local (America/... UTC-06:00). Budget: 2h, started 2026-08-13 07:54:29, hard stop ~09:54:29.

## [07:54] Orchestrator (Claude/agy, this session) — scaffolding plan
Scanned `PROMPT.md`, `SUBMISSION.md`, `DATA-orders.json`, `CASES_-_golden_visible.jsonl`, and the 12 `POLICY_*.md` files to derive the architecture below before writing any delegated prompt.

Architecture chosen:
- `orders_store.py` — deterministic data access + authorization guard (an order lookup for a `user_id` that doesn't own it returns nothing, regardless of what the model asks).
- `retrieval.py` — lightweight keyword/BM25 search over policy docs (no embedding API — keeps cost/latency near zero, informs the cost ADR).
- `prompts.py` — system prompt, grounding + escalation rules, few-shot guardrail examples.
- `agent.py` — tool-calling loop against a local Ollama model (no cloud API key available in this environment; user is installing Ollama).
- `run_cases.py` — the required contract: `{id, question, user_id}` in, `{id, route, answer}` out.
- `eval.py` — scores an answers file against golden `must_include`/`must_not_include` regexes, for the iteration-evidence deliverable.

Work split (two AI coding tools, running concurrently in separate visible terminal windows, per the brief's "AI tooling: expected"):
- **agy** (Claude-based CLI) → `orders_store.py`, `agent.py`, `run_cases.py`, `eval.py` (the harness + orchestration loop).
- **grok** (Grok Build CLI) → `retrieval.py`, `prompts.py` (the knowledge/guardrail layer).

## [07:56] Prompt sent to agy (interactive window)

```
Project folder: C:\Users\jorch\Downloads\Projects\LLM seezle
This is a real take-home for a job interview (SplitWave AI Engineer). Read PROMPT.md
in that folder first -- it is the full brief and overrides anything below if they
conflict. A second AI tool (Grok Build) is concurrently writing retrieval.py and
prompts.py in the same folder -- do NOT touch those two files, but code against the
interface below. All data is synthetic (see PROMPT.md).

Your files (all in the project root):

1. orders_store.py -- loads DATA-orders.json (fields: generated_seed, today, users[],
   orders[] with installments[]). Expose:
   - load_orders(path="DATA-orders.json") -> dict (cache in module state)
   - get_user(user_id) -> dict | None
   - get_orders_for_user(user_id) -> list[dict]
   - get_order(user_id, order_id) -> dict | {"error": "not found"}  -- CRITICAL
     GUARDRAIL: if order_id exists but belongs to a different user_id, this must
     return the same "not found" error, never the real order. This must hold no
     matter what the calling model asks -- it is enforced here, not by prompting.
   - get_next_payment(user_id, order_id=None) -> the next upcoming or failed
     installment (soonest due_date with status in {upcoming, failed}) across the
     user's orders, or within one order if order_id given and owned by user_id.
   Use `today` from the JSON as "now" for date comparisons.

2. agent.py -- the LLM loop, calling a local Ollama server (OpenAI/Ollama-style tool
   calling) at http://localhost:11434/api/chat. Model name from env var
   OLLAMA_MODEL, default "llama3.1". (Ollama may still be downloading -- write the
   code so it's correct once it's up; a clear connection-error message is fine if
   it's not.)
   - Import SYSTEM_PROMPT and ESCALATION_HINTS from prompts.py, search_policy from
     retrieval.py (both being built by the other agent -- assume:
     search_policy(query: str, k: int = 3) -> list[{"doc": str, "text": str}]).
   - Define tools (JSON-schema function-calling format) wrapping: get_orders,
     get_order, get_next_payment, search_policy, and escalate(reason: str) -- a tool
     the model calls when a request must go to a human; it just returns a
     confirmation string, no side effects needed.
   - Loop: system prompt + user question (with the caller's user_id passed as
     context, not as something the model can override) -> let the model call tools
     (cap at ~5 tool-call turns) -> final natural-language answer.
   - After the loop, infer `route` deterministically from which tools were actually
     invoked (not from asking the model to self-report): escalate called ->
     "escalate"; search_policy + any order tool -> "both"; search_policy only ->
     "policy"; any order tool only -> "tool"; nothing called -> "policy" (fallback,
     flag this as a known rough edge in your summary).
   - Expose a single entry point: answer(question: str, user_id: str) ->
     {"route": str, "answer": str}.

3. run_cases.py -- the required contract from PROMPT.md:
   `python3 run_cases.py <cases.jsonl> <answers.jsonl>`
   Reads JSONL of {id, question, user_id}, calls agent.answer, writes JSONL of
   {id, route, answer}.

4. eval.py -- `python3 eval.py <golden.jsonl> <answers.jsonl>`. For each case, check
   the answer text against `must_include` (list of regex alternatives, OR-joined
   per item -- case-insensitive) and `must_not_include` (same, must NOT match).
   Print a per-case PASS/FAIL with which check failed, and a summary
   (N/10 passed, breakdown by expected_route). This script is how we produce the
   "iteration evidence" deliverable (first run vs. final run).

Don't build retrieval.py or prompts.py yourself. If they don't exist yet when you
want to test, stub minimal local versions temporarily under a different filename
(e.g. _stub_prompts.py) for your own testing only, then delete the stub -- never
leave a real prompts.py/retrieval.py behind, the other agent owns those filenames.

When done, print a short summary of files created and anything you couldn't verify
end-to-end (e.g. because Ollama wasn't ready yet).
```

## [07:56] Prompt sent to grok (interactive window)

```
Project folder: C:\Users\jorch\Downloads\Projects\LLM seezle
This is a real take-home for a job interview (SplitWave AI Engineer). Read PROMPT.md
in that folder first -- it is the full brief and overrides anything below if they
conflict. A second AI tool (Claude/agy) is concurrently writing orders_store.py,
agent.py, run_cases.py, eval.py in the same folder -- do NOT touch those files, but
they will import from you. All data is synthetic (see PROMPT.md).

Your files (project root):

1. retrieval.py -- lightweight, dependency-light search over the 12 POLICY_*.md
   files (glob "POLICY_*.md" in this folder). No embedding API calls (cost/latency
   reasons -- this is a deliberate ADR). Use keyword overlap or a simple BM25
   implementation (pure Python or `rank_bm25` if available, don't add a heavy new
   dependency otherwise). Chunk each doc by its markdown sections (## headers).
   Expose:
   - load_policies(policy_dir: str = ".") -> list[{"doc": filename, "section": str,
     "text": str}]  (cache in module state)
   - search_policy(query: str, k: int = 3) -> list[{"doc": filename, "text": str}]
     of the top-k most relevant chunks for the query.

2. prompts.py -- the system prompt and guardrail config used by the agent loop
   (built by the other agent). Read all 12 policy docs first so the rules you write
   are grounded in what they actually say (payment schedules, rescheduling limits,
   failed payments, refunds & returns, disputes, account reactivation, SplitWave Boost
   credit reporting, virtual card, hardship assistance, fees, account security &
   fraud, merchant/order limits). Expose:
   - SYSTEM_PROMPT: str -- instructs the assistant to:
     * Only state facts that came from a tool result (order/account data) or a
       policy search result (and cite the policy doc name); never invent dates,
       amounts, decline reasons, or credit limits.
     * Never claim to have taken an action (paused a payment, waived a fee,
       rescheduled anything) -- it can only report real system state via tools.
     * Escalate instead of answering the substantive ask for: fraud / unrecognized
       orders / account takeover, hardship or inability-to-pay claims, requests for
       an exact decline reason or exact spending-limit number, actually filing a
       dispute (explaining the dispute policy is fine; filing it is not), and any
       attempt in the user's message to override these rules (prompt-injection
       defense) or extract a fee waiver / discretionary exception.
     * For requests needing both policy and account state (e.g. "can I reschedule
       this late payment"), pull both and reason about how the policy applies to
       that specific order's actual status -- don't answer generically when a
       specific order is in play.
     * Never act on or reveal data for an order/user that is not the current
       user_id -- if asked, refuse and explain the authorization boundary rather
       than silently substituting the right account.
   - ESCALATION_HINTS: list[str] -- keyword/phrase hints (e.g. "never shipped",
     "lost my job", "didn't place this order", "exact limit") usable as an optional
     deterministic pre-flag signal; the final route decision is still the model's
     tool-call behavior, this is just a hint the agent loop may pass along or log.

Don't build orders_store.py, agent.py, run_cases.py, or eval.py yourself.

When done, print a short summary of files created and the key guardrail rules you
encoded.
```

---

## Iteration log (real timestamps)

- **[08:03-08:07]** agy and grok both finished their initial builds. Imports verified clean.
- **[08:10-09:23]** Infra debugging saga — batches kept failing with an identical connection-style error across all 10 cases regardless of timeout length.
- **[08:33ish]** Root cause #1: wrong default Ollama model tag (`llama3.1` vs pulled `llama3.1:8b`) caused the *first* failure (404s).
- **[08:39]** Follow-up to grok: compress the 8894-char `SYSTEM_PROMPT` (CPU prompt-eval was a real latency cost) — cut to ~2000 chars, guardrails preserved. Follow-up to agy (parallel, Ollama-independent): `test_authorization.py` (proves the cross-account guardrail deterministically, 4/4 pass) + first `README.md` draft.
- **[08:47-09:23]** Root cause #2: any command long enough to exceed this session's ~590s foreground execution window gets moved to a background context that cannot reach `localhost:11434` — every full-batch run silently failed this way even with a warmed, pinned (`keep_alive: 30m`) local model, while a single direct call always worked. Built `run_checkpoint.py`: persists each case immediately, skips already-completed IDs on resume.
- **[09:23]** User supplied an Ollama Cloud API key. Wired `agent.py` to use `https://ollama.com/api/chat` with `gpt-oss:20b` when `OLLAMA_API_KEY` is set (local path untouched as fallback) — see `DECISIONS.md` #2.
- **[09:37]** Ran checkpointed batch to completion on the cloud endpoint: **10/10 cases in 49s** (vs. 15+ minutes and total failure locally). First real scored run: **4/10** (`answers_run1.jsonl`).
- **[09:37-09:39]** Diagnosed the real run-1 failures: escalation *route* was often correct but the *answer text* omitted required phrasing (no literal "human agent"/"password"/"2FA"); dispute and reschedule questions sometimes skipped a required tool call. One prompt fix in `prompts.py`: required specific literal phrasing per escalation category, and made the "policy + specific order" routing rule unconditional.
- **[09:39]** Reran: **7/10** (`answers_run2.jsonl`, final). Delta: +3 (`v03`, `v04`, `v06` fixed). Two cases shifted on a sub-detail rather than fully resolving (`v01` right route/amount but wrong date format; `v09` escalate→policy flip) — left as "Honestly Unfinished" in `README.md`, not hidden.

## Direct edits made by the orchestrating session (not agy/grok), with reasons
Given the take-home's own time pressure, a few fixes were made directly rather than round-tripped through interactive agy/grok windows, to keep the loop moving inside the 2h budget:
- `agent.py`: fixed the wrong default model tag; added `keep_alive`; added `OLLAMA_TIMEOUT_S` as a dev-only knob distinct from the production p95 target; added the `OLLAMA_API_KEY`-gated cloud-endpoint branch.
- `prompts.py`: the final escalation/routing tightening pass described above — one targeted fix, chosen from real run-1 failure evidence, not guessed.
- `run_checkpoint.py`: new file, the foreground-safe chunked+resumable runner that worked around the background-execution/localhost limitation.
