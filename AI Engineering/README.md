# AI Engineering

**Domain:** GenAI foundations · **Technique:** Retrieval evaluation, mechanism design, low-rank adaptation · **Role fit:** Applied AI Engineer / Forward Deployed Engineer

Three executed notebooks that explain the mechanics behind LLM systems and measure them on real or documented data. Production-style systems are in [Cashi RAG](../Cashi%20RAG/) and [LLM Experiment](../LLM%20Experiment/).

## Notebooks
| Notebook | Problem | Data | Key result |
|---|---|---|---|
| `Retrieval Augmented Generation - RAG System` | Which retriever finds the right policy text? | 12 policy documents and 9 golden questions from LLM Experiment | BM25 best (Recall@5 0.889, MRR 0.617); hybrid RRF did not beat it; chunk size matters more than the retriever |
| `Multi-Agent Coordination - Game Theory and VCG` | Allocate ad slots among self-interested bidders | Simulated sponsored-search market (documented click model) | VCG: 0 violations in 15,000 misreports; GSP 2.14%, first-price 6.44%; strategic efficiency 1.000 / 0.973 / 0.944 |
| `Fine-Tuning LLMs - LoRA Adaptation` | Adapt a model cheaply to shifted data | scikit-learn digits with a synthetic shift (small MLP, not an LLM) | LoRA rank 8 reaches 0.608 accuracy with 27% of the parameters of full fine-tuning (0.652) |

Details and caveats: each notebook ends with Conclusions; numbers are also in `results.md`.

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, scikit-learn, pandas, PyTorch, Matplotlib.

## Limits & security
Small-scale demonstrations: 9 evaluation queries, a simulated auction and a tiny MLP. Not benchmarks against real LLMs. No API keys are needed or stored.
