# Comparativo de Proyectos: Vista Territorio vs. Servidor Administración y Finanzas

## Matriz Comparativa de Capacidades

| Criterio | Proyecto Principal (Vista Territorio) | Proyecto Referencia (Servidor Finanzas) | Estrategia Consolidada |
|---|---|---|---|
| **Interfaz Principal** | Streamlit (Interactivo, HTML Trees, KPIs con señales) | HTML/JS Standalone (Servidor HTTP local) | **Streamlit Modularizado** con componentes HTML enriquecidos. |
| **Engine de Datos** | DuckDB + Polars + PyArrow (Parquet precalculado) | JSON inyectado en HTML + Scripts Python de extracción | **DuckDB + Polars + PyArrow** (máximo rendimiento y streaming). |
| **Operabilidad Local** | Ejecución por terminal / comandos manuales | Scripts `.bat` automatizados para instalación, actualización y servidor | **Lanzadores `.bat` y `.ps1`** en `scripts/` adaptados. |
| **Logging y Diagnóstico** | Logs de consola y archivos sueltos (`actualizacion.log`) | Logging estructurado UTF-8 (`actualizaciones.log`) | **Logging Estructurado UTF-8** centralizado en `logs/`. |
| **Gestión de Catálogos** | Lectura directa de Excel (`Catálogo de estructura.xlsx`, etc.) | Calibrador de mapeos (`calibrar_mapping.py`) | **Pipeline de validación de esquemas y calibración** en `pipelines/validate/`. |
| **Documentación** | Extensa en Markdown (`CLAUDE_*.md`, `MANUAL_*.md`) | Extensa en Markdown (`MD's/`) y PDF generado (`generar_manual.py`) | **Sistema RAG Local** que indexa Markdown, Python, SQL y esquemas. |

## Ventajas Clave a Integrar del Proyecto de Referencia
1. **Lanzadores por lotes `.bat` y `.ps1`**: Simplifican la instalación de dependencias, validación de entorno, ejecución de la app, reconstrucción del RAG y ejecuciones de prueba sin depender de la terminal interactiva.
2. **Sistema de logging UTF-8**: Mantiene una bitácora auditada de todas las fases del ETL y errores de ejecución.
3. **Calibración y validación de catálogos**: Herramientas para detectar registros sin correspondencia (llaves huérfanas) antes de consolidar.
4. **Motor de generación de entregables**: Generador de documentación e informes ejecutivos.
