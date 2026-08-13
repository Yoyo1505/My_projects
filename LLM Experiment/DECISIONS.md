# Decision Records

## 1. Retrieval: keyword/BM25 over policy docs, not embeddings
**Decision:** `retrieval.py` uses lightweight lexical search (BM25/keyword overlap) over 12 markdown docs, no embedding API.
**Options considered:** embeddings + vector DB; full-text keyword search; sending all 12 docs in-context every call.
**Why:** 12 short docs is a corpus embeddings are overkill for; BM25 is free and sub-millisecond, and directly serves the $50/day, p95≤3s constraint at 100k q/day — an embedding call per question adds cost and a network hop for no accuracy win at this corpus size.
**What would change my mind:** if the policy corpus grew to hundreds of docs with paraphrase-heavy queries where lexical overlap misses matches, embeddings would earn their cost.

## 2. Local Ollama first, pivoted to hosted Ollama Cloud mid-build
**Decision:** started with a fully local Ollama model (`llama3.1:8b`, CPU-only, $0 marginal cost); switched `agent.py` to Ollama's hosted cloud endpoint (`gpt-oss:20b` via `https://ollama.com/api/chat`, config-gated on `OLLAMA_API_KEY`) partway through, local path left intact as the no-key fallback.
**Options considered:** stay local; pay-per-token cloud API (Anthropic/OpenAI/xAI); hosted Ollama.
**Why:** measured evidence, not guesswork — a warm local single-turn call took 30-90s and a cold load ~58s on CPU-only hardware; a full 10-case batch took 15+ minutes and repeatedly blew past reasonable dev timeouts. The hosted endpoint ran the same 10-case batch in under a minute. Local proved $0 but operationally unworkable even for *our own* iteration loop, let alone a 3s p95 target; hosted Ollama kept the same API shape (near-zero migration cost) while being fast enough to actually iterate.
**What would change my mind:** real production load testing. At 100k req/day, $50/day is $0.0005/request — worth pricing hosted Ollama vs. a small cloud-native model (Haiku-class) on $/request and p95 before committing; the pivot here was about unblocking iteration speed today, not a final production choice.

## 3. Guardrails enforced structurally, not just by prompt
**Decision:** cross-account order access is blocked in `orders_store.py` (returns "not found" regardless of what the model requests), not merely instructed against in the system prompt.
**Options considered:** prompt-only instruction ("don't look up other users' orders"); structural filter at the data-access layer.
**Why:** prompt instructions are not reliable against adversarial/injected input (the brief explicitly tests this); a function-level filter can't be talked out of its behavior.
**What would change my mind:** none for the authorization boundary itself — this should always be structural. Would reconsider only which *other* rules (e.g. tone, escalation wording) are safe to leave as prompt-only vs. also enforced in code.

---
Cost/latency constraint (100k q/day, ~$50/day, p95≤3s) is explicitly addressed in #1 and #2 above.
