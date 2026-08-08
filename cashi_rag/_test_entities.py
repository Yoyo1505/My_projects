import duckdb
import json
from pathlib import Path

aggs_dir = Path("aggs")
con = duckdb.connect()

divs = [r[0] for r in con.execute("SELECT DISTINCT cat_Direccion_Division FROM read_parquet('aggs/_consolidado.parquet')").fetchall()]
terrs = [r[0] for r in con.execute("SELECT DISTINCT cat_Subdireccion_Territorio FROM read_parquet('aggs/_consolidado.parquet') LIMIT 20").fetchall()]
gpos = [r[0] for r in con.execute("SELECT DISTINCT cat_Grupo_de_Cuentas FROM read_parquet('aggs/_consolidado.parquet')").fetchall()]

print("DIVISIONES:", divs)
print("\nTERRITORIOS (sample):", terrs[:10])
print("\nGRUPOS DE CUENTAS:", gpos)
