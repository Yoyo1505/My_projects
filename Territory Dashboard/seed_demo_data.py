# -*- coding: utf-8 -*-
"""Synthetic aggregates for the public Territory Dashboard demo."""
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

MED = ("Real_2025", "Plan_2026", "Nvo_Plan_2026", "Real_2026")


def _serie(base: float) -> list[float]:
    out, v = [], base
    for s in range(1, SMP + 1):
        v = max(0.0, v * (1 + float(RNG.normal(0, 0.07))))
        out.append(round(v if s <= SMR or True else v, 2))
    # zero real after SMR
    for s in range(SMR, SMP):
        out[s] = out[s]  # plan series keep values
    return out


def _series_bundle(base: float) -> dict[str, list[float]]:
    r25 = _serie(base * 0.92)
    p26 = _serie(base * 1.05)
    nvo = _serie(base * 1.02)
    r26 = _serie(base)
    for i in range(SMR, SMP):
        r26[i] = 0.0
    return {"Real_2025": r25, "Plan_2026": p26, "Nvo_Plan_2026": nvo, "Real_2026": r26}


def _rows_from_entity(dims: dict, series: dict[str, list[float]], extra: dict | None = None) -> list[dict]:
    rows = []
    for i, sem in enumerate(range(1, SMP + 1)):
        rec = {"sem": sem, **dims}
        for m in MED:
            rec[m] = series[m][i]
        if extra:
            rec.update(extra)
        rows.append(rec)
    return rows


def _write_agg(name: str, rows: list[dict], group_cols: list[str]) -> None:
    if not rows:
        return
    df = pl.DataFrame(rows)
    # re-aggregate to the grain of group_cols + sem (sum metrics)
    gcols = ["sem"] + group_cols
    df = df.group_by(gcols).agg([pl.col(m).sum() for m in MED])
    # keep helper cols if present on first row pattern — reattach constants
    for c in ("cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3", "cat_Prefijo", "Categoria",
              "cat_CtaMayor_Nombre", "cat_Agrupador_Reales"):
        if c in pl.DataFrame(rows).columns and c not in df.columns:
            # take first non-null per group if possible — skip for simplicity
            pass
    df.write_parquet(AGGS / f"{name}.parquet")


def build() -> None:
    AGGS.mkdir(exist_ok=True)
    leaf_rows: list[dict] = []  # full grain: terr hierarchy × account
    pdc_ids: dict[str, int] = {}
    eco = 1000

    # Build hierarchy leaves
    for div in DIVISIONES:
        prefijo = div.split()[-1][:3].upper()
        for t_i in range(1, 3):
            terr = f"Territorio {div.split()[-1]} {t_i}"
            zona = f"Zona {div.split()[-1]} {t_i}"
            region = f"Región {div.split()[-1]} {t_i}"
            for p_i in range(1, 3):
                pdc = f"PDC {div.split()[-1]} {t_i}-{p_i}"
                eco += 1
                pdc_ids[pdc] = eco
                for g in GRUPOS:
                    for cta in CUENTAS[g]:
                        base = float(RNG.uniform(15, 120))
                        series = _series_bundle(base)
                        dims = {
                            "cat_Agrupa1": AGRUPA1,
                            "cat_Direccion_Division": div,
                            "cat_Subdireccion_Territorio": terr,
                            "cat_Subdireccion_Zona": zona,
                            "cat_Subdireccion_Region": region,
                            "cat_PDC": pdc,
                            "cat_Grupo_de_Cuentas": g,
                            "cat_Cuentas": cta,
                            "cat_PosPre": f"PosPre {cta}",
                            "cat_Prefijo": prefijo,
                            "cat_Subtipo": "Operativo",
                            "cat_Agrupador_Reales": g.split()[0],
                            "cat_CtaMayor_Nombre": cta,
                            "Categoria": "Expansión" if "Expans" in div else "Operación",
                            "ID_CONCEPTO_CUENTA_NIV3": f"ID-{g[:3]}-{cta[:3]}".upper(),
                        }
                        leaf_rows.extend(_rows_from_entity(dims, series))

    leaf = pl.DataFrame(leaf_rows)

    def agg_to(name: str, cols: list[str], extra_first: list[str] | None = None) -> None:
        keep = ["sem"] + cols
        extras = extra_first or []
        for e in extras:
            if e in leaf.columns and e not in keep:
                keep.append(e)
        # For categorical extras with same grain, take first
        metric_aggs = [pl.col(m).sum() for m in MED]
        other = [pl.col(c).first() for c in keep if c not in ["sem"] + cols and c not in MED]
        g = leaf.group_by(["sem"] + cols).agg(metric_aggs + other)
        # Ensure required measure cols
        g.write_parquet(AGGS / f"{name}.parquet")

    # Standard compute() sources
    agg_to("global", [])
    # global needs no cat cols — group only by sem
    leaf.group_by("sem").agg([pl.col(m).sum() for m in MED]).with_columns(
        pl.lit("Operativo").alias("cat_Subtipo"),
        pl.lit("ID-GLOBAL").alias("ID_CONCEPTO_CUENTA_NIV3"),
    ).write_parquet(AGGS / "global.parquet")

    agg_to("agrupa1", ["cat_Agrupa1"], ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("division", ["cat_Agrupa1", "cat_Direccion_Division"],
           ["cat_Prefijo", "cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("territorio",
           ["cat_Agrupa1", "cat_Direccion_Division", "cat_Subdireccion_Territorio"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("zona",
           ["cat_Agrupa1", "cat_Direccion_Division", "cat_Subdireccion_Territorio",
            "cat_Subdireccion_Zona"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("region",
           ["cat_Agrupa1", "cat_Direccion_Division", "cat_Subdireccion_Territorio",
            "cat_Subdireccion_Zona", "cat_Subdireccion_Region"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    # pdc grain with accounts (Trimestres + Detalle PDC)
    agg_to(
        "pdc",
        ["cat_Agrupa1", "cat_Direccion_Division", "cat_Subdireccion_Territorio",
         "cat_Subdireccion_Zona", "cat_Subdireccion_Region", "cat_PDC",
         "cat_Grupo_de_Cuentas", "cat_Cuentas"],
        ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3", "cat_Prefijo"],
    )
    agg_to("grupo_cuentas", ["cat_Agrupa1", "cat_Grupo_de_Cuentas"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("cuentas", ["cat_Agrupa1", "cat_Grupo_de_Cuentas", "cat_Cuentas"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])
    agg_to("pospre",
           ["cat_Agrupa1", "cat_Grupo_de_Cuentas", "cat_Cuentas", "cat_PosPre"],
           ["cat_Subtipo", "ID_CONCEPTO_CUENTA_NIV3"])

    # Remaining DIM aliases (lightweight copies)
    extras = {
        "formato": ("cat_Formato", "cat_Direccion_Division"),
        "naturaleza": ("cat_Naturaleza", "cat_Grupo_de_Cuentas"),
        "agrupador_reales": ("cat_Agrupador_Reales", "cat_Agrupador_Reales"),
        "agrupa2": ("cat_Agrupa2", "cat_Direccion_Division"),
        "agrupa3": ("cat_Agrupa3", "cat_Direccion_Division"),
        "agrupador": ("cat_Agrupador", "cat_Grupo_de_Cuentas"),
        "clasificacion2": ("cat_Clasificacion_2", "cat_Grupo_de_Cuentas"),
        "segmento1": ("cat_Segmento1", "cat_Direccion_Division"),
        "segmento2": ("cat_Segmento2", "cat_Direccion_Division"),
        "estatus": ("cat_Estatus", "cat_Direccion_Division"),
    }
    for name, (out_col, src_col) in extras.items():
        df = leaf if out_col in leaf.columns else leaf.with_columns(pl.col(src_col).alias(out_col))
        df.group_by(["sem", "cat_Agrupa1", out_col]).agg([pl.col(m).sum() for m in MED]).write_parquet(
            AGGS / f"{name}.parquet")

    # Cierres expansion tree
    leaf.group_by([
        "sem", "Categoria", "cat_Grupo_de_Cuentas", "cat_CtaMayor_Nombre",
        "cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Region",
        "cat_PDC",
    ]).agg([pl.col(m).sum() for m in MED]).write_parquet(AGGS / "cierres_expansion.parquet")

    # Cierres arbol (cuenta × pdc)
    leaf.group_by([
        "sem", "cat_Grupo_de_Cuentas", "cat_Cuentas", "cat_Agrupador_Reales", "cat_PDC",
    ]).agg([pl.col(m).sum() for m in MED]).write_parquet(AGGS / "cierres_arbol.parquet")

    # Minimal consolidado for Cierres gasto join (Serie long format)
    cons_rows = []
    for pdc, pid in pdc_ids.items():
        sub = leaf.filter(pl.col("cat_PDC") == pdc)
        for serie, col in (("R25", "Real_2025"), ("P26", "Plan_2026"), ("R26", "Real_2026")):
            mon = float(sub.select(pl.col(col).sum()).item())
            cons_rows.append({"cat_PDC": pdc, "Serie": serie, "monto": mon})
    pl.DataFrame(cons_rows).write_parquet(AGGS / "_consolidado.parquet")

    # Demo seguimiento (JSON) — replaces missing Excel path
    proyectos = ["Tiendas nuevas", "Remodelaciones", "Cierres programados", "Reubicaciones"]
    detalle = []
    for i, (pdc, pid) in enumerate(list(pdc_ids.items())[:12]):
        detalle.append({
            "Proyecto": proyectos[i % len(proyectos)],
            "Especialidad": "Retail",
            "Formato_Agrupado": "Tienda",
            "Formato": "Standard",
            "ECO": pid,
            "PDC": pdc,
            "Comentario": "Demo synthetic row",
            "Plan": int(RNG.integers(0, 2)),
            "Sem26": int(RNG.integers(20, 35)),
            "Sem_Actual": int(RNG.integers(20, 35)),
        })
    resumen = {
        p: {
            "Plan": int(RNG.integers(5, 20)),
            "Sem26": int(RNG.integers(5, 20)),
            "Sem_Actual": int(RNG.integers(5, 25)),
        }
        for p in proyectos
    }
    (AGGS / "seguimiento_demo.json").write_text(
        json.dumps({"resumen": resumen, "detalle": detalle, "archivo": "demo_seguimiento.json"},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    meta = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "sem_max_real": SMR,
        "sem_max_plan": SMP,
        "demo": True,
        "nota": "Synthetic demo data for public portfolio",
        "version_seed": 2,
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
    (AGGS / "pdc_ids.json").write_text(json.dumps(pdc_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    (AGGS / "pdc_cecos.json").write_text(
        json.dumps({p: [f"CECO-{i}"] for i, p in enumerate(pdc_ids, 1)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (AGGS / "riesgos.json").write_text(
        json.dumps({
            "actualizado": datetime.now().isoformat(timespec="seconds"),
            "riesgos": [
                "— Variaciones Negativas vs AA (YTD) —",
                "Mantenimiento | 12.5 | 4.2% | Higher preventive maintenance spend",
                "— Variaciones Negativas vs Plan (YTD) —",
                "Energía | 8.1 | 3.1% | Tariffs above budget",
            ],
            "oportunidades": [
                "— Variaciones positivas vs AA (YTD) —",
                "Digital | -5.2 | -2.0% | Digital campaign efficiency",
                "— Variaciones positivas vs Plan (YTD) —",
                "Flete | -3.4 | -1.5% | Route renegotiation",
            ],
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Demo data written to {AGGS} ({leaf.height} leaf rows)")


if __name__ == "__main__":
    build()
