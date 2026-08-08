# Dashboard Vista Territorio — Tableros y alertas con IA

Dashboard financiero en **Streamlit** con **tableros interactivos**, drill-down territorial/contable y **alertas asistidas por IA** (riesgos, oportunidades y señales de seguimiento).

## Demo pública

- **Sin login** ni logo corporativo — cualquiera puede abrir el repo y ver el dashboard  
- **Tema visual oscuro** nuevo (sin la paleta/reglas de formato anteriores)  
- Si no hay `aggs/`, se generan **datos demo sintéticos** al arrancar (`seed_demo_data.py`)

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
- SQL Server (opcional, solo en entornos privados)

## Inicio rápido

```powershell
cd Vista Territorio
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py --server.port 8502
```

Abre **http://localhost:8502** — entra directo al dashboard (sin contraseña).

> Primera ejecución: se crea `aggs/` con datos demo si no existe.  
> Datos reales de negocio **no** se versionan en git.

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
