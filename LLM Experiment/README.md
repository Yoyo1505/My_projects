# SplitWave Support Agent

**Domain:** GenAI / agents · **Role fit:** Applied AI Engineer / Forward Deployed Engineer

> Security: set `OLLAMA_API_KEY` only through the environment and never commit key files. Authorization guardrails on order data are tested in `test_authorization.py`. See [SECURITY.md](../SECURITY.md).

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

- **`graph.py`**: Orchestrates the four planes (control, specialist, model, guardrail); entry point used by `run_cases.py`.
- **`router.py`**: Control plane: deterministic routing (`policy` | `tool` | `both` | `escalate`) and order lookup scoped to the authenticated user.
- **`agent.py`**: Specialist plane: LLM reasoning node with tool execution.
- **`llm_client.py`**: Model plane: Ollama client with text normalisation.
- **`verifier.py`**: Guardrail plane: deterministic checks (dates, escalation phrases) after the model answers.
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


---

## Results

10/10 on the visible golden set in two consecutive runs (`answers_run11.jsonl`, `answers_run12.jsonl`). Earlier, simpler single-loop versions scored 7/10; the failures were fixed structurally (deterministic routing and verification) instead of with more prompt wording. Variance of the hosted model means a further run could still surface a new failure.

## Limits & Next Steps

- **Prompt-injection resistance**: rules are explicit and routing is deterministic for known phrasings, but there is no automated red-team pass for novel ones.
- **Latency at scale**: untested beyond the dev-tier endpoint; needs load testing before 100k requests/day (see `DECISIONS.md` #2).
- **No caching layer**: a cache keyed on (user_id, normalised question) would cut cost and p95 latency.
- **Evaluation**: only the visible set; a hidden-set-shaped stress test (paraphrases, hostile inputs) is the natural next step.
