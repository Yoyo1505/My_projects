# AI Engineering

**Domain:** GenAI foundations · **Technique:** Retrieval, mechanism design, low-rank adaptation · **Role fit:** Applied AI Engineer / Forward Deployed Engineer

Three compact notebooks that explain the mechanics behind modern LLM systems using NumPy and scikit-learn (no model downloads). Production-style systems are in [Cashi RAG](../Cashi%20RAG/) and [LLM Experiment](../LLM%20Experiment/).

## Notebooks
| Notebook | Problem | Approach |
|---|---|---|
| `Retrieval Augmented Generation - RAG System` | Ground answers in documents | Vectorisation, similarity search, context assembly |
| `Multi-Agent Coordination - Game Theory and VCG` | Allocate tasks among self-interested agents | Game theory, VCG mechanism, truthful bidding |
| `Fine-Tuning LLMs - LoRA Adaptation` | Adapt a large model cheaply | Low-rank update $W + BA$, parameter-count savings |

## Run
```bash
pip install -r requirements.txt
jupyter notebook notebooks/
```

## Stack
NumPy, SciPy, scikit-learn, pandas, Matplotlib, Jupyter.

## Limits & security
These are didactic reimplementations, not benchmarks against real LLMs; no API keys are needed or stored.
