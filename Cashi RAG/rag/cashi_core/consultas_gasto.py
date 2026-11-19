# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_gasto.py — Consultas de gasto: multidimensional, top, pareto y consulta estándar."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class ConsultasGastoMixin:
    def _query_multidimensional(self, nlu: dict) -> dict:
        dims = nlu.get("dims_solicitadas", [])
        s_ini = nlu["semanas"].get("inicio", 1)
        s_fin = nlu["semanas"].get("fin", self.sem_max_plan)

        dim_cols = []
        group_exprs = []

        mapping_dims = {
            # Homologación de la presentación semanal: territorio '0' ("sin
            # agrupar") se muestra con el nombre de su División (Centro, Norte,
            # Sur, Geografía Nacional). Ver ppt_semanal/bases.py en Gasto Canal Físico.
            "territorio": ("COALESCE(NULLIF(cat_Subdireccion_Territorio, '0'), cat_Direccion_Division)", "Territorio"),
            # Sin clasificar ('0' o vacío) se muestra como "No Clasificado", igual que en el tablero.
            "zona": ("COALESCE(NULLIF(cat_Subdireccion_Zona, '0'), 'No Clasificado')", "Zona"),
            "region": ("COALESCE(NULLIF(cat_Subdireccion_Region, '0'), 'No Clasificado')", "Region"),
            "division": ("cat_Direccion_Division", "División"),
            "grupo_cuentas": ("cat_Grupo_de_Cuentas", "Grupo_Cuentas"),
            "cuenta": ("cat_Cuentas", "Cuenta"),
            "agrupador_reales": ("cat_Agrupador_Reales", "Agrupador_Reales"),
            "ceco": ("ID_CENTRO_COSTOS", "CECO"),
            # PDC se agrupa por ECO_PDV (el identificador real de punto de
            # contacto físico), no por cat_PDC — ver `_construir_filtros_entidad`.
            # Un desglose "por pdc" que agrupara por cat_PDC partiría en 2 filas
            # una misma tienda con nombre de PDC distinto para su empeño.
            "pdc": ("ECO_PDV", "PDC"),
            "semana": ("sem", "Semana"),
            "mes": ("""CASE 
                    WHEN sem BETWEEN 1 AND 4 THEN '01-Enero'
                    WHEN sem BETWEEN 5 AND 8 THEN '02-Febrero'
                    WHEN sem BETWEEN 9 AND 13 THEN '03-Marzo'
                    WHEN sem BETWEEN 14 AND 17 THEN '04-Abril'
                    WHEN sem BETWEEN 18 AND 22 THEN '05-Mayo'
                    WHEN sem BETWEEN 23 AND 26 THEN '06-Junio'
                    WHEN sem BETWEEN 27 AND 30 THEN '07-Julio'
                    WHEN sem BETWEEN 31 AND 35 THEN '08-Agosto'
                    WHEN sem BETWEEN 36 AND 39 THEN '09-Septiembre'
                    WHEN sem BETWEEN 40 AND 44 THEN '10-Octubre'
                    WHEN sem BETWEEN 45 AND 48 THEN '11-Noviembre'
                    WHEN sem BETWEEN 49 AND 53 THEN '12-Diciembre'
                END""", "Mes")
        }

        for d in dims:
            if d in mapping_dims:
                col_expr, alias = mapping_dims[d]
                dim_cols.append(f"{col_expr} AS {alias}")
                group_exprs.append(col_expr)

        if not dim_cols:
            dim_cols = ["cat_Subdireccion_Territorio AS Territorio", "sem AS Semana"]
            group_exprs = ["cat_Subdireccion_Territorio", "sem"]

        select_clause = ", ".join(dim_cols)
        group_clause = ", ".join([str(i+1) for i in range(len(group_exprs))])

        filt_clause, params = self._construir_filtros_entidad(nlu)
        fuente = self._fuente(nlu, {c for g in group_exprs for c in re.findall(r"\b(?:cat_|ID_|ECO_)\w+", g)})

        sql = f"""
            SELECT
                {select_clause},
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Desviacion_MDP
            FROM {fuente}
            WHERE sem BETWEEN {s_ini} AND {s_fin} {filt_clause}
            GROUP BY {group_clause}
            ORDER BY 1, 2
        """

        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)

        if df.empty:
            return self._respuesta_sin_datos("No se encontraron registros multi-dimensionales para los criterios seleccionados.")

        tabla_res = df.to_dict(orient="records")

        tit_dims = " x ".join([d.capitalize() for d in dims])
        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Desglose Multi-Dimensional ({tit_dims})",
            "titulo": f"Matriz Financiera: {tit_dims} (Sem {s_ini}..{s_fin})",
            "respuesta_ejecutiva": (
                f"### 🔀 Desglose Multi-Dimensional ({tit_dims})\n"
                f"Se ejecutó una agrupación matricial dinámica combinando **{len(dims)} dimensiones**.\n\n"
                f"Total de registros consolidados: **{len(df)}**."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    # -------------------------------------------------------------------------
    # OTRAS CONSULTAS ESPECIALIZADAS
    # -------------------------------------------------------------------------

    def _query_top_gasto_entidad(self, nlu: dict) -> dict:
        """Ranking por NIVEL de gasto (no por desviación vs Plan) — responde
        "qué CECO/PDV tiene más gasto de <grupo/cuenta>" (2026-09-28, a
        petición del usuario).

        Antes, "<cuenta> por ceco" caía a `_query_multidimensional`, que
        respeta el filtro de entidad correctamente pero regresa TODOS los
        CECOs sin ordenar (miles de filas) — sirve para exportar, no para
        responder "cuál es el que más gasta" de un vistazo. Aquí se agrupa
        igual que `_query_top_desviaciones` pero se ordena por Real_2026
        descendente y no se exige Plan_2026 > 0 (un CECO puede tener gasto
        real sin presupuesto asignado y aun así ser relevante para esta
        pregunta).
        """
        s_ini, s_fin = nlu["semanas"]["inicio"], nlu["semanas"]["fin"]
        filt_clause, params = self._construir_filtros_entidad(nlu)

        agrupar_pdv = nlu.get("agrupar_variacion_por") == "pdv" and self.tiene_eco_pdv
        if agrupar_pdv:
            entidad_col, entidad_alias = "ECO_PDV", "PDV"
            where_entidad = "AND ECO_PDV IS NOT NULL AND ECO_PDV != 0"
        else:
            entidad_col, entidad_alias = "ID_CENTRO_COSTOS", "CECO"
            where_entidad = "AND ID_CENTRO_COSTOS IS NOT NULL"

        sql = f"""
            SELECT
                {entidad_col} AS {entidad_alias},
                cat_Grupo_de_Cuentas AS Grupo_Cuentas,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026
            FROM {self._fuente(nlu, {entidad_col, "cat_Grupo_de_Cuentas"})}
            WHERE sem BETWEEN {s_ini} AND {s_fin} {where_entidad} {filt_clause}
            GROUP BY 1, 2
            HAVING Real_2026 > 0
            ORDER BY Real_2026 DESC
            LIMIT {nlu['top_n']}
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No se encontró gasto para el periodo y filtros indicados.")

        total_gasto = df["Real_2026"].sum()

        tabla_res = []
        for _, r in df.iterrows():
            desv = r["Real_2026"] - r["Plan_2026"]
            pct_desv = (desv / r["Plan_2026"] * 100) if r["Plan_2026"] > 0 else None
            tabla_res.append({
                entidad_alias: r[entidad_alias],
                "Grupo_Cuentas": r["Grupo_Cuentas"],
                "Real_2026": r["Real_2026"],
                "Plan_2026": r["Plan_2026"],
                "Desviacion_Abs": desv,
                "Desviacion_Pct": round(pct_desv, 1) if pct_desv is not None else None
            })

        ent_nom = self._nombre_entidad(nlu)
        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Ranking Top {nlu['top_n']} {entidad_alias}s con Mayor Gasto",
            "titulo": f"Top {nlu['top_n']} {entidad_alias}s con Mayor Gasto ({ent_nom}, Semanas {s_ini}–{s_fin})",
            "respuesta_ejecutiva": (
                f"### 📊 Resumen Ejecutivo\n"
                f"En el periodo acumulado de la **semana {s_ini} a la {s_fin}** ({ent_nom}), los {len(df)} {entidad_alias}s "
                f"con mayor gasto suman **{M(total_gasto)}** de Real 2026.\n\n"
                f"**Mayor gasto:** {entidad_alias} **{df.iloc[0][entidad_alias]}** ({df.iloc[0]['Grupo_Cuentas']}) "
                f"con **{M(df.iloc[0]['Real_2026'])}**."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_pareto(self, nlu: dict) -> dict:
        """Pareto 80/20 del sobreconsumo. La unidad es la combinación
        CECO × Grupo de Cuentas (un mismo CECO puede aparecer en varias filas,
        una por grupo) — se dice explícito en la respuesta para no confundir
        "N combinaciones" con "N CECOs". 2026-09-29: antes ignoraba los
        filtros de entidad ("pareto de division norte" daba el global) y
        regresaba miles de filas."""
        s_ini, s_fin = nlu["semanas"]["inicio"], nlu["semanas"]["fin"]
        filt_clause, params = self._construir_filtros_entidad(nlu)
        sql = f"""
            WITH ceco_desv AS (
                SELECT
                    ID_CENTRO_COSTOS AS CECO,
                    cat_Grupo_de_Cuentas AS Grupo,
                    SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Desv
                FROM {self._fuente(nlu, {"ID_CENTRO_COSTOS", "cat_Grupo_de_Cuentas"})}
                WHERE sem BETWEEN {s_ini} AND {s_fin} AND ID_CENTRO_COSTOS IS NOT NULL {filt_clause}
                GROUP BY 1, 2
                HAVING Desv > 0
            )
            SELECT CECO, Grupo, Desv FROM ceco_desv ORDER BY Desv DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No hay sobreconsumo en el periodo analizado.")

        total_sobregasto = df["Desv"].sum()
        df["Acumulado"] = df["Desv"].cumsum()
        df["Pct_Acumulado"] = (df["Acumulado"] / total_sobregasto) * 100

        # Combinaciones hasta cruzar el 80% (incluida la que lo cruza).
        n_80 = int((df["Pct_Acumulado"] < 80).sum()) + 1
        df_80 = df.head(min(n_80, len(df))).copy()

        num_cecos_80 = len(df_80)
        pct_cecos = (num_cecos_80 / len(df)) * 100
        n_cecos_distintos = df_80["CECO"].nunique()
        ent_nom = self._nombre_entidad(nlu)

        tabla_res = []
        for _, r in df_80.head(50).iterrows():
            tabla_res.append({
                "CECO": r["CECO"],
                "Grupo": r["Grupo"],
                "Sobreconsumo_MDP": r["Desv"],
                "Acumulado_MDP": r["Acumulado"],
                "Pct_Acum_Total": round(r["Pct_Acumulado"], 1)
            })

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Análisis de Pareto 80/20 de Sobreconsumo",
            "titulo": f"Análisis de Pareto ({ent_nom}, 80% del Sobregasto Acumulado en Semanas {s_ini}–{s_fin})",
            "respuesta_ejecutiva": (
                f"### 📈 Ley de Pareto (80/20) Aplicada al Gasto ({ent_nom})\n"
                f"La unidad analizada es **CECO × Grupo de Cuentas**. De {len(df):,} combinaciones con sobregasto "
                f"(suma **{M(total_sobregasto)}**), **{num_cecos_80:,}** ({pct_cecos:.1f}%) explican el **80%**, "
                f"equivalente a **{M(df_80['Desv'].sum())}**; corresponden a **{n_cecos_distintos:,} CECOs distintos**.\n\n"
                f"Se muestran las primeras {min(50, num_cecos_80)} combinaciones. "
                f"**Acción recomendada:** revisar primero estas combinaciones con sus responsables."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df_80),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_consulta_estandar(self, raw_query: str, nlu: dict) -> dict:
        grupo = nlu.get("grupo_cuentas")
        s_ini, s_fin = nlu["semanas"]["inicio"], nlu["semanas"]["fin"]

        filt_extra, params_extra = self._construir_filtros_entidad(nlu)
        filt_clause = " WHERE sem BETWEEN ? AND ?" + filt_extra
        params = [s_ini, s_fin] + params_extra

        sql = f"""
            SELECT 
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025
            FROM {self._fuente(nlu)}
            {filt_clause}
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        res = cur.fetchone()
        if not res:
            r26, p26, r25 = 0.0, 0.0, 0.0
        else:
            r26, p26, r25 = (res[0] or 0.0), (res[1] or 0.0), (res[2] or 0.0)
        diff_plan = r26 - p26
        pct_plan = ((diff_plan / p26) * 100) if p26 > 0 else 0

        col_group = "cat_Cuentas" if grupo else "cat_Grupo_de_Cuentas"
        sql_det = f"""
            SELECT 
                {col_group} AS Concepto,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Desviacion_MDP
            FROM {self._fuente(nlu, {col_group})}
            {filt_clause}
            GROUP BY 1
            ORDER BY Desviacion_MDP DESC
        """
        cur_det, _, _ = self._exec_sql(sql_det, params)
        df_det = self._fetch_df_arrow(cur_det)
        tabla_res = df_det.to_dict(orient="records") if not df_det.empty else []

        entidad = self._nombre_entidad(nlu)
        eval_gasto = "Desfavorable (Sobreconsumo) 🔴" if diff_plan > 0 else ("Favorable (Ahorro) 🟢" if diff_plan < 0 else "En Presupuesto ⚪")

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Consulta Financiera Estructurada",
            "titulo": f"Resumen Financiero: {entidad} (Sem {s_ini}–{s_fin})",
            "respuesta_ejecutiva": (
                f"### 💼 Resumen Ejecutivo ({entidad})\n"
                f"- **Real 2026:** {M(r26)}\n"
                f"- **Plan 2026:** {M(p26)}\n"
                f"- **Real 2025:** {M(r25)}\n"
                f"- **Variación vs Plan:** **{M(diff_plan)}** ({pct_plan:+.1f}%) — **{eval_gasto}**\n\n"
                f"*(Nota: Cifras consolidadas en millones de pesos de la semana {s_ini} a la {s_fin})*"
            ),
            "real_2026_mdp": r26 / 1e6,
            "plan_2026_mdp": p26 / 1e6,
            "real_2025_mdp": r25 / 1e6,
            "vs_plan_mdp": diff_plan / 1e6,
            "tabla": tabla_res,
            "filtros_interpretados": {"entidad": entidad, "semanas": f"{s_ini}–{s_fin}"},
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df_det),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }
