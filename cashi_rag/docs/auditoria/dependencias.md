# Auditoría de Dependencias del Sistema

## Dependencias de Python (`requirements.txt`)

| Biblioteca | Versión Requerida | Uso Principal |
|---|---|---|
| `streamlit` | `>=1.28.0` | Framework de interfaz gráfica de usuario |
| `polars` | `>=0.19.0` | Ingestión rápida, filtrado lazy y transformaciones de datos |
| `duckdb` | `>=0.9.0` | Motor relacional SQL en memoria/disco para joins masivos y agregaciones |
| `pyarrow` | `>=12.0.0` | Formato e interoperabilidad Parquet / IPC de alta velocidad |
| `pandas` | `>=2.0.0` | Compatibilidad y formateo Styler en Streamlit |
| `plotly` | `>=5.15.0` | Gráficas interactivas de tendencia y barras |
| `openpyxl` | `>=3.1.0` | Lectura y parseo de catálogos Excel |
| `pyodbc` | `>=4.0.39` | Conector a SQL Server (para `extraer_sql.py`) |
| `python-dotenv` | `>=1.0.0` | Gestión de variables de entorno locales (`.env`) |

## Requisitos de Entorno
- **Python**: `>=3.9` (Recomendado 3.10+)
- **OS**: Windows 10/11 / Windows Server
- **Shell**: PowerShell 5.1+ / CMD para scripts BAT
