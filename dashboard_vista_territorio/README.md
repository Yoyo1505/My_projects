# Dashboard Vista Territorio — Tableros y alertas con IA

Dashboard financiero en **Streamlit** con **tableros interactivos**, drill-down territorial/contable y **alertas asistidas por IA** (riesgos, oportunidades y señales de seguimiento).

## Qué incluye

- Tableros: Real / Plan / Nvo Plan / Forecast de cierre  
- Jerarquía territorial: Agrupa 1 → División → Territorio → Zona → Región → PDC  
- Jerarquía contable: Agrupa 1 → Grupo de cuentas → Cuentas → PosPre  
- Pipeline ETL semanal (`extraer_sql.py` → `build_data.py` → `actualizar.py`)  
- Alertas y módulo de riesgos/oportunidades  
- Pruebas de integridad de drill-down (`tests/`)

## Stack

- Streamlit, Plotly  
- Polars, Pandas, DuckDB  
- SQL Server (opcional, vía `pyodbc`)  

## Inicio rápido

```powershell
cd dashboard_vista_territorio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.ejemplo .env
copy usuarios.ejemplo.json usuarios.json
streamlit run app.py --server.port 8502
```

Abre **http://localhost:8502**.

> Sin parquets/aggs completos (generados localmente o desde zips `App_y_Aggs`), algunas vistas pueden quedar vacías. Esos datos **no** van en git.

## Actualización semanal (con SQL)

```powershell
python actualizar.py
python actualizar.py --force
python build_data.py --aggs-only
```

## Documentación

| Archivo | Contenido |
|---------|-----------|
| [MANUAL_USUARIO.md](MANUAL_USUARIO.md) | Uso del tablero |
| [MANUAL_ACTUALIZACION.md](MANUAL_ACTUALIZACION.md) | ETL y refresh |
| [MANUAL_TECNICO.md](MANUAL_TECNICO.md) | Arquitectura técnica |
| [PLAN_RAG_ALERTAS.md](PLAN_RAG_ALERTAS.md) | Alertas / IA |
| [DATA.md](DATA.md) | Datos y secretos fuera del repo |

## Datos fuera del repositorio

Mantén fuera de git (y de esta carpeta en GitHub):

- `.env`, `usuarios.json`
- Parquets, catálogo de estructura, respaldos
- Zips `*_App_y_Aggs`

Ver [DATA.md](DATA.md).
