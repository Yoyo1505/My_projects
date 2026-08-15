# Section 2: Advanced Data Science & Statistics

**Mathematical Focus**: Bayesian inference, causal inference, high-dimensional statistics  
**Key Innovators**: Ferguson (1973), Chernozhukov et al. (2018), Candès & Donoho (2005)

---

## Overview

This section implements three pillars of modern statistics:
1. **Bayesian Nonparametrics** - Clustering without pre-specifying the number of clusters
2. **Causal Inference** - Estimating treatment effects in high dimensions robustly
3. **Compressed Sensing** - Recovering sparse signals from few measurements with theoretical guarantees

---

## Projects in This Section

### Project 1: Dirichlet Process Mixtures (Bayesian Nonparametrics)
**File**: `07_DataScience_DPMixture.ipynb`

**What You'll Learn**:
- Dirichlet Process prior for infinite mixture models
- Chinese Restaurant Process (CRP) analogy
- Gibbs sampling for inference
- Automatic model selection (discovering optimal K)
- Stick-breaking construction

**Mathematical Background**:
```
Model: G ~ DP(α, G_0)
        φ_i | G ~ G
        y_i | φ_i ~ F(· | φ_i)

Challenge: Inference over infinite-dimensional space

Solution: Gibbs sampling with CRP prior
P(z_i = k | rest) ∝ n_k * p(y_i | cluster k) + α * p(y_i | base)
```

**Key Insight**: The model **automatically discovers** the number of clusters from data—no need to specify K in advance. The concentration parameter α controls the tendency to create new clusters.

**Time to Complete**: 5-7 hours

---

### Project 2: Causal Inference (Double Machine Learning)
**File**: `08_DataScience_CausalInference_DML.ipynb`

**What You'll Learn**:
- Rubin's potential outcomes framework
- Neyman-orthogonal scores
- Residualization to remove confounding
- High-dimensional treatment effect estimation
- Comparison: OLS vs LASSO vs Double ML

**Mathematical Background**:
```
Problem: Estimate τ = E[Y(1) - Y(0)] in high dimensions

Challenge: Standard regression biases τ when p >> n

Solution (Chernozhukov et al.):
1. Ŷ = Y - ML_predict(X)  [residualize outcome]
2. T̂ = T - ML_predict(X)  [residualize treatment]
3. τ̂ = (∑ T̂Ŷ) / (∑ T̂²)  [regress residuals]

Why it works: Neyman orthogonality makes τ̂ robust to first-stage ML errors
```

**Key Insight**: Double ML **orthogonalizes** the estimation problem: removing confounding directions makes the treatment effect identifiable even with noisy ML nuisance parameters.

**Time to Complete**: 4-6 hours

---

### Project 3: Compressed Sensing (LASSO & RIP)
**File**: `09_DataScience_CompressedSensing.ipynb`

**What You'll Learn**:
- Restricted Isometry Property (RIP) for matrices
- LASSO for sparse signal recovery
- Measurement bounds: $m = O(k \log(p/k))$
- Theoretical guarantees for exact recovery
- Applications to sensor networks and imaging

**Mathematical Background**:
```
Problem: Recover x ∈ ℝ^p (sparse: ||x||_0 ≤ k) from y = Ax + ε, m << p

Solution: LASSO
x̂ = arg min_x ||y - Ax||² + λ||x||_1

Guarantee (RIP): If A satisfies RIP with δ_k < 1:
||(1-δ_k)||x||² ≤ ||Ax||² ≤ (1+δ_k)||x||²||

Then LASSO recovers x exactly (up to noise) with m = O(k log(p/k)) measurements
```

**Key Insight**: **Sparsity enables underdetermined problems to be solved**. With RIP matrices (random Gaussian, random subsampled Fourier), we can recover k-sparse signals from O(k log p) measurements—exponentially better than naive sampling.

**Time to Complete**: 5-6 hours

---

## How to Run

### Prerequisites
```bash
pip install numpy scipy scikit-learn pandas matplotlib seaborn
```

### Run a Notebook
```bash
jupyter notebook 07_DataScience_DPMixture.ipynb
```

---

## Learning Path

**Beginner**: Project 1 (Dirichlet Process) for nonparametric Bayesian methods  
**Intermediate**: Project 2 (Causal Inference) for high-dim statistics  
**Advanced**: Project 3 (Compressed Sensing) for signal processing theory

---

## Key Formulas & Concepts

| Concept | Formula | Intuition |
|---------|---------|-----------|
| **Dirichlet Process** | $G \sim DP(\alpha, G_0)$ | Infinite mixture prior |
| **Chinese Restaurant** | $P(z_i=k) \propto n_k + \alpha$ | Preferential attachment |
| **Double ML** | $\taû = \frac{\sum \tilde{T}\tilde{Y}}{\sum \tilde{T}²}$ | Orthogonal scores |
| **Compressed Sensing** | $m = O(k \log(p/k))$ | Sublinear measurements |

---

## Common Issues & Solutions

### Issue: Gibbs sampler isn't mixing
**Solution**: Decrease concentration α; initialize better; run longer

### Issue: Double ML estimate has large variance
**Solution**: Increase sample size; use less aggressive regularization

### Issue: LASSO solution is all zeros
**Solution**: Decrease λ (regularization parameter)

---

## Extensions & Advanced Topics

1. **Nonparametric Regression**: Extend DP to regression (DPM of regression models)
2. **Multiple Treatment Arms**: Extend causal to >2 treatments
3. **Time-Series**: Apply compressed sensing to sparse signal tracking
4. **Matrix Completion**: Low-rank recovery from incomplete matrices
5. **Debiased ML**: Add bias correction to Double ML for better coverage

---

## Theory References

- Ferguson, T. S. (1973). "A Bayesian Analysis of Some Nonparametric Problems"
- Sethuraman, J. (1994). "A Constructive Definition of Dirichlet Priors"
- Chernozhukov, V., et al. (2018). "Double Machine Learning for Treatment and Structural Parameters"
- Candès, E. J., & Tao, T. (2005). "Decoding by Linear Programming"

---

## GitHub Setup

```bash
git add SECTION_2_DATA_SCIENCE/
git commit -m "Add data science: Bayesian nonparametrics, causal inference, compressed sensing"
git push
```

Add topics: `machine-learning`, `bayesian-statistics`, `causal-inference`, `compressed-sensing`

---

**Difficulty**: ⭐⭐⭐⭐ (Advanced: requires Bayesian inference, optimization theory)  
**Time Investment**: 14-19 hours total  
**Impact**: Foundational for ML research, causal analysis, signal processing
