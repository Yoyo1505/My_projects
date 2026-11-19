"""Market Risk Lab: historical / parametric / EWMA Monte Carlo VaR & CVaR with Kupiec + Christoffersen backtests.
Usage: python risk_lab.py [--tickers SPY QQQ TLT GLD] [--alpha 0.01]
"""
import argparse
import numpy as np, pandas as pd
from scipy import stats


def load_returns(tickers, years=8):
    import yfinance as yf
    px = yf.download(tickers, period=f"{years}y", auto_adjust=True, progress=False)["Close"].dropna()
    return np.log(px).diff().dropna()


def var_hist(r, a):  return -np.quantile(r, a)
def var_norm(r, a):  return -(r.mean() + r.std() * stats.norm.ppf(a))
def cvar_hist(r, a): return -r[r <= np.quantile(r, a)].mean()


def var_ewma_mc(r, a, lam=0.94, n=20000, seed=0):
    """RiskMetrics volatility with Student-t shocks (df=5, variance-normalised)."""
    sig2 = r.ewm(alpha=1 - lam, adjust=False).var().iloc[-1]
    z = stats.t.rvs(5, size=n, random_state=seed) / np.sqrt(5 / 3)
    return -np.quantile(r.mean() + np.sqrt(sig2) * z, a)


def kupiec(breaches, a):
    """Proportion-of-failures LR test; p < 0.05 -> VaR mis-calibrated."""
    n, x = len(breaches), int(breaches.sum())
    if x in (0, n): return 1.0
    ll = lambda p: x * np.log(p) + (n - x) * np.log(1 - p)
    return 1 - stats.chi2.cdf(-2 * (ll(a) - ll(x / n)), 1)


def christoffersen(b):
    """Independence test: are breaches clustered?"""
    b = np.asarray(b, int); p = np.bincount(2 * b[:-1] + b[1:], minlength=4).astype(float)
    n00, n01, n10, n11 = p
    if min(n01, n11, n10) == 0: return 1.0
    pi01, pi11, pi = n01 / (n00 + n01), n11 / (n10 + n11), (n01 + n11) / p.sum()
    ll = lambda a, b_, c, d: np.sum([x * np.log(y) for x, y in zip((n00, n01, n10, n11), (a, b_, c, d)) if x])
    return 1 - stats.chi2.cdf(-2 * (ll(1 - pi, pi, 1 - pi, pi) - ll(1 - pi01, pi01, 1 - pi11, pi11)), 1)


def backtest(pr, a, window=500):
    out = {"historical": [], "parametric": [], "ewma_t": []}
    for i in range(window, len(pr)):
        w = pr.iloc[i - window:i]
        for k, f in (("historical", var_hist), ("parametric", var_norm), ("ewma_t", var_ewma_mc)):
            out[k].append(pr.iloc[i] < -f(w, a))
    return {k: np.array(v) for k, v in out.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--tickers", nargs="+", default=["SPY", "QQQ", "TLT", "GLD"])
    ap.add_argument("--alpha", type=float, default=0.01); a = ap.parse_args()
    R = load_returns(a.tickers); pr = R.mean(axis=1)              # equal-weight portfolio
    print(f"1-day {1-a.alpha:.0%} VaR / CVaR (portfolio): hist {var_hist(pr,a.alpha):.2%} / {cvar_hist(pr,a.alpha):.2%} | "
          f"normal {var_norm(pr,a.alpha):.2%} | EWMA-t MC {var_ewma_mc(pr,a.alpha):.2%}")
    for k, b in backtest(pr, a.alpha).items():
        print(f"{k:<11} breaches {b.mean():.2%} (target {a.alpha:.0%})  Kupiec p={kupiec(b,a.alpha):.3f}  Christoffersen p={christoffersen(b):.3f}")
