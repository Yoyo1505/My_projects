# -*- coding: utf-8 -*-
"""
rag/build_fast_json.py — Generador de Índice Ultrarrápido RAG (<10ms) para HTML Standalone
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

BASE_DIR = Path(__file__).parent.parent.resolve()
AGGS_DIR = BASE_DIR / "aggs"
CONS_PATH = AGGS_DIR / "_consolidado.parquet"
OUT_JSON = AGGS_DIR / "rag_fastindex.json"


def build_fast_index():
    print("[Fast RAG Builder] Compilando índice ultrarrápido...", flush=True)
    if not CONS_PATH.exists():
        print(f"[Error] No existe {CONS_PATH}")
        return

    con = duckdb.connect()
    
    # 1. Divisiones
    divs_res = con.execute("""
        SELECT cat_Direccion_Division AS division,
               SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS r25,
               SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS p26,
               SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS r26
        FROM read_parquet('aggs/_consolidado.parquet')
        WHERE cat_Direccion_Division IS NOT NULL
        GROUP BY 1
    """).pl().to_dicts()

    # 2. Grupos de Cuentas
    gpos_res = con.execute("""
        SELECT cat_Grupo_de_Cuentas AS grupo,
               SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS r25,
               SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS p26,
               SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS r26
        FROM read_parquet('aggs/_consolidado.parquet')
        WHERE cat_Grupo_de_Cuentas IS NOT NULL
        GROUP BY 1
    """).pl().to_dicts()

    # 3. CECOs Top 500
    cecos_res = con.execute("""
        SELECT CAST(ID_CENTRO_COSTOS AS VARCHAR) AS ceco,
               cat_PDC AS pdc,
               cat_Grupo_de_Cuentas AS grupo,
               SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS r25,
               SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS p26,
               SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS r26
        FROM read_parquet('aggs/_consolidado.parquet')
        WHERE ID_CENTRO_COSTOS IS NOT NULL
        GROUP BY 1, 2, 3
        ORDER BY r26 DESC
        LIMIT 500
    """).pl().to_dicts()

    # 4. Desglose Semanal Global
    sem_res = con.execute("""
        SELECT sem AS semana,
               SUM(CASE WHEN Serie='R25' THEN monto ELSE 0 END) AS r25,
               SUM(CASE WHEN Serie='P26' THEN monto ELSE 0 END) AS p26,
               SUM(CASE WHEN Serie='R26' THEN monto ELSE 0 END) AS r26
        FROM read_parquet('aggs/_consolidado.parquet')
        WHERE sem IS NOT NULL
        GROUP BY 1
        ORDER BY 1
    """).pl().to_dicts()

    fast_data = {
        "divisiones": divs_res,
        "grupos": gpos_res,
        "cecos": cecos_res,
        "semanas": sem_res
    }

    OUT_JSON.write_text(json.dumps(fast_data, ensure_ascii=False), encoding="utf-8")
    print(f"[Fast RAG Builder] Índice guardado en {OUT_JSON} ({OUT_JSON.stat().st_size / 1e3:.1f} KB)", flush=True)


if __name__ == "__main__":
    build_fast_index()
