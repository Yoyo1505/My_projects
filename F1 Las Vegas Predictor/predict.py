"""F1 Las Vegas GP winner predictor.

Pipeline: Jolpica API -> driver/race features -> LightGBM (binary win) -> calibrated
probabilities -> softmax-normalised per race -> leave-one-season-out backtest.
Usage: python predict.py [--from-year 2018] [--round 21] [--season 2026]
"""
import argparse, json, time
from pathlib import Path
import numpy as np, pandas as pd, requests
import lightgbm as lgb
from sklearn.metrics import log_loss

BASE = "https://api.jolpi.ca/ergast/f1"
CACHE = Path(__file__).parent / "data"; CACHE.mkdir(exist_ok=True)


def fetch(season: int, kind: str) -> list[dict]:
    """Page through /{season}/{kind}.json with an on-disk cache (kind: results|qualifying)."""
    f = CACHE / f"{season}_{kind}.json"
    if f.exists():
        return json.loads(f.read_text())
    races, offset = {}, 0
    while True:
        r = requests.get(f"{BASE}/{season}/{kind}.json", params={"limit": 100, "offset": offset}, timeout=30)
        r.raise_for_status()
        d = r.json()["MRData"]
        for race in d["RaceTable"]["Races"]:
            key = race["round"]
            races.setdefault(key, {**race, "rows": []})["rows"] += race.get("Results", race.get("QualifyingResults", []))
        offset += 100
        if offset >= int(d["total"]):
            break
        time.sleep(0.3)
    out = list(races.values())
    f.write_text(json.dumps(out))
    return out


def build_table(seasons) -> pd.DataFrame:
    rows = []
    for s in seasons:
        qual = {(q["round"], x["Driver"]["driverId"]): int(x["position"])
                for q in fetch(s, "qualifying") for x in q["rows"]}
        for race in fetch(s, "results"):
            for x in race["rows"]:
                rows.append(dict(
                    season=s, round=int(race["round"]), race=race["raceName"], date=race["date"],
                    circuit=race["Circuit"]["circuitId"], street=race["Circuit"]["circuitId"] in
                    {"vegas", "monaco", "marina_bay", "baku", "jeddah", "miami"},
                    driver=x["Driver"]["driverId"], team=x["Constructor"]["constructorId"],
                    grid=int(x["grid"]) if int(x["grid"]) > 0 else 20,
                    quali=qual.get((race["round"], x["Driver"]["driverId"]), np.nan),
                    pos=int(x["position"]) if x["position"].isdigit() else 20,
                    points=float(x["points"])))
    df = pd.DataFrame(rows).sort_values(["date", "driver"]).reset_index(drop=True)
    df["win"] = (df.pos == 1).astype(int)
    return df


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Only information available *before* each race (shifted rolling stats)."""
    g = df.groupby("driver")
    df["form_pts"] = g.points.transform(lambda s: s.shift().rolling(5, min_periods=1).mean())
    df["form_win"] = g.win.transform(lambda s: s.shift().rolling(10, min_periods=1).mean())
    df["form_pos"] = g.pos.transform(lambda s: s.shift().rolling(5, min_periods=1).mean())
    df["team_form"] = df.groupby("team").points.transform(lambda s: s.shift().rolling(10, min_periods=1).mean())
    df["street_win"] = df.groupby("driver").apply(
        lambda d: (d.win * d.street).shift().expanding().sum()).reset_index(level=0, drop=True)
    return df.fillna({"form_pts": 0, "form_win": 0, "form_pos": 15, "team_form": 0, "street_win": 0, "quali": df.grid})


FEATS = ["grid", "quali", "form_pts", "form_win", "form_pos", "team_form", "street_win", "street"]
PARAMS = dict(n_estimators=250, learning_rate=0.03, num_leaves=8, min_child_samples=20,
              subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0, verbose=-1)


def normalise(df, p):
    """Probabilities must sum to 1 inside each race."""
    s = pd.Series(p, index=df.index)
    return s / s.groupby([df.season, df["round"]]).transform("sum")


def backtest(df, first_test=2022):
    res = []
    for s in range(first_test, int(df.season.max()) + 1):
        tr, te = df[df.season < s], df[df.season == s]
        if te.empty: continue
        m = lgb.LGBMClassifier(**PARAMS).fit(tr[FEATS], tr.win)
        te = te.assign(p=normalise(te, m.predict_proba(te[FEATS])[:, 1]))
        top = te.loc[te.groupby("round").p.idxmax()]
        res.append(dict(season=s, races=len(top), top1_acc=top.win.mean(),
                        logloss=log_loss(te.win, te.p.clip(1e-4, 1 - 1e-4)),
                        pole_baseline=te[te.grid == 1].win.mean()))
    return pd.DataFrame(res)


def predict_next(df, season, rnd):
    """Fit on everything strictly before the target race; score the grid if available."""
    target = df[(df.season == season) & (df["round"] == rnd)]
    if target.empty:
        # race not yet run: project the last known lineup using latest form
        last = df[df.season == season]["round"].max()
        target = df[(df.season == season) & (df["round"] == last)].copy()
        target["grid"] = target["quali"] = target["pos"].rank()  # proxy grid until qualifying exists
        target["street"], note = True, "no qualifying yet: grid proxied by last race finish"
    else:
        note = "uses actual grid"
    train = df[df.date < target.date.min()]
    m = lgb.LGBMClassifier(**PARAMS).fit(train[FEATS], train.win)
    target = target.assign(p=normalise(target, m.predict_proba(target[FEATS])[:, 1]))
    return target.sort_values("p", ascending=False)[["driver", "team", "grid", "p"]], note


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-year", type=int, default=2018); ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--round", type=int, default=21)
    a = ap.parse_args()
    df = add_features(build_table(range(a.from_year, a.season + 1)))
    bt = backtest(df); print(bt.round(3).to_string(index=False))
    print(f"\nMean top-1 accuracy {bt.top1_acc.mean():.2f} vs pole baseline {bt.pole_baseline.mean():.2f}")
    out, note = predict_next(df, a.season, a.round)
    print(f"\nRound {a.round} ({note})"); print(out.head(8).assign(p=lambda d: d.p.round(3)).to_string(index=False))
    out.to_csv(Path(__file__).parent / "prediction.csv", index=False)
