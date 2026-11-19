# NFL Moneyball

**Domain:** Sports analytics · **Technique:** Ridge regression on opponent-adjusted EPA, value over replacement · **Role fit:** Applied AI Engineer

Moneyball-style analysis of NFL data: (1) predict game margins from team efficiency and compare with the betting market, (2) rank players by value over replacement.

## Problem
Markets price teams efficiently; Moneyball asks where public efficiency metrics (EPA/play) disagree with price, and which positions and players deliver the most value per play.

## Approach
1. nflverse data: team-week EPA and `games.csv` with the closing spread.
2. Pre-game features: EWMA offensive EPA/play and defensive EPA/play allowed, matchup terms, rest difference.
3. `RidgeCV` fitted on prior seasons only; evaluated per season against the closing line (MAE and against-the-spread hit rate).
4. Player value: season EPA minus replacement-level EPA per touch (replacement = first player outside the starter pool for each position).

## Results (run 2026-11-19)
| Season | Games | Model MAE | Market MAE | 50/50 blend MAE | Model ATS |
|---|---|---|---|---|---|
| 2023 | 272 | 10.72 | 9.90 | 10.20 | 44.6% |
| 2024 | 272 | 10.09 | 9.61 | 9.73 | 52.6% |
| 2025 | 272 | 10.23 | 9.72 | 9.83 | 48.7% |
| 2026 (to date) | 150 | 9.86 | 9.57 | 9.65 | 52.1% |

The model does **not** beat the market (MAE about 0.5 points worse, ATS near 50%), which is the expected outcome for a public-data model. The value of the project is a clean, leakage-free evaluation harness plus player-value rankings, not a betting edge.

## Run
```bash
pip install -r requirements.txt
python moneyball.py --first 2015 --last 2026
```

## Stack
Python, pandas, scikit-learn, nflverse public data.

## Limits & security
- No contract or cap data yet, so "undervalued" means value over replacement only; adding salary is the next step.
- Raw EPA totals favour high-volume players; per-play rates with shrinkage would be fairer.
- Not betting advice. Public data only; no credentials. Downloads are cached in `data/` (git-ignored).
