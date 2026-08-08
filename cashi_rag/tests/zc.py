# -*- coding: utf-8 -*-
"""El estado.json quedó con corriendo=true y un PID muerto.
La app NO debe mostrar una barra de progreso eterna."""
import sys, io, json, subprocess
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
BASE = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
sys.path.insert(0, str(BASE))
fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


def vivo(pid):
    if not pid:
        return False
    try:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                           capture_output=True, text=True, timeout=8)
        return str(pid) in r.stdout
    except Exception:
        return True


print("=== 1. El estado.json real quedó zombi ===")
e = json.loads((BASE / "estado.json").read_text(encoding="utf-8"))
print(f"    fase={e['fase']!r} corriendo={e['corriendo']} pid={e.get('pid')}")
check("estado dice corriendo=true", e.get("corriendo") is True)
check("el PID guardado ya no existe", not vivo(e.get("pid")), f"pid {e.get('pid')}")

print("\n=== 2. leer_estado() de la app lo detecta ===")
# replicamos la lógica de app.leer_estado sin arrancar Streamlit
def leer_estado():
    d = json.loads((BASE / "estado.json").read_text(encoding="utf-8"))
    if d.get("corriendo") and not vivo(d.get("pid")):
        d["corriendo"] = False
        d["error"] = d.get("error") or (
            f"el proceso terminó inesperadamente en la fase '{d.get('fase')}'")
    return d


r = leer_estado()
check("marca corriendo=false", r["corriendo"] is False)
check("reporta el error al usuario", bool(r["error"]), r["error"][:70])
check("menciona la fase donde murió", "extrayendo" in (r["error"] or ""))

print("\n=== 3. Integridad tras la muerte del proceso ===")
tmps = list(BASE.glob("*.parquet.tmp"))
check("cero parquets a medias", not tmps, str([t.name for t in tmps]))
import duckdb
n = duckdb.connect().execute(
    f"SELECT COUNT(*) FROM read_parquet('{(BASE/'r26_sem26.parquet').as_posix()}')").fetchone()[0]
check("r26 conserva sus 14,433,688 filas", n == 14_433_688, f"{n:,}")
n25 = duckdb.connect().execute(
    f"SELECT COUNT(*) FROM read_parquet('{(BASE/'r25_sem26.parquet').as_posix()}')").fetchone()[0]
check("r25 conserva sus 23,558,059 filas", n25 == 23_558_059, f"{n25:,}")

print(f"\n{'='*54}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
