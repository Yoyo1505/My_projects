# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_variacion.py — Consultas de variación: marco general, top desviaciones, variación vs plan."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class ConsultasVariacionMixin:
    def _query_variacion_general(self, nlu: dict) -> dict:
        """Variación de Real 2026 contra una referencia (Plan 2026 o Real 2025), total o
        ranking por cualquier dimensión del catálogo.

        Marco (ver _parse_nlu): var_ref = 'plan' | 'aa'; var_dir = 'ahorro' | 'sobregasto'
        | None (solo variación, ordena por magnitud absoluta); var_dim = dimensión del
        ranking o None (total con los filtros de la pregunta); var_rank = hay top N.
        """
        s_ini, s_fin = nlu["semanas"]["inicio"], nlu["semanas"]["fin"]
        filt_clause, params = self._construir_filtros_entidad(nlu)

        ref_serie = "P26" if nlu.get("var_ref") == "plan" else "R25"
        ref_label = "Plan 2026" if nlu.get("var_ref") == "plan" else "Real 2025"
        r26 = "SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END)"
        ref = f"SUM(CASE WHEN Serie = '{ref_serie}' THEN monto ELSE 0 END)"
        desv = f"({r26} - {ref})"

        dim = nlu.get("var_dim")
        if dim == "pdc" and not self.tiene_eco_pdv:
            dim = None
        if dim and nlu.get("var_rank"):
            col_expr, alias, where_dim = VAR_DIM_COLUMNAS[dim]
            fuente = self._fuente(nlu, set(re.findall(r"\b(?:cat_|ID_|ECO_)\w+", col_expr)))
            select = f"{col_expr} AS {alias}"
            group = "GROUP BY 1"
            where = f"WHERE sem BETWEEN {s_ini} AND {s_fin} {where_dim} {filt_clause}"
        else:
            alias = None
            fuente = self._fuente(nlu, set())
            select = "'Total' AS Concepto"
            group = ""
            where = f"WHERE sem BETWEEN {s_ini} AND {s_fin} {filt_clause}"

        having = f"HAVING {ref} <> 0"
        if nlu.get("var_dir") == "ahorro":
            having += f" AND {desv} < 0"
        elif nlu.get("var_dir") == "sobregasto":
            having += f" AND {desv} > 0"
        if nlu.get("var_dir") == "ahorro":
            orden = "Desviacion_Abs ASC"
        elif nlu.get("var_dir") == "sobregasto" or not nlu.get("var_rank"):
            orden = "Desviacion_Abs DESC" if nlu.get("var_dir") == "sobregasto" else "ABS(Desviacion_Abs) DESC"
        else:
            orden = "ABS(Desviacion_Abs) DESC"
        limite = f"LIMIT {nlu['top_n']}" if group else ""

        sql = f"""
            SELECT {select},
                {r26} AS Real_2026,
                {ref} AS Referencia,
                {desv} AS Desviacion_Abs
            FROM {fuente}
            {where}
            {group}
            {having if group else ""}
            ORDER BY {orden}
            {limite}
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No hay datos de variación para el periodo y filtros indicados.")

        # El sobregasto también es una variación; solo el ahorro cambia el título.
        sentido = "Ahorro" if nlu.get("var_dir") == "ahorro" else "Variación"
        ent_nom = self._nombre_entidad(nlu)
        tabla = []
        for _, r in df.iterrows():
            ref_v = float(r["Referencia"])
            d = float(r["Desviacion_Abs"])
            fila = {alias or "Concepto": r[alias or "Concepto"], "Real_2026": r["Real_2026"],
                    ref_label: ref_v, "Desviacion_Abs": d,
                    "Desviacion_Pct": round(d / abs(ref_v) * 100, 1) if ref_v else 0.0}
            tabla.append(fila)

        if group:
            intencion = f"Ranking Top {len(df)} {alias}s con Mayor {sentido} vs {ref_label}"
            titulo = f"Top {len(df)} {alias}s por {sentido} vs {ref_label} ({ent_nom}, Semanas {s_ini}–{s_fin})"
            resumen = (f"Los {len(df)} {alias}s con mayor {sentido.lower()} vs {ref_label} suman "
                       f"**{M(float(df['Desviacion_Abs'].sum()))}**. Primero: **{df.iloc[0][alias]}** "
                       f"con **{M(float(df.iloc[0]['Desviacion_Abs']))}**.")
        else:
            d_total = float(df["Desviacion_Abs"].iloc[0])
            intencion = f"Variación Total vs {ref_label}"
            titulo = f"Variación vs {ref_label} ({ent_nom}, Semanas {s_ini}–{s_fin})"
            resumen = f"Real 2026 vs {ref_label}: **{M(d_total)}** ({float(df['Desviacion_Abs'].iloc[0]) / abs(float(df['Referencia'].iloc[0])) * 100 if float(df['Referencia'].iloc[0]) else 0:+.1f}%)."

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": intencion,
            "titulo": titulo,
            "respuesta_ejecutiva": f"### 📊 Variación\n{resumen}",
            "tabla": tabla,
            "sql_linaje": {"sql_ejecutado": sql_used, "tiempo_ms": dt_ms, "filas_procesadas": len(df)},
        }

    def _query_top_desviaciones(self, nlu: dict) -> dict:
        """Ranking de mayor variación/sobreconsumo vs Plan.

        Respeta los filtros de entidad de la consulta (territorio, división,
        cuenta, etc. — antes ignorados por completo, siempre global) y agrupa
        por PDV (ECO_PDV) en vez de CECO cuando la pregunta lo pide
        explícitamente ("Que PDV de <territorio> tuvo mas variacion en
        <cuenta>?" — patrón confirmado en calibración 2026-08-31, scoring 4-5
        una vez enrutado aquí en vez de a la consulta estándar de un solo
        agregado).
        """
        s_ini, s_fin = nlu["semanas"]["inicio"], nlu["semanas"]["fin"]
        filt_clause, params = self._construir_filtros_entidad(nlu)

        agrupar = nlu.get("agrupar_variacion_por")
        if agrupar == "cuenta":
            # Ranking por cuenta: cada cuenta con su grupo (una cuenta pertenece a un solo grupo)
            entidad_col, entidad_alias = "cat_Cuentas", "Cuenta"
            where_entidad = "AND cat_Cuentas IS NOT NULL AND cat_Cuentas != '0'"
        elif agrupar == "pdv" and self.tiene_eco_pdv:
            entidad_col, entidad_alias = "ECO_PDV", "PDV"
            where_entidad = "AND ECO_PDV IS NOT NULL AND ECO_PDV != 0"
        else:
            entidad_col, entidad_alias = "ID_CENTRO_COSTOS", "CECO"
            where_entidad = "AND ID_CENTRO_COSTOS IS NOT NULL"

        # Sin grupo pedido, el ranking es por entidad total, no por entidad x grupo
        # (salvo en cuentas, donde el grupo es el de la propia cuenta).
        if agrupar == "cuenta":
            grupo_expr, cols_fuente = "cat_Grupo_de_Cuentas", {entidad_col, "cat_Grupo_de_Cuentas"}
        elif nlu.get("grupo_cuentas"):
            grupo_expr, cols_fuente = "cat_Grupo_de_Cuentas", {entidad_col, "cat_Grupo_de_Cuentas"}
        else:
            grupo_expr, cols_fuente = "'Todos los grupos'", {entidad_col}
        desv = "(SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) - SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END))"
        having_extra = ""
        if nlu.get("solo_sobregasto_real"):
            having_extra = f"AND {desv} > 0"
        elif nlu.get("solo_ahorro_real"):
            having_extra = f"AND {desv} < 0"
        orden = "ABS(Desviacion_Abs)" if nlu.get("orden_variacion_absoluta") else "Desviacion_Abs"
        sentido = "ASC" if nlu.get("orden_ascendente") else "DESC"
        sql = f"""
            SELECT
                {entidad_col} AS {entidad_alias},
                {grupo_expr} AS Grupo_Cuentas,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026,
                {desv} AS Desviacion_Abs
            FROM {self._fuente(nlu, cols_fuente)}
            WHERE sem BETWEEN {s_ini} AND {s_fin} {where_entidad} {filt_clause}
            GROUP BY 1, 2
            HAVING Plan_2026 > 0 {having_extra}
            ORDER BY {orden} {sentido}
            LIMIT {nlu['top_n']}
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, params)
        df = self._fetch_df_arrow(cur)
        if df.empty:
            return self._respuesta_sin_datos("No se encontraron desviaciones para el periodo y filtros indicados.")

        total_desv = df["Desviacion_Abs"].sum()

        tabla_res = []
        for _, r in df.iterrows():
            pct = (r["Desviacion_Abs"] / r["Plan_2026"] * 100) if r["Plan_2026"] > 0 else 0
            tabla_res.append({
                entidad_alias: r[entidad_alias],
                "Grupo_Cuentas": r["Grupo_Cuentas"],
                "Real_2026": r["Real_2026"],
                "Plan_2026": r["Plan_2026"],
                "Desviacion_Abs": r["Desviacion_Abs"],
                "Desviacion_Pct": round(pct, 1)
            })

        ent_nom = self._nombre_entidad(nlu)
        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Ranking Top {nlu['top_n']} {entidad_alias}s con Mayor "
                                   f"{'Ahorro' if nlu.get('orden_ascendente') else 'Variación'} vs Plan",
            "titulo": f"Top {nlu['top_n']} Variaciones por {entidad_alias} ({ent_nom}, Semanas {s_ini}–{s_fin})",
            "respuesta_ejecutiva": (
                f"### 📊 Resumen Ejecutivo\n"
                f"En el periodo acumulado de la **semana {s_ini} a la {s_fin}** ({ent_nom}), los {len(df)} {entidad_alias}s con mayor variación "
                f"suman una desviación combinada de **{M(total_desv)}** respecto al Plan 2026.\n\n"
                f"**Principales hallazgos:**\n"
                f"- La mayor variación se concentra en **{entidad_alias} {df.iloc[0][entidad_alias]}** ({df.iloc[0]['Grupo_Cuentas']}) "
                f"con **{M(df.iloc[0]['Desviacion_Abs'])}** respecto a su presupuesto.\n"
                f"- **Acción recomendada:** Revisar justificación operativa con los responsables de cada {entidad_alias}."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_variacion_ppto(self, nlu: dict) -> dict:
        """Queries de variación entre dos métricas de Presupuesto 2027.
        Ej: 'variación SIE vs CONTA', 'SIE vs Comparabilidad por grupo'.
        Retorna 4 columnas: metrica_A, metrica_B, variación absoluta, variación %.
        Solo muestra filas donde ambas métricas tienen valor != 0."""
        from dash_app.services.ppto2027_service import cargar_agregados_ppto

        _COL_LABEL = {
            "Reglas_2026": "SIE",
            "Ordinario_2026": "CONTA",
            "Ppto_2026": "COMPARABILIDAD",
            "Fcst_Oficial_2026": "FCST",
        }

        metricas = nlu.get("metricas_variacion", [])
        if len(metricas) < 2:
            return self._respuesta_sin_datos("Necesito dos métricas para comparar (SIE, CONTA, COMPARABILIDAD, FCST).")

        col_a, col_b = metricas[0], metricas[1]
        lbl_a, lbl_b = _COL_LABEL.get(col_a, col_a), _COL_LABEL.get(col_b, col_b)

        try:
            df = cargar_agregados_ppto()
        except Exception as e:
            return self._respuesta_sin_datos(f"No se pudo cargar el Presupuesto 2027: {e}")

        # Determinar dimensión de agrupación según entidades detectadas
        grupo_cuentas = nlu.get("grupo_cuentas")
        cuenta = nlu.get("cuenta")
        ceco = nlu.get("ceco")
        dims_sol = nlu.get("dims_solicitadas", [])

        if cuenta or "cuenta" in dims_sol:
            dim_col, dim_lbl = "Cuentas", "Cuenta"
        elif grupo_cuentas or "grupo_cuentas" in dims_sol:
            dim_col, dim_lbl = "GrupoCuenta", "Grupo de Cuentas"
        elif ceco or "ceco" in dims_sol:
            dim_col, dim_lbl = "CECO_N7", "CECO"
        else:
            dim_col, dim_lbl = "GrupoCuenta", "Grupo de Cuentas"  # default

        # Filtrar por entidad si la hay
        if grupo_cuentas and dim_col != "GrupoCuenta":
            gpo_norm = normalizar_texto(grupo_cuentas)
            mask = df["GrupoCuenta"].apply(lambda x: normalizar_texto(str(x)) == gpo_norm if pd.notna(x) else False)
            df = df[mask]
        if cuenta and dim_col != "Cuentas":
            cta_norm = normalizar_texto(cuenta)
            mask = df["Cuentas"].apply(lambda x: normalizar_texto(str(x)) == cta_norm if pd.notna(x) else False)
            df = df[mask]
        if ceco:
            mask = df["CECO_N7"].apply(lambda x: str(x).lstrip("0") == str(ceco).lstrip("0") if pd.notna(x) else False)
            df = df[mask]

        # Agrupar
        cols_agg = {col_a: "sum", col_b: "sum"}
        if dim_col in df.columns:
            agg = df.groupby(dim_col, dropna=True).agg(cols_agg).reset_index()
        else:
            agg = df.agg(cols_agg).to_frame().T
            agg[dim_col] = "Total"

        # Solo filas donde ambas métricas tienen valor
        agg = agg[(agg[col_a] != 0) | (agg[col_b] != 0)]

        # Calcular variación
        MDP = 1_000_000
        tabla = []
        for _, row in agg.iterrows():
            va, vb = row[col_a], row[col_b]
            diff = va - vb
            pct = (diff / abs(vb) * 100) if vb and vb != 0 else None
            tabla.append({
                dim_lbl: row[dim_col],
                lbl_a: round(va / MDP, 2),
                lbl_b: round(vb / MDP, 2),
                f"{lbl_a} vs {lbl_b} (MDP)": round(diff / MDP, 2),
                f"{lbl_a} vs {lbl_b} (%)": round(pct, 1) if pct is not None else None,
            })
        tabla.sort(key=lambda x: abs(x.get(f"{lbl_a} vs {lbl_b} (MDP)", 0) or 0), reverse=True)

        titulo = f"Variación {lbl_a} vs {lbl_b} — Ppto 2027"
        total_a = sum(r[lbl_a] for r in tabla)
        total_b = sum(r[lbl_b] for r in tabla)
        total_diff = total_a - total_b
        total_pct = (total_diff / abs(total_b) * 100) if total_b else None

        exec_txt = (
            f"### 📊 {titulo}\n"
            f"**{lbl_a} Total**: {total_a:,.1f} MDP | **{lbl_b} Total**: {total_b:,.1f} MDP | "
            f"**Variación**: {total_diff:+,.1f} MDP ({total_pct:+.1f}%)\n\n"
            f"Se muestran {len(tabla)} fila(s) donde al menos una métrica tiene valor."
        )

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Variación Presupuesto 2027: {lbl_a} vs {lbl_b}",
            "titulo": titulo,
            "respuesta_ejecutiva": exec_txt,
            "tabla": tabla,
            "sql_linaje": {
                "sql_ejecutado": f"pandas groupby sobre agg_full.parquet — {lbl_a} vs {lbl_b} por {dim_lbl}",
                "tiempo_ms": 0.0,
                "filas_procesadas": len(tabla),
                "fuentes_parquet": ["aggs/ppto2027/agg_full.parquet"],
            },
        }
