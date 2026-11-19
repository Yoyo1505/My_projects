# -*- coding: utf-8 -*-
"""Features por CECO-semana SIN fuga temporal: todo lo que depende de la historia usa solo semanas anteriores
(shift(1) antes de cualquier ventana móvil). Magnitudes adimensionales (se dividen entre la escala propia del
CECO) para que el ID o el tamaño del centro no entren como magnitud. Solo Polars; sin bucles por fila.
"""
from __future__ import annotations

import polars as pl

# `npast` (antigüedad) NO es feature: crece con el calendario y haría raras a las semanas nuevas por construcción.
FEATURES = ["lx", "sgn", "zr8", "d1", "d2", "d4", "d8", "vol8", "resid", "dplan", "dplan_chg", "flip", "miss8"]
PISO_ESCALA = 1000.0     # MXN: evita dividir entre ~0 en CECOs de monto minúsculo

# Nombre en lenguaje operativo (lo que ve el usuario en Cashi y en el tablero).
NOMBRES = {
    "lx": "el tamaño del monto", "sgn": "el signo del monto (cargo o abono)",
    "zr8": "el desvío contra sus últimas 8 semanas", "d1": "el cambio contra la semana anterior",
    "d2": "el cambio contra 2 semanas atrás", "d4": "el cambio contra 4 semanas atrás",
    "d8": "el cambio contra 8 semanas atrás", "vol8": "su volatilidad reciente",
    "resid": "la diferencia contra el movimiento de todo el sistema", "dplan": "la diferencia contra el Plan",
    "dplan_chg": "el cambio del Plan", "flip": "el cambio de signo contra la semana anterior",
    "miss8": "las semanas sin dato recientes",
}


def construir(panel: pl.DataFrame) -> pl.DataFrame:
    """`panel`: ceco, sem, real, plan. Devuelve ceco, sem, real, plan, presente, npast, med8 + FEATURES.
    Rejilla ceco × semana desde la primera semana de cada CECO (no el producto cartesiano con conceptos);
    las semanas sin fila cuentan como 0 con `presente`=False (se registra, no se oculta)."""
    if panel.is_empty():
        return pl.DataFrame(schema={c: pl.Float64 for c in ["real", "plan", "med8"] + FEATURES} | {"ceco": pl.String, "sem": pl.Int32,
                                                                                                   "presente": pl.Boolean, "npast": pl.Int64})
    smax = int(panel["sem"].max())
    rejilla = (panel.group_by("ceco").agg(pl.col("sem").min().alias("s0"))
               .with_columns(pl.int_ranges(pl.col("s0"), smax + 1, dtype=pl.Int32).alias("sem"))
               .explode("sem", empty_as_null=False).drop("s0"))
    d = (rejilla.join(panel, on=["ceco", "sem"], how="left")
         .with_columns(pl.col("real").is_not_null().alias("presente"))
         .with_columns(pl.col("real").fill_null(0.0), pl.col("plan").fill_null(0.0))
         .sort(["ceco", "sem"]))
    d = d.join(d.group_by("sem").agg(pl.col("real").sum().alias("tot")), on="sem", how="left")
    d = d.with_columns((pl.col("real") / pl.col("tot")).alias("share"), pl.col("presente").cast(pl.Int32).alias("pres_i"))

    w = dict(window_size=8, min_samples=4)
    past = pl.col("real").shift(1)
    d = d.with_columns(
        past.rolling_median(**w).over("ceco").alias("med8"),
        past.rolling_quantile(0.25, window_size=8, min_samples=4).over("ceco").alias("q25"),
        past.rolling_quantile(0.75, window_size=8, min_samples=4).over("ceco").alias("q75"),
        past.rolling_std(**w).over("ceco").alias("std8"),
        pl.col("real").abs().shift(1).rolling_median(**w).over("ceco").alias("amed8"),
        pl.col("share").shift(1).rolling_median(**w).over("ceco").alias("smed8"),
        pl.col("pres_i").cum_sum().shift(1).over("ceco").alias("npast"),
        (8 - pl.col("pres_i").shift(1).rolling_sum(window_size=8, min_samples=1)).over("ceco").clip(0, 8).alias("miss8"),
        *[pl.col("real").shift(k).over("ceco").alias(f"lag{k}") for k in (1, 2, 4, 8)],
        pl.col("plan").shift(1).over("ceco").alias("plan_l1"),
        pl.col("real").sign().shift(1).over("ceco").alias("sgn_l1"),
    )
    escala = pl.col("amed8") + PISO_ESCALA
    robusta = pl.max_horizontal((pl.col("q75") - pl.col("q25")) / 1.349, 0.05 * pl.col("amed8"), pl.lit(PISO_ESCALA))
    d = d.with_columns(
        pl.col("real").abs().log1p().alias("lx"),
        pl.col("real").sign().alias("sgn"),
        (0.6745 * (pl.col("real") - pl.col("med8")) / robusta).clip(-50, 50).alias("zr8"),
        *[((pl.col("real") - pl.col(f"lag{k}")) / escala).clip(-20, 20).alias(f"d{k}") for k in (1, 2, 4, 8)],
        (pl.col("std8") / escala).clip(0, 20).alias("vol8"),
        (((pl.col("share") - pl.col("smed8")) * pl.col("tot")) / escala).clip(-20, 20).alias("resid"),
        ((pl.col("real") - pl.col("plan")) / (pl.col("plan").abs() + escala)).clip(-20, 20).alias("dplan"),
        ((pl.col("plan") - pl.col("plan_l1")) / (pl.col("plan").abs() + escala)).clip(-20, 20).alias("dplan_chg"),
        (pl.col("real").sign() != pl.col("sgn_l1")).cast(pl.Float64).alias("flip"),
    )
    return d.select(["ceco", "sem", "real", "plan", "presente", "npast", "med8"] + FEATURES)


def elegibles(feat: pl.DataFrame, historia_min: int) -> pl.DataFrame:
    """Filas modelables: con dato esa semana, historia suficiente y todas las features definidas."""
    return feat.filter(pl.col("presente") & (pl.col("npast") >= historia_min) & pl.col("med8").is_not_null()
                       ).drop_nulls(FEATURES)
