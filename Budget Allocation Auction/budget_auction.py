"""Budget allocation auction: VCG (Clarke pivot) vs simpler allocation rules.

SIMULATION. The valuations are simulated. Only the per-center *structure*
(relative size of overspend, overspend ratio) is taken from the synthetic demo
dataset ``Cashi RAG/aggs/_consolidado.parquet`` (created by seed_demo_data.py).

Model
-----
* A budget of B slots (one slot = one money unit of extra funding).
* Unit i has a private concave marginal value curve for slot k = 1..K:
      v_i(k) = m_i * d_i**(k-1),      0 < d_i < 1
  Its true total value of k slots is V_i(k) = sum_{j<=k} v_i(j).
* A unit reports a curve (m_rep, d_rep). Reports are the only thing the
  mechanisms see.
* Mechanisms
    VCG          : allocate the B highest reported slot values (greedy is optimal
                   for concave curves); Clarke pivot payment
                   p_i = W_{-i} - (W - reported value of i's slots).
    Proportional : split B slots in proportion to each unit's total reported
                   value (sum over K slots), largest-remainder rounding, cap K;
                   no payment.
    FirstPrice   : same allocation as VCG; winners pay their reported value.
    Uniform      : same allocation as VCG; every won slot pays the highest
                   losing bid, i.e. the (B+1)-th highest reported slot value.
* Utility of unit i = true value of its allocated slots - payment.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 2026
K_SLOTS = 30
MECHANISMS = ("VCG", "Proportional", "FirstPrice", "Uniform")
DATA_PATH = (
    Path(__file__).resolve().parent.parent
    / "Cashi RAG" / "aggs" / "_consolidado.parquet"
)
DECAY_LO, DECAY_HI = 0.6, 0.9      # decay range set from the overspend ratio
CUTOFF_WEEK = 43                   # last week with real R26 actuals


# ---------------------------------------------------------------------------
# Data-derived center parameters (real structure of the synthetic demo data)
# ---------------------------------------------------------------------------
def center_parameters(path: Path = DATA_PATH, cutoff_week: int = CUTOFF_WEEK) -> pd.DataFrame:
    """Per-center parameters derived from weeks 1..cutoff_week.

    overspend_ratio = R26 / P26            (observed, real structure of the demo data)
    overspend_money = R26 - P26
    m_c             = overspend_money / mean(overspend_money)   (scale, mean 1)
    d_c             = DECAY_LO + (DECAY_HI-DECAY_LO) * z_c, where z_c is the
                      min-max normalised overspend ratio. If all ratios are equal
                      (range 0) z_c = 0.5 for every center.
    """
    df = pd.read_parquet(path)
    d = df[df["sem"] <= cutoff_week]
    tot = d.groupby(["ID_CENTRO_COSTOS", "Serie"])["monto"].sum().unstack()
    out = pd.DataFrame(index=tot.index)
    out["P26"] = tot["P26"]
    out["R26"] = tot["R26"]
    out["overspend_ratio"] = tot["R26"] / tot["P26"]
    out["overspend_money"] = tot["R26"] - tot["P26"]
    out["m_c"] = out["overspend_money"] / out["overspend_money"].mean()
    r = out["overspend_ratio"]
    rng_r = r.max() - r.min()
    z = (r - r.min()) / rng_r if rng_r > 1e-12 else pd.Series(0.5, index=r.index)
    out["d_c"] = DECAY_LO + (DECAY_HI - DECAY_LO) * z
    out["direccion"] = df.groupby("ID_CENTRO_COSTOS")["cat_Direccion_Division"].first()
    return out


# ---------------------------------------------------------------------------
# Market generation (SIMULATED noise around the center parameters)
# ---------------------------------------------------------------------------
@dataclass
class Market:
    m: np.ndarray          # true slot-1 marginal value per unit
    d: np.ndarray          # true decay per unit
    center: np.ndarray     # center index per unit
    center_names: list
    K: int = K_SLOTS

    @property
    def n(self) -> int:
        return int(self.m.size)

    @cached_property
    def true_cum(self) -> np.ndarray:
        return _cum(slot_values(self.m, self.d, self.K))

    def opt(self, B: int) -> float:
        """Maximum achievable true value with B slots (efficient allocation)."""
        flat = np.sort(slot_values(self.m, self.d, self.K).ravel())[::-1]
        return float(flat[: min(B, flat.size)].sum())


def generate_market(units_per_center: int = 40, K: int = K_SLOTS, seed: int = SEED,
                    params: pd.DataFrame | None = None,
                    noise_m: float = 0.30, noise_d: float = 0.02) -> Market:
    """Replicate each center into ``units_per_center`` synthetic units.

    m_i = m_c * LogNormal(0, noise_m)        (multiplicative noise)
    d_i = clip(d_c + Normal(0, noise_d), 0.5, 0.97)
    """
    if params is None:
        params = center_parameters()
    rng = np.random.default_rng(seed)
    cen = np.repeat(np.arange(len(params)), units_per_center)
    m = params["m_c"].to_numpy()[cen] * rng.lognormal(0.0, noise_m, size=cen.size)
    d = np.clip(params["d_c"].to_numpy()[cen] + rng.normal(0.0, noise_d, size=cen.size),
                0.5, 0.97)
    return Market(m=m, d=d, center=cen, center_names=list(params.index), K=K)


# ---------------------------------------------------------------------------
# Valuation helpers
# ---------------------------------------------------------------------------
def slot_values(m: np.ndarray, d: np.ndarray, K: int) -> np.ndarray:
    """(N, K) matrix: value of slot k (column k-1) for each unit."""
    return m[:, None] * d[:, None] ** np.arange(K)[None, :]


def _cum(sv: np.ndarray) -> np.ndarray:
    """(N, K+1) matrix: total value of the first k slots, k = 0..K."""
    return np.concatenate([np.zeros((sv.shape[0], 1)), np.cumsum(sv, axis=1)], axis=1)


def greedy(values: np.ndarray, B: int):
    """Allocate the B highest slot values. Returns (slots per unit, welfare)."""
    N, K = values.shape
    flat = values.ravel()
    b = min(B, flat.size)
    if b <= 0:
        return np.zeros(N, dtype=int), 0.0
    idx = np.argpartition(-flat, b - 1)[:b]
    counts = np.bincount(idx // K, minlength=N)
    return counts, float(flat[idx].sum())


def prop_counts(total: np.ndarray, B: int, K: int) -> np.ndarray:
    """Split B slots proportionally to ``total`` with cap K and largest remainders."""
    total = np.asarray(total, dtype=float)
    N = total.size
    target = min(B, N * K)
    capped = np.zeros(N, dtype=bool)
    x = np.zeros(N)
    for _ in range(N + 1):
        free = ~capped
        rem = target - K * capped.sum()
        s = total[free].sum()
        if s <= 0 or rem <= 0 or not free.any():
            break
        q = np.zeros(N)
        q[free] = rem * total[free] / s
        newly = free & (q >= K)
        if not newly.any():
            x[free] = q[free]
            break
        capped |= newly
    x[capped] = K
    base = np.minimum(np.floor(x + 1e-9), K).astype(int)
    left = target - int(base.sum())
    frac = x - base
    for i in np.argsort(-frac)[: max(left, 0)]:
        if base[i] < K:
            base[i] += 1
    return base


# ---------------------------------------------------------------------------
# Mechanisms
# ---------------------------------------------------------------------------
def _clarke(sv: np.ndarray, B: int, i: int, W: float, own: float) -> float:
    """Clarke pivot payment of unit i: W_{-i} - (others' welfare in chosen allocation)."""
    others = np.delete(sv, i, axis=0)
    _, W_minus = greedy(others, B)
    return W_minus - (W - own)


def allocate(mech: str, rep_m: np.ndarray, rep_d: np.ndarray, B: int,
             K: int = K_SLOTS, only: int | None = None):
    """Run a mechanism on reported curves. Returns (slots per unit, payments).

    If ``only`` is given, VCG computes the payment of that unit only (others 0).
    """
    sv = slot_values(rep_m, rep_d, K)
    cum = _cum(sv)
    N = sv.shape[0]
    if mech == "Proportional":
        return prop_counts(cum[:, -1], B, K), np.zeros(N)
    counts, W = greedy(sv, B)
    own = cum[np.arange(N), counts]
    if mech == "FirstPrice":
        return counts, own.copy()
    if mech == "Uniform":
        flat = np.sort(sv.ravel())[::-1]
        price = float(flat[B]) if flat.size > B else 0.0
        return counts, counts * price
    if mech == "VCG":
        pay = np.zeros(N)
        for i in ([only] if only is not None else range(N)):
            pay[i] = _clarke(sv, B, i, W, own[i])
        return counts, pay
    raise ValueError(mech)


def outcome(mech: str, market: Market, rep_m: np.ndarray, rep_d: np.ndarray, B: int):
    """Full outcome: (slots, payments, true value, utility) per unit."""
    counts, pay = allocate(mech, rep_m, rep_d, B, market.K)
    tv = market.true_cum[np.arange(market.n), counts]
    return counts, pay, tv, tv - pay


def efficiency(counts: np.ndarray, market: Market, B: int) -> float:
    """Total TRUE value of the allocation divided by the optimum."""
    realized = market.true_cum[np.arange(market.n), counts].sum()
    return float(realized / market.opt(B))


def utility_one(mech: str, market: Market, i: int, mi: float, di: float, B: int) -> float:
    """Utility of unit i when it reports (mi, di) and all others are truthful."""
    rep_m = market.m.copy()
    rep_d = market.d.copy()
    rep_m[i] = mi
    rep_d[i] = di
    counts, pay = allocate(mech, rep_m, rep_d, B, market.K, only=i)
    return float(market.true_cum[i, counts[i]] - pay[i])


def misreport(market: Market, i: int, f: float, g: float):
    """Report (f * m_i, clip(g * d_i)). f scales the curve, g scales the decay."""
    return market.m[i] * f, float(np.clip(market.d[i] * g, 0.05, 0.99))


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------
F_GRID = np.round(np.arange(0.5, 2.0001, 0.1), 2)     # includes 1.0
G_GRID = np.array([0.8, 0.9, 1.0, 1.1, 1.2])


def best_response(mech: str, market: Market, i: int, B: int, tol: float = 1e-9):
    """Grid search best response of unit i against truthful others.

    Returns (f, g, gain over truth). Truth (1, 1) is kept unless a deviation
    gains more than tol.
    """
    u_truth = utility_one(mech, market, i, market.m[i], market.d[i], B)
    best = (1.0, 1.0, 0.0)
    best_u = u_truth
    for f in F_GRID:
        for g in G_GRID:
            mi, di = misreport(market, i, f, g)
            u = utility_one(mech, market, i, mi, di, B)
            if u > best_u + tol:
                best_u, best = u, (float(f), float(g), u - u_truth)
    return best


def best_response_profile(mech: str, market: Market, B: int):
    """Every unit best-responds once (simultaneously) against truthful others."""
    fg = np.ones((market.n, 2))
    gains = np.zeros(market.n)
    for i in range(market.n):
        f, g, gain = best_response(mech, market, i, B)
        fg[i] = (f, g)
        gains[i] = gain
    rep_m = market.m * fg[:, 0]
    rep_d = np.clip(market.d * fg[:, 1], 0.05, 0.99)
    return rep_m, rep_d, gains, fg


def truthfulness_test(market: Market, B: int, n_pairs: int = 2000, seed: int = SEED + 1,
                      tol: float = 1e-9):
    """Random (unit, misreport) pairs with all other units truthful."""
    rng = np.random.default_rng(seed)
    units = rng.integers(0, market.n, n_pairs)
    fs = rng.uniform(0.5, 2.0, n_pairs)
    gs = rng.uniform(0.7, 1.3, n_pairs)
    rows = {}
    for mech in MECHANISMS:
        gains = np.empty(n_pairs)
        for j in range(n_pairs):
            i = int(units[j])
            u_t = utility_one(mech, market, i, market.m[i], market.d[i], B)
            mi, di = misreport(market, i, fs[j], gs[j])
            gains[j] = utility_one(mech, market, i, mi, di, B) - u_t
        viol = gains > tol
        rows[mech] = {
            "pairs": n_pairs,
            "violations": int(viol.sum()),
            "violation_rate": float(viol.mean()),
            "max_gain": float(gains.max()),
            "max_gain_if_any_violation": float(gains[viol].max()) if viol.any() else 0.0,
            "mean_gain_of_violations": float(gains[viol].mean()) if viol.any() else 0.0,
            "gains": gains,
        }
    return pd.DataFrame(rows).T


def individual_rationality(market: Market, B: int, tol: float = 1e-9):
    """Truthful profile: count units with negative utility, per mechanism."""
    out = {}
    for mech in MECHANISMS:
        _, _, _, util = outcome(mech, market, market.m, market.d, B)
        out[mech] = {"min_utility": float(util.min()),
                     "units_negative_utility": int((util < -tol).sum())}
    return pd.DataFrame(out).T


def revenue_table(market: Market, B: int):
    """Payments under truthful reporting (money units; budget = B money units)."""
    rows = {}
    for mech in MECHANISMS:
        counts, pay, tv, util = outcome(mech, market, market.m, market.d, B)
        rows[mech] = {
            "slots_allocated": int(counts.sum()),
            "units_winning": int((counts > 0).sum()),
            "total_true_value": float(tv.sum()),
            "efficiency": float(tv.sum() / market.opt(B)),
            "revenue": float(pay.sum()),
            "revenue_pct_budget": float(pay.sum() / B),
            "revenue_pct_value": float(pay.sum() / tv.sum()) if tv.sum() > 0 else 0.0,
        }
    return pd.DataFrame(rows).T


def efficiency_under_scenarios(market: Market, B: int, reps: int = 20, seed: int = SEED + 2):
    """Truthful, random inflation U[1,2] (reps draws), and best response."""
    rng = np.random.default_rng(seed)
    rows = {}
    for mech in MECHANISMS:
        eff_t = efficiency(allocate(mech, market.m, market.d, B, market.K)[0], market, B)
        infl = []
        for _ in range(reps):
            f = rng.uniform(1.0, 2.0, market.n)
            c, _ = allocate(mech, market.m * f, market.d, B, market.K)
            infl.append(efficiency(c, market, B))
        rep_m, rep_d, gains, _ = best_response_profile(mech, market, B)
        c_br, _ = allocate(mech, rep_m, rep_d, B, market.K)
        rows[mech] = {
            "eff_truthful": eff_t,
            "eff_inflate_U12_mean": float(np.mean(infl)),
            "eff_inflate_U12_sd": float(np.std(infl, ddof=1)),
            "eff_best_response": efficiency(c_br, market, B),
            "units_with_profitable_deviation": int((gains > 1e-9).sum()),
            "mean_br_gain": float(gains.mean()),
        }
    return pd.DataFrame(rows).T


def sweep(units_list=(4, 10, 20, 40, 80), budget_list=(60, 240, 480, 960, 1920),
          reps: int = 10, seed: int = SEED + 3):
    """Efficiency vs number of units (budget = 2 slots per unit) and vs budget (N=240)."""
    params = center_parameters()
    res_n, res_b = [], []
    for u in units_list:
        mk = generate_market(units_per_center=u, params=params)
        B = 2 * mk.n
        for mech in MECHANISMS:
            eff_t = efficiency(allocate(mech, mk.m, mk.d, B, mk.K)[0], mk, B)
            rng = np.random.default_rng(seed + u)
            infl = [efficiency(allocate(mech, mk.m * rng.uniform(1, 2, mk.n), mk.d, B, mk.K)[0],
                               mk, B) for _ in range(reps)]
            res_n.append({"units_per_center": u, "N": mk.n, "B": B, "mechanism": mech,
                          "eff_truthful": eff_t, "eff_inflate_mean": float(np.mean(infl))})
    mk = generate_market(units_per_center=40, params=params)
    rng = np.random.default_rng(seed)
    for B in budget_list:
        for mech in MECHANISMS:
            eff_t = efficiency(allocate(mech, mk.m, mk.d, B, mk.K)[0], mk, B)
            infl = [efficiency(allocate(mech, mk.m * rng.uniform(1, 2, mk.n), mk.d, B, mk.K)[0],
                               mk, B) for _ in range(reps)]
            res_b.append({"B": B, "N": mk.n, "mechanism": mech,
                          "eff_truthful": eff_t, "eff_inflate_mean": float(np.mean(infl))})
    return pd.DataFrame(res_n), pd.DataFrame(res_b)
