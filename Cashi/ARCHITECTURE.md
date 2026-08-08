# Arquitectura del Sistema: Dashboard Vista Territorio - Mejorado

## Overview General

El proyecto **Dashboard Vista Territorio - Mejorado** ha sido diseñado bajo una arquitectura **Local-First, Modular y de Alto Rendimiento**.

Combinando **DuckDB + Polars + PyArrow** en la capa de datos, **Streamlit** en la interfaz interactiva, y un **Motor RAG Local** integrado para responder preguntas con citas exactas, el sistema garantiza cero dependencia de servicios externos en la nube.

```
┌────────────────────────────────────────────────────────┐
│                    USUARIO / NAVEGADOR                 │
│              http://localhost:8501 (Streamlit)          │
└──────────────────────────┬─────────────────────────────┘
                           │
       ┌───────────────────┴───────────────────┐
       ▼                                       ▼
┌───────────────────────────────┐   ┌───────────────────────────────┐
│     FRONTEND INTERACTIVO      │   │      ASISTENTE RAG LOCAL      │
│  - Vistas Analíticas          │   │  - Buscador BM25 Semántico    │
│  - Árboles HTML Perezosos     │   │  - Citas exactas a código y   │
│  - Formato Contable MDP       │   │    documentación técnica      │
└──────────────┬────────────────┘   └──────────────┬────────────────┘
               │                                   │
               └───────────────────┬───────────────┘
                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                       BACKEND & SERVICES                          │
│  - app/services/financial_calculations.py (Fórmulas y Reglas)     │
│  - app/services/data_engine.py (Lectura Lazy / DuckDB Cache)      │
│  - rag/query.py & rag/indexer.py (Motor de Búsqueda)              │
└──────────────────────────────────┬────────────────────────────────┘
                                   │
                                   ▼
┌───────────────────────────────────────────────────────────────────┐
│                       CAPA DE DATOS (PARQUET)                     │
│  - aggs/_consolidado.parquet (Formato largo transaccional)       │
│  - aggs/*.parquet (22+ Agregados en formato ancho)               │
│  - Catálogos Excel (Estructura, Cuentas, Puntos de Contacto)      │
└───────────────────────────────────────────────────────────────────┘
```

## Módulos del Sistema
- `app/services/`: Centraliza el cálculo de métricas financieras y la gestión de parquets.
- `app/components/`: Renderiza árboles HTML, tarjetas KPI ejecutivas y formateadores contables.
- `pipelines/transform/`: Pipeline ETL en DuckDB y Polars (`build_data.py`).
- `rag/`: Motor de indexación y recuperación semántica en español sobre el código y reglas.
- `scripts/`: Lanzadores automatizados por lotes (`.bat` y `.ps1`).
