# -*- coding: utf-8 -*-
"""¿La detección de novedades realmente detecta? Prueba con un parquet alterado.
NO toca los parquets buenos: usa copias y las restaura."""
import sys, io, shutil, subprocess, time
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import polars as pl

BASE = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
PQ = BASE / "r26_sem26.parquet"
BK = BASE / "tests" / "r26_backup.parquet"
PY = sys.executable
fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


def rc_check() -> int:
    r = subprocess.run([PY, str(BASE / "extraer_sql.py"), "--check"],
                       cwd=BASE, capture_output=True, timeout=180)
    return r.returncode


print("=== 1. Estado inicial: los parquets están al día ===")
t = time.time()
rc = rc_check()
check("sin cambios -> exit 1", rc == 1, f"exit={rc}, {time.time()-t:.1f}s")

print("\n=== 2. Simulo FILAS de menos (borro 1000 filas) ===")
shutil.copy2(PQ, BK)
try:
    df = pl.read_parquet(PQ)
    df.head(df.height - 1000).write_parquet(PQ)
    rc = rc_check()
    check("menos filas -> exit 0 (hay novedades)", rc == 0, f"exit={rc}")
finally:
    shutil.copy2(BK, PQ)
rc = rc_check()
check("restaurado -> exit 1 otra vez", rc == 1, f"exit={rc}")

print("\n=== 3. Simulo MISMO nº de filas pero MONTO corregido ===")
print("    (el caso que un COUNT(*) solo NO detectaría)")
shutil.copy2(PQ, BK)
try:
    df = pl.read_parquet(PQ)
    col = "SUM_MONTO_MNX_CONS_(SUMA)"
    # cambia un solo importe en +10 millones, misma cantidad de filas
    n_antes = df.height
    df = df.with_row_count("_i").with_columns(
        pl.when(pl.col("_i") == 0)
          .then(pl.col(col).cast(pl.Float64) + 10_000_000.0)
          .otherwise(pl.col(col).cast(pl.Float64))
          .alias(col)).drop("_i")
    df.write_parquet(PQ)
    check("mismo nº de filas tras alterar", pl.read_parquet(PQ).height == n_antes)
    rc = rc_check()
    check("monto distinto -> exit 0 (hay novedades)", rc == 0, f"exit={rc}")
finally:
    shutil.copy2(BK, PQ)
    BK.unlink(missing_ok=True)
rc = rc_check()
check("restaurado -> exit 1", rc == 1, f"exit={rc}")

print("\n=== 4. Error de conexión NO debe leerse como 'sin cambios' ===")
import os
env = os.environ.copy()
env["SQL_SERVER"] = "servidor.inexistente,1433"
r = subprocess.run([PY, str(BASE / "extraer_sql.py"), "--check"],
                   cwd=BASE, capture_output=True, timeout=120, env=env)
check("servidor caído -> exit 2 (no 1)", r.returncode == 2, f"exit={r.returncode}")

print(f"\n{'='*54}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
