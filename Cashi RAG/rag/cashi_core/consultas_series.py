# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_series.py — Series de tiempo y comparativos: tendencias, semana vs semana, R26 vs R25."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class ConsultasSeriesMixin:
    def _query_tendencia_mensual(self, nlu: dict) -> dict:
        s_ini = nlu["semanas"].get("inicio", 1)
        s_fin = nlu["semanas"].get("fin", self.sem_max_plan)

        filt_clause, params = self._construir_filtros_entidad(nlu)

        sql = f"""
            SELECT
                CASE
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
                END AS Mes,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025
            FROM {self._fuente(nlu)}
            WHERE sem BETWEEN {s_ini} AND {s_fin} {filt_clause}
            GROUP BY 1
            ORDER BY 1
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)

        if df.empty:
            return self._respuesta_sin_datos("No se encontraron datos mensuales para la consulta especificada.")

        tabla_res = []
        for _, r in df.iterrows():
            var_plan = r["Real_2026"] - r["Plan_2026"]
            tabla_res.append({
                "Mes": r["Mes"],
                "Real_2026": r["Real_2026"],
                "Plan_2026": r["Plan_2026"],
                "Real_2025": r["Real_2025"],
                "Vs_Plan_MDP": var_plan
            })

        r26_tot = df["Real_2026"].sum()
        p26_tot = df["Plan_2026"].sum()
        ent_nom = self._nombre_entidad(nlu)

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Evolución y Desglose Mensual de Gasto",
            "titulo": f"Desglose Mensual de Gasto: {ent_nom}",
            "respuesta_ejecutiva": (
                f"### 🗓️ Desglose Mensual ({ent_nom})\n"
                f"El gasto acumulado asciende a **{M(r26_tot)}** frente a un Plan de **{M(p26_tot)}** (Variación: **{M(r26_tot - p26_tot)}**).\n\n"
                f"La tabla muestra la evolución mes a mes con el cierre de semanas de cada periodo."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_tendencia_semanal(self, nlu: dict) -> dict:
        s_ini = nlu["semanas"].get("inicio", 1)
        s_fin = nlu["semanas"].get("fin", self.sem_max_real)

        filt_clause, params = self._construir_filtros_entidad(nlu)

        sql = f"""
            SELECT 
                sem AS Semana,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025
            FROM {self._fuente(nlu)}
            WHERE sem BETWEEN {s_ini} AND {s_fin} {filt_clause}
            GROUP BY sem
            ORDER BY sem
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No se encontraron datos semanales para la consulta.")

        tabla_res = []
        for _, r in df.iterrows():
            # 2026-09-17 (pedido del usuario): faltaba el % vs Plan y TODA la
            # comparación vs Año Anterior (solo había Vs_Plan_MDP absoluto) —
            # mismas 4 columnas de variación que ya usa el resto del tablero.
            var_plan = r["Real_2026"] - r["Plan_2026"]
            pct_plan = (var_plan / abs(r["Plan_2026"]) * 100) if r["Plan_2026"] else 0.0
            var_aa = r["Real_2026"] - r["Real_2025"]
            pct_aa = (var_aa / abs(r["Real_2025"]) * 100) if r["Real_2025"] else 0.0
            tabla_res.append({
                "Semana": f"Sem {int(r['Semana'])}",
                "Real_2026": r["Real_2026"],
                "Plan_2026": r["Plan_2026"],
                "Real_2025": r["Real_2025"],
                "Vs_Plan_MDP": var_plan,
                "Vs_Plan_Pct": round(pct_plan, 1),
                "Vs_AA_MDP": var_aa,
                "Vs_AA_Pct": round(pct_aa, 1),
            })

        r26_tot = df["Real_2026"].sum()
        p26_tot = df["Plan_2026"].sum()

        ent_nom = self._nombre_entidad(nlu)

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Evolución y Tendencia Semanal de Gasto",
            "titulo": f"Tendencia Semanal de Gasto: {ent_nom} (Sem {s_ini}..{s_fin})",
            "respuesta_ejecutiva": (
                f"### 📅 Evolución Semanal ({ent_nom})\n"
                f"El gasto acumulado de la **semana {s_ini} a la {s_fin}** asciende a **{M(r26_tot)}** "
                f"frente a un Plan de **{M(p26_tot)}** (Variación: **{M(r26_tot - p26_tot)}**).\n\n"
                f"Se muestra el desglose detallado semana por semana para analizar la volatilidad operativa y picos de consumo."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_semana_vs_semana(self, nlu: dict) -> dict:
        """Variación intersemanal por Grupo de Cuentas. 2026-09-17 (pedido del
        usuario): antes ignoraba por completo la entidad mencionada en la
        pregunta (ej. "cuánto cambió el gasto de nómina de la semana 10 a la
        11" mostraba TODOS los grupos en vez de filtrar a "Gastos de Nómina")
        y no traía el % que cada semana representa del total de gasto real —
        ahora aplica el mismo filtro de entidad que el resto de consultas y
        agrega Pct_Total_S1/S2 (participación de cada grupo sobre el total
        real de esa semana, sin el filtro de entidad, para dar contexto de
        "cuánto pesa" el cambio dentro del gasto total)."""
        sems = nlu["semanas"].get("semanas_especificas", [self.sem_max_real - 1, self.sem_max_real])
        s1, s2 = sems[0], sems[1]
        filt_clause, params = self._construir_filtros_entidad(nlu)

        sql = f"""
            SELECT
                cat_Grupo_de_Cuentas AS Grupo,
                SUM(CASE WHEN sem = {s1} AND Serie = 'R26' THEN monto ELSE 0 END) AS Sem_{s1},
                SUM(CASE WHEN sem = {s2} AND Serie = 'R26' THEN monto ELSE 0 END) AS Sem_{s2}
            FROM {self._fuente(nlu, {"cat_Grupo_de_Cuentas"})}
            WHERE sem IN ({s1}, {s2}) {filt_clause}
            GROUP BY 1
            ORDER BY (SUM(CASE WHEN sem = {s2} AND Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN sem = {s1} AND Serie = 'R26' THEN monto ELSE 0 END)) DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos(f"No hay datos para comparar la semana {s1} con la {s2}.")

        sql_tot = f"""
            SELECT
                SUM(CASE WHEN sem = {s1} AND Serie = 'R26' THEN monto ELSE 0 END) AS Tot_S1,
                SUM(CASE WHEN sem = {s2} AND Serie = 'R26' THEN monto ELSE 0 END) AS Tot_S2
            FROM {self._fuente({})}
            WHERE sem IN ({s1}, {s2})
        """
        cur_tot, _, _ = self._exec_sql(sql_tot)
        df_tot_global = self._fetch_df_arrow(cur_tot)
        tot_s1_global = float(df_tot_global["Tot_S1"].iloc[0]) if not df_tot_global.empty else 0.0
        tot_s2_global = float(df_tot_global["Tot_S2"].iloc[0]) if not df_tot_global.empty else 0.0

        tabla_res = []
        for _, r in df.iterrows():
            v1, v2 = r[f"Sem_{s1}"], r[f"Sem_{s2}"]
            diff = v2 - v1
            pct = ((diff / v1) * 100) if v1 > 0 else 0
            tabla_res.append({
                "Grupo_Cuentas": r["Grupo"],
                f"Sem_{s1}_MDP": v1,
                f"Sem_{s2}_MDP": v2,
                "Variacion_MDP": diff,
                "Variacion_Pct": round(pct, 1),
                f"Pct_Total_Sem_{s1}": round((v1 / tot_s1_global * 100) if tot_s1_global else 0.0, 1),
                f"Pct_Total_Sem_{s2}": round((v2 / tot_s2_global * 100) if tot_s2_global else 0.0, 1),
            })

        tot_s1 = df[f"Sem_{s1}"].sum()
        tot_s2 = df[f"Sem_{s2}"].sum()
        diff_tot = tot_s2 - tot_s1
        ent_nom = self._nombre_entidad(nlu)
        contexto_ent = f" ({ent_nom})" if ent_nom else ""

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Comparativa Semana {s1} vs Semana {s2}{contexto_ent}",
            "titulo": f"Variación Intersemanal: Semana {s1} vs Semana {s2}{contexto_ent} (Real 2026)",
            "respuesta_ejecutiva": (
                f"### 🔄 Comparación Semana {s1} vs Semana {s2}{contexto_ent}\n"
                f"- **Semana {s1}:** {M(tot_s1)}\n"
                f"- **Semana {s2}:** {M(tot_s2)}\n"
                f"- **Variación Neto:** **{M(diff_tot)}** ({((diff_tot/tot_s1)*100 if tot_s1>0 else 0):+.1f}%).\n\n"
                f"La tabla desglosa qué grupos de cuentas aceleraron o redujeron su ritmo de gasto, "
                f"y qué % representa cada uno del gasto real total de esa semana."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_ultimas_4_vs_anteriores(self, nlu: dict) -> dict:
        s_max = self.sem_max_real
        s_rec_ini, s_rec_fin = max(1, s_max - 3), s_max
        s_ant_ini, s_ant_fin = max(1, s_max - 7), max(1, s_max - 4)
        # 2026-09-29: antes ignoraba la entidad de la pregunta (siempre global).
        filt_clause, params = self._construir_filtros_entidad(nlu)

        sql = f"""
            SELECT
                cat_Grupo_de_Cuentas AS Grupo,
                SUM(CASE WHEN sem BETWEEN {s_rec_ini} AND {s_rec_fin} AND Serie = 'R26' THEN monto ELSE 0 END) AS Ultimas_4_Sems,
                SUM(CASE WHEN sem BETWEEN {s_ant_ini} AND {s_ant_fin} AND Serie = 'R26' THEN monto ELSE 0 END) AS Anteriores_4_Sems
            FROM {self._fuente(nlu, {"cat_Grupo_de_Cuentas"})}
            WHERE sem BETWEEN {s_ant_ini} AND {s_rec_fin} {filt_clause}
            GROUP BY 1
            ORDER BY (SUM(CASE WHEN sem BETWEEN {s_rec_ini} AND {s_rec_fin} AND Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN sem BETWEEN {s_ant_ini} AND {s_ant_fin} AND Serie = 'R26' THEN monto ELSE 0 END)) DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)

        tabla_res = []
        for _, r in df.iterrows():
            v_rec = r["Ultimas_4_Sems"]
            v_ant = r["Anteriores_4_Sems"]
            diff = v_rec - v_ant
            pct = ((diff / v_ant) * 100) if v_ant > 0 else 0
            tabla_res.append({
                "Grupo_Cuentas": r["Grupo"],
                f"Sems_{s_rec_ini}_a_{s_rec_fin}": v_rec,
                f"Sems_{s_ant_ini}_a_{s_ant_fin}": v_ant,
                "Diferencia_MDP": diff,
                "Variacion_Pct": round(pct, 1)
            })

        tot_rec = df["Ultimas_4_Sems"].sum()
        tot_ant = df["Anteriores_4_Sems"].sum()
        diff_tot = tot_rec - tot_ant

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Comparativa de 4 Semanas Recientes vs 4 Semanas Anteriores",
            "titulo": f"Últimas 4 Semanas (Sem {s_rec_ini}–{s_rec_fin}) vs 4 Anteriores (Sem {s_ant_ini}–{s_ant_fin}) — {self._nombre_entidad(nlu)}",
            "respuesta_ejecutiva": (
                f"### 🗓️ Análisis del Mes Reciente vs Mes Anterior ({self._nombre_entidad(nlu)})\n"
                f"- **Últimas 4 Semanas ({s_rec_ini}–{s_rec_fin}):** {M(tot_rec)}\n"
                f"- **4 Semanas Anteriores ({s_ant_ini}–{s_ant_fin}):** {M(tot_ant)}\n"
                f"- **Tendencia:** **{M(diff_tot)}** ({((diff_tot/tot_ant)*100 if tot_ant>0 else 0):+.1f}%).\n\n"
                f"Este análisis detecta cambios recientes en la velocidad de ejecución presupuestal."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_real26_vs_real25(self, nlu: dict) -> dict:
        s_fin = nlu["semanas"]["fin"]
        # 2026-09-29: antes ignoraba la entidad de la pregunta (siempre global).
        filt_clause, params = self._construir_filtros_entidad(nlu)
        sql = f"""
            SELECT
                cat_Grupo_de_Cuentas AS Grupo,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END) AS Real_2025
            FROM {self._fuente(nlu, {"cat_Grupo_de_Cuentas"})}
            WHERE sem <= {s_fin} {filt_clause}
            GROUP BY 1
            ORDER BY (SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN Serie = 'R25' THEN monto ELSE 0 END)) DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)

        tabla_res = []
        for _, r in df.iterrows():
            r26 = r["Real_2026"]
            r25 = r["Real_2025"]
            diff = r26 - r25
            pct = ((diff / r25) * 100) if r25 > 0 else 0
            tabla_res.append({
                "Grupo_Cuentas": r["Grupo"],
                f"Real_2026_Sem1_{s_fin}": r26,
                f"Real_2025_Sem1_{s_fin}": r25,
                "Crecimiento_MDP": diff,
                "Crecimiento_Pct": round(pct, 1)
            })

        tot_26 = df["Real_2026"].sum()
        tot_25 = df["Real_2025"].sum()
        diff_tot = tot_26 - tot_25

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Comparativo Real 2026 vs Real 2025 a Periodos Comparables",
            "titulo": f"Real 2026 vs Real 2025 (Acumulado a Semana {s_fin}) — {self._nombre_entidad(nlu)}",
            "respuesta_ejecutiva": (
                f"### ⚖️ Comparativa Interanual (A Semanas Iguales 1..{s_fin}, {self._nombre_entidad(nlu)})\n"
                f"- **Real 2026:** {M(tot_26)}\n"
                f"- **Real 2025:** {M(tot_25)}\n"
                f"- **Variación vs Año Anterior:** **{M(diff_tot)}** ({((diff_tot/tot_25)*100 if tot_25>0 else 0):+.1f}%).\n\n"
                f"Compara el gasto efectivamente ejercido en 2026 contra el mismo periodo del año 2025."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }
