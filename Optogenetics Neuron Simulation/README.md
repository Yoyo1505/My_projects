# Optogenetics Neuron Simulation

**Domain:** Computational neuroscience · **Technique:** ODE simulation + approximate Bayesian inference · **Role fit:** Applied AI Engineer / scientific ML

Simulates a neuron made light-sensitive with channelrhodopsin-2 (ChR2) and asks how well light pulses control its spikes. Executed notebook: [`Optogenetics Neuron Simulation.ipynb`](Optogenetics%20Neuron%20Simulation.ipynb).

## Problem
How much light, for how long and at what rate can we stimulate before control breaks down, and can the unknown light sensitivity of a cell be recovered from its spikes?

## Context
Optogenetics (Boyden, Deisseroth and colleagues; Breakthrough Prize 2013, Lasker Award 2021) controls neurons with light. The membrane model is Hodgkin–Huxley (Nobel Prize in Physiology or Medicine, 1963).

## Approach
1. Hodgkin–Huxley membrane equations plus a four-state ChR2 photocycle (C1, O1, O2, C2) injecting a light-gated current; integrated with LSODA.
2. Experiments: single pulses and a no-opsin control, strength-duration curve, dose-response at three expression levels, frequency sweep for spike fidelity, explanation of why fast trains fail, and ABC inference of the light sensitivity.

## Results
- Two 5 ms pulses give two spikes about 2 ms after onset; no spikes without the opsin.
- Threshold irradiance falls from 0.18 (1 ms pulse) to 0.10 (2 ms) and 0.06 (3 ms or longer).
- Under continuous light, expression level, not intensity, sets the response: one spike at low expression versus up to 7 at high expression.
- Fidelity is 1.00 up to 60 Hz, 0.58 at 80 Hz and 0.51 at 100 Hz; only about 19% of channels are ready before each late pulse of an 80 Hz train.
- ABC recovers a true sensitivity of 0.70 as 0.69 ± 0.04, and tracks 0.30, 0.50 and 1.00 (0.32, 0.50, 1.09).

## Conclusions
See the notebook. Short version: a mechanistic model explains where optical control fails (channel recovery) and a likelihood-free method estimates a parameter that cannot be measured directly.

## Run
```bash
pip install -r requirements.txt
python optogenetics.py                      # figures in ./figures
jupyter notebook "Optogenetics Neuron Simulation.ipynb"
```

## Stack
Python, NumPy, SciPy (LSODA), Matplotlib.

## Limits & security
Single compartment, illustrative kinetics not fitted to recordings, no light scattering, temperature or noise. Qualitative mechanisms transfer, absolute numbers do not. No external data or credentials.
