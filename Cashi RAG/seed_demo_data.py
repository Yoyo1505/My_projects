"""Create a synthetic, disposable finance dataset for Cashi RAG demos."""
from __future__ import annotations

import json
from pathlib import Path

import duckdb

BASE = Path(__file__).resolve().parent
AGGS = BASE / "aggs"
AGGS.mkdir(parents=True, exist_ok=True)

con = duckdb.connect()
con.execute("""
COPY (
    WITH entities AS (
        SELECT * FROM (VALUES
            ('Direccion Norte', 'Territorio Metro Norte', 'Zona Norte', 'Region Uno', 'NOM-001', 'Gastos de Nomina', 'Nomina administrativa', 'Contraloria A', 'Contraloria 6A', 'PDC Norte 1', 1001),
            ('Direccion Norte', 'Territorio Bajio', 'Zona Centro', 'Region Uno', 'REN-002', 'Renta y Servicios', 'Renta', 'Contraloria A', 'Contraloria 6A', 'PDC Bajio 1', 1002),
            ('Direccion Centro', 'Territorio Jalisco', 'Zona Occidente', 'Region Dos', 'LUZ-003', 'Renta y Servicios', 'Energia electrica', 'Contraloria B', 'Contraloria 6B', 'PDC Jalisco 1', 2001),
            ('Direccion Centro', 'Territorio Metro Centro', 'Zona Centro', 'Region Dos', 'MTO-004', 'Mantenimiento', 'Mantenimiento de equipos', 'Contraloria B', 'Contraloria 6B', 'PDC Centro 1', 2002),
            ('Direccion Sur', 'Territorio Sureste', 'Zona Sur', 'Region Tres', 'FLE-005', 'Fletes y Transportes', 'Fletes', 'Contraloria C', 'Contraloria 6C', 'PDC Sureste 1', 3001),
            ('Direccion Sur', 'Territorio Peninsula', 'Zona Sur', 'Region Tres', 'PUB-006', 'Publicidad', 'Publicidad local', 'Contraloria C', 'Contraloria 6C', 'PDC Peninsula 1', 3002)
        ) AS t(cat_Direccion_Division, cat_Subdireccion_Territorio, cat_Subdireccion_Zona,
               cat_Subdireccion_Region, ID_CENTRO_COSTOS, cat_Grupo_de_Cuentas, cat_Cuentas,
               cat_Contraloria, cat_Contraloria_6, cat_PDC, ECO_PDV)
    ), weeks AS (
        SELECT sem FROM range(1, 44) t(sem)
    ), series AS (
        SELECT * FROM (VALUES ('R25'), ('P26'), ('R26')) t(Serie)
    ), expanded AS (
        SELECT e.*, w.sem, s.Serie,
               CAST((CAST(w.sem AS INTEGER) * 17000 + (e.ECO_PDV * 19) % 50000)
                * CASE s.Serie WHEN 'R25' THEN 0.92 WHEN 'P26' THEN 1.00 ELSE 1.03 END AS DOUBLE) AS monto
        FROM entities e CROSS JOIN weeks w CROSS JOIN series s
    )
    SELECT *, monto AS monto_cons,
           ((sem - 1) / 4 + 1) AS MES,
           cat_Grupo_de_Cuentas AS cat_Agrupa1,
           cat_Grupo_de_Cuentas AS cat_Agrupador_Reales,
           cat_Cuentas AS cat_Agrupa2,
           cat_Cuentas AS cat_Agrupa3,
           cat_PDC AS cat_PDC
    FROM expanded
) TO '""" + (AGGS / "_consolidado.parquet").as_posix() + """' (FORMAT PARQUET)
""")

(AGGS / "_meta.json").write_text(json.dumps({
    "sem_max_real": 43,
    "sem_max_plan": 53,
    "source": "synthetic-demo",
    "generated_by": "seed_demo_data.py",
}, indent=2), encoding="utf-8")

print(f"Created synthetic demo data in {AGGS}")
