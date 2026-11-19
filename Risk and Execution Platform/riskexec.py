"""Risk and Execution Platform: allocation -> regime-aware VaR -> liquidation cost -> Heston-priced hedge.

Each function is small and testable; the notebook strings them into one pipeline.
"""
import sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats, integrate, optimize
from sklearn.mixture import GaussianMixture
from sklearn.covariance import LedoitWolf

sys.path[:0] = [str(Path(__file__).resolve().parent.parent / "Financial Risk Analysis")]
import risk_lab as RL  # historical / EWMA-t VaR, Kupiec, Christoffersen

TICKERS = ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"]


# ---------------------------------------------------------------- data
def load_prices(tickers=TICKERS, start="2014-01-01"):
    import yfinance as yf
    px = yf.download(tickers + ["^VIX"], start=start, auto_adjust=True, progress=False)
    close = px["Close"].dropna(how="all")
    vol = px["Volume"][tickers].reindex(close.index)
    return close.dropna(subset=tickers), vol


# ---------------------------------------------------------------- allocation
def momentum_views(ret, lookback=252, top=3, spread=0.02):
    """Mechanical views (no hindsight): the top momentum assets beat the bottom ones by `spread` a year."""
    mom = (1 + ret.iloc[-lookback:]).prod() - 1
    order = mom.sort_values()
    n = len(mom); cols = list(mom.index)
    P = np.zeros((1, n))
    for a in order.index[-top:]: P[0, cols.index(a)] = 1 / top
    for a in order.index[:top]: P[0, cols.index(a)] = -1 / top
    return P, np.array([spread])


def black_litterman(ret, w_prior, P, Q, delta=2.5, tau=0.05):
    """Posterior mean and covariance (He-Litterman form) with Omega = diag(P tau Sigma P')."""
    S = LedoitWolf().fit(ret.values).covariance_ * 252
    pi = delta * S @ w_prior
    omega = np.diag(np.diag(P @ (tau * S) @ P.T))
    A = np.linalg.inv(np.linalg.inv(tau * S) + P.T @ np.linalg.inv(omega) @ P)
    mu = A @ (np.linalg.inv(tau * S) @ pi + P.T @ np.linalg.inv(omega) @ Q)
    return mu, S + A


def mean_variance_weights(mu, S, delta=2.5, cap=0.4):
    """Long-only, fully invested, per-asset cap: max mu'w - delta/2 w'Sw."""
    n = len(mu)
    res = optimize.minimize(lambda w: -(mu @ w - 0.5 * delta * w @ S @ w), np.ones(n) / n, method="SLSQP",
                            bounds=[(0, cap)] * n, constraints={"type": "eq", "fun": lambda w: w.sum() - 1})
    return res.x


def inverse_vol_prior(ret):
    iv = 1 / ret.std()
    return (iv / iv.sum()).values


def rolling_allocation(prices, start_year=2018, train_years=3):
    """Yearly rebalance. Returns daily returns of equal weight, inverse-vol prior and BL-momentum, plus BL weights."""
    ret = prices.pct_change().dropna()
    out = {k: [] for k in ("equal", "prior", "bl")}
    W = {}
    for y in range(start_year, ret.index.year.max() + 1):
        tr = ret[ret.index < f"{y}-01-01"].iloc[-252 * train_years:]
        te = ret[ret.index.year == y]
        if len(tr) < 400 or te.empty:
            continue
        wp = inverse_vol_prior(tr)
        P, Q = momentum_views(tr)
        mu, S = black_litterman(tr, wp, P, Q)
        wb = mean_variance_weights(mu, S)
        W[y] = pd.Series(wb, ret.columns)
        out["equal"].append(te.mean(axis=1)); out["prior"].append(te @ wp); out["bl"].append(te @ wb)
    return pd.DataFrame({k: pd.concat(v) for k, v in out.items()}), pd.DataFrame(W)


# ---------------------------------------------------------------- regime-aware VaR
def regime_features(r):
    return pd.DataFrame({"vol": r.rolling(20).std() * np.sqrt(252), "ret5": r.rolling(5).sum()})


def regime_var(r, alpha=0.01, window=750, refit=63, k=3, seed=0):
    """Rolling out-of-sample one-day VaR from a k-regime mixture on (20d vol, 5d return).
    Per regime: mean and std of the NEXT-day return; VaR = quantile of the probability-weighted mixture."""
    f = regime_features(r).dropna()
    nxt = r.shift(-1).reindex(f.index)
    vals = {}
    gm = None
    for i in range(window, len(f) - 1):
        if (i - window) % refit == 0:
            tr = f.iloc[i - window:i]
            y = nxt.iloc[i - window:i].values
            ok = ~np.isnan(y)
            mu_f, sd_f = tr.mean(), tr.std()
            z = ((tr - mu_f) / sd_f).values
            gm = GaussianMixture(k, covariance_type="full", random_state=seed, n_init=2).fit(z)
            lab = gm.predict(z)
            mus = np.array([y[ok & (lab == j)].mean() if (ok & (lab == j)).sum() > 5 else y[ok].mean() for j in range(k)])
            sds = np.array([y[ok & (lab == j)].std() if (ok & (lab == j)).sum() > 5 else y[ok].std() for j in range(k)])
        pk = gm.predict_proba(((f.iloc[[i]] - mu_f) / sd_f).values)[0]
        q = optimize.brentq(lambda x: (pk * stats.norm.cdf(x, mus, sds)).sum() - alpha, -0.5, 0.5)
        vals[f.index[i]] = -q
    return pd.Series(vals)


def backtest_var(r, var, alpha=0.01):
    """Breach when the next-day return is below -VaR (VaR known at the close of day t)."""
    nxt = r.shift(-1).reindex(var.index)
    b = (nxt < -var).where(nxt.notna()).dropna().astype(bool)
    return {"days": len(b), "breaches": int(b.sum()), "rate": float(b.mean()),
            "kupiec_p": RL.kupiec(b.values, alpha), "christoffersen_p": RL.christoffersen(b.values)}


def rolling_baselines(r, alpha=0.01, window=750):
    h = pd.Series({r.index[i]: RL.var_hist(r.iloc[i - window:i + 1], alpha) for i in range(window, len(r) - 1)})
    e = pd.Series({r.index[i]: RL.var_ewma_mc(r.iloc[i - window:i + 1], alpha, n=4000) for i in range(window, len(r) - 1)})
    return h, e


# ---------------------------------------------------------------- liquidity / execution (Almgren-Chriss style)
def ac_liquidation_cost(notional, adv_usd, sigma_daily, horizon_days=1, theta=0.10):
    """Expected cost (fraction of notional) and price std dev (fraction) of liquidating over horizon_days with TWAP.
    Linear permanent (gamma) and temporary (eta) impact set to `theta` of daily volatility per ADV (an assumption)."""
    X = notional / adv_usd                      # order size in units of ADV
    gamma = eta = theta * sigma_daily
    cost = 0.5 * gamma * X + eta * (X / horizon_days)
    sd = sigma_daily * np.sqrt(horizon_days / 3)
    return cost, sd


def portfolio_liquidation(w, notional, adv_usd, sigma_daily, horizon_days=1, theta=0.10):
    tot, costs = 0.0, {}
    for a, wi in w.items():
        if wi <= 0:
            continue
        c, _ = ac_liquidation_cost(notional * wi, adv_usd[a], sigma_daily[a], horizon_days, theta)
        costs[a] = c
        tot += c * wi
    return tot, costs


# ---------------------------------------------------------------- Heston (little-trap formulation)
def heston_call(S, K, T, r, kappa, theta, xi, rho, v0):
    i = 1j

    def cf(u):
        b = kappa - rho * xi * i * u
        d = np.sqrt(b ** 2 + xi ** 2 * (i * u + u ** 2))
        g = (b - d) / (b + d)
        e = np.exp(-d * T)
        C = r * i * u * T + (kappa * theta / xi ** 2) * ((b - d) * T - 2 * np.log((1 - g * e) / (1 - g)))
        D = ((b - d) / xi ** 2) * (1 - e) / (1 - g * e)
        return np.exp(C + D * v0 + i * u * np.log(S))

    lnK = np.log(K)
    phi_m_i = cf(-i)
    p1 = 0.5 + integrate.quad(lambda u: (np.exp(-i * u * lnK) * cf(u - i) / (i * u * phi_m_i)).real, 1e-8, 150, limit=200)[0] / np.pi
    p2 = 0.5 + integrate.quad(lambda u: (np.exp(-i * u * lnK) * cf(u) / (i * u)).real, 1e-8, 150, limit=200)[0] / np.pi
    return S * p1 - K * np.exp(-r * T) * p2


def heston_put(S, K, T, r, *p):
    return heston_call(S, K, T, r, *p) - S + K * np.exp(-r * T)


def bs_call(S, K, T, r, sig):
    d1 = (np.log(S / K) + (r + sig ** 2 / 2) * T) / (sig * np.sqrt(T))
    d2 = d1 - sig * np.sqrt(T)
    return S * stats.norm.cdf(d1) - K * np.exp(-r * T) * stats.norm.cdf(d2)


HESTON = dict(kappa=4.0, theta=0.04, xi=0.9, rho=-0.7)   # assumed, typical equity values (not calibrated here)


def hedge_backtest(prices, port_ret, vix, moneyness=0.95, T=63, hedge_ratio=1.0, r=0.03, params=HESTON):
    """Quarterly protective put on SPY sized to the portfolio's SPY beta, priced by Heston with v0 = (VIX/100)^2.
    These are model prices, not market quotes, so the premium drag is an estimate."""
    spy = prices["SPY"]
    spy_ret = spy.pct_change().dropna()
    pr = port_ret.dropna()
    beta = np.cov(pr, spy_ret.reindex(pr.index))[0, 1] / spy_ret.reindex(pr.index).var()
    idx = pr.index
    hedged = pr.copy()
    log = []
    starts = list(range(0, len(idx) - T, T))
    notional = hedge_ratio * beta
    for s in starts:
        d0, d1 = idx[s], idx[s + T]
        S0, S1 = spy.loc[d0], spy.loc[d1]
        K = moneyness * S0
        prem = heston_put(S0, K, T / 252, r, params["kappa"], params["theta"], params["xi"], params["rho"],
                          (vix.loc[d0] / 100) ** 2) / S0
        prev = prem                                           # value paid at d0, in units of S0
        for j in range(1, T + 1):                             # mark the put to market every day
            dj = idx[s + j]
            tau = (T - j) / 252
            if tau <= 0:
                val = max(K - spy.loc[dj], 0) / S0
            else:
                val = heston_put(spy.loc[dj], K, tau, r, params["kappa"], params["theta"], params["xi"],
                                 params["rho"], (vix.loc[dj] / 100) ** 2) / S0
            hedged.loc[dj] += notional * (val - prev)          # daily P&L of the long put
            prev = val
        log.append(dict(date=d0, premium_pct=prem * 100, payoff_pct=max(K - S1, 0) / S0 * 100, vix=vix.loc[d0]))
    keep = hedged.loc[idx[1]:idx[starts[-1] + T]]
    return keep, pr.loc[keep.index], pd.DataFrame(log), beta


def cvar(x, a=0.01):
    x = np.asarray(x)
    q = np.quantile(x, a)
    return -x[x <= q].mean()


def max_drawdown(r):
    c = (1 + r).cumprod()
    return (c / c.cummax() - 1).min()
