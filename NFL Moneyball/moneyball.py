"""NFL Moneyball: (1) game-margin model vs. the betting market, (2) player value over replacement.

Data: nflverse (public CSVs). Usage: python moneyball.py [--first 2015] [--last 2026]
"""
import argparse
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error

REL = "https://github.com/nflverse/nflverse-data/releases/download"
CACHE = Path(__file__).parent / "data"; CACHE.mkdir(exist_ok=True)


def load(url: str, name: str) -> pd.DataFrame:
    f = CACHE / name
    if not f.exists():
        pd.read_csv(url, low_memory=False).to_csv(f, index=False)
    return pd.read_csv(f, low_memory=False)


def team_weeks(first, last) -> pd.DataFrame:
    parts = []
    for y in range(first, last + 1):
        try:
            parts.append(load(f"{REL}/stats_team/stats_team_week_{y}.csv", f"team_{y}.csv"))
        except Exception:
            pass  # season not published yet
    t = pd.concat(parts)
    t = t[t.season_type == "REG"].copy()
    t["off_epa"] = t[["passing_epa", "rushing_epa"]].sum(axis=1)
    t["plays"] = t.attempts + t.carries + t.sacks_suffered
    t["epa_play"] = t.off_epa / t.plays.replace(0, np.nan)
    return t[["season", "week", "team", "opponent_team", "epa_play"]]


def add_rolling(t: pd.DataFrame) -> pd.DataFrame:
    """Offense EPA/play (pre-game, EWMA) and defense = what opponents managed against the team."""
    t = t.sort_values(["team", "season", "week"])
    t["off"] = t.groupby("team").epa_play.transform(lambda s: s.shift().ewm(span=6, min_periods=3).mean())
    d = t[["season", "week", "opponent_team", "epa_play"]].rename(columns={"opponent_team": "team", "epa_play": "allowed"})
    t = t.merge(d, on=["season", "week", "team"], how="left").sort_values(["team", "season", "week"])
    t["dfn"] = t.groupby("team").allowed.transform(lambda s: s.shift().ewm(span=6, min_periods=3).mean())
    return t[["season", "week", "team", "off", "dfn"]]


def margin_model(first, last):
    g = load("https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv", "games.csv")
    g = g[(g.game_type == "REG") & g.season.between(first, last)].dropna(subset=["result", "spread_line"])
    r = add_rolling(team_weeks(first, last))
    h = r.add_prefix("h_").rename(columns={"h_season": "season", "h_week": "week", "h_team": "home_team"})
    a = r.add_prefix("a_").rename(columns={"a_season": "season", "a_week": "week", "a_team": "away_team"})
    d = g.merge(h, on=["season", "week", "home_team"]).merge(a, on=["season", "week", "away_team"]).dropna(
        subset=["h_off", "h_dfn", "a_off", "a_dfn"])
    d["x_off"], d["x_def"] = d.h_off - d.a_dfn, d.a_off - d.h_dfn  # matchup terms
    X = d[["h_off", "h_dfn", "a_off", "a_dfn", "x_off", "x_def"]].assign(rest=d.home_rest - d.away_rest)
    res = []
    for s in range(max(first + 3, last - 3), last + 1):
        tr, te = d.season < s, d.season == s
        if not te.any(): continue
        m = RidgeCV(alphas=np.logspace(-2, 3, 12)).fit(X[tr], d.result[tr])
        p = m.predict(X[te])
        mkt = d.spread_line[te]  # nflverse spread_line is already in home-margin terms
        blend = 0.5 * p + 0.5 * mkt
        res.append(dict(season=s, games=int(te.sum()), model_mae=mean_absolute_error(d.result[te], p),
                        market_mae=mean_absolute_error(d.result[te], mkt),
                        blend_mae=mean_absolute_error(d.result[te], blend),
                        model_ats=float(((p > mkt) == (d.result[te] > mkt))[d.result[te] != mkt].mean())))
    return pd.DataFrame(res)


def value_over_replacement(season, top=10):
    p = load(f"{REL}/stats_player/stats_player_week_{season}.csv", f"player_{season}.csv")
    p = p[p.season_type == "REG"].copy()
    p["epa"] = p[["passing_epa", "rushing_epa", "receiving_epa"]].sum(axis=1)
    p["touches"] = p.attempts + p.carries + p.targets
    s = p.groupby(["player_display_name", "position", "team"], as_index=False).agg(epa=("epa", "sum"), touches=("touches", "sum"))
    s = s[s.position.isin(["QB", "RB", "WR", "TE"]) & (s.touches >= 40)]
    starters = {"QB": 32, "RB": 40, "WR": 64, "TE": 24}   # replacement = first player outside the starter pool
    out = []
    for pos, n in starters.items():
        q = s[s.position == pos].sort_values("epa", ascending=False)
        repl = q.epa.iloc[n] / q.touches.iloc[n] if len(q) > n else q.epa.sum() / q.touches.sum()
        out.append(q.assign(vorp=q.epa - repl * q.touches))
    return pd.concat(out).sort_values("vorp", ascending=False).head(top)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--first", type=int, default=2015); ap.add_argument("--last", type=int, default=2026)
    a = ap.parse_args()
    bt = margin_model(a.first, a.last)
    print(bt.round(3).to_string(index=False))
    print(f"\nMean MAE  model {bt.model_mae.mean():.2f} | market {bt.market_mae.mean():.2f} | blend {bt.blend_mae.mean():.2f}")
    for y in range(a.last, a.last - 3, -1):
        try:
            print(f"\nTop value over replacement, {y}"); print(value_over_replacement(y).round(1).to_string(index=False)); break
        except Exception: continue
