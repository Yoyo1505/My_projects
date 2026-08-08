# Arquitectura Actual del Sistema

## Diagrama de Bloques

```
┌────────────────────────────────────────────────────────┐
│                   CAPA DE DATOS                        │
│ - SQL Server VistaRapida (Tablas Real/Plan)             │
│ - nvo_plan_2026.parquet (Plan Modificado 53 sem)      │
│ - Catálogos Excel (Estructura, Cuentas, Puntos, etc.) │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   CAPA DE PROCESAMIENTO                │
│ - pipelines/transform/build_data.py                    │
│   (DuckDB Motor In-Memory + Polars Lazy DataFrames)    │
│ - Generación de aggs/_consolidado.parquet              │
│ - Materialización de 22+ agregados en aggs/*.parquet   │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                   CAPA DE PRESENTACIÓN                 │
│ - Streamlit Dashboard (app.py)                         │
│ - Visualización con Árboles Perezosos HTML/CSS         │
│ - Formato Contable Estricto en Millones MDP            │
│ - Reportes Ejecutivos PDF & Correo HTML                │
└────────────────────────────────────────────────────────┘
```

## Puntos de Entrada
- `app.py`: Entrada principal del dashboard analítico.
- `build_data.py`: Entrada principal para regenerar agregados.
- `actualizar.py`: Orquestador de actualización semanal.
- `scripts/*.bat`: Scripts de automatización operativa.
