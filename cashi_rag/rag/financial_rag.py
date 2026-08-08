# -*- coding: utf-8 -*-
"""
rag/financial_rag.py — Motor RAG Financiero 'Cashi' con Soporte de Granularidad Semanal y Acumulados
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Any, Optional

import duckdb
import polars as pl

BASE_DIR = Path(__file__).parent.parent.resolve()
AGGS_DIR = BASE_DIR / "aggs"
CONS_PATH = AGGS_DIR / "_consolidado.parquet"
META_PATH = AGGS_DIR / "_meta.json"


def normalizar_texto(texto: str) -> str:
    if not texto:
        return ""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    cadena_sin_acentos = "".join([c for c in nfkd if not unicodedata.combining(c)])
    return cadena_sin_acentos.lower().strip()


def M(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"{v / 1e6:,.2f} MDP"


def MC(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    s = M(abs(v))
    return f"({s})" if v > 0 else s


def PC(v) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    return f"({abs(v):,.1f}%)" if v > 0 else f"{abs(v):,.1f}%"


class FinancialRAGEngine:
    def __init__(self):
        self.con = duckdb.connect()
        if CONS_PATH.exists():
            self.con.execute(f"CREATE OR REPLACE VIEW consolidado AS SELECT * FROM read_parquet('{CONS_PATH.as_posix()}')")
            
            divs = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Direccion_Division FROM consolidado WHERE cat_Direccion_Division IS NOT NULL").fetchall()]
            self.map_divisiones = {normalizar_texto(d): d for d in divs}

            terrs = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Subdireccion_Territorio FROM consolidado WHERE cat_Subdireccion_Territorio IS NOT NULL").fetchall()]
            self.map_territorios = {normalizar_texto(t): t for t in terrs}

            gpos = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Grupo_de_Cuentas FROM consolidado WHERE cat_Grupo_de_Cuentas IS NOT NULL").fetchall()]
            self.map_grupos = {normalizar_texto(g): g for g in gpos}
        else:
            self.map_divisiones = {}
            self.map_territorios = {}
            self.map_grupos = {}

        self.meta = json.loads(META_PATH.read_text(encoding="utf-8")) if META_PATH.exists() else {}
        self.smr = self.meta.get("sem_max_real", 30)

    def query(self, text: str) -> Dict[str, Any]:
        norm_query = normalizar_texto(text)

        # 1. Detectar filtro de Semana Específica o Acumulado a Semana X
        sem_corte = self.smr
        es_acumulado_semana = False

        sem_match = re.search(r"\b(acumulado\s+a\s+la\s+semana|acumulado\s+a\s+semana|hasta\s+la\s+semana|hasta\s+semana|semana|sem)\s*#?\s*([0-9]{1,2})\b", norm_query)
        if sem_match:
            val_sem = int(sem_match.group(2))
            if 1 <= val_sem <= 53:
                sem_corte = val_sem
                es_acumulado_semana = True

        # 2. Detectar si pide desglose semanal
        desglose_semanal = any(kw in norm_query for kw in ["desglosado por semana", "por semana", "semanal", "evolucion semanal", "semana a semana", "historico semanal"])

        # 3. Detectar CECO
        ceco_match = re.search(r"\b(ceco|centro de costos?|centro|cecos?)\s*#?\s*([0-9]{3,8})\b", norm_query)
        ceco_id = ceco_match.group(2) if ceco_match else (re.findall(r"\b[0-9]{4,6}\b", norm_query)[0] if re.findall(r"\b[0-9]{4,6}\b", norm_query) else None)

        # 4. Detectar División
        div_encontrada = None
        for norm_div, orig_div in self.map_divisiones.items():
            div_tokens = [t for t in norm_div.split() if t not in ["division", "direccion", "de"]]
            for dt in div_tokens:
                if len(dt) > 3 and dt in norm_query:
                    div_encontrada = orig_div
                    break
            if div_encontrada:
                break

        # 5. Detectar Territorio
        terr_encontrado = None
        for norm_t, orig_t in self.map_territorios.items():
            t_tokens = [t for t in norm_t.split() if t not in ["territorio", "de"]]
            for tt in t_tokens:
                if len(tt) > 3 and tt in norm_query:
                    terr_encontrado = orig_t
                    break
            if terr_encontrado:
                break

        # 6. Detectar Grupo de Cuentas
        grupo_encontrado = None
        synonyms = {
            "nomina": ["nomina", "sueldo", "salario", "personal", "servicios personales"],
            "mantenimiento": ["mantenimiento", "mtto", "edificio", "maquinaria", "local"],
            "publicidad": ["publicidad", "mercadotecnia", "difusion"],
            "renta": ["renta", "luz", "telefono", "alquiler"],
            "flete": ["flete", "traslado", "transporte"],
            "operacion": ["operacion", "operativo", "gastos de operacion"],
            "honorarios": ["honorario", "asesoria", "consultoria"],
        }
        
        for norm_g, orig_g in self.map_grupos.items():
            if norm_g in norm_query:
                grupo_encontrado = orig_g
                break
        
        if not grupo_encontrado:
            for conc_key, syn_list in synonyms.items():
                if any(syn in norm_query for syn in syn_list):
                    for norm_g, orig_g in self.map_grupos.items():
                        if conc_key in norm_g or any(syn in norm_g for syn in syn_list):
                            grupo_encontrado = orig_g
                            break
                    if grupo_encontrado:
                        break

        # Lógica de desglose semanal
        if desglose_semanal:
            return self._query_desglose_semanal(ceco_id, div_encontrada, grupo_encontrado, sem_corte)

        # Lógica por entidad con filtro de semana
        if ceco_id:
            return self._query_ceco(ceco_id, grupo_encontrado, sem_corte, es_acumulado_semana)

        if "match" in norm_query or "mapeo" in norm_query or "cruces" in norm_query:
            return self._query_match_cecos(sem_corte)

        if div_encontrada:
            return self._query_division(div_encontrada, grupo_encontrado, sem_corte, es_acumulado_semana)

        if terr_encontrado:
            return self._query_territorio(terr_encontrado, grupo_encontrado, sem_corte, es_acumulado_semana)

        if grupo_encontrado:
            return self._query_grupo(grupo_encontrado, sem_corte, es_acumulado_semana)

        return self._query_general(sem_corte, es_acumulado_semana)

    def _query_desglose_semanal(self, ceco: Optional[str], div: Optional[str], grupo: Optional[str], sem_corte: int) -> Dict[str, Any]:
        where_clauses = [f"sem <= {sem_corte}"]
        label_filters = []

        if ceco:
            where_clauses.append(f"CAST(ID_CENTRO_COSTOS AS VARCHAR) LIKE '%{ceco}%'")
            label_filters.append(f"CECO {ceco}")
        if div:
            where_clauses.append(f"cat_Direccion_Division = '{div}'")
            label_filters.append(div)
        if grupo:
            where_clauses.append(f"cat_Grupo_de_Cuentas = '{grupo}'")
            label_filters.append(grupo)

        where_str = " WHERE " + " AND ".join(where_clauses)
        filt_txt = " · ".join(label_filters) if label_filters else "Global"

        sql = f"""
            SELECT 
                sem AS Semana,
                SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            {where_str}
            GROUP BY 1
            ORDER BY 1
        """
        res = self.con.execute(sql).pl().to_dicts()
        total_r26 = sum(r["Real_2026"] for r in res)
        total_p26 = sum(r["Plan_2026"] for r in res)

        resp_text = (
            f"Desglose semana a semana (Semanas 1 a {sem_corte}) para **{filt_txt}**:\n"
            f"- **Gasto Acumulado Real 2026**: **{M(total_r26)}**\n"
            f"- **Plan Presupuestado 2026**: **{M(total_p26)}**\n"
            f"- **Variación vs Plan**: **{MC(total_r26 - total_p26)}**"
        )

        return {
            "tipo": "desglose_semanal",
            "titulo": f"Evolución Semanal (Sem 1..{sem_corte}) · {filt_txt}",
            "respuesta": resp_text,
            "real_2026_mdp": round(total_r26 / 1e6, 2),
            "plan_2026_mdp": round(total_p26 / 1e6, 2),
            "vs_plan_mdp": round((total_r26 - total_p26) / 1e6, 2),
            "tabla": res,
            "columnas": ["Semana", "Real_2025", "Plan_2026", "Real_2026"]
        }

    def _query_ceco(self, ceco_id: str, grupo: Optional[str], sem_corte: int, es_acumulado: bool) -> Dict[str, Any]:
        where_extra = f" AND cat_Grupo_de_Cuentas = '{grupo}'" if grupo else ""
        lbl_sem = f" acumulado a Semana {sem_corte}" if es_acumulado else ""

        sql = f"""
            SELECT 
                CAST(ID_CENTRO_COSTOS AS VARCHAR) AS CECO,
                cat_PDC AS PDC,
                cat_Direccion_Division AS Division,
                cat_Grupo_de_Cuentas AS Grupo_Cuentas,
                cat_Cuentas AS Cuenta,
                SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE CAST(ID_CENTRO_COSTOS AS VARCHAR) LIKE '%{ceco_id}%' AND sem <= {sem_corte} {where_extra}
            GROUP BY 1, 2, 3, 4, 5
            ORDER BY Real_2026 DESC
            LIMIT 20
        """
        res = self.con.execute(sql).pl().to_dicts()
        if not res:
            return {
                "tipo": "ceco_detalle",
                "titulo": f"Consulta CECO {ceco_id}",
                "respuesta": f"No se encontraron registros de gasto para el **CECO {ceco_id}**{lbl_sem}.",
                "tabla": [], "columnas": []
            }

        total_r26 = sum(r["Real_2026"] for r in res)
        total_p26 = sum(r["Plan_2026"] for r in res)
        total_r25 = sum(r["Real_2025"] for r in res)
        vs_plan = total_r26 - total_p26
        pdc_nombre = res[0]["PDC"] if res else "CECO"

        grupo_str = f" en **{grupo}**" if grupo else ""
        resp_text = (
            f"El CECO **{ceco_id}** ({pdc_nombre}){grupo_str}{lbl_sem} registra un gasto **Real 2026** "
            f"de **{M(total_r26)}** (Plan 2026: **{M(total_p26)}** | Variación vs Plan: **{MC(vs_plan)}**)."
        )

        return {
            "tipo": "ceco_detalle",
            "titulo": f"Detalle CECO {ceco_id} · {pdc_nombre}{lbl_sem}",
            "respuesta": resp_text,
            "real_2026_mdp": round(total_r26 / 1e6, 2),
            "plan_2026_mdp": round(total_p26 / 1e6, 2),
            "real_2025_mdp": round(total_r25 / 1e6, 2),
            "vs_plan_mdp": round(vs_plan / 1e6, 2),
            "tabla": res,
            "columnas": ["CECO", "PDC", "Grupo_Cuentas", "Cuenta", "Real_2025", "Plan_2026", "Real_2026"]
        }

    def _query_division(self, div_name: str, grupo: Optional[str], sem_corte: int, es_acumulado: bool) -> Dict[str, Any]:
        where_extra = f" AND cat_Grupo_de_Cuentas = '{grupo}'" if grupo else ""
        lbl_sem = f" (Semanas 1 a {sem_corte})" if es_acumulado else ""

        sql = f"""
            SELECT 
                cat_Direccion_Division AS Division,
                cat_Grupo_de_Cuentas AS Grupo_Cuentas,
                SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE cat_Direccion_Division = '{div_name}' AND sem <= {sem_corte} {where_extra}
            GROUP BY 1, 2
            ORDER BY Real_2026 DESC
        """
        res = self.con.execute(sql).pl().to_dicts()
        total_r26 = sum(r["Real_2026"] for r in res)
        total_p26 = sum(r["Plan_2026"] for r in res)
        total_r25 = sum(r["Real_2025"] for r in res)
        vs_plan = total_r26 - total_p26

        grupo_str = f" para el grupo **{grupo}**" if grupo else ""
        resp_text = (
            f"La **{div_name}**{grupo_str}{lbl_sem} acumula un gasto **Real 2026** de **{M(total_r26)}** "
            f"(Plan 2026: **{M(total_p26)}** | Variación vs Plan: **{MC(vs_plan)}**)."
        )

        return {
            "tipo": "division_detalle",
            "titulo": f"Gasto Consolidado: {div_name}{lbl_sem}",
            "respuesta": resp_text,
            "real_2026_mdp": round(total_r26 / 1e6, 2),
            "plan_2026_mdp": round(total_p26 / 1e6, 2),
            "real_2025_mdp": round(total_r25 / 1e6, 2),
            "vs_plan_mdp": round(vs_plan / 1e6, 2),
            "tabla": res,
            "columnas": ["Division", "Grupo_Cuentas", "Real_2025", "Plan_2026", "Real_2026"]
        }

    def _query_territorio(self, terr_name: str, grupo: Optional[str], sem_corte: int, es_acumulado: bool) -> Dict[str, Any]:
        where_extra = f" AND cat_Grupo_de_Cuentas = '{grupo}'" if grupo else ""
        lbl_sem = f" (Semanas 1 a {sem_corte})" if es_acumulado else ""

        sql = f"""
            SELECT 
                cat_Subdireccion_Territorio AS Territorio,
                cat_Grupo_de_Cuentas AS Grupo_Cuentas,
                SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE cat_Subdireccion_Territorio = '{terr_name}' AND sem <= {sem_corte} {where_extra}
            GROUP BY 1, 2
            ORDER BY Real_2026 DESC
        """
        res = self.con.execute(sql).pl().to_dicts()
        total_r26 = sum(r["Real_2026"] for r in res)
        total_p26 = sum(r["Plan_2026"] for r in res)
        vs_plan = total_r26 - total_p26

        resp_text = (
            f"El **{terr_name}**{lbl_sem} registra un gasto **Real 2026** de **{M(total_r26)}** "
            f"(Plan 2026: **{M(total_p26)}** | Variación vs Plan: **{MC(vs_plan)}**)."
        )

        return {
            "tipo": "territorio_detalle",
            "titulo": f"Gasto Territorial: {terr_name}{lbl_sem}",
            "respuesta": resp_text,
            "real_2026_mdp": round(total_r26 / 1e6, 2),
            "plan_2026_mdp": round(total_p26 / 1e6, 2),
            "vs_plan_mdp": round(vs_plan / 1e6, 2),
            "tabla": res,
            "columnas": ["Territorio", "Grupo_Cuentas", "Real_2025", "Plan_2026", "Real_2026"]
        }

    def _query_grupo(self, grupo_name: str, sem_corte: int, es_acumulado: bool) -> Dict[str, Any]:
        lbl_sem = f" (Semanas 1 a {sem_corte})" if es_acumulado else ""

        sql = f"""
            SELECT 
                cat_Grupo_de_Cuentas AS Grupo_Cuentas,
                cat_Cuentas AS Cuenta,
                SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS Real_2025,
                SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS Plan_2026,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE cat_Grupo_de_Cuentas = '{grupo_name}' AND sem <= {sem_corte}
            GROUP BY 1, 2
            ORDER BY Real_2026 DESC
        """
        res = self.con.execute(sql).pl().to_dicts()
        total_r26 = sum(r["Real_2026"] for r in res)
        total_p26 = sum(r["Plan_2026"] for r in res)
        vs_plan = total_r26 - total_p26

        resp_text = (
            f"El Grupo de Cuentas **{grupo_name}**{lbl_sem} acumula un gasto **Real 2026** de **{M(total_r26)}** "
            f"(Plan 2026: **{M(total_p26)}** | Variación vs Plan: **{MC(vs_plan)}**)."
        )

        return {
            "tipo": "grupo_detalle",
            "titulo": f"Grupo de Cuentas: {grupo_name}{lbl_sem}",
            "respuesta": resp_text,
            "real_2026_mdp": round(total_r26 / 1e6, 2),
            "plan_2026_mdp": round(total_p26 / 1e6, 2),
            "vs_plan_mdp": round(vs_plan / 1e6, 2),
            "tabla": res,
            "columnas": ["Grupo_Cuentas", "Cuenta", "Real_2025", "Plan_2026", "Real_2026"]
        }

    def _query_match_cecos(self, sem_corte: int) -> Dict[str, Any]:
        sql = f"""
            SELECT 
                CASE WHEN cat_PDC IN ('0', '(Sin dato)', 'Sin agrupar') OR cat_PDC IS NULL THEN 'CECO Genérico / Sin PDC'
                     ELSE 'Con PDC Asignado' END AS Estado_Match,
                COUNT(DISTINCT ID_CENTRO_COSTOS) AS Cantidad_CECOs,
                SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE sem <= {sem_corte}
            GROUP BY 1
        """
        res = self.con.execute(sql).pl().to_dicts()
        
        sql_top = f"""
            SELECT cat_PDC AS PDC, CAST(ID_CENTRO_COSTOS AS VARCHAR) AS CECO, cat_Direccion_Division AS Division,
                   SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS Real_2026
            FROM consolidado
            WHERE sem <= {sem_corte}
            GROUP BY 1, 2, 3
            ORDER BY Real_2026 DESC
            LIMIT 12
        """
        res_top = self.con.execute(sql_top).pl().to_dicts()

        return {
            "tipo": "match_cecos",
            "titulo": f"Resumen Global de Match CECO ↔ PDC (Sem 1..{sem_corte})",
            "respuesta": "Resumen consolidado de la correspondencia y match entre Centros de Costos (CECO) y Puntos de Contacto (PDC):",
            "resumen_match": res,
            "tabla": res_top,
            "columnas": ["PDC", "CECO", "Division", "Real_2026"]
        }

    def _query_general(self, sem_corte: int, es_acumulado: bool) -> Dict[str, Any]:
        sql = f"SELECT Serie, SUM(monto) AS Total FROM consolidado WHERE sem <= {sem_corte} GROUP BY 1"
        res = self.con.execute(sql).pl().to_dicts()
        totales = {r["Serie"]: r["Total"] for r in res}

        r25, p26, r26, nvo = totales.get("R25", 0.0), totales.get("P26", 0.0), totales.get("R26", 0.0), totales.get("NVO", 0.0)
        vs_plan = r26 - p26
        lbl_sem = f" (Acumulado a Semana {sem_corte})" if es_acumulado else f" (Semanas 1 a {sem_corte})"

        resp = (
            f"Totales consolidados del ejercicio 2026{lbl_sem}:\n"
            f"- **Real 2026**: {M(r26)}\n"
            f"- **Plan 2026**: {M(p26)}\n"
            f"- **Nvo Plan 2026**: {M(nvo)}\n"
            f"- **Real 2025**: {M(r25)}\n"
            f"- **Variación vs Plan**: {MC(vs_plan)}"
        )

        return {
            "tipo": "resumen_general",
            "titulo": f"Resumen Financiero Global{lbl_sem}",
            "respuesta": resp,
            "real_2026_mdp": round(r26 / 1e6, 2),
            "plan_2026_mdp": round(p26 / 1e6, 2),
            "real_2025_mdp": round(r25 / 1e6, 2),
            "nvo_plan_mdp": round(nvo / 1e6, 2),
            "vs_plan_mdp": round(vs_plan / 1e6, 2),
        }


def ask_financial(query_text: str) -> str:
    engine = FinancialRAGEngine()
    res = engine.query(query_text)
    return json.dumps(res, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "gasto de division norte desglosado por semana"
    print(ask_financial(q))
