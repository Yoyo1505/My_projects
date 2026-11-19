# -*- coding: utf-8 -*-
"""
rag/financial_rag.py — Fachada del motor Cashi.

El código vive en rag/cashi_core/: comun (helpers/constantes), nlu, consultas_* , respuestas, ppto2027.
Aquí queda la clase UnifiedCashiRAGEngine (arranque, vistas DuckDB, SQL, process_query y ruteo)
y se reexportan los nombres públicos para no romper a quien importe desde rag.financial_rag.
"""
from __future__ import annotations

import re
import threading
import time
import os
from typing import Any, Dict, Optional, Tuple

import duckdb
import pandas as pd
from rag.cashi_core.comun import *  # noqa: F401,F403
from rag.cashi_core.nlu import NLUMixin
from rag.cashi_core.consultas_gasto import ConsultasGastoMixin
from rag.cashi_core.consultas_variacion import ConsultasVariacionMixin
from rag.cashi_core.consultas_series import ConsultasSeriesMixin
from rag.cashi_core.consultas_alertas import ConsultasAlertasMixin
from rag.cashi_core.consultas_variaciones_semana import ConsultasVariacionesSemanaMixin
from rag.cashi_core.consultas_estructura import ConsultasEstructuraMixin
from rag.cashi_core.consultas_versiones import ConsultasVersionesMixin
from rag.cashi_core.respuestas import RespuestasMixin
from rag.cashi_core.ppto2027 import Ppto2027Mixin


class UnifiedCashiRAGEngine(
    NLUMixin,
    ConsultasGastoMixin,
    ConsultasVariacionMixin,
    ConsultasSeriesMixin,
    ConsultasAlertasMixin,
    ConsultasVariacionesSemanaMixin,
    ConsultasEstructuraMixin,
    ConsultasVersionesMixin,
    RespuestasMixin,
    Ppto2027Mixin,
):
    """Motor Financiero y Documental Inteligente para Cashi."""

    def __init__(self):
        self.con = duckdb.connect()
        try:
            self.con.execute("PRAGMA threads=8")
            self.con.execute("PRAGMA max_memory='4GB'")
            self.con.execute("PRAGMA preserve_insertion_order=false")
        except Exception:
            pass
        self.sem_max_real = 31
        self.sem_max_plan = 53
        
        self.validos_cecos_raw: set = set()
        self.validos_cecos_clean: Dict[str, str] = {}
        self.map_divisiones: Dict[str, str] = {}
        self.map_territorios: Dict[str, str] = {}
        self.map_zonas: Dict[str, str] = {}
        self.map_regiones: Dict[str, str] = {}
        self.map_contralogias: Dict[str, str] = {}
        self.map_contraloria6: Dict[str, str] = {}
        self.map_grupos: Dict[str, str] = {}
        self.map_cuentas: Dict[str, str] = {}
        self.map_agrupa1: Dict[str, str] = {}
        self.map_agrupa2: Dict[str, str] = {}
        self.map_agrupa3: Dict[str, str] = {}
        # map_pdc: texto normalizado -> nombre de PDC (para NLU/sugerencias/
        # display, igual que las demás entidades). pdc_a_eco_pdv: nombre de
        # PDC (tal cual, sin normalizar) -> ECO_PDV numérico, el identificador
        # que de verdad agrupa un punto de contacto físico — un mismo Eco PDV
        # puede tener 2+ nombres de PDC distintos (p.ej. "Ekt X" + "Presta
        # Prenda X" en la misma ubicación). Filtrar por cat_PDC en vez de
        # ECO_PDV subestimaba el gasto real de esos puntos (solo sumaba UNO
        # de los nombres). El resto del dashboard ("Análisis PDC", "Detalle
        # CECO") ya agrupa por ECO_PDV desde el 2026-08-24/25 — Cashi debe
        # coincidir. Ver `_query_consulta_estandar` y hermanas para el filtro.
        self.map_pdc: Dict[str, str] = {}
        self.pdc_a_eco_pdv: Dict[str, int] = {}
        # validos_eco_pdv / eco_pdv_a_nombres: para resolver un número suelto
        # en la pregunta ("6031") como Eco PDV cuando NO es un CECO válido —
        # antes cualquier número no-CECO se descartaba como "ceco_inexistente"
        # sin nunca considerar que el usuario quería decir un PDV (feedback
        # 2026-08-31: "no nota la diferencia entre un eco pdv o un ceco").
        self.validos_eco_pdv: set = set()
        self.eco_pdv_a_nombres: Dict[int, List[str]] = {}

        if META_PATH.exists():
            try:
                meta = json.loads(META_PATH.read_text(encoding="utf-8"))
                self.sem_max_real = meta.get("sem_max_real", 31)
                self.sem_max_plan = meta.get("sem_max_plan", 53)
            except Exception:
                pass

        self.fuente_nativa = False
        self.hay_digital = False
        self._tl = threading.local()   # canal de la consulta en curso, por hilo (un hilo = un usuario)
        self.rollups_disponibles: set = set()
        self.tiene_eco_pdv = False
        self.grafo: Dict[str, Any] = {}

        if CONS_PATH.exists() or DDB_PATH.exists():
            try:
                self._crear_vistas()

                # sem_max_real sale de _meta.json (lo escribe build_data.py al
                # cerrar la semana). NO de MAX(sem) de R26: la serie R26 trae
                # montos cargados hasta la semana 53 (Servicios Administrativos
                # Boff, Costo Activo Fijo, Gastos Despacho ~$100M/sem) y eso
                # hacía que Cashi tomara la semana 53 como "última semana real"
                # — acumulados 1–53 (Plan de todo el año contra Real a la 39),
                # alertas sobre la semana 53 (siempre vacías) y "últimas 4
                # semanas" = 50–53. Solo si no hay _meta.json se usa la base.
                if not META_PATH.exists():
                    max_sem_db = self.con.execute("SELECT MAX(sem) FROM consolidado WHERE Serie = 'R26' AND monto IS NOT NULL AND monto != 0").fetchone()[0]
                    if max_sem_db:
                        self.sem_max_real = max_sem_db

                cecos = [str(r[0]) for r in self.con.execute("SELECT DISTINCT ID_CENTRO_COSTOS FROM consolidado WHERE ID_CENTRO_COSTOS IS NOT NULL AND ID_CENTRO_COSTOS != '0'").fetchall()]
                for c in cecos:
                    c_clean = str(c).strip()
                    self.validos_cecos_raw.add(c_clean)
                    self.validos_cecos_clean[c_clean.lstrip("0")] = c_clean

                divs = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Direccion_Division FROM consolidado WHERE cat_Direccion_Division IS NOT NULL AND cat_Direccion_Division != '0'").fetchall()]
                self.map_divisiones = {normalizar_texto(d): d for d in divs if normalizar_texto(d)}

                terrs = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Subdireccion_Territorio FROM consolidado WHERE cat_Subdireccion_Territorio IS NOT NULL AND cat_Subdireccion_Territorio != '0'").fetchall()]
                self.map_territorios = {normalizar_texto(t): t for t in terrs if normalizar_texto(t)}
                # Alias sin el prefijo "Territorio " ("Metro Norte", "Yucatan"):
                # así se nombran en la presentación semanal y en el tablero.
                for t in terrs:
                    if t.lower().startswith("territorio "):
                        alias = normalizar_texto(t[len("territorio "):])
                        if alias:
                            self.map_territorios.setdefault(alias, t)

                zonas = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Subdireccion_Zona FROM consolidado WHERE cat_Subdireccion_Zona IS NOT NULL AND cat_Subdireccion_Zona != '0'").fetchall()]
                self.map_zonas = {normalizar_texto(z): z for z in zonas if normalizar_texto(z)}

                regiones = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Subdireccion_Region FROM consolidado WHERE cat_Subdireccion_Region IS NOT NULL AND cat_Subdireccion_Region != '0'").fetchall()]
                self.map_regiones = {normalizar_texto(rg): rg for rg in regiones if normalizar_texto(rg)}

                contras = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Contraloria FROM consolidado WHERE cat_Contraloria IS NOT NULL AND cat_Contraloria != '0'").fetchall()]
                self.map_contralogias = {normalizar_texto(c): c for c in contras if normalizar_texto(c)}

                contras6 = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Contraloria_6 FROM consolidado WHERE cat_Contraloria_6 IS NOT NULL AND cat_Contraloria_6 NOT IN ('0', 'No Clasificado')").fetchall()]
                self.map_contraloria6 = {normalizar_texto(c): c for c in contras6 if normalizar_texto(c)}

                gpos = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Grupo_de_Cuentas FROM consolidado WHERE cat_Grupo_de_Cuentas IS NOT NULL AND cat_Grupo_de_Cuentas != '0'").fetchall()]
                self.map_grupos = {normalizar_texto(g): g for g in gpos if normalizar_texto(g)}

                ctas = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Cuentas FROM consolidado WHERE cat_Cuentas IS NOT NULL AND cat_Cuentas != '0'").fetchall()]
                self.map_cuentas = {normalizar_texto(c): c for c in ctas if normalizar_texto(c)}

                agrupa1s = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Agrupa1 FROM consolidado WHERE cat_Agrupa1 IS NOT NULL AND cat_Agrupa1 != '0'").fetchall()]
                self.map_agrupa1 = {normalizar_texto(a): a for a in agrupa1s if normalizar_texto(a)}

                agrupa2s = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Agrupa2 FROM consolidado WHERE cat_Agrupa2 IS NOT NULL AND cat_Agrupa2 != '0'").fetchall()]
                self.map_agrupa2 = {normalizar_texto(a): a for a in agrupa2s if normalizar_texto(a)}

                agrupa3s = [r[0] for r in self.con.execute("SELECT DISTINCT cat_Agrupa3 FROM consolidado WHERE cat_Agrupa3 IS NOT NULL AND cat_Agrupa3 != '0'").fetchall()]
                self.map_agrupa3 = {normalizar_texto(a): a for a in agrupa3s if normalizar_texto(a)}

                if self.tiene_eco_pdv:
                    pdc_rows = self.con.execute("""
                        SELECT DISTINCT cat_PDC, ECO_PDV FROM consolidado
                        WHERE cat_PDC IS NOT NULL AND cat_PDC != '0' AND ECO_PDV IS NOT NULL
                    """).fetchall()
                    for nombre_pdc, eco in pdc_rows:
                        key = normalizar_texto(nombre_pdc)
                        if key:
                            self.map_pdc[key] = nombre_pdc
                        self.pdc_a_eco_pdv[nombre_pdc] = eco
                        eco_int = int(eco)
                        self.validos_eco_pdv.add(eco_int)
                        self.eco_pdv_a_nombres.setdefault(eco_int, [])
                        if nombre_pdc not in self.eco_pdv_a_nombres[eco_int]:
                            self.eco_pdv_a_nombres[eco_int].append(nombre_pdc)
                else:
                    # Este dataset no tiene ECO_PDV todavía — pdc_a_eco_pdv
                    # queda vacío a propósito; _construir_filtros_entidad cae
                    # de vuelta a filtrar por cat_PDC directo (comportamiento
                    # previo a la corrección, sin sumar tienda+empeño juntos).
                    pdcs = [r[0] for r in self.con.execute("SELECT DISTINCT cat_PDC FROM consolidado WHERE cat_PDC IS NOT NULL AND cat_PDC != '0'").fetchall()]
                    self.map_pdc = {normalizar_texto(p): p for p in pdcs if normalizar_texto(p)}

            except Exception as e:
                print(f"[Cashi Engine Warning] Error inicializando view DuckDB: {e}")

            try:
                self._construir_grafo()
            except Exception as e:
                import traceback
                print(f"[Cashi Engine Warning] No se pudo construir el grafo de estructura: {e}")
                traceback.print_exc()

        self.local_doc_rag = LocalRAG()

    # -------------------------------------------------------------------------
    # FUENTES DE DATOS: dashboard.duckdb nativo + agregados, respaldo parquet
    # -------------------------------------------------------------------------
    # Agregados (rollups) que ya genera codigo/build_data.py dentro
    # de dashboard.duckdb, de menor a mayor tamaño. Solo pre-suman por
    # Serie/sem sobre esas columnas — cualquier consulta cuyas columnas de
    # agrupación + filtro quepan completas en uno da el mismo total que
    # `consolidado` (verificado 2026-09-29, R26/P26/R25 sem 1–39 idénticos).
    # Medido 2026-09-29: total de una división 241 ms (parquet) -> 81 ms
    # (consolidado nativo) -> 4 ms (rollup_pdv_general).
    _ROLLUPS_CASHI = (
        # 126K filas: el más chico. Cubre Contraloría (resumen/detalle), Grupo,
        # Cuenta, Subtipo y MES (2026-09-30; también acelera consultas solo por
        # Grupo/Cuenta, que antes iban en vivo a `consolidado`).
        ("r_mes_contraloria", "rollup_mes_contraloria", frozenset({
            "cat_Contraloria", "cat_Contraloria_6", "cat_Grupo_de_Cuentas", "cat_Cuentas",
            "cat_Subtipo", "MES"})),
        ("r_pdv_general", "rollup_pdv_general", frozenset({
            "cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Zona",
            "cat_Subdireccion_Region", "ECO_PDV"})),
        ("r_ceco_general", "rollup_ceco_general", frozenset({
            "cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Zona",
            "cat_Subdireccion_Region", "ID_CENTRO_COSTOS"})),
        ("r_pdv_general_gpo", "rollup_pdv_general_gpo", frozenset({
            "cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Zona",
            "cat_Subdireccion_Region", "ECO_PDV", "cat_Grupo_de_Cuentas"})),
        # 20M filas: solo conviene si hay un CECO concreto en el filtro — al
        # agrupar TODOS los CECO x Grupo es más lento que `consolidado`.
        ("r_ceco_general_gpo", "rollup_ceco_general_gpo", frozenset({
            "cat_Direccion_Division", "cat_Subdireccion_Territorio", "cat_Subdireccion_Zona",
            "cat_Subdireccion_Region", "ID_CENTRO_COSTOS", "cat_Grupo_de_Cuentas"})),
    )

    def _crear_vistas(self):
        """`consolidado`/`ceco_summary` apuntan a dashboard.duckdb (tabla
        nativa, 2–5x más rápida que leer el parquet) si se puede adjuntar en
        solo lectura; si no (archivo bloqueado por una reconstrucción, no
        existe, etc.) se usa aggs/_consolidado.parquet como antes. Las vistas
        *_pq sobre el parquet existen siempre: `_exec_sql` reintenta ahí si
        una consulta sobre la fuente nativa falla."""
        def _con_monto(origen):
            # 2026-10-21: consolidado ya no guarda `monto` (idéntica a monto_cons); se repone como alias
            # para las consultas de Cashi (SUM(monto)). Acepta también el formato anterior, que sí la trae.
            cols = {r[0] for r in self.con.execute(f"DESCRIBE SELECT * FROM {origen}").fetchall()}
            return f"SELECT * FROM {origen}" if "monto" in cols else f"SELECT *, monto_cons AS monto FROM {origen}"

        if CONS_PATH.exists():
            self.con.execute(f"CREATE OR REPLACE VIEW consolidado_pq AS "
                             f"{_con_monto(f'read_parquet({chr(39)}{CONS_PATH.as_posix()}{chr(39)})')}")
        if DDB_PATH.exists() and os.environ.get("CASHI_FUENTE", "").lower() != "parquet":
            try:
                self.con.execute(f"ATTACH '{DDB_PATH.as_posix()}' AS ddb (READ_ONLY)")
                tablas = {r[0] for r in self.con.execute(
                    "SELECT table_name FROM duckdb_tables() WHERE database_name = 'ddb'").fetchall()}
                if "consolidado" in tablas:
                    self.con.execute(f"CREATE OR REPLACE VIEW consolidado AS {_con_monto('ddb.consolidado')}")
                    self.fuente_nativa = True
                    for vista, tabla, _ in self._ROLLUPS_CASHI:
                        if tabla in tablas:
                            self.con.execute(f"CREATE OR REPLACE VIEW {vista} AS SELECT *, monto_cons AS monto FROM ddb.{tabla}")
                            self.rollups_disponibles.add(vista)
            except Exception as e:
                print(f"[Cashi Engine] dashboard.duckdb no disponible ({e}); se usa _consolidado.parquet.")
        if not self.fuente_nativa:
            self.con.execute("CREATE OR REPLACE VIEW consolidado AS SELECT * FROM consolidado_pq")

        # ECO_PDV puede no existir en otros datasets/proyectos hermanos
        # que usan este mismo motor (p.ej. si su build_data.py es más
        # viejo) — la vista y el filtro de PDC deben degradar con
        # gracia a cat_PDC en vez de tronar con "columna no existe".
        cols_consolidado = {r[0] for r in self.con.execute("DESCRIBE consolidado").fetchall()}
        self.tiene_eco_pdv = "ECO_PDV" in cols_consolidado
        eco_pdv_expr = "ECO_PDV" if self.tiene_eco_pdv else "CAST(NULL AS BIGINT) AS ECO_PDV"
        # Agrupador de Reales (2026-10-08): filtro de Cashi con rag/cashi_ml
        agr_expr = ("cat_Agrupador_Reales" if "cat_Agrupador_Reales" in cols_consolidado
                    else "CAST(NULL AS VARCHAR) AS cat_Agrupador_Reales")
        # Canal Digital (build_digitales_db.py): consolidado_dig vive en aggs/digitales.duckdb
        self.hay_digital = False
        dig_path = AGGS_DIR / "digitales.duckdb"
        if self.fuente_nativa and dig_path.exists():
            try:
                self.con.execute(f"ATTACH '{dig_path.as_posix()}' AS dg (READ_ONLY)")
                self.con.execute("CREATE OR REPLACE VIEW consolidado_dig AS SELECT *, monto_cons AS monto FROM dg.consolidado_dig")
                self.hay_digital = True
            except Exception as e:
                print(f"[Cashi Engine] digitales.duckdb no disponible ({e}); Cashi solo responde el canal Físico.")
        for vista, origen in (("ceco_summary", "consolidado"), ("ceco_summary_pq", "consolidado_pq"),
                              ("ceco_summary_dig", "consolidado_dig")):
            if origen == "consolidado_pq" and not CONS_PATH.exists():
                continue
            if origen == "consolidado_dig" and not self.hay_digital:
                continue
            self.con.execute(f"""
                CREATE OR REPLACE VIEW {vista} AS
                SELECT
                    CAST(ID_CENTRO_COSTOS AS VARCHAR) AS ID_CENTRO_COSTOS,
                    cat_Grupo_de_Cuentas,
                    cat_Cuentas,
                    {agr_expr},
                    cat_Contraloria,
                    cat_Contraloria_6,
                    cat_Direccion_Division,
                    cat_Subdireccion_Territorio,
                    cat_Subdireccion_Zona,
                    cat_Subdireccion_Region,
                    cat_PDC,
                    {eco_pdv_expr},
                    sem,
                    Serie,
                    monto
                FROM {origen}
                WHERE ID_CENTRO_COSTOS IS NOT NULL;
            """)

    def _cols_filtro(self, nlu: dict) -> set:
        """Columnas que tocará `_construir_filtros_entidad` para este nlu."""
        cols = set()
        if nlu.get("ceco"):
            cols.add("ID_CENTRO_COSTOS")
        if nlu.get("eco_pdv_directo") is not None:
            cols.add("ECO_PDV")
        for campo, col in (("division", "cat_Direccion_Division"), ("territorio", "cat_Subdireccion_Territorio"),
                           ("zona", "cat_Subdireccion_Zona"), ("region", "cat_Subdireccion_Region"),
                           ("grupo_cuentas", "cat_Grupo_de_Cuentas"), ("cuenta", "cat_Cuentas"),
                           ("agrupador_reales", "cat_Agrupador_Reales")):
            if nlu.get(campo):
                cols.add(col)
        if nlu.get("contraloria"):
            cols.add("cat_Contraloria_6" if nlu.get("contraloria_nivel") == "6" else "cat_Contraloria")
        if nlu.get("pdc"):
            cols.add("ECO_PDV" if self.pdc_a_eco_pdv.get(nlu["pdc"]) is not None else "cat_PDC")
        return cols

    def _fuente(self, nlu: dict, cols_extra=()) -> str:
        """Tabla/vista más chica que cubre las columnas de agrupación
        (`cols_extra`) + las de los filtros de la pregunta. Si ningún agregado
        alcanza, DuckDB calcula en vivo sobre `ceco_summary` con el filtro
        empujado al escaneo (solo lee las divisiones/territorios/grupos/cuentas
        pedidos)."""
        filtros = self._cols_filtro(nlu)
        cols = set(cols_extra) | filtros
        for vista, _, disponibles in self._ROLLUPS_CASHI:
            if vista not in self.rollups_disponibles:
                continue
            if vista == "r_ceco_general_gpo" and "ID_CENTRO_COSTOS" not in filtros:
                continue
            if cols <= disponibles:
                return vista
        return "ceco_summary"

    def _fuentes_de(self, sql: str) -> List[str]:
        """Linaje real de una consulta (qué archivo/tabla se leyó)."""
        usadas = set(re.findall(r"\bFROM\s+(\w+)", sql))
        out = []
        for u in sorted(usadas):
            if u.startswith("r_"):
                out.append(f"aggs/dashboard.duckdb :: {dict((v, t) for v, t, _ in self._ROLLUPS_CASHI).get(u, u)}")
            elif u in ("consolidado", "ceco_summary"):
                out.append("aggs/dashboard.duckdb :: consolidado" if self.fuente_nativa else "aggs/_consolidado.parquet")
            elif u.endswith("_pq"):
                out.append("aggs/_consolidado.parquet")
        return out or ["aggs/_consolidado.parquet"]

    def _construir_grafo(self):
        """Grafo de estructura territorial y contable:
          Territorial: División → Territorio → Zona → Región → ECO → CECO
          Contable: Contraloría → Contraloría5 → Grupo → Cuenta (+ Agrupa1/2/3)
        """
        # Jerarquía territorial completa
        filas_terr = self.con.execute("""
            SELECT DISTINCT
                cat_Direccion_Division, cat_Subdireccion_Territorio,
                cat_Subdireccion_Zona, cat_Subdireccion_Region,
                ECO_PDV, ID_CENTRO_COSTOS
            FROM ceco_summary
        """).fetchall()
        div_terr: Dict[str, set] = {}
        terr_div: Dict[str, str] = {}
        terr_zona: Dict[str, set] = {}
        zona_terr: Dict[str, str] = {}
        zona_region: Dict[str, set] = {}
        region_zona: Dict[str, str] = {}
        terr_eco: Dict[str, set] = {}
        terr_ceco: Dict[str, set] = {}
        ceco_padres: Dict[str, Tuple[str, str, str, str, Optional[int]]] = {}

        for div, terr, zona, region, eco, ceco in filas_terr:
            div, terr, zona, region, ceco = (str(x) if x is not None else "" for x in (div, terr, zona, region, ceco))
            if div and terr:
                div_terr.setdefault(div, set()).add(terr)
                terr_div[terr] = div
            if terr and zona:
                terr_zona.setdefault(terr, set()).add(zona)
                zona_terr[zona] = terr
            if zona and region:
                zona_region.setdefault(zona, set()).add(region)
                region_zona[region] = zona
            if terr and eco is not None and int(eco) != 0:
                terr_eco.setdefault(terr, set()).add(int(eco))
            if terr and ceco:
                terr_ceco.setdefault(terr, set()).add(ceco)
            if ceco and div and terr:
                if ceco not in ceco_padres or (ceco_padres[ceco][4] is None and eco):
                    ceco_padres[ceco] = (div, terr, zona, region, int(eco) if eco is not None and int(eco) != 0 else None)

        # Jerarquía contable
        filas_cta = self.con.execute("""
            SELECT DISTINCT
                cat_Contraloria, cat_Contraloria_6, cat_Grupo_de_Cuentas, cat_Cuentas,
                cat_Agrupa1, cat_Agrupa2, cat_Agrupa3
            FROM consolidado
            WHERE cat_Grupo_de_Cuentas IS NOT NULL AND cat_Cuentas IS NOT NULL
        """).fetchall()
        contra_contra6: Dict[str, str] = {}
        contra6_grupo: Dict[str, set] = {}
        grupo_ctas: Dict[str, set] = {}
        cta_grupo: Dict[str, str] = {}
        cta_agrupas: Dict[str, Tuple[str, str, str]] = {}

        for contra, contra6, gpo, cta, agrupa1, agrupa2, agrupa3 in filas_cta:
            contra, contra6, gpo, cta = (str(x) if x is not None else "" for x in (contra, contra6, gpo, cta))
            if contra and contra6:
                contra_contra6[contra] = str(contra6) if contra6 else ""
            if contra6 and gpo:
                contra6_grupo.setdefault(str(contra6) if contra6 else "", set()).add(gpo)
            if gpo and cta:
                grupo_ctas.setdefault(gpo, set()).add(cta)
                cta_grupo[cta] = gpo
            if cta and (agrupa1 or agrupa2 or agrupa3):
                cta_agrupas[cta] = (str(agrupa1) if agrupa1 else "", str(agrupa2) if agrupa2 else "", str(agrupa3) if agrupa3 else "")

        self.grafo = {
            # Territorial
            "div_terr": div_terr, "terr_div": terr_div,
            "terr_zona": terr_zona, "zona_terr": zona_terr,
            "zona_region": zona_region, "region_zona": region_zona,
            "terr_eco": terr_eco, "terr_ceco": terr_ceco,
            "ceco_padres": ceco_padres,
            # Contable
            "contra_contra6": contra_contra6, "contra6_grupo": contra6_grupo,
            "grupo_ctas": grupo_ctas, "cta_grupo": cta_grupo,
            "cta_agrupas": cta_agrupas,
        }

    def _sql_por_canal(self, sql: str) -> str:
        """Reescribe el FROM de la fuente según el canal de la consulta en curso (hilo propio de cada usuario)."""
        canal = getattr(self._tl, "canal", "Fisico")
        if canal == "Fisico" or not self.hay_digital:
            return sql
        if canal == "Digital":
            sql = re.sub(r"\bFROM\s+ceco_summary\b", "FROM ceco_summary_dig", sql)
            return re.sub(r"\bFROM\s+(consolidado|r_\w+)\b", "FROM consolidado_dig", sql)
        sql = re.sub(r"\bFROM\s+ceco_summary\b",
                     "FROM (SELECT * FROM ceco_summary UNION ALL SELECT * FROM ceco_summary_dig)", sql)
        return re.sub(r"\bFROM\s+(consolidado|r_\w+)\b",
                      "FROM (SELECT * FROM consolidado UNION ALL BY NAME SELECT * FROM consolidado_dig)", sql)

    def _exec_sql(self, sql: str, params=None) -> Tuple[duckdb.DuckDBPyConnection, str, float]:
        t0 = time.perf_counter()
        sql = self._sql_por_canal(sql)
        cur = self.con.cursor()
        try:
            if params is not None:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
        except duckdb.Error:
            # Alternativa: si la fuente nativa (dashboard.duckdb / agregados)
            # falla, se repite la MISMA consulta sobre el parquet consolidado.
            if not self.fuente_nativa or not CONS_PATH.exists():
                raise
            sql = re.sub(r"\bFROM\s+ceco_summary\b", "FROM ceco_summary_pq", sql)
            sql = re.sub(r"\bFROM\s+(consolidado|r_\w+)\b", "FROM consolidado_pq", sql)
            cur = self.con.cursor()
            if params is not None:
                cur.execute(sql, params)
            else:
                cur.execute(sql)
        dt_ms = (time.perf_counter() - t0) * 1000.0
        return cur, sql, round(dt_ms, 2)

    def _fetch_df_arrow(self, cur: duckdb.DuckDBPyConnection) -> pd.DataFrame:
        try:
            arrow_table = cur.fetch_arrow_table()
            return arrow_table.to_pandas()
        except Exception:
            return cur.fetch_df()

    def _construir_filtros_entidad(self, nlu: dict) -> Tuple[str, list]:
        """Construye el fragmento ' AND col = ?' (repetido) y la lista de
        parámetros correspondientes a las entidades resueltas en `nlu`.
        Centralizado para que TODAS las consultas filtren exactamente igual:
        - Comparación insensible a mayúsculas/minúsculas (UPPER(col)=UPPER(?))
          en todas las columnas de catálogo tipo texto — defensa ante
          variaciones de mayúsculas entre cargas semanales del origen.
        - PDC se resuelve vía ECO_PDV (`self.pdc_a_eco_pdv`), no vía cat_PDC:
          un mismo punto de contacto físico puede tener 2+ nombres de PDC
          distintos (tienda + empeño en la misma ubicación) que se deben
          sumar juntos — filtrar por cat_PDC solo capturaba uno de los
          nombres y subestimaba el gasto real de ese punto. El resto del
          dashboard ("Análisis PDC", "Detalle CECO") ya agrupa por ECO_PDV
          desde el 2026-08-24/25; Cashi tiene que reportar la misma cifra.
        """
        filt_clause = ""
        params: list = []

        ceco = nlu.get("ceco")
        if ceco:
            filt_clause += " AND ID_CENTRO_COSTOS = ?"
            params.append(ceco)

        eco_pdv_directo = nlu.get("eco_pdv_directo")
        if eco_pdv_directo is not None:
            filt_clause += " AND ECO_PDV = ?"
            params.append(eco_pdv_directo)

        for campo_nlu, col_sql in (
            ("division", "cat_Direccion_Division"),
            ("territorio", "cat_Subdireccion_Territorio"),
            ("zona", "cat_Subdireccion_Zona"),
            ("region", "cat_Subdireccion_Region"),
            ("grupo_cuentas", "cat_Grupo_de_Cuentas"),
            ("cuenta", "cat_Cuentas"),
            ("agrupador_reales", "cat_Agrupador_Reales"),
        ):
            valor = nlu.get(campo_nlu)
            if valor and campo_nlu in ("zona", "region") and valor == "No Clasificado":
                # Sin clasificar: la columna trae '0' o vacío en esos registros
                filt_clause += f" AND ({col_sql} IS NULL OR {col_sql} = '0' OR {col_sql} = '')"
            elif valor:
                filt_clause += f" AND UPPER({col_sql}) = UPPER(?)"
                params.append(valor)

        contra = nlu.get("contraloria")
        if contra:
            col_contra = "cat_Contraloria_6" if nlu.get("contraloria_nivel") == "6" else "cat_Contraloria"
            filt_clause += f" AND UPPER({col_contra}) = UPPER(?)"
            params.append(contra)

        pdc = nlu.get("pdc")
        if pdc:
            eco_pdv = self.pdc_a_eco_pdv.get(pdc)
            if eco_pdv is not None:
                filt_clause += " AND ECO_PDV = ?"
                params.append(eco_pdv)
            else:
                filt_clause += " AND UPPER(cat_PDC) = UPPER(?)"
                params.append(pdc)

        return filt_clause, params

    def _nombre_entidad(self, nlu: dict) -> str:
        """Nombre legible de TODAS las entidades filtradas, para títulos/resúmenes.

        2026-08-31 (feedback del usuario): antes devolvía solo la entidad más
        específica (CECO > Cuenta > PDC > Zona > Región > Territorio > División
        > Grupo) e ignoraba las demás en silencio — una pregunta como "PDV de
        Territorio Jalisco en Gastos de Nomina" SÍ filtraba por territorio en
        el SQL, pero el título solo decía "Cuenta 'Gastos de Nómina'" y el
        usuario no podía confirmar que el territorio también se había
        aplicado. Ahora concatena todas las entidades detectadas, en el mismo
        orden de especificidad, para que la respuesta sea trazable de un
        vistazo sin tener que abrir el SQL de linaje."""
        partes: List[str] = []

        ceco = nlu.get("ceco")
        if ceco:
            partes.append(f"CECO {ceco}")
        eco_pdv_directo = nlu.get("eco_pdv_directo")
        if eco_pdv_directo is not None:
            nombres = self.eco_pdv_a_nombres.get(eco_pdv_directo, [])
            etiqueta = f" ({nombres[0]})" if nombres else ""
            partes.append(f"PDV {eco_pdv_directo}{etiqueta}")
        cta = nlu.get("cuenta")
        if cta:
            partes.append(f"Cuenta '{cta}'")
        agr = nlu.get("agrupador_reales")
        if agr:
            partes.append(f"Agrupador de Reales '{agr}'")
        pdc = nlu.get("pdc")
        if pdc:
            partes.append(f"PDC '{pdc}'")
        zona = nlu.get("zona")
        if zona:
            partes.append(f"Zona '{zona}'")
        region = nlu.get("region")
        if region:
            partes.append(f"Región '{region}'")
        terr = nlu.get("territorio")
        if terr:
            partes.append(f"'{terr}'" if "territorio" in terr.lower() else f"Territorio '{terr}'")
        div = nlu.get("division")
        if div:
            partes.append(f"'{div}'" if "division" in div.lower() else f"División '{div}'")
        contra = nlu.get("contraloria")
        if contra:
            partes.append(f"'{contra}'" if "contraloria" in contra.lower() else f"Contraloría '{contra}'")
        gpo = nlu.get("grupo_cuentas")
        # Evita "Cuenta 'X' + Grupo 'X'" cuando el mismo texto matcheó ambos
        # catálogos (p.ej. "Gastos de Nómina" existe igual en cat_Cuentas y
        # en cat_Grupo_de_Cuentas) — es la misma entidad, no dos filtros.
        if gpo and gpo != cta:
            partes.append(f"Grupo '{gpo}'")

        if not partes:
            return "Consolidado Global"
        return " + ".join(partes)

    def process_query(self, text: str, contexto_previo: Optional[dict] = None, canal: str = "Fisico") -> dict:
        """`contexto_previo`: dict opcional con los `filtros_resueltos` de la
        respuesta anterior (ver más abajo) — permite resolver follow-ups como
        "¿y por semana?" o "¿y en 2025?" que no repiten el CECO/división/etc.
        ya mencionado en el turno previo.
        `canal` (2026-10-21): 'Fisico' (default), 'Digital' o 'Ambos', el mismo del filtro global del tablero;
        `_exec_sql` redirige las consultas a las vistas digitales (consolidado_dig / ceco_summary_dig)."""
        self._tl.canal = canal if canal in ("Fisico", "Digital", "Ambos") else "Fisico"
        if not text or not text.strip():
            return self._respuesta_vacia("Por favor escribe una pregunta sobre el gasto o documentación del sistema.")

        # Léxico de sinónimos (rag/lexico/sinonimos.json): "centros de costos" -> ceco, etc.
        norm_query = _numeros_a_digitos(_canonizar(normalizar_texto(text)))

        # "Gasto con la versión de la semana N" (snapshots datos/r26_semNN.parquet): se revisa antes del NLU general.
        if self._es_consulta_version(norm_query):
            return self._responder_version(text, norm_query)

        # Variaciones dinámicas entre métricas de Ppto 2027 (SIE vs CONTA, etc.)
        # Se detectan ANTES del bloque ppto2027 porque comparten keywords con él.
        _METRICAS_PRE = {
            "sie": "Reglas_2026", "conta": "Ordinario_2026", "contabilidad": "Ordinario_2026",
            "ordinario": "Ordinario_2026", "comparabilidad": "Ppto_2026", "ppto": "Ppto_2026",
            "fcst": "Fcst_Oficial_2026", "forecast": "Fcst_Oficial_2026",
        }
        _cols_pre = list({col for kw, col in _METRICAS_PRE.items() if kw in norm_query})
        if len(_cols_pre) >= 2 and any(kw in norm_query for kw in ["vs", "variacion", "diferencia", "contra", "versus", "comparar"]):
            nlu_pre = self._parse_nlu(text, norm_query, contexto_previo=contexto_previo)
            nlu_pre["ruta"] = "variacion_ppto"
            nlu_pre["metricas_variacion"] = _cols_pre[:2]
            return self._execute_financial_routing(text, norm_query, nlu_pre)

        # Ruta aislada para preguntas sobre el Presupuesto 2027 ("Ppto 2027",
        # otro proyecto/dataset, integrado 2026-09-15). Se revisa ANTES del
        # NLU financiero de Gasto Canal Fisico y con gatillos explícitos para
        # no interferir con el enrutador calibrado existente (catálogos,
        # umbrales de fuzzy-match, etc. son de OTRO dataset).
        if self._es_consulta_ppto2027(norm_query):
            return self._responder_ppto2027(text, norm_query)

        nlu = self._parse_nlu(text, norm_query, contexto_previo=contexto_previo)
        # Canal dicho en la pregunta ("canales digitales") manda sobre el filtro global del tablero.
        if nlu.get("canal_texto") and nlu["ruta"] != "variaciones_semana" and (nlu["canal_texto"] == "Fisico" or self.hay_digital):
            self._tl.canal = nlu["canal_texto"]

        doc_results = []
        if nlu["ruta"] in ("documental", "mixta", "sin_coincidencias"):
            doc_results = self.local_doc_rag.search(text, top_k=3)

        if nlu["ruta"] == "documental":
            return self._format_documental_response(text, nlu, doc_results)

        if nlu["ruta"] == "sugerencia_entidad":
            return self._respuesta_sugerencia_entidad(text, nlu)

        if nlu["ruta"] == "aclaracion":
            return self._respuesta_aclaracion(text, nlu.get("ml_opciones", []))

        if nlu["ruta"] in ("financiera", "mixta", "anomalias", "alertas_sobregasto", "senales_sobregasto", "variaciones_semana", "estructura", "variacion_ppto", "top_desviaciones", "top_gasto_entidad", "pareto",
                           "tendencia_semanal", "tendencia_mensual", "semana_vs_semana", "ultimas_4_vs_anteriores",
                           "real_2026_vs_real_2025", "cecos_sin_match", "calidad_linaje", "servicio_detalle", "multidimensional",
                           "variacion_general"):
            res_fin = self._execute_financial_routing(text, norm_query, nlu)
            if doc_results and nlu["ruta"] == "mixta":
                res_fin["citas_documentales"] = doc_results
                res_fin["tipo_respuesta"] = "mixta"
                res_fin["intencion_detectada"] += " + Evidencia Documental Local RAG"
            res_fin["filtros_resueltos"] = {
                "ceco": nlu.get("ceco"),
                "eco_pdv_directo": nlu.get("eco_pdv_directo"),
                "division": nlu.get("division"),
                "territorio": nlu.get("territorio"),
                "zona": nlu.get("zona"),
                "region": nlu.get("region"),
                "contraloria": nlu.get("contraloria"),
                "contraloria_nivel": nlu.get("contraloria_nivel"),
                "grupo_cuentas": nlu.get("grupo_cuentas"),
                "cuenta": nlu.get("cuenta"),
                "agrupador_reales": nlu.get("agrupador_reales"),
                "pdc": nlu.get("pdc"),
            }
            # Entidad aplicada con poca seguridad: la respuesta usa la mejor opción y se
            # ofrecen otras tres como botones ("¿Quisiste decir...?").
            if nlu.get("ml_incierta"):
                opciones = alternativas_para_boton(text, nlu["ml_incierta"][0])
                if opciones:
                    res_fin["alternativas_entidad"] = {
                        "mensaje": f"¿Quisiste decir otra opción en lugar de "
                                   f"**'{nlu['ml_incierta'][0]['canon']}'**?",
                        "opciones": opciones,
                    }
            if nlu.get("contexto_aplicado"):
                res_fin["respuesta_ejecutiva"] = (
                    "*(Se reutilizó el filtro de tu pregunta anterior — dilo explícitamente si quieres cambiarlo.)*\n\n"
                    + res_fin["respuesta_ejecutiva"]
                )
            return res_fin

        if doc_results and "error" not in doc_results[0]:
            return self._format_documental_response(text, nlu, doc_results)

        return self._respuesta_vacia(f"No se encontraron registros ni documentos normativos para **'{text}'**.")

    def _execute_financial_routing(self, raw_query: str, norm_query: str, nlu: dict) -> dict:
        ruta = nlu["ruta"]

        if nlu.get("ceco_inexistente"):
            return self._respuesta_sin_datos(
                f"El CECO **{nlu['ceco_inexistente']}** no fue localizado en el catálogo de datos consolidados."
            )

        if ruta == "multidimensional":
            return self._query_multidimensional(nlu)
        elif ruta == "variacion_general":
            return self._query_variacion_general(nlu)
        elif ruta == "top_desviaciones":
            return self._query_top_desviaciones(nlu)
        elif ruta == "top_gasto_entidad":
            return self._query_top_gasto_entidad(nlu)
        elif ruta == "pareto":
            return self._query_pareto(nlu)
        elif ruta == "tendencia_mensual":
            return self._query_tendencia_mensual(nlu)
        elif ruta == "tendencia_semanal":
            return self._query_tendencia_semanal(nlu)
        elif ruta == "semana_vs_semana":
            return self._query_semana_vs_semana(nlu)
        elif ruta == "ultimas_4_vs_anteriores":
            return self._query_ultimas_4_vs_anteriores(nlu)
        elif ruta == "real_2026_vs_real_2025":
            return self._query_real26_vs_real25(nlu)
        elif ruta == "anomalias":
            return self._query_anomalias_mad(nlu)
        elif ruta == "alertas_sobregasto":
            return self._query_alertas_sobregasto(nlu)
        elif ruta == "senales_sobregasto":
            return self._query_senales_sobregasto(nlu)
        elif ruta == "variaciones_semana":
            return self._query_variaciones_semana(nlu)
        elif ruta == "estructura":
            return self._query_estructura(raw_query, norm_query, nlu)
        elif ruta == "variacion_ppto":
            return self._query_variacion_ppto(nlu)
        elif ruta == "cecos_sin_match":
            return self._query_match_cecos(nlu)
        elif ruta == "calidad_linaje":
            return self._query_calidad_linaje(nlu)
        elif ruta == "servicio_detalle":
            return self._query_plano4_servicio(nlu)
        else:
            return self._query_consulta_estandar(raw_query, nlu)

    # -------------------------------------------------------------------------
    # NUEVA CONSULTA MULTI-DIMENSIONAL DINÁMICA (Ej. Territorio por Semana)
    # -------------------------------------------------------------------------
