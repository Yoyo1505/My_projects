# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_alertas.py — Anomalías, alertas y señales de sobregasto."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class ConsultasAlertasMixin:
    def _query_anomalias_mad(self, nlu: dict) -> dict:
        """Detección de anomalías vía MAD (Median Absolute Deviation).

        Igual que `_query_top_desviaciones`: ahora respeta los filtros de
        entidad de la consulta y agrupa por PDV en vez de CECO cuando se pide
        explícitamente (calibración 2026-08-31).
        """
        filt_clause, params = self._construir_filtros_entidad(nlu)

        agrupar_pdv = nlu.get("agrupar_variacion_por") == "pdv" and self.tiene_eco_pdv
        if agrupar_pdv:
            entidad_col, entidad_alias = "ECO_PDV", "PDV"
            where_entidad = "AND ECO_PDV IS NOT NULL AND ECO_PDV != 0"
        else:
            entidad_col, entidad_alias = "ID_CENTRO_COSTOS", "CECO"
            where_entidad = "AND ID_CENTRO_COSTOS IS NOT NULL"

        sql = f"""
            WITH ceco_sem AS (
                SELECT
                    {entidad_col} AS {entidad_alias},
                    cat_Grupo_de_Cuentas AS Grupo,
                    sem,
                    SUM(monto) AS Gasto
                FROM {self._fuente(nlu, {entidad_col, "cat_Grupo_de_Cuentas"})}
                WHERE Serie = 'R26' AND sem <= {self.sem_max_real} {where_entidad} {filt_clause}
                GROUP BY 1, 2, 3
                HAVING SUM(monto) > 50000
            ),
            ceco_med AS (
                SELECT
                    {entidad_alias},
                    Grupo,
                    sem,
                    Gasto,
                    MEDIAN(Gasto) OVER (PARTITION BY {entidad_alias}) AS Mediana,
                    ABS(Gasto - MEDIAN(Gasto) OVER (PARTITION BY {entidad_alias})) AS DevMediana
                FROM ceco_sem
            ),
            ceco_mad AS (
                SELECT
                    {entidad_alias},
                    Grupo,
                    sem,
                    Gasto,
                    Mediana,
                    DevMediana,
                    MEDIAN(DevMediana) OVER (PARTITION BY {entidad_alias}) AS MAD
                FROM ceco_med
            )
            SELECT
                {entidad_alias},
                Grupo AS Grupo_Cuentas,
                sem AS Semana_Num,
                Gasto AS Gasto_Semanal,
                Mediana AS Mediana_Historica,
                (Gasto - Mediana) AS Desviacion_vs_Mediana,
                CASE WHEN MAD > 0 THEN ABS(Gasto - Mediana) / MAD ELSE 0 END AS Score_Anomalia_MAD
            FROM ceco_mad
            WHERE MAD > 0 AND (Gasto - Mediana) > 100000 AND (ABS(Gasto - Mediana) / MAD) > 3.0
            ORDER BY Score_Anomalia_MAD DESC
            LIMIT 15
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No se encontraron anomalías estadísticas severas en el periodo y filtros indicados.")

        tabla_res = []
        for _, r in df.iterrows():
            tabla_res.append({
                entidad_alias: r[entidad_alias],
                "Grupo_Cuentas": r["Grupo_Cuentas"],
                "Semana": f"Sem {int(r['Semana_Num'])}",
                "Gasto_Semanal": r["Gasto_Semanal"],
                "Mediana_Historica": r["Mediana_Historica"],
                "Desviacion_vs_Mediana": r["Desviacion_vs_Mediana"],
                "Score_Anomalia_MAD": round(r["Score_Anomalia_MAD"], 2)
            })

        ent_nom = self._nombre_entidad(nlu)
        return {
            "tipo_respuesta": "anomalias",
            "intencion_detectada": f"Detección Estadística de Anomalías de Gasto por {entidad_alias} (MAD Engine DuckDB)",
            "titulo": f"{entidad_alias}s con Comportamiento Anómalo / Atípico ({ent_nom}, Sem 1..{self.sem_max_real})",
            "respuesta_ejecutiva": (
                f"### ⚠️ Anomalías y Picos Atípicos Detectados (DuckDB MAD Engine)\n"
                f"Se detectaron **{len(tabla_res)} eventos semanales atípicos** ({ent_nom}) cuya desviación supera 3.0 veces la mediana histórica del {entidad_alias}.\n\n"
                f"**Caso más severo:** {entidad_alias} **{tabla_res[0][entidad_alias]}** en la **{tabla_res[0]['Semana']}** "
                f"con un gasto de **{M(tabla_res[0]['Gasto_Semanal'])}** (Mediana habitual: {M(tabla_res[0]['Mediana_Historica'])})."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_alertas_sobregasto(self, nlu: dict) -> dict:
        """Alertas de sobregasto por VARIACIÓN semana-contra-semana (no por
        nivel de gasto, como `_query_anomalias_mad`).

        Para cada Grupo de Cuentas y, por separado, para cada CECO/ECO_PDV,
        calcula el incremento (Gasto[sem] - Gasto[sem-1]) semana a semana,
        usando la historia de **2 años (R25 + R26)** para la mediana y el MAD
        de esa variación por entidad — con solo el año en curso, entidades
        con pocas semanas de historia (o Grupos casi sin variación) generan
        MAD≈0 y cualquier movimiento chico dispara un score absurdo (caso
        real detectado 2026-09-28: un cambio de $231,813 con score de
        cientos de billones porque su MAD histórico era ~0).

        El piso mínimo en pesos YA NO es un valor fijo adivinado ($100,000
        para todo): se calcula como el **percentil 95 de |variación semanal|
        histórica real** (R25+R26) de esa misma dimensión (Grupo de Cuentas o
        CECO/PDV) — dimensiones con escalas muy distintas (un Grupo agrega
        decenas de CECOs) necesitan pisos distintos. Medido 2026-09-28:
        P95 Grupo de Cuentas ≈ $6.46M, P95 CECO ≈ $20,494 — un piso fijo de
        $100,000 dejaba pasar casi cualquier ruido en Grupo y bloqueaba casi
        toda alerta real a nivel CECO.

        Alerta = (a) score MAD > 3.0 sobre la mediana histórica de esa
        entidad, Y (b) |variación| > percentil 95 de su dimensión. Resultado
        ordenado por monto absoluto de la variación (mayor a menor), no por
        score — un score enorme por un movimiento pequeño ya no debería
        salir primero.
        """
        filt_clause, params = self._construir_filtros_entidad(nlu)
        agrupar_pdv = nlu.get("agrupar_variacion_por") == "pdv" and self.tiene_eco_pdv
        entidad_col_cecopdv = "ECO_PDV" if agrupar_pdv else "ID_CENTRO_COSTOS"
        entidad_alias_cecopdv = "PDV" if agrupar_pdv else "CECO"
        where_entidad = "AND ECO_PDV IS NOT NULL AND ECO_PDV != 0" if agrupar_pdv else "AND ID_CENTRO_COSTOS IS NOT NULL"

        def _sql_alertas(entidad_col: str, entidad_alias: str, where_extra: str) -> str:
            fuente = self._fuente(nlu, {entidad_col})
            return f"""
                WITH serie_r26 AS (
                    SELECT {entidad_col} AS Entidad, sem, SUM(monto) AS Gasto
                    FROM {fuente}
                    WHERE Serie = 'R26' AND sem <= {self.sem_max_real} {where_extra} {filt_clause}
                    GROUP BY 1, 2
                    HAVING SUM(monto) > 50000
                ),
                serie_r25 AS (
                    SELECT {entidad_col} AS Entidad, sem, SUM(monto) AS Gasto
                    FROM {fuente}
                    WHERE Serie = 'R25' {where_extra} {filt_clause}
                    GROUP BY 1, 2
                    HAVING SUM(monto) > 50000
                ),
                deltas_r26 AS (
                    SELECT Entidad, sem, Gasto,
                           Gasto - LAG(Gasto) OVER (PARTITION BY Entidad ORDER BY sem) AS Variacion
                    FROM serie_r26
                ),
                deltas_r25 AS (
                    SELECT Entidad,
                           Gasto - LAG(Gasto) OVER (PARTITION BY Entidad ORDER BY sem) AS Variacion
                    FROM serie_r25
                ),
                deltas_hist AS (
                    SELECT Entidad, Variacion FROM deltas_r26 WHERE Variacion IS NOT NULL
                    UNION ALL
                    SELECT Entidad, Variacion FROM deltas_r25 WHERE Variacion IS NOT NULL
                ),
                con_mediana AS (
                    SELECT Entidad, Variacion,
                           MEDIAN(Variacion) OVER (PARTITION BY Entidad) AS Mediana_Variacion
                    FROM deltas_hist
                ),
                stats_entidad AS (
                    SELECT DISTINCT Entidad, Mediana_Variacion,
                           MEDIAN(ABS(Variacion - Mediana_Variacion)) OVER (PARTITION BY Entidad) AS MAD_Variacion
                    FROM con_mediana
                ),
                umbral_global AS (
                    SELECT quantile_cont(ABS(Variacion), 0.95) AS Piso_P95
                    FROM deltas_hist
                )
                SELECT
                    '{entidad_alias}' AS Dimension,
                    d.Entidad,
                    d.sem AS Semana_Num,
                    d.Gasto AS Gasto_Semanal,
                    d.Variacion AS Variacion_Semanal,
                    (d.Gasto - d.Variacion) AS Gasto_Semana_Anterior,
                    CASE WHEN (d.Gasto - d.Variacion) != 0
                         THEN (d.Variacion / ABS(d.Gasto - d.Variacion)) * 100
                         ELSE NULL END AS Variacion_Pct,
                    s.Mediana_Variacion,
                    CASE WHEN s.MAD_Variacion > 0 THEN ABS(d.Variacion - s.Mediana_Variacion) / s.MAD_Variacion ELSE 0 END AS Score_Anomalia_MAD,
                    u.Piso_P95
                FROM deltas_r26 d
                JOIN stats_entidad s ON s.Entidad = d.Entidad
                CROSS JOIN umbral_global u
                WHERE d.sem = {self.sem_max_real}
                  AND s.MAD_Variacion > 0
                  AND (ABS(d.Variacion - s.Mediana_Variacion) / s.MAD_Variacion) > 3.0
                  AND ABS(d.Variacion) > u.Piso_P95
                ORDER BY ABS(d.Variacion) DESC
                LIMIT 20
            """

        sql_grupo = _sql_alertas("cat_Grupo_de_Cuentas", "Grupo de Cuentas", "AND cat_Grupo_de_Cuentas IS NOT NULL")
        sql_cecopdv = _sql_alertas(entidad_col_cecopdv, entidad_alias_cecopdv, where_entidad)

        # filt_clause aparece 2 veces por consulta (serie_r26 y serie_r25): los
        # parámetros van duplicados. Antes se pasaban una sola vez y cualquier
        # alerta con entidad ("alertas de sobregasto division norte") tronaba
        # con "Values were not provided for prepared statement parameters".
        cur_g, sql_g_used, dt_g_ms = self._exec_sql(sql_grupo, params * 2)
        df_g = self._fetch_df_arrow(cur_g)
        cur_c, sql_c_used, dt_c_ms = self._exec_sql(sql_cecopdv, params * 2)
        df_c = self._fetch_df_arrow(cur_c)

        df_total = pd.concat([df_g, df_c], ignore_index=True) if not (df_g.empty and df_c.empty) else pd.DataFrame()
        if df_total.empty:
            return self._respuesta_sin_datos(
                f"No se detectaron incrementos semanales anómalos en la Semana {self.sem_max_real} "
                f"para Grupos de Cuentas ni para {entidad_alias_cecopdv}s, con los filtros indicados."
            )
        df_total["Variacion_Abs"] = df_total["Variacion_Semanal"].abs()
        df_total["Variacion_Pct_Abs"] = df_total["Variacion_Pct"].abs()
        orden_pct = bool(nlu.get("orden_variacion_pct"))
        columna_orden = "Variacion_Pct_Abs" if orden_pct else "Variacion_Abs"
        df_total = df_total.sort_values(columna_orden, ascending=False, na_position="last")

        piso_grupo = df_g["Piso_P95"].iloc[0] if not df_g.empty else None
        piso_cecopdv = df_c["Piso_P95"].iloc[0] if not df_c.empty else None

        tabla_res = []
        for _, r in df_total.iterrows():
            tabla_res.append({
                "Dimension": r["Dimension"],
                "Entidad": r["Entidad"],
                "Semana": f"Sem {int(r['Semana_Num'])}",
                "Gasto_Semana_Anterior": r["Gasto_Semana_Anterior"],
                "Gasto_Semanal": r["Gasto_Semanal"],
                "Variacion_Semanal": r["Variacion_Semanal"],
                "Variacion_Pct": round(r["Variacion_Pct"], 1) if pd.notna(r["Variacion_Pct"]) else None,
                "Mediana_Variacion_Historica": r["Mediana_Variacion"],
                "Score_Anomalia_MAD": round(r["Score_Anomalia_MAD"], 2),
                "Piso_Estadistico_P95": round(r["Piso_P95"], 0)
            })

        peor = tabla_res[0]
        peor_pct_txt = f" ({peor['Variacion_Pct']:+.1f}%)" if peor["Variacion_Pct"] is not None else ""
        ent_nom = self._nombre_entidad(nlu)
        return {
            "tipo_respuesta": "alertas_sobregasto",
            "intencion_detectada": "Alertas de Sobregasto por Variación Semanal Anómala (MAD sobre incrementos)",
            "titulo": f"Alertas de Sobregasto — Variación Anómala en Semana {self.sem_max_real} ({ent_nom})",
            "respuesta_ejecutiva": (
                f"### 🚨 Alertas de Sobregasto por Variación Semanal (Sem {self.sem_max_real})\n"
                f"Se detectaron **{len(tabla_res)} alertas** ({ent_nom}), ordenadas de mayor a menor "
                f"{'variación porcentual' if orden_pct else 'monto'}. "
                f"Alerta = variación semanal estadísticamente anómala (score MAD > 3.0 vs su propia historia "
                f"2025+2026) **y** económicamente relevante (por arriba del percentil 95 de variación semanal "
                f"real de su dimensión: {'Grupo de Cuentas ' + M(piso_grupo) if piso_grupo is not None else ''}"
                f"{' · ' if piso_grupo is not None and piso_cecopdv is not None else ''}"
                f"{entidad_alias_cecopdv + ' ' + M(piso_cecopdv) if piso_cecopdv is not None else ''}) — "
                f"criterio dual (monto + %) recomendado en análisis de variación FP&A, nunca solo porcentaje.\n\n"
                f"**{'Mayor variación %' if orden_pct else 'Mayor monto'}:** {peor['Dimension']} **{peor['Entidad']}** "
                f"con una variación de **{M(peor['Variacion_Semanal'])}**{peor_pct_txt} "
                f"esta semana (variación típica: {M(peor['Mediana_Variacion_Historica'])})."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_g_used + "\n\n-- (2) " + sql_c_used,
                "tiempo_ms": dt_g_ms + dt_c_ms,
                "filas_procesadas": len(df_total),
                "fuentes_parquet": self._fuentes_de(sql_g_used + sql_c_used)
            }
        }

    def _query_senales_sobregasto(self, nlu: dict) -> dict:
        """Hallazgo ejecutivo de sobregasto de UNA semana (la pedida, o la
        última semana real). Mismo cálculo y mismo texto que el bloque
        "Señales de sobregasto" de la pestaña Alertas de Sobregasto."""
        from rag.senales_sobregasto import calcular_senales, ENTIDADES

        sem_info = nlu.get("semanas", {})
        semana = sem_info.get("fin") if sem_info.get("tipo") in ("individual", "especificas", "rango") else self.sem_max_real
        semana = min(int(semana or self.sem_max_real), self.sem_max_real)
        dims = nlu.get("dims_solicitadas", [])
        if nlu.get("agrupar_variacion_por") == "pdv" and self.tiene_eco_pdv:
            entidad = "pdv"
        elif "division" in dims:
            entidad = "division"
        elif "cuenta" in dims:
            entidad = "cuenta"
        else:
            entidad = "ceco"
        ent_col = ENTIDADES[entidad][0]

        filt_clause, params = self._construir_filtros_entidad(nlu)
        rama_map = None
        try:
            from pathlib import Path
            a = pd.read_parquet(Path(__file__).parent.parent.parent / "datos" / "cat_arbol.parquet",
                                columns=["ID_CENTRO_COSTOS", "cat_Rama"])
            rama_map = dict(zip(a["ID_CENTRO_COSTOS"].astype(str), a["cat_Rama"]))
        except Exception:
            pass
        cols_fuente = ({ent_col, "ID_CENTRO_COSTOS", "cat_Cuentas"} if rama_map
                       else {ent_col, "cat_Subdireccion_Territorio", "cat_Grupo_de_Cuentas"})
        fuente = self._fuente(nlu, cols_fuente)
        sqls: List[str] = []
        t0 = time.perf_counter()

        def ejecutar(sql: str, prm: list) -> pd.DataFrame:
            cur, sql_usado, _ = self._exec_sql(sql, prm)
            sqls.append(sql_usado)
            return self._fetch_df_arrow(cur)

        def etiquetar(x) -> str:
            if entidad == "pdv":
                try:
                    eco = int(float(x))
                except (TypeError, ValueError):
                    return "sin PDV asignado"
                nombres = self.eco_pdv_a_nombres.get(eco, [])
                return f"{eco} ({nombres[0]})" if nombres else str(eco)
            if entidad == "ceco":
                padres = self.grafo.get("ceco_padres", {}).get(str(x))
                return f"{x} ({padres[1]})" if padres else str(x)
            return str(x)

        s = calcular_senales(ejecutar, fuente, "monto", filt_clause, params, semana,
                             entidad=entidad, etiquetar=etiquetar, rama_map=rama_map)
        dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        ent_nom = self._nombre_entidad(nlu)
        tabla_res = [{
            ENTIDADES[entidad][1]: t["nombre"],
            "Exceso_vs_Plan": t["monto"],
            "Pct_del_Exceso_Bruto": round(t["pct_bruto"], 1),
            "Semanas_Seguidas_con_Exceso": t["persistencia"],
        } for t in s.get("top", [])]
        return {
            "tipo_respuesta": "alertas_sobregasto",
            "intencion_detectada": "Señales de Sobregasto de la Semana (hallazgo ejecutivo)",
            "titulo": f"Señales de Sobregasto — Semana {semana} ({ent_nom})",
            "respuesta_ejecutiva": (
                f"### 🧭 Señales de sobregasto — Semana {semana} ({ent_nom})\n"
                + s["texto"].replace("\n", "  \n")
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": "\n\n".join(sqls),
                "tiempo_ms": dt_ms,
                "filas_procesadas": s.get("universo", 0),
                "fuentes_parquet": self._fuentes_de("\n".join(sqls)),
            },
        }
