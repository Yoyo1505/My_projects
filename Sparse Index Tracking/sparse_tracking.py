"""Sparse index tracking of the S&P 500 (proxied by SPY) with non-negative LASSO.

Pipeline
--------
1. Data: daily adjusted closes / volumes from Yahoo Finance (yfinance).
2. Selection: min_w 0.5*||r - R w||^2 + lam * sum(w), w >= 0 (NNLS on a
   Cholesky/QR-transformed system), weights renormalised to sum to 1, and lam
   found by bisection so that exactly K weights are non-zero.
3. Re-fit: long-only, sum-to-one least squares on the selected support (SLSQP).
4. Baselines: top-K by trailing market-cap proxy (equal and dollar-volume
   weights), random K-subsets (re-fitted the same way), greedy forward selection.
5. Walk-forward: 3-year training window, hold 6 months, roll forward by 6 months.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
from scipy.linalg import solve_triangular
from scipy.optimize import minimize, nnls

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

INDEX = "SPY"
TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "JPM", "JNJ", "XOM", "PG", "HD", "V", "MA",
    "UNH", "KO", "PEP", "WMT", "CVX", "MRK", "ABBV", "BAC", "PFE", "CSCO", "ADBE",
    "CRM", "NFLX", "COST", "TMO", "AVGO", "MCD", "ACN", "LIN", "DHR", "TXN", "NEE",
    "HON", "QCOM", "UPS", "ORCL", "AMGN",
]
START = "2018-11-19"
TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
def download_data(start: str = START, end: str | None = None, use_cache: bool = True):
    """Download (or load cached) adjusted closes, volumes and shares outstanding.

    Returns dict with keys close, volume, shares (Series), dropped (list of str).
    """
    os.makedirs(DATA_DIR, exist_ok=True)
    close_p = os.path.join(DATA_DIR, "adj_close.csv")
    vol_p = os.path.join(DATA_DIR, "volume.csv")
    shares_p = os.path.join(DATA_DIR, "shares_outstanding.json")
    symbols = TICKERS + [INDEX]

    if use_cache and all(os.path.exists(p) for p in (close_p, vol_p, shares_p)):
        close = pd.read_csv(close_p, index_col=0, parse_dates=True)
        volume = pd.read_csv(vol_p, index_col=0, parse_dates=True)
        with open(shares_p) as fh:
            shares = pd.Series(json.load(fh), dtype=float)
    else:
        raw = yf.download(symbols, start=start, end=end, auto_adjust=True,
                          progress=False, group_by="column")
        close, volume = raw["Close"], raw["Volume"]
        close.to_csv(close_p)
        volume.to_csv(vol_p)
        shares_d = {}
        for t in TICKERS:
            try:
                s = yf.Ticker(t).info.get("sharesOutstanding")
            except Exception:
                s = None
            if s:
                shares_d[t] = float(s)
        with open(shares_p, "w") as fh:
            json.dump(shares_d, fh, indent=1)
        shares = pd.Series(shares_d, dtype=float)

    # Keep only completed sessions: drop today's row, which may be an intraday value.
    today = pd.Timestamp.today().normalize()
    close = close[close.index < today]
    volume = volume[volume.index < today]

    # Drop tickers with missing history (any NaN in the sample, or no share count).
    missing = [c for c in close.columns if close[c].isna().any()]
    missing += [c for c in close.columns if c not in shares.index and c != INDEX]
    missing = sorted(set(missing) - {INDEX})
    keep = [c for c in close.columns if c not in missing]
    close = close[keep].dropna()
    volume = volume[keep].reindex(close.index)
    shares = shares.reindex([c for c in close.columns if c != INDEX])
    return {"close": close, "volume": volume, "shares": shares, "dropped": missing}


def simple_returns(close: pd.DataFrame) -> pd.DataFrame:
    """Simple daily returns p_t / p_{t-1} - 1 (used consistently everywhere)."""
    return close.pct_change().dropna()


# ---------------------------------------------------------------------------
# Sparse selection
# ---------------------------------------------------------------------------
def sparse_nnls(R: np.ndarray, r: np.ndarray, lam: float) -> np.ndarray:
    """Solve min_{w>=0} 0.5*||r - R w||^2 + lam * sum(w) exactly.

    Thin QR R = Q U gives 0.5||r-Rw||^2 = 0.5||q - U w||^2 + const with q = Q'r.
    The linear term lam*1'w is absorbed by choosing v with U'v = U'q - lam*1,
    so the problem becomes min_{w>=0} ||U w - v||, solved by scipy's NNLS.
    """
    Q, U = np.linalg.qr(R)
    q = Q.T @ r
    c = U.T @ q - lam
    v = solve_triangular(U.T, c, lower=True)
    w, _ = nnls(U, v)
    return w


def select_sparse(R: np.ndarray, r: np.ndarray, K: int, iters: int = 80):
    """Bisection on log(lam) so that exactly K weights are non-zero.

    Returns (weights renormalised to sum 1, lam, exact_flag, support_indices).
    If no lam gives exactly K non-zeros, the support is the top-K weights at the
    smallest lam that yields more than K non-zeros (exact_flag = False).
    """
    tol = 1e-10
    lo = 1e-12
    hi = 1.01 * float(np.max(R.T @ r))  # above this lam all weights are zero

    def solve(lam):
        w = sparse_nnls(R, r, lam)
        s = w.sum()
        return w / s if s > 0 else w

    best_lo_w = None
    for _ in range(iters):
        mid = np.sqrt(lo * hi)
        w = solve(mid)
        nz = int(np.sum(w > tol))
        if nz == K:
            support = np.flatnonzero(w > tol)
            return w, mid, True, support
        if nz > K:
            lo = mid
            best_lo_w = (w, mid)
        else:
            hi = mid
    if best_lo_w is None:
        best_lo_w = (solve(lo), lo)
    w, lam = best_lo_w
    support = np.argsort(-w)[:K]
    return w, lam, False, np.sort(support)


def refit_subset(Rs: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Long-only, sum-to-one least squares on a given support (SLSQP)."""
    T, n = Rs.shape
    if n == 1:
        return np.ones(1)
    scale = 1e4  # keeps the objective O(1) for SLSQP tolerances

    def f(w):
        e = r - Rs @ w
        return scale * np.mean(e * e)

    def g(w):
        e = r - Rs @ w
        return -2.0 * scale * (Rs.T @ e) / T

    res = minimize(
        f, np.full(n, 1.0 / n), jac=g, method="SLSQP", bounds=[(0.0, 1.0)] * n,
        constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1.0,
                      "jac": lambda w: np.ones(n)}],
        options={"maxiter": 500, "ftol": 1e-12},
    )
    w = np.clip(res.x, 0.0, None)
    return w / w.sum()


def tracking_mse(R: np.ndarray, r: np.ndarray, idx, w) -> float:
    return float(np.mean((r - R[:, idx] @ w) ** 2))


def greedy_path(R: np.ndarray, r: np.ndarray, Kmax: int) -> list:
    """Forward selection: at each step add the stock that most reduces the
    in-sample tracking MSE after re-fitting the weights on the enlarged set."""
    N = R.shape[1]
    selected: list = []
    for _ in range(Kmax):
        best_j, best_err = None, np.inf
        for j in range(N):
            if j in selected:
                continue
            idx = selected + [j]
            w = refit_subset(R[:, idx], r)
            err = tracking_mse(R, r, idx, w)
            if err < best_err:
                best_j, best_err = j, err
        selected.append(best_j)
    return selected


# ---------------------------------------------------------------------------
# Walk-forward machinery
# ---------------------------------------------------------------------------
def make_windows(dates: pd.DatetimeIndex, train_years: int = 3, test_months: int = 6):
    """List of (train_mask, test_mask) boolean arrays over the return dates."""
    end = dates[-1] + pd.Timedelta(days=1)
    t = dates[0] + pd.DateOffset(years=train_years)
    windows = []
    while t < end:
        tr_start = t - pd.DateOffset(years=train_years)
        te_end = min(t + pd.DateOffset(months=test_months), end)
        train = (dates >= tr_start) & (dates < t)
        test = (dates >= t) & (dates < te_end)
        if test.any() and train.any():
            windows.append((train, test))
        t = t + pd.DateOffset(months=test_months)
    return windows


def _full(N: int, idx, w) -> np.ndarray:
    out = np.zeros(N)
    out[list(idx)] = w
    return out


def port_returns(W: np.ndarray, R: np.ndarray, windows) -> np.ndarray:
    """Concatenated out-of-sample portfolio returns; W[k] are weights for window k."""
    pieces = [R[test] @ W[k] for k, (_, test) in enumerate(windows)]
    return np.concatenate(pieces)


def te_per_window(W, R, r, windows, which: str) -> float:
    vals = []
    for k, (train, test) in enumerate(windows):
        m = train if which == "in" else test
        vals.append(np.std(R[m] @ W[k] - r[m], ddof=1) * np.sqrt(TRADING_DAYS))
    return float(np.mean(vals))


def turnover(W: np.ndarray) -> float:
    """Mean two-way turnover sum|w_t - w_{t-1}| over rebalances (first buy excluded)."""
    if len(W) < 2:
        return float("nan")
    return float(np.mean(np.abs(np.diff(W, axis=0)).sum(axis=1)))


def summarise(W, R, r, windows, name: str) -> dict:
    oos_p = port_returns(W, R, windows)
    oos_idx = np.concatenate([np.flatnonzero(test) for _, test in windows])
    oos_t = r[oos_idx]
    diff = oos_p - oos_t
    return {
        "method": name,
        "n_stocks": float(np.mean(np.sum(W > 1e-8, axis=1))),
        "TE_IS_ann": te_per_window(W, R, r, windows, "in"),
        "TE_OOS_ann": float(np.std(diff, ddof=1) * np.sqrt(TRADING_DAYS)),
        "TE_OOS_window_mean": te_per_window(W, R, r, windows, "out"),
        "corr_SPY": float(np.corrcoef(oos_p, oos_t)[0, 1]),
        "ret_gap_ann": float((oos_p.mean() - oos_t.mean()) * TRADING_DAYS),
        "turnover_per_rebal": turnover(W),
    }


def run_walk_forward(close: pd.DataFrame, volume: pd.DataFrame, shares: pd.Series,
                     Ks=(5, 10, 15, 20), n_random: int = 200, seed: int = 42,
                     train_years: int = 3, test_months: int = 6, verbose: bool = True):
    """Full out-of-sample study. Returns a dict of DataFrames / arrays."""
    stocks = [c for c in close.columns if c != INDEX]
    N = len(stocks)
    rets = simple_returns(close)
    R = rets[stocks].to_numpy()
    r = rets[INDEX].to_numpy()
    dates = rets.index
    windows = make_windows(dates, train_years, test_months)
    nW = len(windows)
    rng = np.random.default_rng(seed)
    Kmax = max(Ks)

    # Trailing scores on prices (aligned to return dates via close index).
    mcap = close[stocks] * shares[stocks]
    dvol = close[stocks] * volume[stocks]

    W = {}           # method name -> (nW, N) weights
    lam_log = {K: [] for K in Ks}
    exact_log = {K: [] for K in Ks}
    greedy_paths = []
    W_rand = {K: np.zeros((n_random, nW, N)) for K in Ks}

    for k, (train, test) in enumerate(windows):
        R_tr, r_tr = R[train], r[train]
        tr_dates = dates[train]
        mcap_score = mcap.loc[tr_dates].mean().to_numpy()
        dv_score = dvol.loc[tr_dates].mean().to_numpy()
        path = greedy_path(R_tr, r_tr, Kmax)
        greedy_paths.append(path)

        for K in Ks:
            # Sparse NNLS selection + SLSQP re-fit on the support.
            w_l, lam, exact, support = select_sparse(R_tr, r_tr, K)
            w_sub = refit_subset(R_tr[:, support], r_tr)
            W.setdefault(f"Sparse K={K}", np.zeros((nW, N)))[k] = _full(N, support, w_sub)
            lam_log[K].append(lam)
            exact_log[K].append(exact)

            # Top-K by market-cap proxy: equal weight and dollar-volume weight.
            top = np.argsort(-mcap_score)[:K]
            W.setdefault(f"Top-{K} mcap, equal", np.zeros((nW, N)))[k] = _full(
                N, top, np.full(K, 1.0 / K))
            dv_w = dv_score[top] / dv_score[top].sum()
            W.setdefault(f"Top-{K} mcap, DV-weighted", np.zeros((nW, N)))[k] = _full(
                N, top, dv_w)

            # Greedy forward selection (prefix of the greedy path), re-fitted.
            g_idx = path[:K]
            w_g = refit_subset(R_tr[:, g_idx], r_tr)
            W.setdefault(f"Greedy K={K}", np.zeros((nW, N)))[k] = _full(N, g_idx, w_g)

            # Random K-subsets, re-fitted the same way.
            for d in range(n_random):
                idx = rng.choice(N, size=K, replace=False)
                w_r = refit_subset(R_tr[:, idx], r_tr)
                W_rand[K][d, k] = _full(N, idx, w_r)
        if verbose:
            print(f"window {k + 1}/{nW}: train {dates[train][0].date()}..{dates[train][-1].date()}"
                  f" | test {dates[test][0].date()}..{dates[test][-1].date()}")

    # Summaries
    rows = [summarise(W[name], R, r, windows, name) for name in W]
    summary = pd.DataFrame(rows)

    rand_rows = []
    rand_oos = {}
    for K in Ks:
        per_draw = []
        for d in range(n_random):
            s = summarise(W_rand[K][d], R, r, windows, f"Random K={K}")
            per_draw.append(s)
        dfd = pd.DataFrame(per_draw)
        rand_oos[K] = dfd
        rand_rows.append({
            "method": f"Random K={K} (median of {n_random})",
            "n_stocks": K,
            "TE_IS_ann": dfd.TE_IS_ann.median(),
            "TE_OOS_ann": dfd.TE_OOS_ann.median(),
            "TE_OOS_window_mean": dfd.TE_OOS_window_mean.median(),
            "corr_SPY": dfd.corr_SPY.median(),
            "ret_gap_ann": dfd.ret_gap_ann.median(),
            "turnover_per_rebal": dfd.turnover_per_rebal.median(),
        })
    summary = pd.concat([summary, pd.DataFrame(rand_rows)], ignore_index=True)

    random_dist = pd.DataFrame({
        K: rand_oos[K].TE_OOS_ann.describe(percentiles=[0.05, 0.5, 0.95]) for K in Ks
    }).T
    random_dist.index.name = "K"

    oos_idx = np.concatenate([np.flatnonzero(t) for _, t in windows])
    oos_dates = dates[oos_idx]
    oos_returns = pd.DataFrame({name: port_returns(W[name], R, windows) for name in W},
                               index=oos_dates)
    oos_returns[INDEX] = r[oos_idx]

    lam_table = pd.DataFrame({f"K={K}": {"exact_fraction": float(np.mean(exact_log[K])),
                                         "median_lambda": float(np.median(lam_log[K]))}
                              for K in Ks})
    last = nW - 1
    last_weights = {
        f"Sparse K={K}": pd.Series(W[f"Sparse K={K}"][last], index=stocks)
        for K in Ks
    }
    greedy_names = [stocks[j] for j in greedy_paths[-1]]
    return {
        "stocks": stocks,
        "windows": windows,
        "dates": dates,
        "summary": summary,
        "random_dist": random_dist,
        "oos_returns": oos_returns,
        "weights_last": last_weights,
        "lambda_exact": lam_table,
        "greedy_last_path": greedy_names,
        "greedy_paths": greedy_paths,
        "W": W,
        "W_rand": W_rand,
        "rand_oos": rand_oos,
        "window_dates": [(dates[tr][0], dates[tr][-1], dates[te][0], dates[te][-1])
                         for tr, te in windows],
    }


# ---------------------------------------------------------------------------
# Plots
# ---------------------------------------------------------------------------
def plot_te_vs_k(res, Ks=(5, 10, 15, 20)):
    s = res["summary"]
    fig, ax = plt.subplots(figsize=(8, 5))
    series = {
        "Sparse (NNLS)": s[s.method.str.startswith("Sparse")],
        "Top-K mcap, equal": s[s.method.str.contains("mcap, equal")],
        "Top-K mcap, DV-weighted": s[s.method.str.contains("DV-weighted")],
        "Greedy forward": s[s.method.str.startswith("Greedy")],
    }
    for label, df in series.items():
        df = df.copy()
        df["K"] = df.method.str.extract(r"(?:K=|Top-)(\d+)")[0].astype(int)
        df = df.sort_values("K")
        ax.plot(df.K, df.TE_OOS_ann * 100, marker="o", label=label)
    rd = res["random_dist"]
    ax.plot(rd.index, rd["50%"] * 100, "k--", marker="s", label="Random (median)")
    ax.fill_between(rd.index, rd["5%"] * 100, rd["95%"] * 100, color="grey", alpha=0.2,
                    label="Random (5-95%)")
    ax.set_xlabel("K (number of stocks)")
    ax.set_ylabel("Out-of-sample tracking error (% ann.)")
    ax.set_title("Out-of-sample tracking error vs K")
    ax.set_xticks(list(Ks))
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_cumulative(res, name="Sparse K=15"):
    oo = res["oos_returns"]
    cum = (1 + oo[[name, INDEX]]).cumprod() - 1
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(cum.index, cum[name] * 100, label=name)
    ax.plot(cum.index, cum[INDEX] * 100, label=INDEX, alpha=0.8)
    ax.set_ylabel("Cumulative return (%)")
    ax.set_title(f"Out-of-sample cumulative return: {name} vs {INDEX}")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    return fig


def plot_weights(res, name="Sparse K=15"):
    w = res["weights_last"][name]
    w = w[w > 1e-8].sort_values(ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(w.index, w.values * 100)
    ax.set_ylabel("Weight (%)")
    ax.set_title(f"{name}: weights from the last walk-forward fit")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig
