# NFL Moneyball

**Domain:** Sports analytics · **Technique:** Ridge regression on opponent-adjusted EPA, value over replacement, salary efficiency · **Role fit:** Applied AI Engineer

Moneyball-style analysis of NFL data: (1) does a public-data model beat the betting market, (2) which players delivered the most value over replacement per dollar. Executed notebook: [`NFL Moneyball.ipynb`](NFL%20Moneyball.ipynb).

## Problem
Markets price teams efficiently; Moneyball asks where public efficiency metrics (EPA per play) disagree with price, and where salary and production diverge.

## Approach
1. nflverse public data: team-week EPA, `games.csv` with the closing spread (2015 to 2026), player-week stats and historical contracts (OverTheCap data republished by nflverse, signings through 2022).
2. Pre-game features: exponentially weighted offensive and defensive EPA/play, matchup terms, rest difference.
3. `RidgeCV` fitted on prior seasons; evaluated by MAE and against-the-spread (ATS) hit rate against the closing line.
4. Value over replacement (VORP) per player, joined with the APY of the contract in force in 2022.

## Results (run 2026-11-19)
| Season | Games | Model MAE | Market MAE | 50/50 blend MAE | Model ATS |
|---|---|---|---|---|---|
| 2023 | 272 | 10.72 | 9.90 | 10.20 | 44.6% |
| 2024 | 272 | 10.09 | 9.61 | 9.73 | 52.6% |
| 2025 | 272 | 10.23 | 9.72 | 9.83 | 48.7% |
| 2026 (to date) | 150 | 9.86 | 9.57 | 9.65 | 52.1% |

- The model does **not** beat the market: overall ATS 50.4% (break-even is about 52.4%), and games with the biggest disagreement are only 51.0% winners.
- Salary vs production, 2022 (126 matched players): correlation 0.34 (0.26 among veterans). Best value: Jalen Hurts, Amon-Ra St. Brown, Terry McLaurin, Brock Purdy, Tyler Allgeier (rookie-scale deals). Worst use of cap: veteran running backs (average -4.6 EPA over replacement at $11.0M/yr) and veteran quarterbacks such as Russell Wilson, Matt Ryan and Carson Wentz.

## Conclusions
See the notebook. Short version: the edge is not in out-predicting the line; it is in finding roles where price and production diverge.

## Run
```bash
pip install -r requirements.txt
python moneyball.py --first 2015 --last 2026
jupyter notebook "NFL Moneyball.ipynb"
```

## Stack
Python, pandas, scikit-learn, Matplotlib, nflverse public data.

## Limits & security
- Contract data ends with 2022 signings, so the salary analysis is a single-season study and cannot value the 2026 roster. ESPN has no public NFL salary page and no JDK is installed in this environment, so a Java scraper was not used.
- EPA ignores offensive-line and scheme effects; names are matched across sources; part-season players are judged on few games.
- Not betting advice. Public data only; no credentials. Downloads are cached in `data/` (git-ignored).
