# Auditoría de Riesgos y Puntos Críticos

## 1. Riesgos Financieros e Integridad de Datos
- **Join Fan-Out (1:2 en Cuentas Especiales)**:
  - *Riesgo*: 12 Cta Mayor en el catálogo de cuentas tienen 2 filas duplicadas con distinto PosPre.
  - *Mitigación*: Se mantiene la regla documentada de conservar ambas filas sin prorratear el monto transaccional, indicándolo explícitamente en las vistas de detalle.
- **División por Cero**:
  - *Riesgo*: Presupuesto `Plan 2026` o `Real 2025` igual a cero genera `ZeroDivisionError` en variaciones porcentuales.
  - *Mitigación*: Implementación de salvaguarda `if denominator: ... else: 0.0` en todas las funciones de cálculo.

## 2. Riesgos de Rendimiento y Memoria
- **Materialización Excesiva de `_consolidado.parquet`**:
  - *Riesgo*: `_consolidado.parquet` tiene ~1.4 GB. Si se carga completo en memoria con pandas en cada petición, agota la RAM.
  - *Mitigación*: DuckDB se configura con límites de hilos (`PRAGMA threads=16`), límite de memoria (`PRAGMA memory_limit='16GB'`) y directorio temporal de spill a disco `_ddb_tmp`.

## 3. Riesgos Operativos y Entorno Windows
- **ThreatLocker / Permisos de Archivo**:
  - *Riesgo*: En Windows, ThreatLocker o bloqueos de archivo pueden generar `PermissionError (Errno 13)`.
  - *Mitigación*: Uso de manejo de excepciones y limpieza de procesos Python colgados antes de reiniciar Streamlit.
- **Rutas con Espacios**:
  - *Riesgo*: Nombres de carpetas como `Dashboard Vista Territorio - mejorado` contienen espacios.
  - *Mitigación*: Todos los scripts de PowerShell y BAT utilizan comillas explícitas y `pathlib.Path`.
