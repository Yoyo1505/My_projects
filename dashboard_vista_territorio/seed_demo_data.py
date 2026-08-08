# -*- coding: utf-8 -*-
"""Genera agregados sintéticos en aggs/ para demo del repositorio (sin datos reales)."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
import polars as pl

BASE = Path(__file__).parent.resolve()
AGGS = BASE / "aggs"

GRUPOS = [
    "Gastos de Operación",
    "Nómina y Beneficios",
    "Marketing",
    "Renta y Servicios",
    "Logística",
]
CUENTAS = {
    "Gastos de Operación": ["Mantenimiento", "Suministros", "Seguros"],
    "Nómina y Beneficios": ["Sueldos", "Prestaciones", "Capacitación"],
    "Marketing": ["Digital", "ATL", "Promociones"],
    "Renta y Servicios": ["Arrendamiento", "Energía", "Agua"],
    "Logística": ["Flete", "Almacén", "Última milla"],
}
DIVISIONES = [
    "Division Norte",
    "Division Centro",
    "Division Sur",
    "Corporativo",
    "Expansión",
]
AGRUPA1 = "Red Comercial"
SMR, SMP = 30, 53
RNG = np.random.default_rng(42)


def _serie(base: float, sems: range, noise: float = 0.08) -> list[float]:
    out = []
    v = base
    for _ in sems:
        v = max(0.0, v * (1 + float(RNG.normal(0, noise))))
        out.append(round(v, 2))
    return out


def build() -> None:
    AGGS.mkdir(exist_ok=True)
    sems = list(range(1, SMP + 1))
    rows_gpo, rows_cta, rows_div, rows_glob = [], [], [], []

    for g in GRUPOS:
        base = float(RNG.uniform(800, 4500))
        r25 = _serie(base * 0.92, range(1, SMP + 1))
        p26 = _serie(base * 1.05, range(1, SMP + 1))
        nvo = _serie(base * 1.02, range(1, SMP + 1))
        r26 = _serie(base, range(1, SMR + 1)) + [0.0] * (SMP - SMR)
        for i, s in enumerate(sems):
            rows_gpo.append({
                "sem": s,
                "cat_Agrupa1": AGRUPA1,
                "cat_Grupo_de_Cuentas": g,
                "Real_2025": r25[i],
                "Plan_2026": p26[i],
                "Nvo_Plan_2026": nvo[i],
                "Real_2026": r26[i],
                "cat_Subtipo": "Operativo",
                "ID_CONCEPTO_CUENTA_NIV3": f"ID-{g[:3].upper()}",
            })
        for c in CUENTAS[g]:
            factor = 1 / len(CUENTAS[g])
            for i, s in enumerate(sems):
                rows_cta.append({
                    "sem": s,
                    "cat_Agrupa1": AGRUPA1,
                    "cat_Grupo_de_Cuentas": g,
                    "cat_Cuentas": c,
                    "Real_2025": r25[i] * factor,
                    "Plan_2026": p26[i] * factor,
                    "Nvo_Plan_2026": nvo[i] * factor,
                    "Real_2026": r26[i] * factor,
                    "cat_Subtipo": "Operativo",
                    "ID_CONCEPTO_CUENTA_NIV3": f"ID-{g[:3].upper()}-{c[:3].upper()}",
                })

    for d in DIVISIONES:
        base = float(RNG.uniform(1200, 5000))
        r25 = _serie(base * 0.9, range(1, SMP + 1))
        p26 = _serie(base * 1.04, range(1, SMP + 1))
        nvo = _serie(base * 1.01, range(1, SMP + 1))
        r26 = _serie(base, range(1, SMR + 1)) + [0.0] * (SMP - SMR)
        for i, s in enumerate(sems):
            rows_div.append({
                "sem": s,
                "cat_Agrupa1": AGRUPA1,
                "cat_Direccion_Division": d,
                "Real_2025": r25[i],
                "Plan_2026": p26[i],
                "Nvo_Plan_2026": nvo[i],
                "Real_2026": r26[i],
                "cat_Subtipo": "Operativo",
                "ID_CONCEPTO_CUENTA_NIV3": f"ID-DIV-{d[:4].upper()}",
            })

    # Global = suma de grupos por semana
    by_sem = {}
    for r in rows_gpo:
        s = r["sem"]
        b = by_sem.setdefault(s, {
            "sem": s, "Real_2025": 0.0, "Plan_2026": 0.0,
            "Nvo_Plan_2026": 0.0, "Real_2026": 0.0,
            "cat_Subtipo": "Operativo",
            "ID_CONCEPTO_CUENTA_NIV3": "ID-GLOBAL",
        })
        for k in ("Real_2025", "Plan_2026", "Nvo_Plan_2026", "Real_2026"):
            b[k] += r[k]
    rows_glob = list(by_sem.values())

    pl.DataFrame(rows_glob).write_parquet(AGGS / "global.parquet")
    pl.DataFrame(rows_gpo).write_parquet(AGGS / "grupo_cuentas.parquet")
    pl.DataFrame(rows_cta).write_parquet(AGGS / "cuentas.parquet")
    pl.DataFrame(rows_div).write_parquet(AGGS / "division.parquet")

    # alias mínimos vacíos-compatibles (mismos cols base) para no romper load
    base_cols = pl.DataFrame(rows_div)
    for name, col in [
        ("territorio", "cat_Subdireccion_Territorio"),
        ("zona", "cat_Subdireccion_Zona"),
        ("region", "cat_Subdireccion_Region"),
        ("pdc", "cat_PDC"),
        ("pospre", "cat_PosPre"),
        ("formato", "cat_Formato"),
        ("naturaleza", "cat_Naturaleza"),
        ("agrupador_reales", "cat_Agrupador_Reales"),
        ("agrupa1", "cat_Agrupa1"),
        ("agrupa2", "cat_Agrupa2"),
        ("agrupa3", "cat_Agrupa3"),
        ("agrupador", "cat_Agrupador"),
        ("clasificacion2", "cat_Clasificacion_2"),
        ("segmento1", "cat_Segmento1"),
        ("segmento2", "cat_Segmento2"),
        ("estatus", "cat_Estatus"),
    ]:
        df = base_cols.with_columns(pl.lit("Demo").alias(col)) if col not in base_cols.columns else base_cols
        # simplify: copy division structure with renamed label col
        d = pl.DataFrame(rows_div).with_columns(
            pl.col("cat_Direccion_Division").alias(col) if col != "cat_Agrupa1"
            else pl.lit(AGRUPA1).alias(col)
        )
        if col != "cat_Direccion_Division" and "cat_Direccion_Division" in d.columns and col != "cat_Agrupa1":
            pass
        d.write_parquet(AGGS / f"{name}.parquet")

    meta = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sem_max_real": SMR,
        "sem_max_plan": SMP,
        "demo": True,
        "nota": "Datos sintéticos para demo pública del repositorio",
    }
    (AGGS / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (AGGS / "orden_gpo.json").write_text(
        json.dumps({g: i + 1 for i, g in enumerate(GRUPOS)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (AGGS / "responsables_gpo.json").write_text(
        json.dumps({"Demo Analyst": GRUPOS}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (AGGS / "pdc_ids.json").write_text("{}", encoding="utf-8")
    (AGGS / "pdc_cecos.json").write_text("{}", encoding="utf-8")
    (AGGS / "riesgos.json").write_text(
        json.dumps({
            "actualizado": datetime.now().isoformat(timespec="seconds"),
            "riesgos": [
                "— Variaciones Negativas vs AA (YTD) —",
                "Mantenimiento | 12.5 | 4.2% | Mayor gasto en mantenimiento preventivo",
                "— Variaciones Negativas vs Plan (YTD) —",
                "Energía | 8.1 | 3.1% | Tarifas por encima de presupuesto",
            ],
            "oportunidades": [
                "— Variaciones positivas vs AA (YTD) —",
                "Digital | -5.2 | -2.0% | Eficiencia en campañas digitales",
                "— Variaciones positivas vs Plan (YTD) —",
                "Flete | -3.4 | -1.5% | Renegociación de rutas",
            ],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Demo data written to {AGGS}")


if __name__ == "__main__":
    build()
