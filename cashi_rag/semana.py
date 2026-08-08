# -*- coding: utf-8 -*-
"""
semana.py — Calendario EKT y nombres de parquet por semana.

Fuente única de verdad para "¿en qué semana EKT estamos?" y "¿cómo se llama
el parquet de esta semana?". Antes el nombre estaba escrito a mano como
`r26_sem26.parquet` en extraer_sql.py y build_data.py, así que al pasar la
semana se seguía sobrescribiendo el parquet viejo.

Calendario: semanas de 7 días. La semana 1 de 2026 arranca el domingo
28-dic-2025 (verificado: sem 27 de 2026 = 28-jun a 4-jul). 2025 tuvo 52
semanas, su semana 1 arranca el domingo 29-dic-2024. Igual que app.py.
"""
from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

BASE = Path(__file__).parent.resolve()

ANCLA = {2025: date(2024, 12, 29), 2026: date(2025, 12, 28)}


def semana_ekt(d: date | None = None, anio: int = 2026) -> int:
    """Semana EKT (1-53) en la que cae `d`. Por defecto, hoy."""
    d = d or date.today()
    if anio not in ANCLA:
        raise ValueError(f"sin ancla de calendario para {anio}")
    return (d - ANCLA[anio]).days // 7 + 1


def rango_semana(s: int, anio: int = 2026) -> tuple[date, date]:
    """(primer día, último día) de la semana EKT `s`."""
    ini = ANCLA[anio] + timedelta(days=7 * (s - 1))
    return ini, ini + timedelta(days=6)


def semana_corte(d: date | None = None, anio: int = 2026) -> int:
    """Última semana EKT **cerrada**. La semana en curso aún no tiene datos
    completos en SQL, así que el corte es la anterior."""
    return semana_ekt(d, anio) - 1


def nombres(sem: int | None = None) -> dict[str, str]:
    """{'Real 2025': 'r25_sem28.parquet', ...} para la semana dada (o la vigente).

    El sufijo es la semana EKT **de 2026** en curso: identifica el corte de la
    extracción, no el año de cada tabla. Real 2025 se re-extrae con el mismo
    sufijo porque su contenido puede corregirse retroactivamente.
    """
    s = sem if sem is not None else semana_ekt()
    return {
        "Real 2025": f"r25_sem{s}.parquet",
        "Real 2026": f"r26_sem{s}.parquet",
        "Plan 2026": f"p26_sem{s}.parquet",
    }


def ruta(tabla: str, sem: int | None = None) -> Path:
    return BASE / nombres(sem)[tabla]


def parquet_mas_reciente(prefijo: str) -> Path | None:
    """El parquet existente con la semana más alta, p.ej. prefijo='r26'.
    Sirve para leer sin saber qué semana se extrajo por última vez."""
    cands = []
    for p in BASE.glob(f"{prefijo}_sem*.parquet"):
        try:
            cands.append((int(p.stem.split("_sem")[1]), p))
        except (IndexError, ValueError):
            continue
    return max(cands)[1] if cands else None


if __name__ == "__main__":
    hoy = date.today()
    s = semana_ekt(hoy)
    ini, fin = rango_semana(s)
    print(f"hoy {hoy} -> semana EKT {s} ({ini} a {fin})")
    print(f"semana de corte (última cerrada): {semana_corte(hoy)}")
    print("parquet de esta semana:")
    for t, n in nombres().items():
        existe = "OK" if (BASE / n).exists() else "falta"
        print(f"  {t:12s} {n:22s} [{existe}]")
    print("más reciente en disco:")
    for pre in ("r25", "r26", "p26"):
        p = parquet_mas_reciente(pre)
        print(f"  {pre}: {p.name if p else '(ninguno)'}")
