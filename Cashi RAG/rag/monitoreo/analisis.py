# -*- coding: utf-8 -*-
"""Análisis de un canal para un rango de semanas: lo comparten Cashi (texto) y el tablero (gráficas/tablas).

No abre conexiones: quien llama pasa `ejecutar(sql, params) -> DataFrame` y los nombres de las fuentes
(cada fuente expone sem, Serie, monto y las columnas de filtro). Devuelve DataFrames, sin formato.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

import pandas as pd

from . import config as C
from .atipicos import detectar, bloques, texto_semanas
from .variaciones import variaciones


def contiene_semana(texto: str, semana: int) -> bool:
    """¿'6 a 8 y 12' incluye la semana 7? (texto_semanas agrupa tres o más consecutivas como 'a a b')."""
    import re
    for tok in re.split(r",\s*| y ", texto):
        m = re.fullmatch(r"(\d+) a (\d+)", tok.strip())
        if m and int(m.group(1)) <= semana <= int(m.group(2)):
            return True
        if tok.strip() == str(semana):
            return True
    return False


def analizar(ejecutar: Callable[[str, list], pd.DataFrame], *, ini: int, fin: int, dim: str,
             fuente_ceco: str, fuente_g: str, m_col: str = "monto", filt: str = "", prm: Optional[list] = None,
             tabla_fcst: Optional[str] = None, f_col: str = "FCST_cons", where_fcst: str = "",
             params_fcst: Optional[list] = None, siempre_var: bool = False,
             contexto: Optional[Callable[[List[str]], Dict[str, dict]]] = None,
             nombre_ceco: Optional[Callable[[str], str]] = None, canal: Optional[str] = None,
             ml_solo_coinciden: bool = False) -> dict:
    """Claves: serie (sem, Real, Plan), tot_atip, media_tot, mediana_tot, var (N contra N-1; solo si fin==ini
    y fin>1), grupos_atip (ent, imp, sems), ceco_atip (lista de dicts con contexto), concentracion, filas.
    `dim`: "grupo" o "cuenta"."""
    prm = list(prm or [])
    es_rango = fin > ini
    col = "cat_Cuentas" if dim == "cuenta" else "cat_Grupo_de_Cuentas"
    out: dict = {"vacio": False, "col": col, "es_rango": es_rango, "ini": ini, "fin": fin}

    # Serie semanal por CECO (Real) y Plan total por semana (para la gráfica).
    c = ejecutar(f"""
        SELECT ID_CENTRO_COSTOS AS ceco, sem, Serie, SUM({m_col}) AS monto
        FROM {fuente_ceco}
        WHERE Serie IN ('R26', 'P26') AND sem BETWEEN 1 AND {int(fin)} AND ID_CENTRO_COSTOS IS NOT NULL {filt}
        GROUP BY 1, 2, 3
    """, list(prm))
    real = c[c["Serie"] == "R26"][["ceco", "sem", "monto"]].copy()
    if real.empty:
        out["vacio"] = True
        return out
    if not pd.api.types.is_string_dtype(real["ceco"]):      # astype(str) sobre columna Arrow itera en Python (0.5 s)
        real["ceco"] = real["ceco"].astype(str)
    out["filas"] = int(len(real))

    tot = real.groupby("sem", as_index=False)["monto"].sum().rename(columns={"monto": "Real"})
    plan = c[c["Serie"] == "P26"].groupby("sem", as_index=False)["monto"].sum().rename(columns={"monto": "Plan"})
    serie = tot.merge(plan, on="sem", how="left").fillna({"Plan": 0.0})
    out["serie"] = serie
    tt = tot.rename(columns={"Real": "monto"}).assign(t="TOTAL")
    a_tot = detectar(tt, "t", C.IMPACTO_MIN_TOTAL, modo="retro")
    out["tot_atip"] = a_tot[(a_tot["sem"] >= ini) & (a_tot["sem"] <= fin)].reset_index(drop=True)
    out["media_tot"] = float(tot["Real"].mean())
    out["mediana_tot"] = float(tot["Real"].median())

    piso_g = C.IMPACTO_MIN_GRUPO if dim == "grupo" else C.IMPACTO_MIN_GRUPO / 4
    out["grupos_atip"] = pd.DataFrame(columns=["ent", "imp", "sems"])
    if es_rango:
        sg = ejecutar(f"""
            SELECT {col} AS ent, sem, SUM({m_col}) AS monto FROM {fuente_g}
            WHERE Serie = 'R26' AND sem BETWEEN 1 AND {int(fin)} AND {col} IS NOT NULL {filt}
            GROUP BY 1, 2
        """, list(prm))
        ag = detectar(sg, "ent", piso_g, modo="retro")
        ag = ag[(ag["sem"] >= ini) & (ag["sem"] <= fin)]
        out["grupos_atip"] = (ag.groupby("ent").agg(imp=("dif", "sum"), sems=("sem", list)).reset_index()
                              .pipe(lambda d: d.reindex(d["imp"].abs().sort_values(ascending=False).index))
                              .reset_index(drop=True)) if not ag.empty else pd.DataFrame(columns=["ent", "imp", "sems"])
    if (not es_rango or siempre_var) and fin > 1:
        out["var"] = variaciones(ejecutar, fin, dim, tabla=fuente_g, m_col=m_col, tabla_fcst=tabla_fcst, f_col=f_col,
                                 where_extra=filt, params=prm, where_fcst=where_fcst, params_fcst=params_fcst)
        out["hay_fcst"] = tabla_fcst is not None

    # CECOs atípicos con contexto.
    a_cc = detectar(real, "ceco", C.IMPACTO_MIN_CECO, modo="retro")
    a_rng = a_cc[(a_cc["sem"] >= ini) & (a_cc["sem"] <= fin)]
    out["ceco_atip"] = []
    if not a_rng.empty:
        bl = bloques(a_rng, "ceco")
        tipo = bl.sort_values("n", ascending=False).drop_duplicates("ceco").set_index("ceco")["tipo"].to_dict()
        res = a_rng.groupby("ceco").agg(n=("sem", "size"), impacto=("dif", "sum"), sems=("sem", list)).reset_index()
        res = res.reindex(res["impacto"].abs().sort_values(ascending=False).index)
        ctx = contexto(res["ceco"].tolist()) if contexto else {}
        monto_fin = real[real["sem"] == fin].set_index("ceco")["monto"]
        filas: List[dict] = []
        for r in res.itertuples():
            k = ctx.get(r.ceco, {})
            filas.append({
                "CECO": r.ceco, "Nombre": nombre_ceco(r.ceco) if nombre_ceco else "",
                "Agrupador": k.get("agrupador") or "", "Division": k.get("division") or "",
                "Territorio": k.get("territorio") or "", "Zona": k.get("zona") or "", "Region": k.get("region") or "",
                "Semanas_Atipicas": texto_semanas(r.sems), "Num_Semanas": int(r.n),
                "Tipo": tipo.get(r.ceco, "PUNTUAL"),
                "Impacto_vs_Normal_MXN": round(float(r.impacto), 2),
                f"Monto_Sem_{fin}_MXN": round(float(monto_fin.get(r.ceco, 0.0)), 2),
            })
        if not es_rango:       # una sola semana: solo los atípicos precisamente en esa semana
            filas = [f for f in filas if contiene_semana(f["Semanas_Atipicas"], fin)]
        out["ceco_atip"] = filas

    # Modelo no supervisado (si hay resultados): score por CECO atípico y alertas del modelo en el rango.
    out["ml"] = {"hay": False, "alertas": [], "estado": None}
    if canal:
        from . import lectura
        ml = lectura.scores(canal, ini, fin)
        st = lectura.estado()
        if not ml.empty or st:
            out["ml"]["hay"] = True
            out["ml"]["estado"] = st
            por = ml.groupby("ceco").agg(score=("score", "max"), alerta=("alerta", "max")).to_dict("index") if not ml.empty else {}
            for f in out["ceco_atip"]:
                k = por.get(f["CECO"])
                f["ML_Score"] = round(float(k["score"]), 3) if k else None
                f["ML_Alerta"] = bool(k["alerta"]) if k else False
            # El modelo evalúa el CECO completo (no una cuenta): se limita a los CECOs que tienen gasto en el alcance
            # pedido y, si el alcance es una cuenta/grupo, solo a los que además marcó el detector estadístico.
            al = ml[ml["alerta"] & ml["ceco"].isin(set(real["ceco"]))].sort_values("score", ascending=False)
            if ml_solo_coinciden:
                al = al[al["ceco"].isin({f["CECO"] for f in out["ceco_atip"]})]
            out["ml"]["acotado_a_cuenta"] = bool(ml_solo_coinciden)
            if not al.empty:
                ctx2 = contexto(al["ceco"].unique().tolist()) if contexto else {}
                en_estadistico = {f["CECO"] for f in out["ceco_atip"]}
                sems_por = al.groupby("ceco")["sem"].apply(list).to_dict()
                for x in al.drop_duplicates("ceco").itertuples():      # una fila por CECO: la semana de mayor rareza
                    k = ctx2.get(x.ceco, {})
                    out["ml"]["alertas"].append({
                        "CECO": x.ceco, "Nombre": nombre_ceco(x.ceco) if nombre_ceco else "",
                        "Semanas": texto_semanas(sems_por[x.ceco]), "Num_Semanas": len(sems_por[x.ceco]),
                        "Agrupador": k.get("agrupador") or "", "Division": k.get("division") or "",
                        "Territorio": k.get("territorio") or "", "Zona": k.get("zona") or "",
                        "Score": round(float(x.score), 3), "Concordancia": bool(x.concordancia),
                        "Causas": getattr(x, "causas", "") or "", "Monto_MXN": round(float(x.real), 2),
                        "Tambien_Estadistico": x.ceco in en_estadistico})

    # Dónde se concentra el impacto (agrupador y división con mayor peso absoluto).
    conc: Dict[str, tuple] = {}
    if len(out["ceco_atip"]) >= 2:
        d = pd.DataFrame(out["ceco_atip"])
        d["abs"] = d["Impacto_vs_Normal_MXN"].abs()
        for campo in ("Agrupador", "Division"):
            s = d[d[campo] != ""].groupby(campo)["abs"].sum().sort_values(ascending=False)
            if len(s) and s.sum() > 0:
                conc[campo] = (str(s.index[0]), float(s.iloc[0] / s.sum() * 100))
    out["concentracion"] = conc
    return out
