# Portfolio Projects: Deep Research Foundations
## Principles, Quotes & Mathematical Foundations

---

## PART I: QUANTITATIVE TRADING & STOCHASTIC CONTROL

### 1.1 Optimal Execution via Almgren-Chriss Framework

#### Historical Context & Nobel Recognition
The foundation of modern quantitative finance rests on the work of **Robert C. Merton** and **Myron Scholes**, who won the 1997 Nobel Prize in Economics for their Black-Scholes option pricing model. The continuous-time framework they established:

> "The problem is to find the optimal policy for purchasing or selling a large block of stock over a specified time horizon." — Almgren & Chriss (2000)

**Merton on Dynamic Portfolio Theory** (1971):
> "The investor's goal is to maximize expected utility of consumption over his lifetime. The dynamic nature of the problem requires continuous rebalancing in response to price changes."

#### Core Principle: Hamilton-Jacobi-Bellman Equation
The optimal trading problem reduces to solving the HJB equation:

$$V_t + \frac{1}{2}\sigma^2 S^2 V_{SS} + rSV_S - rV = 0$$

Where $V(S,t)$ is the value function. Almgren-Chriss extends this to incorporate market impact costs:

**Temporary Impact** (in $\$$ per share):
$$\text{Cost} = \lambda \cdot q^{\alpha}$$
where $\lambda$ is market depth, $q$ is order size, $\alpha \in [1.5, 2]$ is impact elasticity

**Permanent Impact** (shift in equilibrium price):
$$\Delta P = \gamma \cdot v$$
where $v$ is trading rate (shares/time)

#### Key Papers
- Almgren, R., & Chriss, N. (2000). "Optimal Execution of Portfolio Transactions"
- Gatheral, J. (2010). "No-dynamic-arbitrage and market impact"

---

### 1.2 Markowitz Portfolio Optimization & Modern Extensions

#### Nobel Prize Context
**Harry Markowitz** (Nobel 1990):
> "The investor considers expected return a desirable thing and variance of return an undesirable thing. The investor should maximize expected return subject to an upper limit on variance."

#### The Mean-Variance Problem
Minimize portfolio variance subject to expected return constraint:

$$\min_{\mathbf{w}} \mathbf{w}^T \Sigma \mathbf{w}$$
$$\text{s.t.} \quad \mathbf{w}^T \boldsymbol{\mu} = \mu_p, \quad \sum_i w_i = 1$$

Where:
- $\mathbf{w}$ = portfolio weights
- $\Sigma$ = covariance matrix (estimated from returns)
- $\boldsymbol{\mu}$ = expected returns vector

#### The Problem: Estimation Error
Ledoit & Wolf (2004) showed sample covariance is **severely ill-conditioned** in high dimensions:

> "The sample covariance matrix is known to perform poorly when the number of assets is large relative to the length of the time series. Shrinkage toward the identity matrix dramatically improves performance." — Ledoit & Wolf (2004)

**Shrinkage Estimator**:
$$\Sigma_{\text{shrink}} = \alpha \Sigma_{\text{sample}} + (1-\alpha) \Sigma_{\text{target}}$$

Where $\alpha$ is chosen to minimize Frobenius norm. Typical targets:
- **Single-factor model**: $\Sigma_{\text{target}} = \beta \beta^T + \text{diag}(\sigma^2_\epsilon)$
- **Constant correlation**: $\Sigma_{\text{target}} = \bar{\rho}[\mathbf{1}\mathbf{1}^T - I] + \text{diag}(\sigma^2)$

#### Black-Litterman Extension
Fischer Black & Robert Litterman (1991):
> "Investors typically have views about the expected return of certain assets and want to construct portfolios that take advantage of these views."

**BL Posterior**:
$$E[\mathbf{r}|\text{views}] = \Sigma \mathbf{P}^T [\mathbf{P}\Sigma\mathbf{P}^T + \Omega]^{-1} (\mathbf{Q} - \mathbf{P}\boldsymbol{\mu}_{\text{prior}})$$

Where:
- $\mathbf{P}$ = view matrix (which assets, which correlations)
- $\mathbf{Q}$ = view returns
- $\Omega$ = view confidence

---

### 1.3 Stochastic Volatility & Heston Model

#### Seminal Work
**Steven Heston** (1993):
> "A closed-form solution for European option prices when the volatility of the underlying stock price is stochastic appears to be intractable. Instead, I derive a semi-closed-form solution using characteristic functions."

#### The Model
$$dS = \mu S dt + \sqrt{v} S dW_S$$
$$dv = \kappa(\theta - v) dt + \sigma_v \sqrt{v} dW_v$$

Where:
- $v$ = instantaneous variance (latent state)
- $\kappa$ = mean-reversion speed
- $\theta$ = long-run variance
- $\sigma_v$ = volatility of volatility
- $\rho$ = correlation between asset and volatility shocks

#### Calibration via Carr-Madan (FFT)
**Carr & Madan** (1999) express call option price via characteristic function:

$$C(K,T) = \frac{e^{-rT}}{\pi} \int_0^{\infty} \frac{e^{-i\nu \log K} \phi(\nu - i/2)}{v^2 + 1/4} d\nu$$

Where $\phi(\nu)$ is the characteristic function. This is vastly faster than MC simulation for calibration.

**Reference Paper**: Carr, P., & Madan, D. (1999). "Option Valuation Using the Fast Fourier Transform"

---

## PART II: DATA SCIENCE & ADVANCED STATISTICS

### 2.1 Bayesian Nonparametrics: Dirichlet Process Mixtures

#### Foundational Insight
**Thomas S. Ferguson** (1973):
> "The Dirichlet Process provides a convenient mechanism for specifying a prior distribution over the space of probability measures. It is nonparametric in the sense that the prior does not assume a fixed parametric form for the data distribution."

#### The Model
Data: $y_1, \ldots, y_n \sim \text{Mixture}$
- Number of components $K$ unknown
- Component parameters $\boldsymbol{\phi}_k$ random
- Weights $\pi_k$ random via Dirichlet Process

$$G \sim \text{DP}(\alpha, G_0)$$
$$\phi_i | G \sim G, \quad y_i | \phi_i \sim F(\cdot | \phi_i)$$

Where:
- $\alpha$ = concentration parameter (higher → more clusters)
- $G_0$ = base measure (prior on component parameters)
- $F$ = likelihood (e.g., Gaussian)

#### Stick-Breaking Construction
**Sethuraman** (1994):
$$G = \sum_{k=1}^{\infty} \pi_k \delta_{\phi_k}$$

Where:
$$\pi_k = V_k \prod_{j=1}^{k-1}(1-V_j), \quad V_k \sim \text{Beta}(1, \alpha)$$

This gives explicit, tractable sampler: Chinese Restaurant Process

#### Chinese Restaurant Process
> "Customers enter a restaurant and sit at tables. Customer $n$ sits at an occupied table $k$ with probability $n_k/(n-1+\alpha)$, or at a new table with probability $\alpha/(n-1+\alpha)$."

**Polya Urn interpretation**: clustering naturally emerges from exchangeability.

---

### 2.2 Causal Inference: Double Machine Learning

#### Motivation
**Donald Rubin's Potential Outcomes Framework** (Rubin, 1974):
> "The fundamental problem of causal inference is that we can only observe one of two potential outcomes for each unit. We never see what would have happened in the counterfactual world."

#### The Problem
Estimate treatment effect $\tau = E[Y(1) - Y(0)]$ in high dimensions where $p \gg n$

Standard regression fails: $Y = \beta_0 + \beta_1 T + \beta_p X + \epsilon$ with LASSO biases treatment coefficient

#### Double Machine Learning Solution
**Chernozhukov et al.** (2018):
> "Machine learning methods can estimate nuisance parameters (confounders) without bias to the treatment coefficient if we use Neyman-orthogonal scores."

**Algorithm**:

1. **Regress out confounding**: $\hat{m}(X) = \text{ML}(Y \sim X)$ and $\hat{r}(X) = \text{ML}(T \sim X)$
2. **Compute residuals**: $\tilde{Y} = Y - \hat{m}(X)$, $\tilde{T} = T - \hat{r}(X)$
3. **Estimate treatment effect**: $\hat{\tau} = \frac{\sum_i \tilde{T}_i \tilde{Y}_i}{\sum_i \tilde{T}_i^2}$

**Why it works**: The first-stage ML errors don't propagate to $\tau$ estimate due to Neyman orthogonality:

$$\mathbb{E}[\partial_\nu \psi(Z,\eta_0)] = 0$$

Where $\psi$ is the moment condition and $\nu$ are nuisance parameters.

**Key Papers**:
- Chernozhukov, V., et al. (2018). "Double Machine Learning for Treatment and Structural Parameters"
- Athey, S., & Wager, S. (2019). "Generalized Random Forests"

---

### 2.3 High-Dimensional Statistics: Compressed Sensing

#### Nobel-Caliber Insight
**David Donoho & Emmanuel Candès** (Breakthrough Prize, 2016):
> "Compressed sensing shows that one can recover high-dimensional sparse signals from far fewer measurements than the signal dimension, provided the measurement matrix satisfies the Restricted Isometry Property."

#### The Problem
Recover $\mathbf{x} \in \mathbb{R}^p$ (sparse, $\|\mathbf{x}\|_0 \leq k$) from $\mathbf{y} = A\mathbf{x} + \epsilon$ where $m \ll p$ (underdetermined)

#### The Solution: $\ell_1$ Minimization (LASSO)
$$\hat{\mathbf{x}} = \arg\min_{\mathbf{x}} \|\mathbf{y} - A\mathbf{x}\|_2^2 + \lambda \|\mathbf{x}\|_1$$

**Theoretical Guarantee** (RIP Condition):
If $A$ satisfies Restricted Isometry Property with constant $\delta_k < 1$:

$$(1-\delta_k)\|\mathbf{x}\|_2^2 \leq \|A\mathbf{x}\|_2^2 \leq (1+\delta_k)\|\mathbf{x}\|_2^2$$

for all $k$-sparse $\mathbf{x}$, then $\hat{\mathbf{x}}$ recovers $\mathbf{x}$ exactly (or with error $O(\epsilon)$).

#### RIP: Intuition
> "Random matrices satisfy RIP with high probability: Gaussian, Bernoulli, or structured random matrices (Fourier subsample, random convolution) all work."

**Measurement Bound**:
$$m = O(k \log(p/k))$$

This is exponentially better than $p$ measurements! But requires $k$ to be known.

---

## PART III: AI ENGINEERING & LLM SYSTEMS

### 3.1 Retrieval-Augmented Generation (RAG)

#### Historical Context
**Patrick Lewis et al.** (2020) - Facebook AI Research:
> "We show how to augment parametric knowledge in a pre-trained sequence-to-sequence model with non-parametric memory provided by a dense vector index of Wikipedia. This retrieval-augmented generation approach sets new state-of-the-art on open-domain QA."

#### The Architecture
```
Question → [Retriever] → Top-K docs → [Reranker] → Context
                                            ↓
                                        [LLM] + Context → Answer
```

**Retrieval** (Dense Passage Retrieval):
- Encode question: $q_{\text{emb}} = \text{encoder}(q)$
- Encode documents: $d_i^{\text{emb}} = \text{encoder}(d_i)$
- Similarity: $s_i = q_{\text{emb}} \cdot d_i^{\text{emb}} / (\|q_{\text{emb}}\| \cdot \|d_i^{\text{emb}}\|)$

**Critical Issue**: Training retriever & reader jointly requires solving a non-differentiable "top-K selection" problem

#### Information-Theoretic View
**Shannon's Channel Capacity**:
$$C = \log_2(1 + \text{SNR}) \text{ bits/dimension}$$

RAG performance depends on:
1. **Retrieval precision**: $P(\text{relevant doc in top-K})$ — affects signal
2. **Context length capacity**: attention bandwidth $O(n^2)$
3. **Information bottleneck**: reranking balances coverage vs. precision

---

### 3.2 Multi-Agent Orchestration with Game Theory

#### Foundational Theory
**John Nash** (Nobel 1994) - Non-Cooperative Games:
> "It is shown that finite games always have at least one equilibrium point, in mixed strategies. This equilibrium point is the point of rest to which the game outcomes converge in finite games."

#### Agent Coordination Problem
Multiple agents allocate shared resources (compute, memory, context window):
- Agent $i$ has strategy set $S_i$
- Payoff function $u_i(s_1, \ldots, s_n)$ depends on all agents' choices
- **Goal**: Find Nash equilibrium

**Example**: Two agents querying LLM with limited tokens
- Agent 1 gets tokens $t_1$, gets reward $u_1(t_1, t_2)$
- Agent 2 gets tokens $t_2$, gets reward $u_2(t_1, t_2)$
- Constraint: $t_1 + t_2 = T_{\max}$

**Solution**: Use mechanism design to enforce truthful bidding

#### Mechanism Design (Vickrey-Clarke-Groves)
**William Vickrey** (Nobel 1996):
> "The Vickrey auction—where bidders bid truthfully at equilibrium—can be generalized to allocate any divisible resource efficiently."

**VCG payment** for agent $i$:
$$p_i = \sum_{j \neq i} v_j(x^{-i}) - \sum_{j \neq i} v_j(x^*)$$

Where:
- $x^*$ = optimal allocation
- $x^{-i}$ = allocation without agent $i$
- $v_j$ = valuation function

**Key insight**: Agent $i$ pays the external cost imposed on others—truthful bidding is dominant strategy.

---

### 3.3 Fine-Tuning with Convergence Analysis

#### Modern Foundation: Transfer Learning Theory
**Mehryar Borodin & David Cortes** (PAC-Bayes Bound, 2000s):
> "When transferring from a pre-trained model, generalization error is bounded by the source task error plus a term depending on the divergence between source and target distributions."

#### Low-Rank Adaptation (LoRA)
**Edward Hu et al.** (Microsoft, 2021):
> "We show that fine-tuned models have a low intrinsic dimension—we can update only a small number of rank-$r$ matrices $\Delta W = BA$ rather than the full weight matrix $W$."

$$W_{\text{adapted}} = W + \Delta W = W + BA$$

Where $B \in \mathbb{R}^{d \times r}$, $A \in \mathbb{R}^{r \times d}$, $r \ll d$

**Computational savings**: $O(dr)$ vs $O(d^2)$ memory

#### Convergence Analysis for Fine-Tuning
**Supervised Fine-Tuning loss**:
$$L(\theta) = \frac{1}{n}\sum_{i=1}^{n} -\log p_{\theta}(y_i | x_i)$$

**Gradient descent update**:
$$\theta_{t+1} = \theta_t - \eta \nabla L(\theta_t)$$

**Convergence rate** (convex approximation):
$$L(\theta_T) - L(\theta^*) = O(1/T)$$

**In practice** (non-convex landscape):
- **Critical point convergence**: $\|\nabla L(\theta_T)\|^2 = O(1/T)$
- **Generalization gap**: $\text{Train loss} - \text{Test loss} = O(\sqrt{d \log T / n})$

**Reference**: Hu, E. J., et al. (2021). "LoRA: Low-Rank Adaptation of Large Language Models"

---

## PART IV: QUANTUM COMPUTING & ALGORITHMS

### 4.1 Variational Quantum Eigensolver (VQE)

#### 2025 Nobel Prize Context
**John Clarke, Michel Devoret, John Martinis** (Nobel Prize in Physics, 2025):
> "The discovery of macroscopic quantum tunneling and energy quantization in electrical circuits opened the path to superconducting qubits, which form the basis of today's quantum computers."

#### The Problem
Find ground state energy of a quantum Hamiltonian:
$$E_0 = \min_{\psi} \langle \psi | H | \psi \rangle$$

**Classical bottleneck**: Exponential complexity—state space is $2^n$ for $n$ qubits

#### VQE Solution (Peruzzo et al., 2014)
Use a parametrized quantum circuit (ansatz) $|\psi(\boldsymbol{\theta})\rangle$:

$$E(\boldsymbol{\theta}) = \langle \psi(\boldsymbol{\theta}) | H | \psi(\boldsymbol{\theta}) \rangle$$

**Algorithm**:
1. Initialize ansatz parameters $\boldsymbol{\theta}$
2. Measure energy $E(\boldsymbol{\theta})$ on quantum device (sample multiple times due to noise)
3. Use classical optimizer (COBYLA, Adam) to update $\boldsymbol{\theta}$:
   $$\boldsymbol{\theta}_{t+1} = \boldsymbol{\theta}_t - \eta \nabla_{\boldsymbol{\theta}} E(\boldsymbol{\theta}_t)$$
4. Repeat until convergence

**Hybrid advantage**: Quantum device handles what's hard classically (energy computation), classical computer handles easy part (optimization)

#### Hardware Reality: Ansatz Design
**Unitary ansatz** (Trotterization):
$$|\psi(\boldsymbol{\theta})\rangle = \prod_{l=1}^{L} e^{-i\theta_l H_l}$$

Where $H_l$ are Pauli strings. **Problem**: 
- Each gate has $\sim 1\%$ error rate on current hardware (NISQ era)
- Circuit depth $L$ must be shallow (~20-100 gates) to avoid coherence loss
- Barren plateaus: gradients vanish exponentially in $n$ for random initialization

**Fix**: Use problem-inspired ansatz (hardware-efficient layers)

---

### 4.2 Quantum Approximate Optimization Algorithm (QAOA)

#### Seminal Paper
**Farhi, Goldstone, Gutmann** (2014):
> "We show how a quantum computer can efficiently solve combinatorial optimization problems using a time-dependent Hamiltonian that encodes the problem structure."

#### The Problem: Max-Cut
Given graph $G = (V, E)$, partition vertices to maximize edges between partitions:
$$\max_{x \in \{0,1\}^n} \sum_{(i,j) \in E} (1 - x_i x_j)$$

**Classical complexity**: NP-hard. Best classical approximation: Goemans-Williamson $\approx 0.878$-factor

#### QAOA Formulation
**Problem Hamiltonian** (encodes objective):
$$H_P = \sum_{(i,j) \in E} \frac{1}{2}(1 - Z_i Z_j)$$

**Mixer Hamiltonian** (explores solution space):
$$H_M = \sum_i X_i$$

**QAOA unitary** (alternating):
$$U(\boldsymbol{\beta}, \boldsymbol{\gamma}) = \prod_{p=1}^{P} e^{-i\beta_p H_M} e^{-i\gamma_p H_P}$$

Where $p$ is circuit depth (higher $p$ → better approximation, but harder to optimize)

**Expectation value**:
$$E(\boldsymbol{\beta}, \boldsymbol{\gamma}) = \langle \psi_0 | U^\dagger H_P U | \psi_0 \rangle$$

**Optimize** classically over $(\boldsymbol{\beta}, \boldsymbol{\gamma})$

#### Approximation Guarantees
For $p=1$: QAOA achieves $\approx 0.692$-approximation on random Max-Cut (vs 0.5 random)

For portfolio optimization: Encodes Markowitz problem as Max-Weight-Cut → solve with QAOA on quantum hardware

---

### 4.3 Quantum Error Correction & Surface Codes

#### Foundational Work
**Alexei Kitaev** (2003) - Topological Quantum Error Correction:
> "Error correction need not be done by measuring a large number of qubits. Topological codes can correct arbitrary errors using only local measurements."

**Turing Award** (2022) winners **Charles Bennett & Gilles Brassard** (2025):
> "The foundation of quantum information science demonstrates that quantum systems can store, transmit, and process information while maintaining security against eavesdropping."

#### The Challenge
Quantum decoherence: every gate has error rate $\epsilon \sim 10^{-3}$ to $10^{-4}$. To build a fault-tolerant quantum computer, need **quantum error correction**.

#### Surface Code (Kitaev + Google's approach)
**2D grid** of physical qubits. **Stabilizer operators** (measure without disrupting logical information):

$$S_{plaq} = Z_1 Z_2 Z_3 Z_4 \quad \text{(4-body)}, \quad S_{star} = X_1 X_2 X_3 X_4 \text{(4-body)}$$

Measure eigenvalues $\pm 1$ classically → syndrome. Decode via:
$$|\text{error}\rangle = \arg\min_e D(\text{syndrome}, S(e))$$

Where $S(e)$ is predicted syndrome for error $e$, $D$ is graph distance.

**Key result**: If physical error rate $\epsilon < \epsilon_{\text{threshold}} \approx 10^{-3}$, logical error rate exponentially decreases with code distance $d$:

$$\epsilon_L \sim (\epsilon / \epsilon_{\text{th}})^{(d+1)/2}$$

**Current hardware**:
- Google Willow (2024): approaching $\epsilon_{\text{th}}$
- IBM, IonQ: within factor of ~10 of threshold

---

## SUMMARY: Unifying Principles

### Across All Domains

1. **Dimensionality reduction under constraints**: 
   - Trading: High-dimensional portfolio → shrinkage estimators
   - Data Science: High-dim inference → LASSO/RIP
   - AI: High-dim LLM → LoRA (rank-$r$ updates)
   - Quantum: Exponential Hilbert space → shallow circuits + ansatz

2. **Optimization under uncertainty**:
   - Trading: Stochastic control (SDEs)
   - Data Science: Causal estimation (potential outcomes)
   - AI: Non-convex landscape + generalization gap
   - Quantum: Barren plateaus + measurement noise

3. **Information-theoretic bounds**:
   - Sample complexity, generalization, channel capacity
   - Trade-offs between statistical efficiency & computational efficiency

---

## References

**Textbooks & Monographs**:
- Markowitz, H. M. (1987). "Mean-Variance Analysis in Portfolio Choice and Capital Markets"
- Björk, T. (2009). "Arbitrage Theory in Continuous Time" (3rd ed.)
- Murphy, K. P. (2012). "Machine Learning: A Probabilistic Perspective"
- Nielsen, M. A., & Chuang, I. L. (2010). "Quantum Computation and Quantum Information"

**Key Papers**:
- Almgren & Chriss (2000), Heston (1993), Carr & Madan (1999)
- Ledoit & Wolf (2004), Chernozhukov et al. (2018)
- Candès & Tao (2005) on RIP/Compressed Sensing
- Lewis et al. (2020) on RAG
- Hu et al. (2021) on LoRA
- Farhi, Goldstone, Gutmann (2014) on QAOA
- Kitaev (2003) on Topological Codes

---

*Compiled for applied mathematician portfolio development, August 2026*
