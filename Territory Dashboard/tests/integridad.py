# -*- coding: utf-8 -*-
"""Verifica que los parquets y agregados sobrevivieron intactos."""
import sys, io, json
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import duckdb
import polars as pl

B = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
ESPERADO = {"r25_sem26.parquet": 23_558_059,
            "r26_sem26.parquet": 14_433_688,
            "p26_sem26.parquet": 20_300_809}

print("=== Parquets fuente ===")
con = duckdb.connect()
ok = True
for f, e in ESPERADO.items():
    p = B / f
    try:
        n = con.execute(f"SELECT COUNT(*) FROM read_parquet('{p.as_posix()}')").fetchone()[0]
        bien = n == e
        ok &= bien
        print(f"  [{'OK ' if bien else 'DIF'}] {f:22s} {n:>12,}  (esperado {e:>12,})")
    except Exception as ex:
        ok = False
        print(f"  [ERR] {f}: {str(ex)[:70]}")

print("\n=== Temporales a medias ===")
tmps = list(B.glob("*.parquet.tmp"))
print(f"  {'ninguno' if not tmps else [t.name for t in tmps]}")
ok &= not tmps

print("\n=== Agregados (los que lee la app) ===")
m = json.loads((B / "aggs" / "_meta.json").read_text(encoding="utf-8"))
g = pl.read_parquet(B / "aggs" / "global.parquet").filter(pl.col("sem") <= m["sem_max_real"])
print(f"  generado    : {m['generado']}")
print(f"  corte real  : semana {m['sem_max_real']}")
print(f"  Real 2026   : {g['Real_2026'].sum()/1e6:>12,.1f} M")
print(f"  Real 2025   : {g['Real_2025'].sum()/1e6:>12,.1f} M")
print(f"  Plan 2026   : {g['Plan_2026'].sum()/1e6:>12,.1f} M")

print("\n=== Respaldo disponible ===")
r = B / "_respaldo"
if r.exists():
    for f in sorted(r.glob("*.parquet")):
        print(f"  {f.name:22s} {f.stat().st_size/1e6:>7,.0f} MB")
else:
    print("  (sin respaldo)")

print(f"\n{'='*56}")
print("TODO INTACTO" if ok else "HAY PROBLEMAS - revisar arriba")
sys.exit(0 if ok else 1)
