# Results: AI Engineering notebooks

All three notebooks were rebuilt to use real or clearly documented data and were executed
top to bottom with `jupyter nbconvert --execute` (fixed seeds, no errors). Every number below
comes from the executed outputs.

## 1. Retrieval Augmented Generation - RAG System

Data: the 12 SplitWave policy files `POLICY_*.md` and the golden cases in
`CASES_-_golden_visible.jsonl` from the sibling folder `LLM Experiment/`. Nine cases with a
retrieval route are used as queries (v01, route `tool`, is excluded).

Key numbers (paragraph chunks, 33 chunks, 9 queries):
- TF-IDF cosine: Recall@1 0.444, Recall@3 0.556, Recall@5 0.778, MRR 0.578.
- BM25: Recall@1 0.444, Recall@3 0.667, Recall@5 0.889, MRR 0.617 (best of the three).
- Hybrid RRF: Recall@1 0.444, Recall@3 0.556, Recall@5 0.778, MRR 0.586. It did not beat BM25.
- Chunk-size ablation, Recall@3: 0.222 (words-20, 116 chunks) up to 0.889 (words-80, BM25 and hybrid).
- Fixed 100-word budget (fairer than chunk counts): paragraph 3/9 (TF-IDF), 4/9 (BM25), 3/9 (hybrid).
- Sanity check: our TF-IDF matches scikit-learn to a maximum difference of 2.2e-16.

Caveats and failures:
- Nine queries: one query changes Recall by 0.111, so differences of one or two queries are noise.
- The hit definition is a regex proxy (all `must_include` patterns covered by the top-k chunks), not human relevance. Generic patterns (`3`, `escalat`, `human|agent`) inflate hits.
- Whole-document chunks score 9/9 at Recall@3 only because they are long; at the 100-word budget they score 1/9. The budget of 100 words was chosen a priori, not tuned.
- Query v06 (dispute) is only fully covered at rank 9 (TF-IDF) and 10 (BM25).
- Path: the notebook reads `../../LLM Experiment` relative to `notebooks/`, so it needs the sibling folder in place.

## 2. Multi-Agent Coordination - Game Theory and VCG

Data: **simulated** sponsored-search market (8 advertisers, 4 slots) with a documented
position-based click model (CTR = quality x examination rate). No real bid logs are used.
The NYC TLC taxi data was reachable but was not used: taxi trips have no natural
bidder-item valuation, and it would have needed simulated driver costs anyway.

Key numbers:
- Hungarian allocation matches the sorted GSP allocation on 1,000 markets (0 mismatches).
- Hand-checked VCG example: payments 0.0480 and 0.0240, matching the hand calculation.
- Truthfulness, 3,000 markets x 5 misreports (15,000 per mechanism): VCG 0 violations (0.0000);
  GSP 321 (0.0214, max gain 0.0956); first-price 966 (0.0644, max gain 0.3611).
- VCG had no negative truthful utilities (individual rationality).
- Single-slot first-price shading: best bid 0.598 for value 0.9 (factor 0.664), against the
  closed-form prediction of 0.600.
- Strategic play, 200 markets (3 best-response rounds): VCG efficiency 1.0000, revenue
  0.1582 per market; GSP efficiency 0.9729, revenue 0.1567; first-price efficiency 0.9442,
  revenue 0.1488.
- First-price winners shade their bids to a mean of 0.70 of value; GSP winners to 0.87.

Caveats and failures:
- Everything is simulated. The revenue ranking depends on the assumed click model and value distributions.
- The VCG-over-first-price revenue gap (about 6%) was not tested for significance over 200 markets.
- Best-response dynamics ran for 3 rounds on a 61-point grid. Convergence was not checked further.
- The truthfulness test is random sampling. It cannot prove truthfulness; VCG's truthfulness is a theorem, and the test checks the implementation.

## 3. Fine-Tuning LLMs - LoRA Adaptation

**Small-scale demonstration: a 2-layer MLP, not an LLM.**

Data: scikit-learn's bundled `load_digits` (1,797 images, no download). Pretrained on 1,000
clean images. Adapted on 150 shifted images, with 50 for learning-rate selection and 397 for
testing. The shift is synthetic: a 2-pixel shift, intensity x0.6, and noise sigma 0.2. The
20 Newsgroups option was not attempted.

Key numbers (3 seeds, one pretrained model):

| Method | Trainable params | % of full | Test acc (mean +/- std) | Train time, s |
|---|---|---|---|---|
| Zero-shot | 0 | 0 | 0.1511 | 0 |
| Full fine-tuning | 9,610 | 100 | 0.6524 +/- 0.0000 | 1.285 |
| LoRA r=1 | 330 | 3.43 | 0.3871 +/- 0.0260 | 1.449 |
| LoRA r=2 | 660 | 6.87 | 0.4467 +/- 0.0203 | 1.626 |
| LoRA r=4 | 1,320 | 13.74 | 0.5768 +/- 0.0155 | 1.723 |
| LoRA r=8 | 2,640 | 27.47 | 0.6079 +/- 0.0072 | 1.610 |

- Clean source test accuracy is 0.9600; the shift drops the pretrained model to 0.1511.
- LoRA parameter counts follow $330r$. The rank-4 layer check gave 768 = 4 x 192.
- Accuracy rises monotonically with rank. LoRA r=8 is within 4.5 points of full fine-tuning.

Caveats and failures:
- Training is short (300 full-batch steps on 150 images). Full fine-tuning reaches only 0.652, so all methods are under-trained and the ranking could change with a longer schedule.
- The selected learning rate for LoRA r=1, 2 and 4 is 1e-2, the top of the grid. A larger rate was not tested.
- Full fine-tuning is deterministic here, so its std of 0 is by construction.
- LoRA was not faster in wall-clock time at this size (final run: 1.45 to 1.72 s against 1.29 s for full fine-tuning; an earlier run gave the same ordering). Timings are noisy on this shared machine. Overhead dominates; the benefit is the parameter count.
- One pretrained model; the three seeds vary only the LoRA initialisation.

## Execution status

| Notebook | Status |
|---|---|
| Retrieval Augmented Generation - RAG System | Executed cleanly (0 error cells) |
| Multi-Agent Coordination - Game Theory and VCG | Executed cleanly (0 error cells) |
| Fine-Tuning LLMs - LoRA Adaptation | Executed cleanly (0 error cells) |

Dependencies: `requirements.txt` now lists `scipy` (VCG Hungarian solver) and `torch` (LoRA);
`numpy`, `pandas`, `matplotlib`, `scikit-learn` and `jupyter` were already there.
README.md was not changed.
