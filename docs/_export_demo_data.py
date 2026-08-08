# -*- coding: utf-8 -*-
"""Export Territory aggs + Cashi index into docs/ static JSON for GitHub Pages.

Run from repository root:

    python docs/_export_demo_data.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "docs"
AGGS = ROOT / "Territory Dashboard" / "aggs"
CASHI = ROOT / "Cashi RAG"
SMR = 30


def ensure_territory_aggs() -> None:
    meta = AGGS / "_meta.json"
    if meta.exists() and (AGGS / "division.parquet").exists():
        return
    print("Seeding Territory Dashboard aggs…")
    subprocess.check_call([sys.executable, str(ROOT / "Territory Dashboard" / "seed_demo_data.py")])


def ensure_cashi_index() -> Path:
    idx = CASHI / "rag" / "index_store.json"
    if not idx.exists():
        print("Building Cashi index…")
        subprocess.check_call([sys.executable, str(CASHI / "rag" / "indexer.py")], cwd=str(CASHI))
    return idx


def export_territory() -> None:
    ensure_territory_aggs()
    out_dir = WEB / "territory" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    def load(name: str) -> pl.DataFrame:
        return pl.read_parquet(AGGS / f"{name}.parquet")

    g = load("global").sort("sem")
    global_weekly = {
        "sem": g["sem"].to_list(),
        "Real_2025": [round(float(x), 1) for x in g["Real_2025"].to_list()],
        "Plan_2026": [round(float(x), 1) for x in g["Plan_2026"].to_list()],
        "Real_2026": [
            round(float(x), 1) if int(s) <= SMR else None
            for s, x in zip(g["sem"].to_list(), g["Real_2026"].to_list())
        ],
        "Nvo_Plan_2026": [round(float(x), 1) for x in g["Nvo_Plan_2026"].to_list()],
    }

    def ytd(df: pl.DataFrame, group_cols: list[str]) -> pl.DataFrame:
        d = df.filter(pl.col("sem") <= SMR)
        metrics = ["Real_2025", "Plan_2026", "Real_2026", "Nvo_Plan_2026"]
        if group_cols:
            return (
                d.group_by(group_cols)
                .agg([pl.col(c).sum() for c in metrics])
                .sort("Real_2026", descending=True)
            )
        return d.select([pl.col(c).sum().alias(c) for c in metrics])

    glob_ytd = ytd(load("global"), []).to_dicts()[0]
    for k, v in list(glob_ytd.items()):
        if isinstance(v, float):
            glob_ytd[k] = round(v, 1)

    div = ytd(load("division"), ["cat_Direccion_Division"]).rename(
        {"cat_Direccion_Division": "name"}
    )
    gpo = ytd(load("grupo_cuentas"), ["cat_Grupo_de_Cuentas"]).rename(
        {"cat_Grupo_de_Cuentas": "name"}
    )
    terr = ytd(
        load("territorio"),
        ["cat_Direccion_Division", "cat_Subdireccion_Territorio"],
    )

    tree = []
    for drow in div.to_dicts():
        dname = drow["name"]
        children = []
        for trow in terr.filter(pl.col("cat_Direccion_Division") == dname).to_dicts():
            children.append(
                {
                    "name": trow["cat_Subdireccion_Territorio"],
                    "Real_2025": round(trow["Real_2025"], 1),
                    "Plan_2026": round(trow["Plan_2026"], 1),
                    "Real_2026": round(trow["Real_2026"], 1),
                }
            )
        tree.append(
            {
                "name": dname,
                "Real_2025": round(drow["Real_2025"], 1),
                "Plan_2026": round(drow["Plan_2026"], 1),
                "Real_2026": round(drow["Real_2026"], 1),
                "children": children,
            }
        )

    cta = ytd(load("cuentas"), ["cat_Grupo_de_Cuentas", "cat_Cuentas"])
    accounts = []
    for r in cta.to_dicts():
        accounts.append(
            {
                "grupo": r["cat_Grupo_de_Cuentas"],
                "cuenta": r["cat_Cuentas"],
                "Real_2025": round(r["Real_2025"], 1),
                "Plan_2026": round(r["Plan_2026"], 1),
                "Real_2026": round(r["Real_2026"], 1),
                "vs_plan": round(r["Real_2026"] - r["Plan_2026"], 1),
                "vs_aa": round(r["Real_2026"] - r["Real_2025"], 1),
            }
        )

    seg_path = AGGS / "seguimiento_demo.json"
    seg = json.loads(seg_path.read_text(encoding="utf-8")) if seg_path.exists() else {}
    riesgos_path = AGGS / "riesgos.json"
    riesgos = json.loads(riesgos_path.read_text(encoding="utf-8")) if riesgos_path.exists() else {}

    out = {
        "meta": {"sem_max_real": SMR, "demo": True, "currency": "MDP demo units"},
        "kpis": {
            "Real_2026": glob_ytd["Real_2026"],
            "Real_2025": glob_ytd["Real_2025"],
            "Plan_2026": glob_ytd["Plan_2026"],
            "Forecast": round(glob_ytd["Real_2026"] + (glob_ytd["Plan_2026"] * 0.35), 1),
            "vs_aa": round(glob_ytd["Real_2026"] - glob_ytd["Real_2025"], 1),
            "vs_plan": round(glob_ytd["Real_2026"] - glob_ytd["Plan_2026"], 1),
        },
        "weekly": global_weekly,
        "by_division": [
            {
                "name": r["name"],
                "Real_2025": round(r["Real_2025"], 1),
                "Plan_2026": round(r["Plan_2026"], 1),
                "Real_2026": round(r["Real_2026"], 1),
            }
            for r in div.to_dicts()
        ],
        "by_grupo": [
            {
                "name": r["name"],
                "Real_2025": round(r["Real_2025"], 1),
                "Plan_2026": round(r["Plan_2026"], 1),
                "Real_2026": round(r["Real_2026"], 1),
            }
            for r in gpo.to_dicts()
        ],
        "hierarchy": tree,
        "accounts": accounts,
        "cierres": seg,
        "riesgos": riesgos,
    }
    path = out_dir / "demo.json"
    path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path} ({path.stat().st_size // 1024} KB)")


def export_cashi() -> None:
    idx = ensure_cashi_index()
    store = json.loads(idx.read_text(encoding="utf-8"))
    slim = []
    for ch in store.get("chunks", []):
        slim.append(
            {
                "file": ch.get("file"),
                "heading": ch.get("heading"),
                "type": ch.get("type", "markdown"),
                "content": (ch.get("content") or "")[:1200],
                "start_line": ch.get("start_line", 1),
                "end_line": ch.get("end_line", 1),
            }
        )
    out_dir = WEB / "cashi" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "chunks.json"
    path.write_text(json.dumps({"chunks": slim}, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path} ({len(slim)} chunks, {path.stat().st_size // 1024} KB)")


def main() -> None:
    export_territory()
    export_cashi()
    print("Done. Commit docs/ if you want Pages updated.")


if __name__ == "__main__":
    main()
