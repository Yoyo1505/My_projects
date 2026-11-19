# F1 Las Vegas Predictor

**Domain:** Sports analytics · **Technique:** Gradient boosting + probability calibration · **Role fit:** Applied AI Engineer

Predicts the probability that each driver wins the Las Vegas Grand Prix (2026, round 21) from public race history. Executed notebook: [`F1 Las Vegas Predictor.ipynb`](F1%20Las%20Vegas%20Predictor.ipynb).

## Problem
Who wins a street race with little circuit-specific history? A single pick ("the pole sitter") ignores form, team pace and street-circuit effects; the useful output is a calibrated probability per driver.

## Approach
1. Jolpica-F1 API results and qualifying, 2018 to 2026 (cached under `data/`).
2. Leakage-safe features (rolling stats shifted by one race): grid, qualifying, driver form, constructor form, street-circuit wins.
3. LightGBM binary "win" classifier; probabilities renormalised to sum to 1 within each race.
4. Expanding-window backtest by season, compared with a "pole sitter wins" baseline; calibration and Brier score on pooled out-of-sample predictions.

## Results (run 2026-11-19)
| Season | Races | Top-1 accuracy | Log-loss | Pole baseline |
|---|---|---|---|---|
| 2022 | 22 | 0.55 | 0.097 | 0.45 |
| 2023 | 22 | 0.82 | 0.064 | 0.64 |
| 2024 | 24 | 0.50 | 0.132 | 0.46 |
| 2025 | 24 | 0.58 | 0.093 | 0.67 |
| 2026 (to date) | 20 | 0.75 | 0.075 | 0.70 |

- Mean top-1 accuracy 0.64 vs 0.58 for the pole baseline; the model loses in 2025, so the edge is modest and not consistent.
- Probabilities are usable: Brier score 0.028 vs 0.047 for a uniform 5%, and predicted and observed frequencies track each other (weakest for 2% to 5% predictions).
- Provisional Las Vegas forecast (grid proxied by the last race, since qualifying had not happened): Verstappen about 50%, Norris about 37%, Antonelli and Hadjar about 5% each. Re-run after qualifying.

## Conclusions
See the notebook. Short version: a calibrated model with a small, inconsistent advantage over a trivial baseline; the value is the leakage-free validation and the calibration check.

## Run
```bash
pip install -r requirements.txt
python predict.py --season 2026 --round 21   # writes prediction.csv
jupyter notebook "F1 Las Vegas Predictor.ipynb"
```

## Stack
Python, pandas, LightGBM, scikit-learn, requests, Matplotlib.

## Limits & security
- Only three previous Las Vegas races exist, so circuit-specific signal is thin; no tyre, weather or safety-car data (next: FastF1 telemetry and a race Monte Carlo).
- Public API only; no credentials. Responses are cached locally in `data/` (git-ignored).
