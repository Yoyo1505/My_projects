# -*- coding: utf-8 -*-
"""rag/cashi_core/ppto2027.py — Consultas del presupuesto 2027."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class Ppto2027Mixin:
    def _es_consulta_ppto2027(self, norm_query: str) -> bool:
        return any(g in norm_query for g in self._PPTO2027_GATILLOS)

    def _mejor_valor_catalogo(self, valores: list, norm_query: str) -> Optional[str]:
        """Coincidencia simple (substring/token, ver token_match) contra un
        catálogo de texto libre — se prefiere el match más largo (más
        específico) cuando hay varios candidatos."""
        candidatos = [v for v in valores if v and token_match(normalizar_texto(str(v)), norm_query)]
        if not candidatos:
            return None
        return max(candidatos, key=lambda v: len(str(v)))

    def _responder_ppto2027(self, text: str, norm_query: str) -> dict:
        t0 = time.time()
        try:
            from dash_app.services import ppto2027_service as psvc
        except Exception as e:
            return self._respuesta_vacia(f"No se pudo cargar el módulo de Presupuesto 2027: {e}")

        # --- Filtros: intervalo de tiempo (Mes/Semana), CECO y ID_CUENTAS ---
        meses_map = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
            "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
        }
        meses = [v for k, v in meses_map.items() if k in norm_query] or None

        semana_rango = None
        m_sem_rango = re.search(r"semana\s+(\d{1,2})\s*(?:a|al|-)\s*(\d{1,2})", norm_query)
        if m_sem_rango:
            semana_rango = (int(m_sem_rango.group(1)), int(m_sem_rango.group(2)))
        else:
            m_sem = re.search(r"semana\s+(\d{1,2})\b", norm_query)
            if m_sem:
                semana_rango = (int(m_sem.group(1)), int(m_sem.group(1)))

        cecos_op = sorted(set(psvc.opciones("CECO_N7")) | set(psvc.opciones("CECO_N8")))
        ceco_match = self._mejor_valor_catalogo(cecos_op, norm_query)
        cecos = [ceco_match] if ceco_match else None

        cuenta_match = self._mejor_valor_catalogo(psvc.opciones("Cuentas"), norm_query)
        cuentas = [cuenta_match] if cuenta_match else None

        filtros = {"meses": meses, "semana_rango": semana_rango, "cecos": cecos, "cuentas": cuentas}

        try:
            kpis = psvc.kpis_resumen(**filtros)
        except Exception as e:
            return self._respuesta_vacia(f"Error al consultar Presupuesto 2027: {e}")

        dt_ms = round((time.time() - t0) * 1000, 1)

        etiquetas_filtro = []
        if meses:
            etiquetas_filtro.append(f"Mes(es) {', '.join(str(m) for m in meses)}")
        if semana_rango:
            etiquetas_filtro.append(f"Semana {semana_rango[0]}" if semana_rango[0] == semana_rango[1]
                                     else f"Semanas {semana_rango[0]}–{semana_rango[1]}")
        if ceco_match:
            etiquetas_filtro.append(f"CECO: {ceco_match}")
        if cuenta_match:
            etiquetas_filtro.append(f"Cuenta: {cuenta_match}")
        filtro_txt = " | ".join(etiquetas_filtro) if etiquetas_filtro else "Sin filtro (consolidado 2026)"

        sie, fcst, comp, conta = (kpis[m] for m in psvc.METRICAS_V1)
        tabla_res = [{
            "SIE (Reglas 2026)": sie, "FCST (Oficial 2026)": fcst,
            "COMPARABILIDAD (Ppto 2026)": comp, "CONTA (Ordinario 2026)": conta,
            "vs SIE": sie - conta, "vs FCST": fcst - conta, "vs Comparabilidad": comp - conta,
        }]

        return {
            "tipo_respuesta": "financiera",
            "intencion_detectada": "Presupuesto 2027 (SIE / FCST / COMPARABILIDAD / CONTA)",
            "titulo": f"Presupuesto 2027 — {filtro_txt}",
            "respuesta_ejecutiva": (
                f"### 📊 Presupuesto 2027 ({filtro_txt})\n"
                f"- **SIE** (Real Gasto Canal Físico): {M(sie)}\n"
                f"- **FCST** (Forecast Oficial): {M(fcst)}\n"
                f"- **COMPARABILIDAD** (Presupuesto maestro): {M(comp)}\n"
                f"- **CONTA** (SAP + Luz): {M(conta)}\n\n"
                f"Ver la pestaña **Presupuesto 2027** para el árbol completo "
                f"(Grupo de Cuentas → Cuentas → Posición → Despacho → Servicio → Responsable)."
            ),
            "tabla": tabla_res,
            "filtros_resueltos": {"ceco": None, "eco_pdv_directo": None, "division": None, "territorio": None,
                                   "zona": None, "region": None, "grupo_cuentas": None, "cuenta": None, "pdc": None},
            "sql_linaje": {
                "sql_ejecutado": (
                    f"-- dash_app/services/ppto2027_service.py:kpis_resumen("
                    f"meses={meses}, semana_rango={semana_rango}, cecos={cecos}, cuentas={cuentas})"
                ),
                "tiempo_ms": dt_ms,
                "filas_procesadas": 1,
                "fuentes_parquet": ["Ppto 2027/aggs/agg_full.parquet"],
            },
        }
