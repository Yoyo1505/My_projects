# -*- coding: utf-8 -*-
"""rag/cashi_core/respuestas.py — Respuestas documentales, aclaraciones, sugerencias y respuestas vacías."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class RespuestasMixin:
    def _format_documental_response(self, query_text: str, nlu: dict, doc_results: list) -> dict:
        if not doc_results or "error" in doc_results[0]:
            return self._respuesta_vacia(f"No se encontraron fragmentos normativos para '{query_text}'.")

        citas_md = []
        for r in doc_results:
            citas_md.append(
                f"#### 📄 [{r['file']}]({r['file']}#L{r['start_line']}-L{r['end_line']}) — `{r['heading']}` (BM25: {r['score']})\n"
                f"```{r['type']}\n{r['snippet']}\n```"
            )

        return {
            "tipo_respuesta": "documental",
            "intencion_detectada": "Búsqueda Documental RAG Local (BM25 Engine)",
            "titulo": f"Evidencia Documental Normativa: '{query_text}'",
            "respuesta_ejecutiva": (
                f"### 📖 Fragmentos Documentales Normativos Coincidentes\n"
                f"Se consultó la base de conocimiento técnica e indexador local. Coincidencias clave:\n\n" +
                "\n\n".join(citas_md)
            ),
            "citas_documentales": doc_results,
            "tabla": []
        }

    def _respuesta_sin_datos(self, msj: str) -> dict:
        return {
            "tipo_respuesta": "sin_coincidencias",
            "intencion_detectada": "Consulta Sin Resultados",
            "titulo": "Sin Coincidencias de Datos",
            "respuesta_ejecutiva": f"ℹ️ {msj}",
            "tabla": []
        }

    def _respuesta_aclaracion(self, query_text: str, opciones: list) -> dict:
        """La frase existe en dos dimensiones del catálogo: se pregunta cuál quiere el usuario."""
        etiquetas = {"territorio": "Territorio", "division": "División", "zona": "Zona",
                     "region": "Región", "grupo_cuentas": "Grupo de Cuentas", "cuenta": "Cuenta",
                     "agrupador_reales": "Agrupador de Reales", "pdc": "PDC"}
        lineas = "\n".join(f"- **{etiquetas.get(d, d)}:** {v}" for d, v in opciones)
        return {
            "tipo_respuesta": "aclaracion",
            "intencion_detectada": "Entidad Ambigua",
            "titulo": "¿A cuál te refieres?",
            "respuesta_ejecutiva": (
                f"**'{query_text}'** existe en más de una parte del catálogo. "
                f"Dime cuál quieres:\n\n{lineas}\n\n"
                f"*Vuelve a preguntar usando el nombre completo de la opción.*"
            ),
            "sugerencias_entidades": [(etiquetas.get(d, d), v, 1.0) for d, v in opciones],
            "tabla": [],
        }

    def _respuesta_sugerencia_entidad(self, query_text: str, nlu: dict) -> dict:
        """Ninguna entidad mencionada llegó a UMBRAL_AUTO_APLICAR pero sí hay
        candidatos parecidos (UMBRAL_SUGERENCIA <= ratio < UMBRAL_AUTO_APLICAR)
        — se ofrecen como "¿quisiste decir...?" en vez de aplicar un filtro
        débil en silencio o responder con el consolidado global sin avisar."""
        sugerencias = nlu.get("sugerencias_entidades", [])
        lineas = "\n".join(f"- **{etq}:** {val}" for etq, val, _ in sugerencias)
        return {
            "tipo_respuesta": "sugerencia",
            "intencion_detectada": "Entidad No Reconocida con Certeza",
            "titulo": "¿Quisiste decir alguna de estas opciones?",
            "respuesta_ejecutiva": (
                f"No encontré una coincidencia exacta para **'{query_text}'** en los catálogos "
                f"de División, Territorio, Grupo de Cuentas, Cuenta o PDC.\n\n"
                f"¿Quisiste decir alguna de estas opciones?\n\n{lineas}\n\n"
                f"*Vuelve a escribir tu pregunta usando uno de estos nombres tal cual aparece arriba.*"
            ),
            "sugerencias_entidades": sugerencias,
            "tabla": []
        }

    # -------------------------------------------------------------------------
    # PRESUPUESTO 2027 (dataset externo, "E:\Desarrollos\Ppto 2027") — ruta
    # aislada, no comparte catálogos/umbrales con el enrutador financiero de
    # Gasto Canal Fisico. Reutiliza dash_app/services/ppto2027_service.py, que
    # a su vez reutiliza tal cual las funciones reales de Ppto 2027
    # (generar_agregados/cargar_catalogos) — mismos números que ve el usuario
    # ahí, sin recalcular nada por separado.
    # -------------------------------------------------------------------------
    _PPTO2027_GATILLOS = (
        "presupuesto 2027", "ppto 2027", "ppto2027", "presupuesto canales 2027",
        "tablero ppto", "comparabilidad", "fcst oficial", "forecast oficial",
    )

    def _respuesta_vacia(self, msj: str) -> dict:
        return {
            "tipo_respuesta": "sin_coincidencias",
            "intencion_detectada": "Consulta Indeterminada",
            "titulo": "Consulta No Coincidente",
            "respuesta_ejecutiva": f"{msj}\n\n💡 **Ejemplos de Consulta:**\n- *'Gasto por territorio por semana'*\n- *'Gasto por división por mes'*\n- *'Top CECOs con mayor sobreconsumo'*\n- *'Variación semana 30 vs 31'*\n- *'Real 2026 vs 2025'*",
            "tabla": []
        }
