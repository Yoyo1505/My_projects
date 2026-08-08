# Changelog — Dashboard Vista Territorio - Mejorado

## [Version 2.0.0] - 2026-08-03

### Añadido
- **Consolidación de Proyectos**: Integración de capacidades del servidor de administración y finanzas (scripts por lotes `.bat`, orquestación de logs UTF-8, calibrador de mapeos) con la interfaz de Vista Territorio.
- **Asistente Cashi Integrado en UI**: Incorporada la pestaña **`🤖 Cashi`** dentro del Dashboard Streamlit en `app.py`, permitiendo consultas en lenguaje natural sobre CECOs, Divisiones, Nómina, Rentas, Publicidad, Match de CECOs, desgloses semanales y acumulados a semanas específicas.
- **RAG Local Integrado**: Motor de indexación y búsqueda semántica en español en `rag/` (`indexer.py` y `query.py`), con 724 fragmentos indexados y citas exactas.
- **Suite de Scripts Operativos**: Incorporados en `scripts/` (instalación, validación de entorno, actualización de datos, lanzador Streamlit, reconstrucción RAG, ejecutor de pruebas).
- **Documentación de Auditoría**: Generados en `docs/auditoria/` los inventarios, mapas de datos, linaje, matriz de fusión, reglas de negocio y análisis de riesgos.
- **Backend Modular**: Estructurados los módulos `app/services/` y `app/components/`.

### Mejorado
- **Rendimiento ETL**: Pipeline en `build_data.py` optimizado con DuckDB en memoria/disco spill y Polars.
- **Robustez**: Salvaguardas ante división por cero y manejo estricto de nulos.
- **Pruebas de Calidad**: Smoke tests en `_test_smoke.py` validados con éxito en las 8 secciones de la interfaz.

### Preservado
- Preservadas al 100% todas las reglas financieras corporativas (`Real 2025`, `Plan 2026`, `Nvo Plan 2026`, `Real 2026`, `Forecast`), formato en Millones MDP y split PosPre 1:2.
