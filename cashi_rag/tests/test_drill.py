# -*- coding: utf-8 -*-
"""Prueba el drill-down: la función compute() con filtros de padre acumulados,
que es exactamente lo que la app hace al bajar de nivel. Verifica contra el parquet."""
import sys, io, json, importlib.util
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import polars as pl

BASE = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
AGGS = BASE / "aggs"
fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


META = json.loads((AGGS / "_meta.json").read_text(encoding="utf-8"))
SMR = META["sem_max_real"]
HIER = ["division", "territorio", "zona", "region", "pdc"]
COLS = {"division": "cat_Direccion_Division", "territorio": "cat_Subdireccion_Territorio",
        "zona": "cat_Subdireccion_Zona", "region": "cat_Subdireccion_Region", "pdc": "cat_PDC"}
PARENTS = {
    "territorio": ["cat_Direccion_Division"],
    "zona": ["cat_Direccion_Division", "cat_Subdireccion_Territorio"],
    "region": ["cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Zona"],
    "pdc": ["cat_Direccion_Division", "cat_Subdireccion_Territorio",
            "cat_Subdireccion_Zona", "cat_Subdireccion_Region"],
}
MED = ["Real_2025", "Plan_2026", "Real_2026", "Nvo_Plan_2026"]


def agg(alias, si, sf, filtros):
    """réplica exacta de compute() de app.py"""
    df = pl.read_parquet(AGGS / f"{alias}.parquet")
    col = COLS[alias]
    gcols = [p for p in PARENTS.get(alias, []) if p in df.columns] + [col]
    for k, v in filtros:
        df = df.filter(pl.col(k) == v)
    if df.height == 0:
        return []
    real_hi = min(sf, SMR)
    inr = (pl.col("sem") >= si) & (pl.col("sem") <= sf)
    inrl = (pl.col("sem") >= si) & (pl.col("sem") <= real_hi)
    df = df.with_columns([
        pl.when(inr).then(pl.col("Real_2025")).otherwise(0.0).alias("Real_2025"),
        pl.when(inr).then(pl.col("Plan_2026")).otherwise(0.0).alias("Plan_2026"),
        pl.when(inr).then(pl.col("Nvo_Plan_2026")).otherwise(0.0).alias("Nvo_Plan_2026"),
        pl.when(inrl).then(pl.col("Real_2026")).otherwise(0.0).alias("Real_2026")])
    g = df.group_by(gcols).agg([pl.col(m).sum() for m in MED])
    rows = sorted(g.to_dicts(), key=lambda r: abs(r["Real_2026"]), reverse=True)
    return rows


print("=== Drill territorial: 5 niveles, cada hijo suma == su padre ===")
filtros, padre_val = [], None
for i, alias in enumerate(HIER):
    rows = agg(alias, 1, SMR, filtros)
    check(f"nivel {i} ({alias}) devuelve filas", len(rows) > 0, f"{len(rows)} filas")
    if not rows:
        break
    top = rows[0]
    col = COLS[alias]
    print(f"       top: {top[col]!r}  Real26={top['Real_2026']/1e6:,.1f} M")

    if padre_val is not None:
        suma = sum(r["Real_2026"] for r in rows)
        check(f"suma nivel {i} == padre nivel {i-1}", abs(suma - padre_val) < 1.0,
              f"{suma/1e6:,.2f}M vs {padre_val/1e6:,.2f}M")
    padre_val = top["Real_2026"]
    filtros = filtros + [(col, top[col])]

print("\n=== Homónimos: PDC con mismo nombre en 2 regiones NO se fusiona ===")
p = pl.read_parquet(AGGS / "pdc.parquet")
u = p.select(["cat_PDC", "cat_Subdireccion_Region"]).unique()
d = (u.group_by("cat_PDC").agg(pl.count().alias("n"))
      .filter((pl.col("n") > 1) & (~pl.col("cat_PDC").is_in(["0", "(Sin dato)"]))))
if d.height:
    nom = d.row(0)[0]
    rows = agg("pdc", 1, SMR, [])
    hits = [r for r in rows if r["cat_PDC"] == nom]
    check("homónimo aparece >1 vez", len(hits) > 1, f"{nom!r} × {len(hits)}")
    for h in hits[:3]:
        print(f"       {h['cat_Subdireccion_Region']}: {h['Real_2026']/1e6:,.2f} M")
else:
    check("hay homónimos que probar", False)

print("\n=== Jerarquía contable: Grupo → Cuentas ===")
gc = pl.read_parquet(AGGS / "grupo_cuentas.parquet")
cu = pl.read_parquet(AGGS / "cuentas.parquet")
g = (gc.filter(pl.col("sem") <= SMR).group_by("cat_Grupo_de_Cuentas")
       .agg(pl.col("Real_2026").sum()).sort("Real_2026", descending=True))
top_g = g.row(0, named=True)
c = (cu.filter((pl.col("sem") <= SMR) & (pl.col("cat_Grupo_de_Cuentas") == top_g["cat_Grupo_de_Cuentas"]))
       .group_by("cat_Cuentas").agg(pl.col("Real_2026").sum()))
suma = c["Real_2026"].sum()
check("cuentas suman igual que su grupo", abs(suma - top_g["Real_2026"]) < 1.0,
      f"{top_g['cat_Grupo_de_Cuentas']!r}: {suma/1e6:,.1f}M vs {top_g['Real_2026']/1e6:,.1f}M "
      f"({c.height} cuentas)")

print("\n=== Rango de semanas recalcula ===")
a = agg("division", 1, 13, [])
b = agg("division", 1, SMR, [])
sa = sum(r["Real_2026"] for r in a)
sb = sum(r["Real_2026"] for r in b)
check("sem 1-13 < sem 1-27", sa < sb, f"{sa/1e6:,.0f}M vs {sb/1e6:,.0f}M")
g13 = pl.read_parquet(AGGS / "global.parquet").filter(pl.col("sem") <= 13)["Real_2026"].sum()
check("sem 1-13 cuadra con global", abs(sa - g13) < 1.0, f"{sa/1e6:,.1f}M vs {g13/1e6:,.1f}M")

print(f"\n{'='*54}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
