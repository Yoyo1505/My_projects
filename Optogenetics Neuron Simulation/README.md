# Optogenetics Neuron Simulation

**Domain:** Computational neuroscience · **Technique:** ODE simulation + approximate Bayesian inference · **Role fit:** Applied AI Engineer / scientific ML

Simulates a neuron made light-sensitive with channelrhodopsin-2 (ChR2) and asks how well light pulses control its spikes.

## Context
Optogenetics (Boyden, Deisseroth and colleagues; Breakthrough Prize 2013, Lasker Award 2021) controls neurons with light. The membrane model is Hodgkin–Huxley (Nobel Prize in Physiology or Medicine, 1963).

## Approach
1. Hodgkin–Huxley membrane equations plus a 4-state ChR2 photocycle (C1, O1, O2, C2) injecting a light-gated current.
2. Experiments: single light pulses, a frequency sweep for spike fidelity (fraction of pulses producing a spike), and approximate Bayesian computation (ABC) to recover an unknown light sensitivity from spike count and latency.

## Results
- Fidelity is 1.00 from 5 to 60 Hz and drops to 0.58 at 80 Hz (channel recovery limits fast stimulation).
- ABC recovers a true sensitivity of 0.70 as 0.69 ± 0.04 (300 prior draws).
- Figures are written to `figures/` (`pulse_response.png`, `fidelity_sweep.png`, `abc_posterior.png`).
- Kinetic constants are simplified and not fitted to experimental recordings.

## Run
```bash
pip install -r requirements.txt
python optogenetics.py
```

## Stack
Python, NumPy, SciPy (LSODA), Matplotlib.

## Limits & security
Single-compartment neuron with simplified kinetics; no network or tissue light scattering. No external data or credentials.
