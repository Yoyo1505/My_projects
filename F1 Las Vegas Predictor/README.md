# F1 Las Vegas Predictor

**Domain:** Sports analytics · **Technique:** Gradient boosting + probability normalisation · **Role fit:** Applied AI Engineer

Predicts the probability that each driver wins the Las Vegas Grand Prix (2026, round 21) from public race history.

## Problem
Who wins a street race with little circuit-specific history? A single pick ("the pole sitter") ignores form, team pace and street-circuit effects; the useful output is a probability per driver.

## Approach
1. Pull results and qualifying for 2018–2026 from the Jolpica-F1 API (cached under `data/`).
2. Leakage-safe features (all shifted so only pre-race information is used): grid, qualifying, rolling driver points/finish/win rate, constructor form, street-circuit win history.
3. LightGBM binary "win" classifier; probabilities are renormalised to sum to 1 within each race.
4. Expanding-window backtest by season (train on earlier seasons only), compared with a "pole sitter wins" baseline.

## Results (run 2026-11-19)
| Season | Races | Top-1 accuracy | Log-loss | Pole baseline |
|---|---|---|---|---|
| 2022 | 22 | 0.55 | 0.097 | 0.45 |
| 2023 | 22 | 0.82 | 0.064 | 0.64 |
| 2024 | 24 | 0.50 | 0.132 | 0.46 |
| 2025 | 24 | 0.58 | 0.093 | 0.67 |
| 2026 (to date) | 20 | 0.75 | 0.075 | 0.70 |

Mean top-1 accuracy is 0.64 vs 0.58 for the pole baseline. The edge is modest and not consistent (the baseline wins in 2025), so treat the output as a probability, not a certainty.
Before qualifying exists the grid is proxied by the last race's finishing order; re-run after qualifying for the real forecast.

## Run
```bash
pip install -r requirements.txt
python predict.py --season 2026 --round 21   # writes prediction.csv
```

## Stack
Python, pandas, LightGBM, scikit-learn, requests.

## Limits & security
- No tyre-strategy, weather or safety-car data yet (next: FastF1 telemetry and a Monte Carlo race simulation).
- Public API only; no credentials. Responses are cached locally in `data/` (git-ignored).
