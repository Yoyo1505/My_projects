# Inventario del Proyecto Principal: Dashboard Vista Territorio

## Overview
- **Ruta de origen**: `E:\Usuarios\112665\Downloads\Dashboard Vista Territorio - copia`
- **Carpeta de consolidación y trabajo**: `E:\Usuarios\112665\Downloads\Dashboard Vista Territorio - mejorado`
- **Propósito**: Dashboard ejecutivo y analítico para la gestión financiera y territorial de gasto de Grupo Elektra.

## Componentes Principales

### 1. Aplicación Frontend (Streamlit)
- `app.py` (~166 KB, ~3,000 líneas):
  - Frontend completo desarrollado en Streamlit.
  - Implementa motor de cálculo en memoria (`_medidas()`, `compute()`, `_agregar_df()`).
  - Renderizado HTML/CSS de Árboles Perezosos (`arbol_perezoso`, `arbol_multicol`, `arbol_jerarquia`).
  - Formato contable estricto en Millones de Pesos (MDP), positivo=gasto entre paréntesis/rojo (`.vt-pos`), negativo=ahorro sin paréntesis/carbón (`.vt-neg`).
  - Tarjetas KPI ejecutivas con banderas de señal ▲ (gasto arriba / rojo) y ▼ (ahorro / azul).
  - Pestañas: Resumen, Temporalidad, Div / Terr, Detalle Cuenta, Detalle PDC, PDC & Calor, Cierres, Trimestres.
  - Generación de reportes PDF mediante exportación HTML responsiva.

### 2. Pipeline ETL y Backend de Datos
- `build_data.py` (~59 KB, ~1,200 líneas):
  - Motor de extracción, transformación y carga basado en DuckDB + Polars.
  - Fusiona las 4 series temporales: Real 2025, Plan 2026, Real 2026, y Nvo Plan 2026 (ancho, 53 semanas).
  - Cruza catálogos locales en Excel (`Catálogo grupo cuentas.xlsx`, `Catálogo de estructura.xlsx`, `FCST VTA RAPIDA.xlsx`, `Seguimiento Expansion.xlsx`, `Puntos de contacto.xlsx`).
  - Genera la fuente maestra `aggs/_consolidado.parquet` (formato largo, ~1.4 GB) y 22+ agregados precalculados en formato ancho en `aggs/*.parquet`.
  - Exporta JSONs auxiliares de metadatos (`_meta.json`, `pdc_ids.json`, `pdc_cecos.json`, `orden_gpo.json`, `responsables_gpo.json`, `riesgos.json`).

### 3. Orquestación y Extracción
- `actualizar.py`: Orquestador de la actualización semanal, verifica cortes de semana EKT y llama a `build_data.py --aggs-only`.
- `extraer_sql.py`: Extractor SQL Server transaccional (persiste en `r25_semXX.parquet`, `r26_semXX.parquet`, `p26_semXX.parquet`).
- `semana.py`: Lógica de semanas EKT, calendario corporativo y resolución de parquets más recientes.
- `generar_pdf.py`: Generador de entregable ejecutivo en PDF.
- `generar_correo_canales.py`: Generador de reporte HTML para envío por correo electrónico.

### 4. Pruebas y Control de Calidad
- `_test_smoke.py`: Smoke test raíz que valida carga de datos, coincidencia de `SECCIONES` y funciones de medidas.
- Carpetas `tests/`: Pruebas de drill-down (`test_drill.py`), integridad de datos (`integridad.py`), prorrateo (`test_prorrateo.py`), y paleta de colores (`paleta_check.py`).

### 5. Documentación Técnica y Manuales
- `CLAUDE_CONTEXTO_MAESTRO.md` (20.9 KB): Contexto maestro del proyecto, estructura de carpetas, mapeos y bitácora de parches.
- `MAPA_CODIGO.md` (8.4 KB): Mapa de funciones, reglas fijas de presentación y estructura de `app.py`.
- `CLAUDE_errores_build.md` (11.3 KB): Bitácora histórica de errores resueltos en DuckDB/Polars/Excel.
- `MANUAL_TECNICO.md`, `MANUAL_ACTUALIZACION.md`, `MANUAL_USUARIO.md`, `PLAN_RAG_ALERTAS.md`.
