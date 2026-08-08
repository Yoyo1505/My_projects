# Matriz de Fusión e Integración de Componentes

## Clasificación e Integración de Funcionalidades

| Componente | Origen | Decisión | Ubicación Objetivo | Razón y Beneficio |
|---|---|---|---|---|
| Engine ETL DuckDB + Polars | Principal | **Mejorar** | `pipelines/transform/build_data.py` | Optimiza velocidad y streaming sin saturar la memoria RAM. |
| UI Dashboard Streamlit | Principal | **Modularizar** | `app/frontend/` & `app/components/` | Separa la interfaz de la lógica de negocio y evita monopolizar `app.py`. |
| Scripts BAT Operativos | Referencia | **Reutilizar y Adaptar** | `scripts/*.bat` | Proporciona accesos rápidos e intuitivos para usuario no técnico. |
| Orquestación de Logs UTF-8 | Referencia | **Fusionar** | `logs/actualizaciones.log` | Ofrece trazabilidad detallada de ejecuciones y diagnóstico. |
| Calibrador de Catálogos | Referencia | **Adaptar** | `pipelines/validate/calibrar_mapping.py` | Detecta desalineaciones en catálogos antes de generar agregados. |
| Sistema RAG Local | Consolidado | **Crear** | `rag/` | Permite consultas de lenguaje natural sobre el proyecto con citas exactas. |
| Manuales Ejecutivos PDF/HTML | Referencia | **Fusionar** | `docs/operacion/` & `scripts/generar_manual.py` | Genera documentación impresa/imprimible alineada al negocio. |
