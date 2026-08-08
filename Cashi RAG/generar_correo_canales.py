# -*- coding: utf-8 -*-
"""
Genera el correo HTML "Gasto Canales Físicos" (formato Outlook) leyendo
TODOS los números directamente de aggs/ (mismos parquets que usa app.py).
El texto narrativo de las secciones de Variaciones sale de aggs/riesgos.json,
que build_data.build_riesgos() genera a partir de 'Riesgos y Oportunidades.docx'
(el mismo Word que alimenta la pestaña Riesgos & Oport. del dashboard) — es
análisis humano de Planeación, no un dato calculable, por eso NO se redacta
solo. El Word necesita 4 títulos de párrafo: RIESGOS, OPORTUNIDADES (YTD) y
RIESGOS SEMANAL, OPORTUNIDADES SEMANAL (semanales, opcionales).

Uso:
    python -c "import build_data; build_data.build_riesgos()"   # refresca riesgos.json
    python generar_correo_canales.py                 # semana de corte vigente (SMR)
    python generar_correo_canales.py --semana 29
    python generar_correo_canales.py --destinatario "Teresita" --salida correo.html
"""
from __future__ import annotations

import argparse
import html as _html
import json
from pathlib import Path

import polars as pl

BASE = Path(__file__).parent.resolve()
AGGS = BASE / "aggs"

COLOR_ROJO = "#C8102E"
COLOR_VERDE = "#2E7D32"
COLOR_GRIS = "#4A5568"


# ---------------------------------------------------------------- utilidades
def M(v: float) -> str:
    """Entero en millones, sin decimales (formato del correo). Los aggs traen
    montos en pesos crudos (no en millones) -> se divide entre 1e6 aquí, igual
    que hace M()/MC() en app.py."""
    if v is None:
        return "—"
    return f"{round(abs(v) / 1e6):,}"


def MC(v: float) -> str:
    """Convención contable del correo: gasto (positivo interno) va con
    paréntesis, ahorro/negativo sin signo — igual que MC() en app.py."""
    if v is None:
        return "—"
    return f"({M(v)})" if v > 0 else M(v)


def color_valor(v: float) -> str:
    """Convención del dashboard: positivo (gasto) rojo, negativo (ahorro) verde."""
    return COLOR_ROJO if (v is not None and v > 0) else COLOR_VERDE


# ---------------------------------------------------------------- carga de datos
def cargar_meta() -> dict:
    return json.loads((AGGS / "_meta.json").read_text(encoding="utf-8"))


def cargar_orden_gpo() -> dict:
    fp = AGGS / "orden_gpo.json"
    return json.loads(fp.read_text(encoding="utf-8")) if fp.exists() else {}


def agregar_grupo_cuentas(rango: tuple[int, int], smr: int) -> pl.DataFrame:
    """Real25/Plan26/Real26 por Grupo de Cuentas en el rango de semanas
    [lo, hi], igual que compute('grupo_cuentas', ...) en app.py pero sin
    prorrateo de mes (el correo siempre trabaja por semana entera). Real 2026
    se topa en el corte real (smr): semanas futuras sin dato real cuentan 0."""
    lo, hi = rango
    df = pl.read_parquet(AGGS / "grupo_cuentas.parquet")
    real_hi = min(hi, smr)
    g = (df.filter((pl.col("sem") >= lo) & (pl.col("sem") <= hi))
           .with_columns(
               pl.when((pl.col("sem") >= lo) & (pl.col("sem") <= real_hi))
                 .then(pl.col("Real_2026")).otherwise(0.0).alias("Real_2026_topado"))
           .group_by("cat_Grupo_de_Cuentas")
           .agg([pl.col("Real_2025").sum(), pl.col("Plan_2026").sum(),
                 pl.col("Real_2026_topado").sum().alias("Real_2026")]))
    return g


def agregar_forecast_grupo(rango: tuple[int, int], smr: int) -> pl.DataFrame:
    """Forecast por Grupo de Cuentas. Dos casos (decisión del usuario):
      - Rango YTD (incluye semanas > smr, ej. 1..53): misma fórmula que
        'Forecast_Cierre' en _medidas() de app.py = Real_2026 topado al corte
        + Plan_2026 de las semanas aún no reales ("Plan Restante").
      - Rango que cae ENTERO dentro de semanas ya reales (típicamente la fila
        SEMANAL, una sola semana <= smr): Forecast_Cierre daría 0 de Plan
        Restante ahí (no tiene sentido para una semana ya pasada) -> se usa
        directamente Plan_2026 de esas semanas como aproximación del forecast.
    Cobertura 100% del universo en ambos casos (forecast_ceco.parquet, un CSV
    externo, solo cubre 61 de 128k combinaciones cuenta×sem — no apto aquí)."""
    lo, hi = rango
    df = pl.read_parquet(AGGS / "grupo_cuentas.parquet")
    sub = df.filter((pl.col("sem") >= lo) & (pl.col("sem") <= hi))
    if hi <= smr:
        return sub.group_by("cat_Grupo_de_Cuentas").agg(pl.col("Plan_2026").sum().alias("Forecast"))
    real_hi = min(hi, smr)
    g = (sub.with_columns([
               pl.when((pl.col("sem") >= lo) & (pl.col("sem") <= real_hi))
                 .then(pl.col("Real_2026")).otherwise(0.0).alias("_real_topado"),
               pl.when(pl.col("sem") > smr).then(pl.col("Plan_2026")).otherwise(0.0).alias("_plan_restante"),
           ])
           .group_by("cat_Grupo_de_Cuentas")
           .agg((pl.col("_real_topado").sum() + pl.col("_plan_restante").sum()).alias("Forecast")))
    return g


def totales_globales(rango: tuple[int, int], smr: int) -> dict:
    lo, hi = rango
    df = pl.read_parquet(AGGS / "global.parquet")
    real_hi = min(hi, smr)
    r = (df.filter((pl.col("sem") >= lo) & (pl.col("sem") <= hi))
           .with_columns(
               pl.when((pl.col("sem") >= lo) & (pl.col("sem") <= real_hi))
                 .then(pl.col("Real_2026")).otherwise(0.0).alias("Real_2026_topado"))
           .select([pl.col("Real_2025").sum(), pl.col("Plan_2026").sum(),
                    pl.col("Real_2026_topado").sum().alias("Real_2026")])
           .to_dicts()[0])
    fce = agregar_forecast_grupo(rango, smr)
    r["Forecast"] = fce["Forecast"].sum() if fce.height else 0.0
    return r


def semanal_por_semana(smr: int, smp: int) -> pl.DataFrame:
    """Real25/Plan26/Real26/Forecast por semana, 1..smp, para la tabla de
    Temporalidad 'semana por semana' al final del correo."""
    g = pl.read_parquet(AGGS / "global.parquet")
    base = (g.group_by("sem")
              .agg([pl.col("Real_2025").sum(), pl.col("Plan_2026").sum(),
                    pl.col("Real_2026").sum()])
              .sort("sem"))
    base = base.with_columns(
        pl.when(pl.col("sem") > smr).then(0.0).otherwise(pl.col("Real_2026")).alias("Real_2026"))
    fp = AGGS / "forecast_ceco.parquet"
    if fp.exists():
        fc = (pl.read_parquet(fp).group_by("sem").agg(pl.col("Forecast").sum()).sort("sem"))
        base = base.join(fc, on="sem", how="left").with_columns(pl.col("Forecast").fill_null(0.0))
    else:
        base = base.with_columns(pl.lit(0.0).alias("Forecast"))
    return base.filter(pl.col("sem") <= smp)


# ---------------------------------------------------------------- riesgos.docx
def leer_riesgos() -> dict:
    """Lee aggs/riesgos.json, generado por build_data.build_riesgos() a partir
    de 'Riesgos y Oportunidades.docx'. Ese parser reconoce 4 títulos de
    párrafo en el Word: RIESGOS / OPORTUNIDADES (bloques YTD, los que también
    muestra la pestaña Riesgos & Oport. del dashboard) y RIESGOS SEMANAL /
    OPORTUNIDADES SEMANAL (bloques semanales, exclusivos de este correo). Si
    riesgos.json no existe o está desactualizado, correr primero:
    python -c "import build_data; build_data.build_riesgos()" """
    fp = AGGS / "riesgos.json"
    if not fp.exists():
        return {"riesgos_ytd": [], "oportunidades_ytd": [], "riesgos_semanal": [], "oportunidades_semanal": []}
    d = json.loads(fp.read_text(encoding="utf-8"))
    return {
        "riesgos_ytd": d.get("riesgos", []),
        "oportunidades_ytd": d.get("oportunidades", []),
        "riesgos_semanal": d.get("riesgos_semanal", []),
        "oportunidades_semanal": d.get("oportunidades_semanal", []),
    }


def bloque_variacion_html(titulo: str, items: list[str], color: str, bg: str, borde: str) -> str:
    """Una caja de variaciones (negativas u positivas) — replica el HTML de
    referencia: título + lista de vineta con línea divisoria entre ellas."""
    if not items:
        cuerpo = ('<div style="color:#999;font-size:15px;font-style:italic;'
                  'text-align:center;padding:20px 0;">Sin variaciones registradas '
                  'en este período.</div>')
    else:
        partes = []
        for i, texto in enumerate(items):
            borde_css = "" if i == len(items) - 1 else "border-bottom:1px solid #dfd;"
            partes.append(
                f'<div style="margin-bottom:11px;padding-bottom:11px;{borde_css}'
                f'color:#222;page-break-inside:avoid;break-inside:avoid;">'
                f'<div style="font-size:15px;color:#555;margin-top:4px;line-height:1.75;">'
                f'{_html.escape(texto)}</div></div>')
        cuerpo = "".join(partes)
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="510" '
            f'style="background:{bg};border-left:4px solid {borde};"><tr><td '
            f'style="padding:16px 18px;color:#222;">'
            f'<div style="font-size:14px;font-weight:bold;color:{color};'
            f'text-transform:uppercase;letter-spacing:1px;margin-bottom:12px;">'
            f'{_html.escape(titulo)}</div>{cuerpo}</td></tr></table>')


# ---------------------------------------------------------------- tabla grupo cuentas
def fila_grupo_cuentas_html(nombre: str, r25, p26, fc, r26, total_r25=None, total_p26=None,
                            total_fc=None, total_r26=None, es_total=False,
                            es_hijo_renta=False) -> str:
    # convención del correo (igual que el HTML de referencia): la columna
    # "Vs X" es POSITIVA cuando hay ahorro respecto a X (favorable, verde) ->
    # es X - Real, no Real - X.
    vs_fc, vs_plan, vs_aa = fc - r26, p26 - r26, r25 - r26
    bg = "#4A5568" if es_total else ("#EEF3F8" if es_hijo_renta else "#fff")
    color_txt = "#fff" if es_total else "#222"
    peso_total = "font-weight:bold;" if es_total else ""

    def celda(v, tot=None):
        color = "#fff" if es_total else color_valor(v)
        pctv = f"{round(abs(v)/abs(tot)*100)}%" if tot else "0%"
        return (f'<td width="92" style="padding:9px 8px;text-align:right;font-size:14px;'
                f'color:{color};">{MC(v) if not (v is None or abs(v) < 0.5e6) else "—"}</td>'
                f'<td width="46" style="padding:9px 8px;text-align:right;font-size:12px;'
                f'color:{"#ddd" if es_total else "#888"};">{pctv}</td>')

    def celda_var(v, base):
        # favorable (ahorro, v>=0) = verde, desfavorable (v<0) = rojo
        color = "#fff" if es_total else (COLOR_VERDE if v >= 0 else COLOR_ROJO)
        pctv = f"{round(abs(v)/abs(base)*100)}%" if base else "0%"
        return (f'<td width="92" style="padding:9px 8px;text-align:right;font-size:14px;'
                f'color:{color};">{"—" if abs(v) < 0.5e6 else M(v)}</td>'
                f'<td width="46" style="padding:9px 8px;text-align:right;font-size:12px;'
                f'color:{"#fff" if es_total else color};">{pctv}</td>')

    label = (f'<span style="padding-left:14px;font-style:italic;font-size:14px;color:#555;">'
             f'&middot; {_html.escape(nombre)}</span>' if es_hijo_renta else
             f'<span style="font-size:14px;color:{color_txt};{peso_total}">{_html.escape(nombre)}</span>')

    tr25, tp26, tfc, tr26 = total_r25 or r25, total_p26 or p26, total_fc or fc, total_r26 or r26
    return (f'<tr style="background:{bg};border-bottom:1px solid #E8E8E8;">'
            f'{celda(r25, tr25)}{celda(p26, tp26)}{celda(fc, tfc)}{celda(r26, tr26)}'
            f'<td width="234" style="padding:9px 12px;{"color:#fff;font-weight:bold;" if es_total else ""}">'
            f'{label}</td>{celda_var(vs_fc, fc)}{celda_var(vs_plan, p26)}{celda_var(vs_aa, r25)}</tr>')


def tabla_grupo_cuentas_html(rango, smr, orden_gpo) -> str:
    g = agregar_grupo_cuentas(rango, smr)
    fc = agregar_forecast_grupo(rango, smr)
    j = (g.join(fc.select(["cat_Grupo_de_Cuentas", "Forecast"]), on="cat_Grupo_de_Cuentas", how="left")
          .with_columns(pl.col("Forecast").fill_null(0.0)))
    filas = j.to_dicts()
    filas.sort(key=lambda r: (orden_gpo.get(r["cat_Grupo_de_Cuentas"], 999), r["cat_Grupo_de_Cuentas"]))

    header = (
        '<tr>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Real<br>2025</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#CCCCCC;text-align:right;font-size:11px;border-right:1px solid #777;">%</td>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Plan<br>2026</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#CCCCCC;text-align:right;font-size:11px;border-right:1px solid #777;">%</td>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Fcst<br>2026</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#CCCCCC;text-align:right;font-size:11px;border-right:1px solid #999;">%</td>'
        '<td width="92" style="padding:6px 3px;background:#4A5568;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Real<br>2026</td>'
        '<td width="46" style="padding:6px 1px;background:#4A5568;color:#FFFFFF;text-align:right;font-size:11px;border-right:1px solid #5d6a7a;">%</td>'
        '<td width="234" style="padding:6px 9px;background:#4A5568;color:#fff;font-weight:bold;font-size:15px;border-right:1px solid #444;">Grupo de Cuentas</td>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Vs Fcst</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#FFFFFF;text-align:right;font-size:11px;border-right:1px solid #789aaa;">%</td>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Vs Plan</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#FFFFFF;text-align:right;font-size:11px;border-right:1px solid #789aaa;">%</td>'
        '<td width="92" style="padding:6px 3px;background:#607D8B;color:#fff;font-weight:bold;text-align:right;font-size:13px;">Vs AA</td>'
        '<td width="46" style="padding:6px 1px;background:#607D8B;color:#FFFFFF;text-align:right;font-size:11px;">%</td>'
        '</tr>')

    tot = totales_globales(rango, smr)
    filas_html = "".join(
        fila_grupo_cuentas_html(r["cat_Grupo_de_Cuentas"], r["Real_2025"], r["Plan_2026"],
                                r["Forecast"], r["Real_2026"],
                                total_r25=tot["Real_2025"], total_p26=tot["Plan_2026"],
                                total_fc=tot["Forecast"], total_r26=tot["Real_2026"])
        for r in filas)

    total_html = fila_grupo_cuentas_html("TOTAL GASTO", tot["Real_2025"], tot["Plan_2026"],
                                         tot["Forecast"], tot["Real_2026"], es_total=True)

    colgroup = ('<colgroup><col width="92"><col width="46"><col width="92"><col width="46">'
                '<col width="92"><col width="46"><col width="92"><col width="46"><col width="234">'
                '<col width="92"><col width="46"><col width="92"><col width="46"><col width="92">'
                '<col width="46"></colgroup>')
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;'
            f'page-break-inside:avoid;break-inside:avoid;"><tr><td style="padding:0 0 10px;">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;'
            f'border-collapse:collapse;table-layout:fixed;page-break-inside:avoid;break-inside:avoid;">'
            f'{colgroup}{header}{filas_html}{total_html}</table></td></tr></table>')


# ---------------------------------------------------------------- KPIs / bandas
# Convención única de todo el correo (igual que el HTML de referencia):
# vs_X = X - Real_2026 -> POSITIVO significa ahorro/favorable (verde),
# NEGATIVO significa que se gastó más de lo esperado (rojo).
def _favorable(v: float) -> bool:
    return v is None or v >= 0


def banda_html(titulo: str, subtitulo: str, tot: dict, bg: str) -> str:
    r25, p26, r26 = tot["Real_2025"], tot["Plan_2026"], tot["Real_2026"]
    vs_plan, vs_aa = p26 - r26, r25 - r26

    def chip(etq, v, base):
        signo = "+" if v >= 0 else "-"
        pctv = round(abs(v) / abs(base) * 100) if base else 0
        bg_chip = "#1B5E20" if _favorable(v) else "#b71c1c"
        return (f'<span style="background:{bg_chip};color:#fff;padding:4px 11px;border-radius:3px;'
                f'font-size:14px;font-weight:bold;margin-right:6px;">{etq} {signo}{M(v)}M / '
                f'{pctv}% &#8212; {"FAV" if _favorable(v) else "DESF"}</span>')
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;'
            f'background:{bg};page-break-inside:avoid;break-inside:avoid;"><tr><td style="padding:10px 26px;">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
            f'<td><span style="color:#fff;font-size:16px;font-weight:bold;letter-spacing:1px;'
            f'text-transform:uppercase;">{titulo}</span><span style="color:#fff;font-size:15px;"> '
            f'&#183; {subtitulo}</span></td><td align="right">'
            f'{chip("vs Plan", vs_plan, p26)}{chip("vs AA", vs_aa, r25)}'
            f'</td></tr></table></td></tr></table>')


def kpi_card(titulo: str, valor_display: str, sub: str, color: str) -> str:
    return (f'<table cellpadding="12" cellspacing="0" border="0" width="252" style="background:#fff;'
            f'border-top:3px solid {color};border-radius:0 0 4px 4px;"><tr><td>'
            f'<div style="font-size:13px;color:#888;text-transform:uppercase;letter-spacing:1px;'
            f'margin-bottom:3px;">{titulo}</div>'
            f'<div style="font-size:22px;font-weight:bold;color:{color};">{valor_display}</div>'
            f'<div style="font-size:14px;color:{color if color==COLOR_VERDE else "#888"};">{sub}</div>'
            f'</td></tr></table>')


def kpis_html(tot: dict) -> str:
    r25, p26, fc, r26 = tot["Real_2025"], tot["Plan_2026"], tot["Forecast"], tot["Real_2026"]
    vs_fc, vs_plan, vs_aa = fc - r26, p26 - r26, r25 - r26
    pct_fc = round(abs(vs_fc) / abs(fc) * 100) if fc else 0
    pct_plan = round(abs(vs_plan) / abs(p26) * 100) if p26 else 0
    pct_aa = round(abs(vs_aa) / abs(r25) * 100) if r25 else 0

    c1 = kpi_card("Real 2026", f"${MC(r26)} M", f"AA: ${MC(r25)}M", COLOR_ROJO)
    c2 = kpi_card("Vs Forecast", f"{M(vs_fc)} M" if _favorable(vs_fc) else f"({M(vs_fc)} M)",
                  f'{pct_fc}% &#183; {"Favorable" if _favorable(vs_fc) else "Desfavorable"}',
                  COLOR_VERDE if _favorable(vs_fc) else COLOR_ROJO)
    c3 = kpi_card("Vs Plan", f"{M(vs_plan)} M" if _favorable(vs_plan) else f"({M(vs_plan)} M)",
                  f'{pct_plan}% &#183; {"Favorable" if _favorable(vs_plan) else "Desfavorable"}',
                  COLOR_VERDE if _favorable(vs_plan) else COLOR_ROJO)
    c4 = kpi_card("Vs A&#241;o Anterior", f"{M(vs_aa)} M" if _favorable(vs_aa) else f"({M(vs_aa)} M)",
                  f'{pct_aa}% &#183; {"Favorable" if _favorable(vs_aa) else "Desfavorable"}',
                  COLOR_VERDE if _favorable(vs_aa) else COLOR_ROJO)
    return (f'<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;'
            f'background:#f5f5f5;page-break-inside:avoid;break-inside:avoid;"><tr><td style="padding:12px 26px 9px;">'
            f'<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>'
            f'<td width="252" style="padding-right:6px;">{c1}</td>'
            f'<td width="252" style="padding-right:6px;">{c2}</td>'
            f'<td width="252" style="padding-right:6px;">{c3}</td>'
            f'<td width="250">{c4}</td></tr></table></td></tr></table>')


# ---------------------------------------------------------------- main
def construir_correo(semana: int | None, destinatario: str) -> str:
    meta = cargar_meta()
    smr, smp = meta["sem_max_real"], meta["sem_max_plan"]
    sem_reporte = semana or smr
    orden_gpo = cargar_orden_gpo()
    riesgos = leer_riesgos()

    rango_sem = (sem_reporte, sem_reporte)
    rango_ytd = (1, smr)

    tot_sem = totales_globales(rango_sem, smr)
    tot_ytd = totales_globales(rango_ytd, smr)

    partes = []
    partes.append(f'<p style="margin:0 0 5px;font-size:16px;color:#222;">Buenas tardes '
                  f'<strong>{_html.escape(destinatario)}</strong>,</p>'
                  f'<p style="margin:0;font-size:15px;color:#555;line-height:1.5;">Adjunto el reporte '
                  f'de variaciones de gasto <strong style="color:{COLOR_ROJO};">Canales F&#237;sicos '
                  f'&#8212; Semana {sem_reporte}, 2026</strong>. A continuaci&#243;n el resumen ejecutivo.</p>')

    partes.append(banda_html("SEMANAL", f"Semana {sem_reporte}", tot_sem, COLOR_GRIS))
    partes.append(kpis_html(tot_sem))
    partes.append(tabla_grupo_cuentas_html(rango_sem, smr, orden_gpo))
    partes.append(bloque_variacion_html("Variaciones Negativas vs Plan &#8212; Semanal",
                  riesgos.get("riesgos_semanal", []), COLOR_ROJO, "#FFF5F5", COLOR_ROJO))
    partes.append(bloque_variacion_html("Variaciones Positivas vs Plan &#8212; Semanal",
                  riesgos.get("oportunidades_semanal", []), COLOR_VERDE, "#F5FFF5", COLOR_VERDE))

    partes.append(banda_html("ACUMULADO YTD", f"Semanas 1&#8211;{smr}", tot_ytd, COLOR_GRIS))
    partes.append(kpis_html(tot_ytd))
    partes.append(tabla_grupo_cuentas_html(rango_ytd, smr, orden_gpo))
    partes.append(bloque_variacion_html("Variaciones Negativas vs Plan &#8212; YTD",
                  riesgos.get("riesgos_ytd", []), COLOR_ROJO, "#FFF5F5", COLOR_ROJO))
    partes.append(bloque_variacion_html("Variaciones Positivas vs Plan &#8212; YTD",
                  riesgos.get("oportunidades_ytd", []), COLOR_VERDE, "#F5FFF5", COLOR_VERDE))

    cuerpo = "\n".join(partes)

    html_out = f"""<!DOCTYPE html><html lang="es"><head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
<title>Reporte Gasto Red Grupo Elektra - Semana {sem_reporte}</title>
<style>
@media print, screen {{
  .seccion-variacion {{ page-break-inside: avoid !important; break-inside: avoid !important; display: block; }}
  div[style*="color:#222"] {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
  svg {{ page-break-inside: avoid !important; break-inside: avoid !important; }}
}}
</style>
<style>
#cb:hover{{background:#f5f5f5;transform:translateY(-1px);box-shadow:0 4px 10px rgba(0,0,0,0.3);}}
#cb.ok{{background:#2E7D32 !important;color:#fff !important;}}
@media print{{#toolbar{{display:none !important;}}}}
</style>
</head>
<body style="margin:0;padding:0;background:#f5f5f5;">
<div id="toolbar" style="position:sticky;top:0;z-index:999;background:linear-gradient(to right,{COLOR_ROJO},#a00d24);border-bottom:3px solid #8B0F23;padding:18px 24px;display:flex;align-items:center;justify-content:space-between;font-family:Arial,sans-serif;box-shadow:0 4px 12px rgba(0,0,0,0.15);">
<div><div style="font-size:11px;color:#FFB3BD;font-weight:600;letter-spacing:1px;text-transform:uppercase;">Reporte Semanal</div>
<div style="font-size:17px;color:#fff;font-weight:bold;margin-top:2px;">Gasto Canales F&#237;sicos &#183; Semana {sem_reporte} &#8212; 2026</div></div>
<button id="cb" onclick="doCopy()" style="background:#fff;color:{COLOR_ROJO};border:none;padding:14px 28px;font-size:15px;font-weight:bold;border-radius:6px;cursor:pointer;font-family:Arial,sans-serif;box-shadow:0 2px 6px rgba(0,0,0,0.2);">&#128203; ABRIR PARA COPIAR A OUTLOOK</button>
</div>
<div id="em">
<style>
.tb{{display:flex;align-items:center;gap:10px;padding:10px 0 14px;border-bottom:0.5px solid #e0e0e0;margin-bottom:14px;}}
</style>
<div class="tb">
  <div style="flex:1">

<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;"><tr><td style="background:{COLOR_ROJO};padding:20px 26px;">
<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
<td><div style="color:#EEEEEE;font-size:13px;letter-spacing:3px;text-transform:uppercase;margin-bottom:6px;">CANALES F&#237;SICOS &#183; PLANEACI&#211;N FINANCIERA</div>
<div style="color:#fff;font-size:26px;font-weight:bold;margin-bottom:3px;">Gasto Canales F&#237;sicos</div>
<div style="color:#FFFFFF;font-size:16px;">Reporte Semanal &nbsp;&#183;&nbsp; Semana {sem_reporte} &#8212; 2026</div></td>
<td align="right" style="vertical-align:bottom;"><div style="background:#D0344D;padding:9px 14px;border-radius:4px;text-align:right;">
<div style="color:#DDDDDD;font-size:13px;text-transform:uppercase;letter-spacing:1px;">Cifras en</div>
<div style="color:#fff;font-size:16px;font-weight:bold;">Millones de Pesos</div>
<div style="color:#DDDDDD;font-size:13px;">Constantes</div></div></td>
</tr></table></td></tr></table>

<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;"><tr><td style="padding:14px 26px 12px;border-bottom:1px solid #f0f0f0;">
{cuerpo}
</td></tr></table>

<table cellpadding="0" cellspacing="0" border="0" width="1200" style="width:1200px;background:{COLOR_GRIS};page-break-inside:avoid;break-inside:avoid;"><tr><td style="padding:15px 26px;">
<table cellpadding="0" cellspacing="0" border="0" width="100%"><tr>
<td><div style="color:#FFFFFF;font-size:15px;">Planeaci&#243;n Financiera &nbsp;&#183;&nbsp; Canales F&#237;sicos</div>
<div style="color:#fff;font-size:15px;margin-top:4px;">Pr&#243;ximo reporte: <strong>Semana {sem_reporte + 1} &#8212; 2026</strong></div></td>
<td align="right">
<div style="color:#fff;font-size:14px;">Cifras en Millones de Pesos Constantes</div>
<div style="color:#FFFFFF;font-size:16px;font-weight:bold;margin-top:3px;">Semana {sem_reporte} &nbsp;&#183;&nbsp; 2026</div>
</td></tr></table></td></tr></table>
</div>
</div>
<script>
function doCopy(){{
  var el=document.getElementById('em');
  var r=document.createRange(); r.selectNode(el);
  var sel=window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
  document.execCommand('copy'); sel.removeAllRanges();
  var b=document.getElementById('cb'); b.classList.add('ok');
  b.innerHTML='&#10003; &#161;COPIADO! Ahora pega en Outlook con Ctrl+V';
}}
</script>
</body></html>"""
    return html_out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--semana", type=int, default=None, help="semana EKT a reportar (default: corte real vigente)")
    ap.add_argument("--destinatario", default="Teresita", help="nombre en el saludo")
    ap.add_argument("--salida", default=None, help="ruta del .html de salida")
    args = ap.parse_args()

    html_out = construir_correo(args.semana, args.destinatario)
    meta = cargar_meta()
    sem = args.semana or meta["sem_max_real"]
    salida = Path(args.salida) if args.salida else BASE / f"correo_canalesfisicos_sem{sem}.html"
    salida.write_text(html_out, encoding="utf-8")
    print(f"Generado: {salida}")


if __name__ == "__main__":
    main()
