# Section 3: AI Engineering & Large Language Models

**Mathematical Focus**: Information retrieval, mechanism design, deep learning optimization  
**Key Contributors**: Lewis et al. (2020), Hu et al. (2021), Nash (1994)

---

## Overview

This section implements three production-grade AI systems:
1. **Retrieval-Augmented Generation (RAG)** - Connect LLMs to external knowledge bases
2. **Multi-Agent Systems** - Coordinate multiple AI agents using game theory
3. **Fine-Tuning & LoRA** - Adapt large models efficiently with convergence analysis

---

## Projects in This Section

### Project 1: Retrieval-Augmented Generation (RAG)
**File**: `11_AI_RAG_System.ipynb`

**What You'll Learn**:
- Dense passage retrieval (semantic search)
- Embedding models and cosine similarity
- Reranking and context selection
- Citation tracking and attribution
- Evaluation metrics (NDCG, RAGAS, F1)

**Mathematical Background**:
```
Retriever: Score(q, d) = cos(embed(q), embed(d))
          where embeddings are learned or pre-trained

Reranker: Score_reranked = cross-encoder(q, d)  [more accurate but slower]

LLM: Answer = LLM(question + top_k_documents)

Evaluation: NDCG = ∑ (2^rel_i - 1) / log(i+1)
```

**Key Insight**: RAG is the **most deployed pattern in enterprise LLM systems**. It connects parametric knowledge (LLM weights) with non-parametric memory (retrieved documents), enabling up-to-date answers without retraining.

**Time to Complete**: 5-7 hours

---

### Project 2: Multi-Agent Orchestration with Game Theory
**File**: `12_AI_MultiAgent_GameTheory.ipynb`

**What You'll Learn**:
- Nash equilibrium in agent coordination
- Mechanism design (Vickrey-Clarke-Groves)
- Resource allocation via auction
- Agent orchestration frameworks
- Truthful mechanism design

**Mathematical Background**:
```
Game: Multiple agents compete for resources (compute, tokens, memory)

Nash Equilibrium: Each agent's strategy is optimal given others' strategies
σ* = arg max_σ_i E[u_i(σ_i, σ*_{-i})]

VCG Mechanism: Truth-revealing auction
Payment_i = ∑_{j≠i} v_j(x^{-i}) - ∑_{j≠i} v_j(x*)

Property: Truthful bidding is a dominant strategy
```

**Key Insight**: **Game theory provides principled ways to coordinate multiple AI agents**. VCG mechanisms guarantee efficient allocation and incentivize truthful reporting—essential for distributed AI systems.

**Time to Complete**: 4-5 hours

---

### Project 3: Fine-Tuning with LoRA & Convergence Analysis
**File**: `13_AI_FineTuning_LoRA.ipynb`

**What You'll Learn**:
- Low-rank adaptation (LoRA) for efficient fine-tuning
- Supervised fine-tuning loss
- Convergence rates (convex + non-convex)
- Generalization bounds
- Practical evaluation metrics

**Mathematical Background**:
```
Standard Fine-Tuning: W_new = W + ΔW  [update full matrix: O(d²)]

LoRA: W_new = W + BA  [update low-rank: O(dr), r << d]

Convergence: L(θ_T) - L(θ*) = O(1/T)  [convex]
            ||∇L(θ_T)||² = O(1/T)       [non-convex]

Generalization: Train_loss - Test_loss = O(√(d log T / n))
```

**Key Insight**: LoRA shows that **fine-tuned models have low intrinsic dimension**. By training only rank-r matrices (r << d), we achieve 100x memory savings with minimal accuracy loss—crucial for deploying large models.

**Time to Complete**: 5-6 hours

---

## How to Run

### Prerequisites
```bash
pip install anthropic openai langchain chromadb numpy pandas matplotlib scikit-learn
```

### Run a Notebook
```bash
jupyter notebook 11_AI_RAG_System.ipynb
```

---

## Learning Path

**Beginner**: Project 1 (RAG) for LLM application patterns  
**Intermediate**: Project 3 (LoRA) for efficient adaptation  
**Advanced**: Project 2 (Multi-Agent) for distributed AI systems

---

## Key Formulas & Concepts

| Concept | Formula | Intuition |
|---------|---------|-----------|
| **Semantic Search** | $score = \text{cos}(\text{embed}(q), \text{embed}(d))$ | Meaning-based retrieval |
| **LoRA** | $W' = W + BA, \, r << d$ | Low-rank updates |
| **Nash Eq** | $\sigma_i^* = \arg\max u_i(\sigma_i, \sigma_{-i}^*)$ | Stable equilibrium |
| **VCG Price** | $p_i = \sum_{j≠i} v_j(x^{-i})$ | External cost |

---

## Common Issues & Solutions

### Issue: RAG is returning irrelevant documents
**Solution**: Use better embedding model; adjust retrieval threshold; add reranking

### Issue: Fine-tuning diverges (loss increases)
**Solution**: Reduce learning rate; use smaller LoRA rank; check data quality

### Issue: Agents don't reach equilibrium
**Solution**: Increase iterations; use smaller step size; check mechanism design

---

## Extensions & Advanced Topics

1. **Hybrid Retrieval**: Combine semantic + keyword search (BM25)
2. **Self-Critique RAG**: Agents evaluate and improve their own answers
3. **Reward Modeling**: Learn preferences from human feedback
4. **Quantized LoRA**: Combine LoRA with quantization for extreme efficiency
5. **Multi-Turn Agents**: Complex task decomposition and planning

---

## Theory References

- Lewis, P., et al. (2020). "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
- Hu, E. J., et al. (2021). "LoRA: Low-Rank Adaptation of Large Language Models"
- Nash, J. F. (1950). "Equilibrium Points in N-Person Games"
- Vickrey, W. (1961). "Counterspeculation, Auctions, and Competitive Sealed Tenders"

---

## GitHub Setup

```bash
git add SECTION_3_AI_ENGINEERING/
git commit -m "Add AI engineering: RAG systems, multi-agent coordination, LoRA fine-tuning"
git push
```

Add topics: `llm`, `retrieval-augmented-generation`, `ai-agents`, `deep-learning`

---

**Difficulty**: ⭐⭐⭐ (Intermediate-Advanced: requires DL + optimization knowledge)  
**Time Investment**: 14-18 hours total  
**Impact**: State-of-the-art LLM systems; industry-standard patterns
