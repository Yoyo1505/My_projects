# Section 1: Quantitative Trading & Stochastic Control

**Mathematical Focus**: Dynamic optimization, stochastic processes, covariance estimation  
**Nobel Prize Winners**: Markowitz (1990), Scholes & Merton (1997)

---

## Overview

This section implements three fundamental problems in quantitative finance:
1. **Optimal Execution** - How to execute a large trade to minimize market impact
2. **Portfolio Optimization** - How to allocate capital across assets to maximize risk-adjusted returns
3. **Option Pricing** - How to price derivatives under stochastic volatility

Each project builds on rigorous mathematics: HJB equations, mean-variance theory, and PDEs.

---

## Projects in This Section

### Project 1: Almgren-Chriss Optimal Execution
**File**: `02_Trading_Optimal_Execution.ipynb`

**What You'll Learn**:
- Hamilton-Jacobi-Bellman (HJB) equation for optimal control
- Temporary vs. permanent market impact models
- Solving optimization with SLSQP
- Sensitivity analysis and robustness testing
- Stochastic price dynamics simulation

**Mathematical Background**:
```
Problem: Minimize execution cost = temporary impact + permanent impact + inventory risk

Solve: min_v ∑[λ|v_i|^1.5 + γ v_i σ + η(Q - ∑v_i)^2]

Result: Non-uniform optimal schedule balances speed vs. price risk
```

**Key Insight**: The optimal trading schedule is NOT uniform—execute more aggressively at the start and slow down as you approach the finish.

**Time to Complete**: 4-6 hours

---

### Project 2: Portfolio Optimization (Markowitz + Black-Litterman + Shrinkage)
**File**: `04_Trading_PortfolioOptimization.ipynb`

**What You'll Learn**:
- Mean-variance framework (Harry Markowitz, Nobel 1990)
- Ledoit-Wolf shrinkage for covariance estimation
- Black-Litterman model for incorporating investor views
- Computing efficient frontiers
- Out-of-sample robustness evaluation

**Mathematical Background**:
```
Markowitz: min_w w^T Σ w  subject to w^T μ = μ_p, ∑w_i = 1

Challenge: Σ is ill-conditioned (high condition number)

Solution: Σ_shrunk = (1-α)Σ_sample + α Σ_target
where α is chosen to minimize expected loss
```

**Key Insight**: In high dimensions, **estimation error dominates**. Ledoit-Wolf shrinkage dramatically improves out-of-sample performance by reducing the condition number of the covariance matrix.

**Time to Complete**: 4-5 hours

---

### Project 3: Stochastic Volatility & Option Pricing (Heston Model)
**File**: `05_Trading_HestonVolatility.ipynb`

**What You'll Learn**:
- Heston stochastic volatility model (how volatility evolves over time)
- Characteristic function approach (analytic formulas)
- FFT-based pricing (Carr-Madan method) for speed
- Volatility smile generation and interpretation
- Parameter calibration via global optimization

**Mathematical Background**:
```
Stock: dS = μS dt + √v S dW^S
Volatility: dv = κ(θ - v) dt + σ_v√v dW^v

Option Price: C(K,T) = (e^{-rT}/π) ∫ e^{-iξ ln K} φ(ξ-i/2)/(ξ^2+1/4) dξ

Calibration: min_{θ} ∑[Model_Price(θ) - Market_Price]^2
```

**Key Insight**: Black-Scholes assumes constant volatility, which creates **unrealistic prices for out-of-money options**. Heston's model generates the empirically observed "volatility smile" where implied volatility varies by strike.

**Time to Complete**: 6-8 hours

---

## How to Run

### Prerequisites
```bash
pip install numpy scipy pandas matplotlib scikit-learn
```

### Run a Notebook
```bash
jupyter notebook 02_Trading_Optimal_Execution.ipynb
```

---

## Learning Path

**Beginner**: Start with Project 2 (Markowitz) for portfolio basics
**Intermediate**: Project 1 (optimal execution) for stochastic control
**Advanced**: Project 3 (Heston) for pricing theory and calibration

---

## Key Formulas & Concepts

| Concept | Formula | Intuition |
|---------|---------|-----------|
| **Optimal Execution** | $\min_v C(v)$ s.t. $\sum v = Q$ | Balance speed vs. impact |
| **Efficient Frontier** | $w^* = \Sigma^{-1}(\mu - r_f)$ | Best return for each risk level |
| **Shrinkage** | $\Sigma_{shrunk} = (1-\alpha)\Sigma_s + \alpha\Sigma_t$ | Regularize covariance |
| **Heston** | $dv = \kappa(\theta-v)dt + ..$ | Volatility mean-reverts |

---

## Common Issues & Solutions

### Issue: Optimization doesn't converge
**Solution**: Check constraints are satisfied; use multiple initial guesses

### Issue: Covariance matrix is singular
**Solution**: Add shrinkage or use pseudo-inverse

### Issue: Heston prices don't match market
**Solution**: Increase calibration precision; check parameter bounds

---

## Extensions & Advanced Topics

1. **Transaction Costs**: Add bid-ask spreads and commissions
2. **Adaptive Execution**: Re-optimize at each time step based on observed prices
3. **Jump Diffusion**: Extend Heston to include price jumps (Merton's model)
4. **Multi-asset Execution**: Coordinate execution across correlated assets
5. **Machine Learning**: Use neural networks to learn optimal trading policies (RL)

---

## Theory References

- Almgren, R., & Chriss, N. (2000). "Optimal Execution of Portfolio Transactions"
- Markowitz, H. M. (1952). "Portfolio Selection"
- Heston, S. L. (1993). "A Closed-Form Solution for Options with Stochastic Volatility with Applications to Bond and Currency Options"
- Carr, P., & Madan, D. (1999). "Option Valuation Using the Fast Fourier Transform"

---

## GitHub Setup

```bash
# Copy to your GitHub repo
git add SECTION_1_TRADING/
git commit -m "Add quantitative trading projects: execution, portfolio optimization, Heston pricing"
git push
```

Add topics to your repo: `quantitative-finance`, `algorithmic-trading`, `mathematical-finance`

---

**Difficulty**: ⭐⭐⭐⭐ (Advanced: requires understanding of stochastic calculus)  
**Time Investment**: 14-19 hours total  
**Impact**: Foundational for quant finance careers and algorithmic trading
