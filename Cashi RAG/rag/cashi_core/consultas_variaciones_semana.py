# -*- coding: utf-8 -*-
"""rag/cashi_core/consultas_variaciones_semana.py — "variaciones de la semana N", "de la 1 a la N",
"¿qué semanas fueron atípicas?".

Lenguaje operativo: la estadística (z robusto sobre mediana/MAD, piso de materialidad) solo decide QUÉ
es atípico; la respuesta dice cuáles CECOs, cuáles semanas y qué cuentas lo explican. La variación de
una semana es N contra N-1 por grupo de cuentas, para Real, Plan y FCST SIE. El cálculo está en
rag/monitoreo/analisis.py (lo comparte el tablero); aquí solo se da formato.

Canales: cada canal (Físico, Digital) se analiza por separado y la respuesta los distingue. Cada CECO
atípico trae su contexto (nombre, agrupador, división, territorio, zona, región) y un resumen de dónde
se concentra el impacto.
"""
from __future__ import annotations

import json
import time
from typing import Dict, List

import pandas as pd

from rag.cashi_core.comun import *  # noqa: F401,F403
from rag.monitoreo import config as MC
from rag.monitoreo.analisis import analizar
from rag.monitoreo.atipicos import texto_semanas

_CANAL_TXT = {"Fisico": "Físico", "Digital": "Digital"}
_CANAL_EMO = {"Fisico": "🏪", "Digital": "💻"}
_NOMBRES_CECO: Dict[str, str] = {}


def _mdp(v: float) -> str:
    return f"{'−' if v < 0 else ''}${abs(v) / 1e6:,.2f} MDP"


def _smdp(v: float) -> str:
    return f"{'+' if v >= 0 else '−'}${abs(v) / 1e6:,.2f} MDP"


def _spct(p: float) -> str:
    return f"{'+' if p >= 0 else '−'}{abs(p):.2f}%"


def _sems(texto: str) -> str:
    """'43' → 'semana 43'; '6 a 8 y 12' → 'semanas 6 a 8 y 12'."""
    return ("semana " if texto.strip().isdigit() else "semanas ") + texto


def nombre_ceco(ceco: str) -> str:
    """Nombre del CECO desde aggs/ceco_nombres.json (se carga una vez)."""
    if not _NOMBRES_CECO:
        try:
            with open(AGGS_DIR / "ceco_nombres.json", encoding="utf-8") as f:
                _NOMBRES_CECO.update({str(k): str(v) for k, v in json.load(f).items()})
        except Exception:
            _NOMBRES_CECO["_"] = ""
    return _NOMBRES_CECO.get(str(ceco), "")


def _cadena(*valores) -> str:
    """'Norte › Norte › Zona 3' → 'Norte › Zona 3' (sin repetir niveles iguales ni vacíos)."""
    out: List[str] = []
    for v in valores:
        v = (str(v).strip() if v is not None else "")
        if v and v.lower() not in ("nan", "none", "0") and (not out or out[-1] != v):
            out.append(v)
    return " › ".join(out)


class ConsultasVariacionesSemanaMixin:
    def _contexto_cecos(self, ejecutar, ids: List[str]) -> Dict[str, dict]:
        """Agrupador, división, territorio, zona y región vigentes (última semana con dato) por CECO."""
        if not ids or "r_ceco_general" not in self.rollups_disponibles:
            return {}
        try:
            df = ejecutar("""
                SELECT CAST(ID_CENTRO_COSTOS AS VARCHAR) AS ceco,
                       arg_max(cat_Agrupa1, sem) AS agrupador,
                       arg_max(cat_Direccion_Division, sem) AS division,
                       arg_max(cat_Subdireccion_Territorio, sem) AS territorio,
                       arg_max(cat_Subdireccion_Zona, sem) AS zona,
                       arg_max(cat_Subdireccion_Region, sem) AS region
                FROM r_ceco_general
                WHERE ID_CENTRO_COSTOS IN (SELECT unnest(?))
                GROUP BY 1
            """, [list(ids)])
        except Exception:
            return {}
        return {r.ceco: r._asdict() for r in df.itertuples(index=False)}

    # ------------------------------------------------------------------ un canal (formato)
    def _variaciones_un_canal(self, nlu: dict, canal: str, ini: int, fin: int, ejecutar, titulo_canal: bool):
        filt, prm = self._construir_filtros_entidad(nlu)
        self._tl.canal = canal
        solo_cta = set(self._cols_filtro(nlu)) <= {"cat_Grupo_de_Cuentas", "cat_Cuentas"}
        dim = "cuenta" if nlu.get("grupo_cuentas") or nlu.get("cuenta") else "grupo"
        tabla_fcst = None
        if self.fuente_nativa and solo_cta:
            tabla_fcst = "ddb.agg_fcst_srv_cuenta" if canal == "Fisico" else "ddb.dig_fcst_srv_cuenta"
        r = analizar(
            ejecutar, ini=ini, fin=fin, dim=dim,
            fuente_ceco=self._fuente(nlu, {"ID_CENTRO_COSTOS"}),
            fuente_g=self._fuente(nlu, {"cat_Grupo_de_Cuentas", "cat_Cuentas"}),
            filt=filt, prm=prm, tabla_fcst=tabla_fcst,
            where_fcst=filt if tabla_fcst else "", params_fcst=prm if tabla_fcst else None,
            contexto=lambda ids: self._contexto_cecos(ejecutar, ids), nombre_ceco=nombre_ceco, canal=canal,
            ml_solo_coinciden=bool({"cat_Grupo_de_Cuentas", "cat_Cuentas", "cat_Agrupador_Reales"} & set(self._cols_filtro(nlu))))
        es_rango = fin > ini
        en_sem = f"la semana {fin}" if not es_rango else f"las semanas {ini} a {fin}"
        partes: List[str] = []
        if titulo_canal:
            partes.append(f"#### {_CANAL_EMO[canal]} Canal {_CANAL_TXT[canal]}")
        if r["vacio"]:
            partes.append(f"No hay gasto Real en el canal {_CANAL_TXT[canal]} para este alcance en {en_sem}.")
            return partes, [], 0

        # 1) Total
        a_tot = r["tot_atip"]
        if a_tot.empty:
            sujeto = f"{en_sem} no se salió" if not es_rango else "ninguna semana del rango se salió"
            partes.append(f"**Total:** {sujeto} de lo normal (mediana {_mdp(r['mediana_tot'])} por semana).")
        else:
            mayores = a_tot.reindex(a_tot["dif"].abs().sort_values(ascending=False).index).head(MC.TOP_N).sort_values("sem")
            filas = "\n".join(
                f"| {int(x.sem)} | {_mdp(x.monto)} | {_smdp(x.dif)} | {_smdp(x.monto - r['media_tot'])} |"
                for x in mayores.itertuples())
            resto = "" if len(mayores) == len(a_tot) else f" (la tabla muestra las {len(mayores)} de mayor salto)"
            en_total = "en la " if len(a_tot) == 1 else "en las "
            partes.append(
                f"**Total:** el monto se salió de lo normal (arriba o abajo de su mediana) {en_total}"
                f"**{_sems(texto_semanas(a_tot['sem'].tolist()))}**{resto}.\n\n"
                f"| Semana | Monto | vs mediana | vs promedio |\n|---:|---:|---:|---:|\n{filas}")

        # 2) Grupo de cuentas (o cuenta)
        col, etq = r["col"], ("Cuenta" if dim == "cuenta" else "Grupo de cuentas")
        if es_rango:
            ag = r["grupos_atip"]
            etq_pl = "Cuentas" if dim == "cuenta" else "Grupos de cuentas"
            if ag.empty:
                partes.append(f"**{etq_pl}:** ninguna se salió de lo normal en {en_sem}.")
            else:
                partes.append(f"**{etq_pl} atípicas** (de mayor a menor impacto):\n" + "\n".join(
                    f"- **{x.ent}** — {_sems(texto_semanas(x.sems))}, {_smdp(x.imp)} contra su nivel normal"
                    for x in ag.head(MC.TOP_N).itertuples()))
        elif "var" in r and not r["var"].empty:
            v, hay_f = r["var"], r["hay_fcst"]
            cols_t = [etq, f"Real {fin}", f"Real {fin - 1}", "Var. Real", f"Plan {fin}", "Var. Plan"]
            if hay_f:
                cols_t += ["FCST SIE", "Real vs FCST"]
            cols_t.append("Real vs Plan")
            lin = []
            for x in v.head(MC.TOP_N).itertuples(index=False):
                rr = dict(zip(v.columns, x))
                fila = (f"| {rr[col]}{' ⚠️' if rr['atipico'] else ''} | {_mdp(rr['Real_N'])} | {_mdp(rr['Real_N1'])} | "
                        f"{_smdp(rr['Var_Real'])} ({_spct(rr['Var_Real_Pct'])}) | {_mdp(rr['Plan_N'])} | "
                        f"{_smdp(rr['Var_Plan'])} |")
                if hay_f:
                    fila += f" {_mdp(rr['FCST_N'])} | {_smdp(rr['Real_vs_FCST'])} |"
                lin.append(fila + f" {_smdp(rr['Real_vs_Plan'])} |")
            t = v[["Real_N", "Real_N1", "Plan_N", "Plan_N1", "FCST_N"]].sum()
            partes.append(
                f"**Semana {fin} contra semana {fin - 1}** por {etq.lower()} (de mayor a menor variación del Real). "
                f"Total Real {_mdp(t['Real_N'])} contra {_mdp(t['Real_N1'])} ({_smdp(t['Real_N'] - t['Real_N1'])}); "
                f"Plan {_mdp(t['Plan_N'])} contra {_mdp(t['Plan_N1'])}"
                + (f"; FCST SIE {_mdp(t['FCST_N'])}" if hay_f else "") + ".\n\n"
                + "| " + " | ".join(cols_t) + " |\n|:--|" + "---:|" * (len(cols_t) - 1) + "\n" + "\n".join(lin)
                + ("\n\n⚠️ = esa semana se salió de lo normal para esa fila." if v.head(MC.TOP_N)["atipico"].any() else ""))
            if not hay_f:
                partes.append("*FCST SIE solo se compara con filtros de grupo o cuenta (no existe por CECO, PDV ni territorio).*")

        # 3) CECOs atípicos con contexto
        tabla = [{"Canal": _CANAL_TXT[canal], **f} for f in r["ceco_atip"]]
        ml_texto = self._texto_ml(r, en_sem)
        if not tabla:
            partes.append(f"**CECOs:** ninguno se salió de lo normal en {en_sem}.")
            if ml_texto:
                partes.append(ml_texto)
            return partes, tabla, r["filas"]
        lineas = []
        for t in tabla[:MC.TOP_N]:
            donde = _cadena(t["Agrupador"], t["Division"], t["Territorio"], t["Zona"])
            nom = f" — {t['Nombre']}" if t["Nombre"] else ""
            lineas.append(f"- **{t['CECO']}**{nom}" + (f" · {donde}" if donde else "") +
                          f" — {_sems(t['Semanas_Atipicas'])} ({t['Tipo'].lower().replace('_', ' ')}), "
                          f"{_smdp(t['Impacto_vs_Normal_MXN'])} contra su nivel normal")
        partes.append(f"**CECOs atípicos** ({len(tabla)} en total; se muestran los {min(len(tabla), MC.TOP_N)} de mayor impacto, "
                      f"el resto va en la tabla descargable):\n" + "\n".join(lineas))
        conc = r["concentracion"]
        frases = [f"{et} **{conc[k][0]}** ({conc[k][1]:.0f}% del impacto)"
                  for k, et in (("Agrupador", "el agrupador"), ("Division", "la división")) if k in conc]
        if frases:
            partes.append("🔎 El impacto de estos CECOs se concentra en " + " y en ".join(frases) + ".")
        if ml_texto:
            partes.append(ml_texto)
        return partes, tabla, r["filas"]

    @staticmethod
    def _texto_ml(r: dict, en_sem: str) -> str:
        """Segunda opinión del modelo no supervisado (si hay resultados vigentes)."""
        ml = r.get("ml") or {}
        if not ml.get("hay"):
            return ""
        st = ml.get("estado") or {}
        al = ml.get("alertas") or []
        lin = []
        if al:
            lin.append(f"🤖 **Modelo de detección** (no supervisado, {st.get('version', '')}): marcó {len(al)} "
                       f"CECO{'s' if len(al) != 1 else ''} en {en_sem}"
                       + (f"; los {MC.TOP_N} de mayor rareza:" if len(al) > MC.TOP_N else ":"))
            for a in al[:MC.TOP_N]:
                donde = _cadena(a["Agrupador"], a["Division"], a["Territorio"])
                nom = f" — {a['Nombre']}" if a["Nombre"] else ""
                solo = "" if a["Tambien_Estadistico"] else " *(solo lo vio el modelo)*"
                lin.append(f"- **{a['CECO']}**{nom}" + (f" · {donde}" if donde else "") +
                           f" — {_sems(a['Semanas'])}, rareza máxima {a['Score'] * 100:.1f}%{solo}"
                           + (f". Pesa sobre todo: {a['Causas']}" if a["Causas"] else ""))
        else:
            lin.append(f"🤖 **Modelo de detección** ({st.get('version', '')}): no marcó CECOs raros en {en_sem}.")
        if ml.get("acotado_a_cuenta"):
            lin.append("*El modelo evalúa el CECO completo, no una cuenta: aquí solo se muestran los que además se salieron de lo normal en esa cuenta.*")
        lin.append("*La explicación del modelo es aproximada; la causa contable está en las tablas de arriba.*")
        return "\n".join(lin)

    # ------------------------------------------------------------------ consulta
    def _query_variaciones_semana(self, nlu: dict) -> dict:
        sem_info = nlu.get("semanas", {})
        ini = int(sem_info.get("inicio") or 1)
        fin = min(int(sem_info.get("fin") or self.sem_max_real), self.sem_max_real)
        ini = max(1, min(ini, fin))
        canal_pedido = nlu.get("canal_texto") or getattr(self._tl, "canal", "Fisico")
        if canal_pedido == "Ambos" and self.hay_digital:
            canales = ["Fisico", "Digital"]
        elif canal_pedido == "Digital" and self.hay_digital:
            canales = ["Digital"]
        else:
            canales = ["Fisico"]
        canal_original = getattr(self._tl, "canal", "Fisico")
        sqls: List[str] = []
        t0 = time.perf_counter()

        def ejecutar(sql: str, p: list) -> pd.DataFrame:
            cur, usado, _ = self._exec_sql(sql, p)
            sqls.append(usado)
            return self._fetch_df_arrow(cur)

        partes: List[str] = []
        tabla: List[dict] = []
        filas = 0
        ent_nom = self._nombre_entidad(nlu)
        titulo_sem = f"semana {fin}" if fin == ini else f"semanas {ini} a {fin}"
        try:
            for cn in canales:
                p, t, n = self._variaciones_un_canal(nlu, cn, ini, fin, ejecutar, titulo_canal=len(canales) > 1)
                partes += p
                tabla += t
                filas += n
        finally:
            self._tl.canal = canal_original
        if not filas:
            return self._respuesta_sin_datos("No encontré gasto Real para ese alcance en las semanas pedidas.")
        canal_txt = " y ".join(_CANAL_TXT[c] for c in canales)
        if len(canales) == 1 and self.hay_digital:
            otro = "digital" if canales[0] == "Fisico" else "físico"
            partes.append(f"*Esta respuesta es solo del canal {canal_txt}. Para verla del canal {otro} o de ambos "
                          f"canales, pídelo en la pregunta (por ejemplo \"… en ambos canales\") o cambia el filtro Canal.*")
        dt_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "tipo_respuesta": "variaciones_semana",
            "intencion_detectada": "Variaciones semana contra semana y semanas atípicas (Real, Plan, FCST SIE)",
            "titulo": f"Variaciones — {titulo_sem} · Canal {canal_txt} ({ent_nom})",
            "respuesta_ejecutiva": f"### 📈 Variaciones y atípicos — {titulo_sem} · Canal {canal_txt} ({ent_nom})\n\n"
                                   + "\n\n".join(partes),
            "tabla": tabla,
            "sql_linaje": {
                "sql_ejecutado": "\n\n".join(sqls),
                "tiempo_ms": dt_ms,
                "filas_procesadas": filas,
                "fuentes_parquet": self._fuentes_de("\n".join(sqls)),
            },
        }
