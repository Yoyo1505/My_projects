"""Cardinality-constrained portfolio selection with QAOA (statevector simulation).

Problem: choose exactly K of n assets, x in {0,1}^n, minimising
    f(x) = q * x' Sigma x - mu' x
QUBO with penalty:  C(x) = f(x) + A * (sum_i x_i - K)^2
Bit convention: qubit i <-> bit i of the basis index (little endian, same as qiskit).
"""
import os

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

TICKERS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ", "XLE", "XLK"]
TRAIN_END = "2022-12-31"
TEST_START = "2023-01-01"
TRADING_DAYS = 252


# ---------------------------------------------------------------- data
def load_prices(path="data/adj_close.csv"):
    """Adjusted daily closes; downloads with yfinance if the cached CSV is missing."""
    if not os.path.exists(path):
        import yfinance as yf
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        df = yf.download(TICKERS, start="2015-01-01", auto_adjust=False, progress=False)["Adj Close"]
        df[TICKERS].to_csv(path)
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    return df[TICKERS]


def split_returns(prices):
    rets = prices.pct_change().dropna()
    return rets.loc[:TRAIN_END], rets.loc[TEST_START:]


def estimate_mu_sigma(train_rets):
    """Annualised mean (arithmetic) and Ledoit-Wolf shrunk annualised covariance."""
    mu = train_rets.mean().values * TRADING_DAYS
    lw = LedoitWolf().fit(train_rets.values)
    return mu, lw.covariance_ * TRADING_DAYS, lw.shrinkage_


# ---------------------------------------------------------------- QUBO
def all_bitstrings(n):
    """X[b, i] = bit i of basis index b (qubit i)."""
    b = np.arange(2 ** n)
    return ((b[:, None] >> np.arange(n)[None, :]) & 1).astype(float)


def objective(X, mu, sigma, q):
    return q * np.einsum("bi,ij,bj->b", X, sigma, X) - X @ mu


def qubo_coeffs(mu, sigma, q, K, A):
    """C(x) = c0 + a.x + x' Qs x  with Qs symmetric and zero-diagonal."""
    a = -mu + q * np.diag(sigma) + A * (1 - 2 * K)
    Qs = q * sigma + A
    np.fill_diagonal(Qs, 0.0)
    c0 = A * K ** 2
    return a, Qs, c0


def qubo_cost(X, mu, sigma, q, K, A):
    a, Qs, c0 = qubo_coeffs(mu, sigma, q, K, A)
    return c0 + X @ a + np.einsum("bi,ij,bj->b", X, Qs, X)


def penalised_direct(X, mu, sigma, q, K, A):
    """Penalised objective written directly (used to verify the QUBO expansion)."""
    return objective(X, mu, sigma, q) + A * (X.sum(1) - K) ** 2


def choose_penalty(mu, sigma, q, K, X, start=1e-3):
    """Smallest A (doubling from `start`) for which the global minimum of C is feasible."""
    feas = X.sum(1) == K
    A = start
    while True:
        C = qubo_cost(X, mu, sigma, q, K, A)
        if feas[int(np.argmin(C))]:
            return A
        A *= 2


def ising_from_qubo(a, Qs, c0):
    """x_i = (1 - Z_i)/2  ->  const + sum_i h_i Z_i + sum_{i<j} J_ij Z_i Z_j."""
    B = 2 * Qs  # pair coefficients B_ij (i != j, symmetric)
    const = c0 + a.sum() / 2 + np.triu(B, 1).sum() / 4
    h = -a / 2 - B.sum(1) / 4
    J = np.triu(B, 1) / 4
    return const, h, J


def ising_diag(X, const, h, J):
    Z = 1 - 2 * X
    return const + Z @ h + np.einsum("bi,ij,bj->b", Z, J, Z)


# ---------------------------------------------------------------- brute force
def best_feasible(C, X, K, top=5):
    idx = np.where(X.sum(1) == K)[0]
    return idx[np.argsort(C[idx])][:top]


def bits_to_assets(b, n):
    return [i for i in range(n) if (b >> i) & 1]


def assets_to_bits(assets):
    return int(sum(1 << i for i in assets))


# ---------------------------------------------------------------- QAOA (numpy statevector)
def _apply_x_mixer(psi, beta, n):
    """exp(-i beta sum_q X_q) = prod_q RX(2 beta)."""
    c, s = np.cos(beta), -1j * np.sin(beta)
    t = psi.reshape((2,) * n)
    for q in range(n):
        ax = n - 1 - q
        t = np.moveaxis(t, ax, 0)
        t = np.stack([c * t[0] + s * t[1], s * t[0] + c * t[1]], axis=0)
        t = np.moveaxis(t, 0, ax)
    return t.reshape(-1)


def _apply_xy_ring(psi, beta, n):
    """Ring XY mixer: prod over ring edges of exp(-i beta (XX+YY)/2); conserves Hamming weight."""
    c, s = np.cos(beta), -1j * np.sin(beta)
    t = psi.reshape((2,) * n)
    for q in range(n):
        i, j = n - 1 - q, n - 1 - ((q + 1) % n)
        t = np.moveaxis(t, (i, j), (0, 1))
        shp = t.shape
        v = t.reshape(4, -1)
        new = v.copy()  # basis order |00>,|01>,|10>,|11>; only the {01,10} block is mixed
        new[1] = c * v[1] + s * v[2]
        new[2] = s * v[1] + c * v[2]
        t = np.moveaxis(new.reshape(shp), (0, 1), (i, j))
    return t.reshape(-1)


def dicke_state(n, K, X):
    """Uniform superposition over all bitstrings of Hamming weight K (Dicke state |D^n_K>)."""
    psi = (X.sum(1) == K).astype(complex)
    return psi / np.sqrt(psi.real.sum())


def qaoa_state(C, gammas, betas, n, mixer="x", init=None):
    psi = np.full(2 ** n, 1 / np.sqrt(2 ** n), dtype=complex) if init is None else init.copy()
    mix = _apply_x_mixer if mixer == "x" else _apply_xy_ring
    for g, b in zip(gammas, betas):
        psi = psi * np.exp(-1j * g * C)
        psi = mix(psi, b, n)
    return psi


def expectation(psi, C):
    return float(np.sum(np.abs(psi) ** 2 * C))


def run_qaoa(C, n, p, mixer="x", init=None, n_starts=6, seed=0, maxiter=400):
    """COBYLA from several random starts; returns the best run and all run costs."""
    rng = np.random.default_rng(seed)
    scale = C.max() - C.min()
    runs = []
    for _ in range(n_starts):
        x0 = np.concatenate([rng.uniform(0, np.pi / scale, p), rng.uniform(0, np.pi / 2, p)])
        f = lambda th: expectation(qaoa_state(C, th[:p], th[p:], n, mixer, init), C)
        res = minimize(f, x0, method="COBYLA", options={"maxiter": maxiter, "rhobeg": 0.3})
        runs.append((float(res.fun), res.x[:p], res.x[p:]))
    runs.sort(key=lambda r: r[0])
    best = runs[0]
    return {"expected_cost": best[0], "gammas": best[1], "betas": best[2],
            "all_run_costs": [r[0] for r in runs]}


def measure_stats(psi, C, X, K, opt_bits, shots=4096, seed=1):
    """Exact probabilities plus shot-sampled best feasible portfolio."""
    probs = np.abs(psi) ** 2
    probs = probs / probs.sum()
    feas = X.sum(1) == K
    rng = np.random.default_rng(seed)
    draws = rng.choice(len(probs), size=shots, p=probs)
    dfeas = feas[draws]
    out = {
        "p_opt": float(probs[opt_bits]),
        "p_feasible": float(probs[feas].sum()),
        "shots_feasible_frac": float(dfeas.mean()),
    }
    if dfeas.any():
        cand = draws[dfeas]
        b = int(cand[np.argmin(C[cand])])
        out["best_sampled_feasible"] = b
        out["best_sampled_cost"] = float(C[b])
    else:
        out["best_sampled_feasible"] = None
        out["best_sampled_cost"] = np.nan
    return out


def approx_ratio(exp_cost, C_mean, C_min):
    """1 = optimum, 0 = mean cost of a uniformly random guess."""
    return (C_mean - exp_cost) / (C_mean - C_min)


# ---------------------------------------------------------------- Qiskit cross-check
def qiskit_crosscheck(psi_np, gammas, betas, n, const, h, J, C_np):
    """Rebuild the same p-layer circuit with qiskit gates and compare states and expectations."""
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp, Statevector

    qc = QuantumCircuit(n)
    qc.h(range(n))
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n) if abs(J[i, j]) > 0]
    for g, b in zip(gammas, betas):
        for i in range(n):
            qc.rz(2 * g * h[i], i)          # exp(-i g h Z) = RZ(2 g h)
        for i, j in pairs:
            qc.rzz(2 * g * J[i, j], i, j)   # exp(-i g J ZZ) = RZZ(2 g J)
        for i in range(n):
            qc.rx(2 * b, i)                 # exp(-i b X) = RX(2 b)
    sv = Statevector(qc)
    fidelity = float(abs(np.vdot(psi_np, sv.data)))

    terms = [("Z", [i], h[i]) for i in range(n) if abs(h[i]) > 0]
    terms += [("ZZ", [i, j], J[i, j]) for i, j in pairs]
    op = SparsePauliOp.from_sparse_list(terms, num_qubits=n) + SparsePauliOp.from_list([("I" * n, const)])
    e_qiskit = float(np.real(sv.expectation_value(op)))
    return {"fidelity": fidelity, "exp_qiskit": e_qiskit, "exp_numpy": expectation(psi_np, C_np)}


# ---------------------------------------------------------------- baselines and evaluation
def greedy_forward(mu, sigma, q, K):
    n = len(mu)
    S = []
    for _ in range(K):
        best, best_val = None, np.inf
        for i in range(n):
            if i in S:
                continue
            val = subset_objective(S + [i], mu, sigma, q)
            if val < best_val:
                best, best_val = i, val
        S.append(best)
    return sorted(S)


def subset_objective(assets, mu, sigma, q):
    x = np.zeros(len(mu))
    x[list(assets)] = 1
    return q * x @ sigma @ x - mu @ x


def portfolio_metrics(assets, test_rets):
    """Equal weight over `assets`, daily rebalanced, simple returns, rf = 0."""
    r = test_rets.iloc[:, list(assets)].mean(axis=1).values
    ann_ret = r.mean() * TRADING_DAYS
    vol = r.std(ddof=1) * np.sqrt(TRADING_DAYS)
    w = np.r_[1.0, np.cumprod(1 + r)]
    mdd = float((w / np.maximum.accumulate(w) - 1).min())
    return {"ann_return": ann_ret, "ann_vol": vol, "sharpe": ann_ret / vol,
            "max_drawdown": mdd, "wealth": w}
