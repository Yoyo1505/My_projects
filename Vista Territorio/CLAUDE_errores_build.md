# Registro de errores — build_data.py / Dashboard Vista Territorio

Bitácora de bugs reales encontrados y corregidos en el pipeline. Se actualiza cada vez que aparece uno nuevo — no borrar entradas viejas, son historial.

## 2026-07-21 — Catálogos leídos desde la carpeta equivocada

**Síntoma:** el usuario corrigió duplicados en "Catálogo grupo cuentas.xlsx" y "Catálogo de estructura.xlsx" (dentro de la carpeta del dashboard), corrió el build, y los montos seguían saliendo duplicados.

**Causa raíz:** `build_data.py` tenía `CAT_CUENTAS = DL / "Catálogo grupo cuentas.xlsx"` con `DL = Path.home() / "Downloads"` — es decir, leía de la **raíz** de Downloads (archivo del 02/06, viejo), no de la copia corregida dentro de `Dashboard Vista Territorio\` (21/07). Dos copias del mismo nombre de archivo en carpetas distintas, el script apuntaba a la que no se editaba.

**Fix:** `CAT_CUENTAS` y `CAT_ESTRUCT` ahora apuntan a `BASE` (carpeta del propio script), no a `Path.home()/"Downloads"`.

**Cómo se detectó:** comparando `Get-ChildItem` de ambas rutas — `LastWriteTime` no coincidía con lo que el usuario acababa de editar.

**Prevención:** si el usuario dice "ya corregí el catálogo pero no se refleja", lo primero es verificar qué archivo *físico* está leyendo el script (`grep CAT_CUENTAS`/`CAT_ESTRUCT` en build_data.py) contra dónde el usuario realmente guardó el cambio, no asumir que hay un solo archivo con ese nombre.

---

## 2026-07-21 — `CREATE OR REPLACE VIEW` no reemplaza una tabla registrada por Arrow con el mismo nombre

**Síntoma:** `build_data.py --rebuild` fallaba en `build_forecast_ceco()` con:
```
_duckdb.BinderException: Binder Error: Values list "c" does not have a column named "cat_Grupo_de_Cuentas"
```
pese a que el código tenía un `try/except` que debía detectar justo ese caso y reconstruir la vista `cat_c` con el alias correcto.

**Causa raíz:** en `build_consolidado()`, `con.register("cat_c", cta.to_arrow())` registra `cat_c` como **tabla** Arrow (columnas crudas, sin alias `cat_*`). Más adelante, `build_forecast_ceco()` detecta que falta el alias (el `try` sí falla como se espera) y ejecuta `CREATE OR REPLACE VIEW cat_c AS ...` para reemplazarla — pero DuckDB **no logra** reemplazar una tabla registrada por `.register()` con una vista SQL del mismo nombre: ambas coexisten y las consultas posteriores siguen resolviendo a la tabla vieja sin alias. `CREATE OR REPLACE` no lanza error, así que el bug es silencioso hasta que se usa `cat_Grupo_de_Cuentas` más abajo.

Reproducido aislado:
```python
con.register('cat_c', df.to_arrow())          # tabla cruda
con.execute('CREATE OR REPLACE VIEW cat_c AS SELECT ... AS cat_Grupo_de_Cuentas ...')  # "funciona"
con.execute('SELECT cat_Grupo_de_Cuentas FROM cat_c')  # BinderException: columna no existe
```

**Fix:** agregar `con.unregister("cat_c")` (envuelto en try/except por si no estaba registrada) inmediatamente antes del `CREATE OR REPLACE VIEW cat_c`, en `build_forecast_ceco()`.

**Prevención:** cualquier `CREATE OR REPLACE VIEW <nombre>` en DuckDB que pueda chocar con un `con.register(<mismo nombre>, ...)` previo en la misma conexión necesita el `unregister` explícito primero. No confiar en que "OR REPLACE" cubra también los objetos registrados vía Arrow.

---

## 2026-07-21 — Filtro de "Grupo de Cuentas" no respetaba el orden del catálogo

**Síntoma:** las tablas y gráficas sí mostraban el grupo de cuentas en el orden de la columna "Orden presentación Gpo. Cta" del catálogo, pero el multiselect de la barra lateral (`app.py`, filtro "Grupo de Cuentas") los listaba alfabéticamente.

**Causa raíz:** `_gpos = sorted(...)` sin `key=`, en vez de usar `_orden_gpo_key` (la función que ya existía y que sí usaban las tablas/gráficas vía `_agregar_df`).

**Fix:** `sorted(..., key=_orden_gpo_key)` en la construcción de `_gpos` (línea ~967 de `app.py`).

---

## 2026-07-21 — Drill-down territorial (pdc_pospre) colgaba el navegador

**Síntoma:** pestaña Detalle Cuenta, vista "Territorial completo": al abrir se colgaba el navegador con `WebSocketClosedError` en la consola de streamlit.

**Causa raíz doble:**
1. `pdc_pospre.parquet` (agg nuevo para las 2 vistas del drill-down) resultó en 17.75M filas porque Territorio/Zona/Región en el catálogo **no son una jerarquía limpia** (un mismo Territorio cae bajo ~20-25 combinaciones de Zona/Región) y eso se cruzaba con PDC (4,115 valores) y PosPre en un único `GROUP BY`.
2. `app.py` cargaba ese parquet completo en RAM al arrancar (`pl.read_parquet` en `load_all`) y encima pre-armaba el árbol **completo** en HTML de una sola vez (`_arbol_html` con `pandas.iterrows()`), generando miles de nodos `<details>` aunque el usuario nunca los viera.

**Fix (dos partes):**
- **Carga diferida**: `_AggsDiferidos` (clase dict con `__missing__`) en `app.py` — `conciliacion`, `pdc`, `cierres_det` y `pdc_pospre`/`cierres_pdc` ya NO se leen al arrancar; se cargan (con spinner) la primera vez que una pestaña los pide. Arranque bajó de leer ~1.1GB a ~25MB.
- **Árbol perezoso** (`arbol_perezoso()` en `app.py`): cada nivel del árbol se calcula solo cuando el usuario abre esa rama (`_nivel_arbol_perezoso`, filtra con `pl.scan_parquet`+`filter` antes de `collect()`). NO usa `st.expander` (Streamlit no permite anidarlos más de 1 nivel — con 7 niveles el render se rompía y solo se veía el primer grupo de la raíz). Usa `st.button` + `st.session_state` con `on_click` (evita doble rerun). Las hojas de una rama (pueden ser miles de PDCs) se agrupan en un solo `st.markdown`, no un widget por hoja — evita saturar el canal websocket.

**Prevención:** cualquier agg nuevo que cruce >4-5 columnas de alta cardinalidad combinada, medir el conteo de filas ANTES de usarlo en un árbol pre-renderizado. Si supera ~1M filas, usar carga lazy + render bajo demanda desde el inicio, no como parche posterior.

---

## 2026-07-21 — Pestaña "Movimiento" quedó a medias eliminada

**Síntoma:** se pidió quitar la pestaña Movimiento; se sacó de `SECCIONES` pero el bloque de código (~185 líneas: `MOV_COLS`, `_fila_mov`, `arbol_movimiento`, el `if SEC == "Movimiento"`) siguió completo en `app.py` como código muerto inalcanzable, y `EXTRA` seguía cargando `movimiento.parquet` sin necesidad.

**Fix:** eliminado el bloque completo (líneas ~2153 en adelante hasta el final del archivo en ese momento) y la carga de `movimiento.parquet` en `load_all`. `build_movimiento()` en `build_data.py` se dejó intacta (sigue generando el parquet por si se usa fuera del dashboard).

**Prevención:** al pedir "eliminar pestaña X", verificar que se quite tanto del menú de navegación (`SECCIONES`) como el bloque `if SEC == "X":` completo y cualquier carga de datos exclusiva de esa pestaña — un `grep` del nombre de la pestaña tras el cambio debe devolver solo comentarios/menciones incidentales, no código activo.

---

## 2026-07-21 — Filtro por ID_CENTRO_COSTOS: por qué NO se metió en el agg `pdc`

`ID_CENTRO_COSTOS` (columna cruda del CECO) tiene 21,056 valores únicos contra 4,115 de `cat_PDC` — varios PDC genéricos ("0", "Cerrados y Cancelados") agrupan cientos de CECOs. Meterlo en el agg `pdc.parquet` (agregación numérica por semana) habría multiplicado filas ~5x (7.8M → ~40M), repitiendo el problema de `pdc_pospre`.

**Solución aplicada:** `build_pdc_cecos()` en `build_data.py` genera `aggs/pdc_cecos.json` — un mapa ligero **solo de texto** `{cat_PDC: [lista de CECOs]}`, sin duplicar montos. `app.py` invierte el mapa (`_CECO_A_PDC`) y lo usa como filtro de texto en la pestaña Detalle PDC (campo "Buscar por ID Centro de Costos"), sin tocar el agg numérico.

**Prevención:** cuando se pida "agrega un filtro por columna X" y X tiene alta cardinalidad relativa a la dimensión ya agregada, evaluar primero si el filtro necesita vivir en el agg numérico (join con montos) o si basta un mapeo de texto aparte — casi siempre es lo segundo.

---

## 2026-07-21 — Riesgos y Oportunidades: de 2 a 4 secciones en el Word

El correo semanal "Canales Físicos" (`generar_correo_canales.py`, ver abajo) necesita texto narrativo separado para Semanal y YTD, cada uno con Negativas/Positivas — 4 combinaciones, no 2.

**Fix:** `build_riesgos()` en `build_data.py` reconoce ahora 4 títulos de párrafo en `Riesgos y Oportunidades.docx`: `RIESGOS`, `OPORTUNIDADES` (YTD, los que ya mostraba la pestaña Riesgos & Oport. del dashboard — compatibilidad retro intacta) y `RIESGOS SEMANAL`, `OPORTUNIDADES SEMANAL` (nuevos, opcionales — si no están en el Word, generan listas vacías sin romper nada). Sale todo a `aggs/riesgos.json` con 4 claves: `riesgos`, `oportunidades`, `riesgos_semanal`, `oportunidades_semanal`.

**Recordatorio operativo:** cada semana, Planeación debe pegar los comentarios de variaciones bajo los 4 títulos correspondientes en el Word (no solo los 2 de YTD), o las cajas "Semanal" del correo saldrán vacías ("Sin variaciones registradas").

---

## 2026-07-21 — generar_correo_canales.py: fórmula del "Forecast" semanal

Al automatizar el correo "Gasto Canales Físicos" (ver `generar_correo_canales.py`), la columna "Fcst 2026" no se pudo replicar con exactitud:

- **YTD**: sí es exacto — misma fórmula que `Forecast_Cierre` en `app.py` (`Real_2026` topado al corte real + `Plan_2026` de las semanas aún no reales, "Plan Restante").
- **Semanal** (una sola semana ya pasada, `hi <= smr`): `Forecast_Cierre` da `Plan_Restante = 0` ahí (no hay "semanas futuras" dentro de un rango de 1 semana ya real), así que la fórmula real no aplica. Se usa `Plan_2026` de esa semana como aproximación — decisión explícita del usuario, con ~2M de diferencia vs. el correo original (que aparentemente usa un forecast externo más fino no disponible en los aggs actuales).
- `forecast_ceco.parquet` (CSV externo) se descartó como fuente para esto: solo cubre 61 de ~2,028 cuentas — cobertura parcial, no apto para totales.

**Prevención:** si se pide reproducir un número exacto de un reporte de referencia y la fórmula candidata da resultados sistemáticamente distintos (no solo redondeo), no forzar — preguntar al usuario por la fórmula real en vez de iterar a ciegas. Aquí se hizo así y se resolvió en 1 pregunta.

---

## Notas de entorno relevantes para diagnosticar builds lentos

- **ThreatLocker** puede bloquear lectura de archivos recién editados (`Errno 13`) hasta que el usuario lo aprueba manualmente — ver `env_sandbox_lectura_bloqueada.md` en memoria.
- Comandos `Get-Process`/`Get-CimInstance` lanzados durante un build pesado (DuckDB con `PRAGMA threads=6`, `memory_limit=6GB`) pueden colgarse por contención de recursos y quedar como **procesos powershell.exe zombie** en segundo plano, que a su vez compiten por CPU/disco con el build y lo ralentizan más. Si un build va sospechosamente más lento que una corrida anterior equivalente, revisar `Get-CimInstance Win32_Process -Filter "Name='powershell.exe'"` y matar los que no correspondan a la sesión activa.
- El log de `build_data.py` hace *flush* con retraso bajo carga alta — que una línea no avance en el archivo de log no significa que el proceso esté trabado; confirmar siempre con CPU acumulado del proceso (`Get-Process python | Select CPU`) antes de asumir que se colgó.
