"""Optogenetic control of a neuron: Hodgkin-Huxley (Nobel 1963) + channelrhodopsin-2 photocycle.

Light-gated current I_ChR2 = g_ChR2 * (O1 + gamma*O2) * (V - E_ChR2), 4-state kinetics
(Nagel 2003 / Nikolic 2009 simplified). Experiments: light-pulse response, frequency
fidelity sweep, and Bayesian-style (ABC) recovery of an unknown light-sensitivity.
Usage: python optogenetics.py   -> writes figures to ./figures
"""
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "figures"; OUT.mkdir(exist_ok=True)
Cm, gNa, gK, gL, ENa, EK, EL = 1.0, 120.0, 36.0, 0.3, 50.0, -77.0, -54.4   # uF/cm2, mS/cm2, mV
E_CHR2, GAMMA = 0.0, 0.1
ep1, ep2, Gd1, Gd2, Gr = 0.8535, 0.14, 0.1, 0.05, 0.004                    # kinetic constants (ms^-1 scale)


def light(t, pulses):
    """pulses: list of (t_on, t_off, irradiance in 0..1)."""
    return sum(i for a, b, i in pulses if a <= t < b)


def rhs(t, y, pulses, g_chr2, sens):
    V, m, h, n, C1, O1, O2, C2 = y
    phi = sens * light(t, pulses)                       # photon flux scaled by light sensitivity
    am = 0.1 * (V + 40) / (1 - np.exp(-(V + 40) / 10)) if abs(V + 40) > 1e-6 else 1.0
    bm = 4 * np.exp(-(V + 65) / 18)
    ah, bh = 0.07 * np.exp(-(V + 65) / 20), 1 / (1 + np.exp(-(V + 35) / 10))
    an = 0.01 * (V + 55) / (1 - np.exp(-(V + 55) / 10)) if abs(V + 55) > 1e-6 else 0.1
    bn = 0.125 * np.exp(-(V + 65) / 80)
    I_chr = g_chr2 * (O1 + GAMMA * O2) * (V - E_CHR2)
    dV = (-gNa * m**3 * h * (V - ENa) - gK * n**4 * (V - EK) - gL * (V - EL) - I_chr) / Cm
    k1, k2 = ep1 * phi, ep2 * phi
    dC1 = Gd1 * O1 + Gr * C2 - k1 * C1
    dO1 = k1 * C1 - (Gd1 + 0.05) * O1 + 0.02 * O2
    dO2 = k2 * C2 + 0.05 * O1 - (Gd2 + 0.02) * O2
    dC2 = Gd2 * O2 - (k2 + Gr) * C2
    return [dV, am * (1 - m) - bm * m, ah * (1 - h) - bh * h, an * (1 - n) - bn * n, dC1, dO1, dO2, dC2]


def simulate(pulses, T=200, g_chr2=0.4, sens=1.0):
    y0 = [-65, 0.05, 0.6, 0.32, 1, 0, 0, 0]
    return solve_ivp(rhs, (0, T), y0, args=(pulses, g_chr2, sens), method="LSODA",
                     t_eval=np.arange(0, T, 0.05), max_step=0.1, rtol=1e-6, atol=1e-8)


def spike_times(sol, thr=0.0):
    V = sol.y[0]
    idx = np.where((V[1:] >= thr) & (V[:-1] < thr))[0]
    return sol.t[idx]


def fidelity_sweep(freqs=(5, 10, 20, 40, 60, 80), width=3.0, T=400):
    """Fraction of light pulses that trigger exactly one spike (spike fidelity)."""
    out = []
    for f in freqs:
        period = 1000 / f
        pulses = [(10 + k * period, 10 + k * period + width, 1.0) for k in range(int((T - 10) / period))]
        sp = spike_times(simulate(pulses, T=T))
        hits = sum(any(a <= s < a + period for s in sp) for a, _, _ in pulses)
        out.append((f, hits / max(len(pulses), 1)))
    return out


def infer_sensitivity(true_sens=0.7, n_draws=300, seed=0):
    """Approximate Bayesian computation: recover light sensitivity from observed spike count + latency."""
    rng = np.random.default_rng(seed)
    pulses = [(20, 23, 1.0), (80, 83, 1.0)]
    summ = lambda s: np.array([len(spike_times(s)), (spike_times(s)[0] - 20) if len(spike_times(s)) else 50.0])
    obs = summ(simulate(pulses, 150, sens=true_sens))
    prior = rng.uniform(0.1, 1.5, n_draws)
    dist = np.array([np.linalg.norm(summ(simulate(pulses, 150, sens=s)) - obs) for s in prior])
    return prior, prior[dist <= np.quantile(dist, 0.1)]


if __name__ == "__main__":
    sol = simulate([(20, 25, 1.0), (80, 85, 1.0)], T=150)
    fig, ax = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    ax[0].plot(sol.t, sol.y[0], lw=1); ax[0].set_ylabel("V (mV)"); ax[0].set_title("Light-evoked spikes (ChR2-HH neuron)")
    ax[1].plot(sol.t, sol.y[5] + sol.y[6], c="tab:blue"); ax[1].set_ylabel("ChR2 open fraction"); ax[1].set_xlabel("ms")
    for a in ax: a.axvspan(20, 25, color="c", alpha=.2); a.axvspan(80, 85, color="c", alpha=.2)
    fig.tight_layout(); fig.savefig(OUT / "pulse_response.png", dpi=130)
    fid = fidelity_sweep(); print("Frequency (Hz) -> spike fidelity"); [print(f"{f:>4} Hz  {x:.2f}") for f, x in fid]
    plt.figure(figsize=(5, 3.5)); plt.plot(*zip(*fid), "o-"); plt.xlabel("Pulse frequency (Hz)"); plt.ylabel("Spike fidelity"); plt.ylim(0, 1.05)
    plt.tight_layout(); plt.savefig(OUT / "fidelity_sweep.png", dpi=130)
    prior, post = infer_sensitivity(); print(f"ABC posterior for light sensitivity (true 0.70): {post.mean():.2f} +/- {post.std():.2f}")
    plt.figure(figsize=(5, 3.5)); plt.hist(post, bins=12); plt.axvline(0.7, c="r", ls="--"); plt.xlabel("sensitivity"); plt.tight_layout()
    plt.savefig(OUT / "abc_posterior.png", dpi=130)
