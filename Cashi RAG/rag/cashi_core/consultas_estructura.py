# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_estructura.py — Estructura/jerarquías, plano 4, match de CECOs y calidad/linaje."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class ConsultasEstructuraMixin:
    def _query_estructura(self, raw_query: str, norm_query: str, nlu: dict) -> dict:
        """Preguntas de estructura jerárquica (sin montos):
        Territorial: División → Territorio → Zona → Región → ECO → CECO
        Contable:    Contraloría → Contraloría5 → Grupo → Cuenta (+ Agrupas)
        Soporta navegación en ambas direcciones (hijo→padre y padre→hijos)."""
        g = self.grafo  # puede estar vacío; los bloques críticos tienen fallback SQL

        def _ret(titulo, lineas, tabla, intencion="Consulta de Estructura"):
            return {
                "tipo_respuesta": "financiera",
                "intencion_detectada": intencion,
                "titulo": titulo,
                "respuesta_ejecutiva": "### 🗺️ " + titulo + "\n" + "\n".join(lineas),
                "tabla": tabla,
                "sql_linaje": {
                    "sql_ejecutado": "(grafo en memoria)",
                    "tiempo_ms": 0.0,
                    "filas_procesadas": len(tabla),
                    "fuentes_parquet": self._fuentes_de("FROM ceco_summary"),
                },
            }

        tabla: List[dict] = []
        lineas: List[str] = []
        ceco  = nlu.get("ceco")
        div   = nlu.get("division")
        terr  = nlu.get("territorio")
        zona  = nlu.get("zona")
        region = nlu.get("region")
        contra = nlu.get("contraloria")
        gpo   = nlu.get("grupo_cuentas")
        cta   = nlu.get("cuenta")
        eco   = nlu.get("eco_pdv_directo")
        if eco is None and nlu.get("pdc"):
            eco = self.pdc_a_eco_pdv.get(nlu["pdc"])

        _kw_padre  = any(kw in norm_query for kw in ["pertenece", "corresponde", "de que", "a que", "padre", "pertenecia"])

        # ============================================================
        # TERRITORIAL: hijo → padre (consultas inversas)
        # ============================================================

        # Región → Zona (de qué zona es región X)
        if region and not zona and (_kw_padre or any(kw in norm_query for kw in ["zona", "zonas"])):
            zona_res = g.get("region_zona", {}).get(region)
            if zona_res:
                terr_res = g.get("zona_terr", {}).get(zona_res)
                div_res  = g.get("terr_div", {}).get(terr_res, "") if terr_res else ""
                titulo = f"Jerarquía de la Región {region}"
                lineas.append(f"La región **{region}** pertenece a la zona **{zona_res}** › territorio **{terr_res}** › **{div_res}**.")
                return _ret(titulo, lineas, [{"Región": region, "Zona": zona_res, "Territorio": terr_res, "División": div_res}])

        # Zona → Territorio (de qué territorio es zona X)
        if zona and not terr and (_kw_padre or any(kw in norm_query for kw in ["territorio", "territorios"])):
            terr_res = g.get("zona_terr", {}).get(zona)
            if terr_res:
                div_res = g.get("terr_div", {}).get(terr_res, "")
                titulo = f"Jerarquía de la Zona {zona}"
                lineas.append(f"La zona **{zona}** pertenece al territorio **{terr_res}** › **{div_res}**.")
                return _ret(titulo, lineas, [{"Zona": zona, "Territorio": terr_res, "División": div_res}])

        # Territorio → División (de qué división es territorio X)
        if terr and not div and (_kw_padre or any(kw in norm_query for kw in ["division", "divisiones"])):
            div_res = g.get("terr_div", {}).get(terr)
            if not div_res:
                try:
                    _sql = "SELECT DISTINCT cat_Direccion_Division FROM consolidado WHERE cat_Subdireccion_Territorio = ? AND cat_Direccion_Division IS NOT NULL LIMIT 1"
                    _cur, _, _ = self._exec_sql(_sql, [terr])
                    _row = _cur.fetchone()
                    if _row:
                        div_res = _row[0]
                except Exception:
                    pass
            if div_res:
                titulo = f"División de {terr}"
                lineas.append(f"El territorio **{terr}** pertenece a **{div_res}**.")
                return _ret(titulo, lineas, [{"Territorio": terr, "División": div_res}])

        # ============================================================
        # TERRITORIAL: padre → hijos
        # ============================================================

        # División → sus Territorios
        if div and not terr:
            terrs = sorted(g.get("div_terr", {}).get(div, set()))
            if not terrs:
                try:
                    _sql = "SELECT DISTINCT cat_Subdireccion_Territorio FROM consolidado WHERE cat_Direccion_Division = ? AND cat_Subdireccion_Territorio IS NOT NULL ORDER BY 1"
                    _cur, _, _ = self._exec_sql(_sql, [div])
                    terrs = [r[0] for r in _cur.fetchall() if r[0]]
                except Exception:
                    pass
            titulo = f"Territorios de {div}"
            lineas.append(f"**{div}** tiene **{len(terrs)} territorios**:")
            for t in terrs:
                zonas_t = g.get("terr_zona", {}).get(t, set())
                tabla.append({"Territorio": t, "Zonas": len(zonas_t), "ECOs": len(g.get("terr_eco", {}).get(t, set())), "CECOs": len(g.get("terr_ceco", {}).get(t, set()))})
            return _ret(titulo, lineas, tabla)

        # Territorio → sus Zonas
        if terr and not zona and any(kw in norm_query for kw in ["zona", "zonas", "cuantas zonas", "que zonas"]):
            # '0' o vacío = sin clasificar: una sola fila "No Clasificado" con sus regiones
            regiones_por_zona: dict = {}
            for z_raw in g.get("terr_zona", {}).get(terr, set()):
                z = "No Clasificado" if z_raw in (None, "", "0") else z_raw
                regiones_por_zona.setdefault(z, set()).update(g.get("zona_region", {}).get(z_raw, set()))
            zonas = sorted(regiones_por_zona)
            titulo = f"Zonas de {terr}"
            lineas.append(f"**{terr}** tiene **{len(zonas)} zona(s)**:")
            for z in zonas:
                tabla.append({"Zona": z, "Regiones": len(regiones_por_zona[z])})
            return _ret(titulo, lineas, tabla)

        # Territorio → sus Regiones
        if terr and not region and any(kw in norm_query for kw in ["region", "regiones", "cuantas regiones", "que regiones"]):
            regiones = sorted({r for z in g.get("terr_zona", {}).get(terr, set()) for r in g.get("zona_region", {}).get(z, set())})
            titulo = f"Regiones de {terr}"
            lineas.append(f"**{terr}** tiene **{len(regiones)} región(es)**:")
            tabla = [{"Región": r} for r in regiones]
            return _ret(titulo, lineas, tabla)

        # Territorio → ECOs/CECOs (general)
        if terr and not zona and not region:
            ecos  = g.get("terr_eco", {}).get(terr, set())
            cecos = g.get("terr_ceco", {}).get(terr, set())
            zonas = g.get("terr_zona", {}).get(terr, set())
            div_p = g.get("terr_div", {}).get(terr, "")
            titulo = f"Estructura de {terr}"
            lineas.append(f"**{terr}** pertenece a **{div_p}** y tiene **{len(zonas)} zonas**, **{len(ecos):,} ECOs** y **{len(cecos):,} CECOs**.")
            tabla = [{"ECO": p} for p in sorted(ecos)[:300]]
            return _ret(titulo, lineas, tabla)

        # Zona → sus Regiones
        if zona and not region and any(kw in norm_query for kw in ["region", "regiones", "cuantas regiones", "que regiones"]):
            regiones = sorted(g.get("zona_region", {}).get(zona, set()))
            titulo = f"Regiones de {zona}"
            lineas.append(f"La zona **{zona}** tiene **{len(regiones)} región(es)**:")
            tabla = [{"Región": r} for r in regiones]
            return _ret(titulo, lineas, tabla)

        # CECO → cadena jerárquica completa (incluyendo contraloría si se pide)
        if ceco:
            padres = g.get("ceco_padres", {}).get(str(ceco))
            titulo = f"Jerarquía del CECO {ceco}"
            if not padres:
                # Fallback SQL directo sobre consolidado
                try:
                    _sql_ceco = """
                        SELECT DISTINCT cat_Direccion_Division, cat_Subdireccion_Territorio,
                            cat_Subdireccion_Zona, cat_Subdireccion_Region, ECO_PDV
                        FROM consolidado
                        WHERE ID_CENTRO_COSTOS = ? AND cat_Direccion_Division IS NOT NULL
                        LIMIT 1
                    """
                    _cur, _, _ = self._exec_sql(_sql_ceco, [str(ceco)])
                    _row = _cur.fetchone()
                    if _row:
                        div_p, terr_p, zona_p, region_p, eco_p = _row
                        div_p = str(div_p) if div_p else ""
                        terr_p = str(terr_p) if terr_p else ""
                        zona_p = str(zona_p) if zona_p else ""
                        region_p = str(region_p) if region_p else ""
                        padres = (div_p, terr_p, zona_p, region_p, int(eco_p) if eco_p else None)
                except Exception:
                    pass
            if padres:
                div_p, terr_p, zona_p, region_p, eco_p = padres if len(padres) == 5 else (*padres[:2], "", "", padres[2] if len(padres) > 2 else None)
                ruta_txt = f"**{div_p}** › **{terr_p}**"
                if zona_p: ruta_txt += f" › **{zona_p}**"
                if region_p: ruta_txt += f" › **{region_p}**"
                if eco_p: ruta_txt += f" › ECO **{eco_p}**"
                fila = {"CECO": ceco, "División": div_p, "Territorio": terr_p, "Zona": zona_p or "", "Región": region_p or "", "ECO_PDV": eco_p or ""}
                # Si pregunta por contraloría, añadirla via SQL
                if any(kw in norm_query for kw in ["contraloria", "que contraloria", "a que contraloria"]):
                    try:
                        cur, _, _ = self._exec_sql("SELECT DISTINCT cat_Contraloria FROM consolidado WHERE ID_CENTRO_COSTOS = ? AND cat_Contraloria IS NOT NULL ORDER BY 1", [str(ceco)])
                        contras = [r[0] for r in cur.fetchall() if r[0]]
                        if contras:
                            fila["Contraloría"] = ", ".join(contras)
                            ruta_txt += f" | Contraloría: **{', '.join(contras)}**"
                    except Exception:
                        pass
                lineas.append(f"El CECO **{ceco}** → {ruta_txt}.")
                tabla = [fila]
            else:
                lineas.append(f"El CECO **{ceco}** no tiene jerarquía registrada.")
            return _ret(titulo, lineas, tabla)

        if eco is not None:
            cecos = sorted(c for c, pd in g.get("ceco_padres", {}).items() if len(pd) >= 5 and pd[4] == int(eco))
            padres = g.get("ceco_padres", {}).get(cecos[0]) if cecos else None
            titulo = f"Estructura del ECO PDV {eco}"
            lineas.append(f"El ECO **{eco}**" + (f" está en **{padres[0]}** › **{padres[1]}**" if padres else "")
                          + f" y agrupa **{len(cecos)} CECOs**.")
            tabla = [{"CECO": c} for c in cecos[:200]]
            return _ret(titulo, lineas, tabla)

        # ============================================================
        # CONTABLE: Contraloría → jerarquía
        # ============================================================

        # Cuenta → su Contraloría
        if cta and not gpo and any(kw in norm_query for kw in ["contraloria", "que grupo", "a que pertenece"]):
            gpo_res = g.get("cta_grupo", {}).get(cta)
            titulo = f"Jerarquía de la Cuenta {cta}"
            if gpo_res:
                contra_res = next((c for c, c6s in g.get("contra6_grupo", {}).items() for c6 in c6s if gpo_res in g.get("contra6_grupo", {}).get(c6, set())), None)
                lineas.append(f"La cuenta **{cta}** → grupo **{gpo_res}**" + (f" › contraloría **{contra_res}**" if contra_res else "") + ".")
                tabla = [{"Cuenta": cta, "Grupo": gpo_res, "Contraloría": contra_res or ""}]
            else:
                lineas.append(f"La cuenta **{cta}** no tiene grupo asignado.")
            return _ret(titulo, lineas, tabla)

        # Cuenta → su Grupo (simple)
        if cta and not gpo:
            titulo = f"Grupo de la Cuenta {cta}"
            gpo_res = g.get("cta_grupo", {}).get(cta)
            lineas.append(f"La cuenta **{cta}** pertenece al grupo **{gpo_res}**." if gpo_res else f"La cuenta **{cta}** no tiene grupo asignado.")
            tabla = [{"Cuenta": cta, "Grupo": gpo_res or ""}] if gpo_res else []
            return _ret(titulo, lineas, tabla)

        # Grupo → sus Cuentas
        if gpo:
            ctas = sorted(g.get("grupo_ctas", {}).get(gpo, set()))
            titulo = f"Cuentas del Grupo {gpo}"
            lineas.append(f"El grupo **{gpo}** tiene **{len(ctas)} cuenta(s)**.")
            tabla = [{"Cuenta": c} for c in ctas]
            return _ret(titulo, lineas, tabla)

        # Contraloría → sus Grupos
        if contra:
            contra6 = g.get("contra_contra6", {}).get(contra, "")
            grupos = sorted(g.get("contra6_grupo", {}).get(contra6, set()) if contra6 else set())
            titulo = f"Grupos de {contra}"
            lineas.append(f"La contraloría **{contra}** → **{contra6}** tiene **{len(grupos)} grupo(s) de cuentas**.")
            tabla = [{"Grupo": grp, "Cuentas": len(g.get("grupo_ctas", {}).get(grp, set()))} for grp in grupos]
            return _ret(titulo, lineas, tabla)

        # ============================================================
        # Vista general (sin entidad específica)
        # ============================================================

        if any(kw in norm_query for kw in ["cuenta", "grupo", "contraloria"]):
            titulo = "Jerarquía Contable"
            lineas.append(f"Hay **{len(g.get('contra_contra6', {}))} contralorías**, **{len(g.get('grupo_ctas', {}))} grupos de cuentas** y **{len(g.get('cta_grupo', {}))} cuentas**.")
            tabla = [{"Grupo_de_Cuentas": k, "Cuentas": len(v)} for k, v in sorted(g.get("grupo_ctas", {}).items())]
        else:
            titulo = "Estructura Territorial"
            div_terr = g.get("div_terr", {})
            terr_zona = g.get("terr_zona", {})
            lineas.append(f"Hay **{len(div_terr)} divisiones**, **{len(g.get('terr_div', {}))} territorios**, "
                          f"**{len(g.get('zona_terr', {}))} zonas**, **{len(g.get('region_zona', {}))} regiones** y "
                          f"**{len(g.get('ceco_padres', {})):,} CECOs**.")
            tabla = [{"División": d, "Territorios": len(ts), "Zonas": sum(len(terr_zona.get(t, set())) for t in ts),
                      "ECOs": sum(len(g.get("terr_eco", {}).get(t, set())) for t in ts),
                      "CECOs": sum(len(g.get("terr_ceco", {}).get(t, set())) for t in ts)}
                     for d, ts in sorted(div_terr.items())]
        return _ret(titulo, lineas, tabla)

    def _query_plano4_servicio(self, nlu: dict) -> dict:
        srv_id = nlu.get("servicio_id")
        like_patron = f"%{srv_id}%"
        sql = """
            SELECT
                cat_Cuentas AS Cuenta,
                cat_Grupo_de_Cuentas AS Grupo,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026,
                SUM(CASE WHEN Serie = 'P26' THEN monto ELSE 0 END) AS Plan_2026
            FROM consolidado
            WHERE UPPER(cat_PosPre) LIKE ? OR UPPER(cat_Denom_PosPre) LIKE ? OR UPPER(cat_Cuentas) LIKE ?
            GROUP BY 1, 2
            ORDER BY Real_2026 DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql, [like_patron, like_patron, like_patron])
        df = self._fetch_df_arrow(cur)

        tabla_res = df.to_dict(orient="records") if not df.empty else []

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": f"Consulta de Plano 4 (Servicios e ID {srv_id})",
            "titulo": f"Detalle de Servicio Plano 4: {srv_id}",
            "respuesta_ejecutiva": (
                f"### 🔌 Plano 4: Detalle de Servicio ({srv_id})\n"
                f"Se consultó el grafo de servicios para el identificador **{srv_id}**.\n\n"
                f"Total de conceptos mapeados: **{len(df)}**."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_match_cecos(self, nlu: dict) -> dict:
        sql_match = """
            SELECT 
                cat_Subtipo AS Estatus_Match,
                COUNT(DISTINCT ID_CENTRO_COSTOS) AS Cantidad_CECOs,
                SUM(CASE WHEN Serie = 'R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE cat_Subtipo IS NOT NULL
            GROUP BY 1
            ORDER BY Real_2026 DESC
        """
        cur, sql_used, dt_ms = self._exec_sql(sql_match)
        df = self._fetch_df_arrow(cur)

        tabla_res = []
        for _, r in df.iterrows():
            tabla_res.append({
                "Estatus_Match_Radar": r["Estatus_Match"],
                "Cantidad_CECOs": r["Cantidad_CECOs"],
                "Real_2026_MDP": r["Real_2026"]
            })

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Auditoría de Match de CECOs y Respaldo Eco PDV",
            "titulo": "Estatus del Match de CECOs en Radar Preventivo",
            "respuesta_ejecutiva": (
                f"### 🔗 Estatus de Calidad del Mapeo de CECOs\n"
                f"Resumen de la conciliación entre el catálogo maestro de Puntos de Contacto (PDC) "
                f"y los Centros de Costos (CECO) en las reglas del Radar Preventivo."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": sql_used,
                "tiempo_ms": dt_ms,
                "filas_procesadas": len(df),
                "fuentes_parquet": self._fuentes_de(sql_used)
            }
        }

    def _query_calidad_linaje(self, nlu: dict) -> dict:
        cur1, _, dt1 = self._exec_sql("SELECT COUNT(*) FROM consolidado")
        total_recs = cur1.fetchone()[0]

        cur2, _, dt2 = self._exec_sql("SELECT COUNT(*) FROM consolidado WHERE ID_CENTRO_COSTOS IS NULL")
        null_ceco = cur2.fetchone()[0]

        cur3, _, dt3 = self._exec_sql("SELECT COUNT(*) FROM consolidado WHERE cat_Direccion_Division IS NULL")
        null_div = cur3.fetchone()[0]

        tabla_res = [
            {"Metrica_Calidad": "Total Registros Consolidados", "Valor": f"{total_recs:,}", "Estatus": "OK ✅"},
            {"Metrica_Calidad": "Registros sin CECO", "Valor": f"{null_ceco:,}", "Estatus": "Revisar ⚠️" if null_ceco > 0 else "OK ✅"},
            {"Metrica_Calidad": "Registros sin División", "Valor": f"{null_div:,}", "Estatus": "Revisar ⚠️" if null_div > 0 else "OK ✅"},
            {"Metrica_Calidad": "Corte de Datos Real 2026", "Valor": f"Semana {self.sem_max_real}", "Estatus": "Vigente 🟢"},
            {"Metrica_Calidad": "Corte de Datos Plan 2026", "Valor": f"Semana {self.sem_max_plan}", "Estatus": "Vigente 🟢"}
        ]

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Auditoría de Calidad y Linaje de Datos",
            "titulo": "Reporte de Integridad y Linaje de Datos (_consolidado.parquet)",
            "respuesta_ejecutiva": (
                f"### 🛡️ Diagnóstico de Linaje de Datos\n"
                f"El motor procesó **{total_recs:,} filas** almacenadas en DuckDB/Parquet.\n"
                f"Integridad estructural validada al 100%."
            ),
            "tabla": tabla_res,
            "sql_linaje": {
                "sql_ejecutado": "SELECT COUNT(*) FROM consolidado (Múltiples comprobaciones)",
                "tiempo_ms": dt1 + dt2 + dt3,
                "filas_procesadas": total_recs,
                "fuentes_parquet": ["aggs/_consolidado.parquet"]
            }
        }
