# Contexto maestro — Dashboard Vista Territorio

**Leer ESTE archivo primero, siempre, antes de tocar código.** Contiene el
mapa de qué documento leer para qué, el estado de la carpeta completa
(incluyendo respaldos), y el estado más reciente de trabajo en curso. Evita
re-explorar la carpeta o releer `app.py`/`build_data.py` completos en cada
sesión nueva.

## Índice de documentación existente — leer el doc específico, no todo

| Documento | Contenido | Cuándo abrirlo |
|---|---|---|
| `MAPA_CODIGO.md` | Mapa de funciones/líneas de `app.py`, reglas de presentación fijas, lista de pestañas | Antes de editar CUALQUIER parte de `app.py` |
| `CLAUDE_errores_build.md` | Bitácora de bugs de `build_data.py` ya resueltos (DuckDB, catálogos, rutas) | Antes de tocar `build_data.py` o si un build falla raro |
| `MANUAL_TECNICO.md` | Arquitectura general, jerarquías de datos, algoritmos de render, tests | Para entender el diseño general, onboarding |
| `MANUAL_ACTUALIZACION.md` | Cómo correr la actualización semanal (`actualizar.py`) | Cuando el usuario pregunta cómo actualizar semana |
| `MANUAL_USUARIO.md` | Manual para el usuario final del dashboard (no técnico) | Nunca para desarrollo, solo si piden regenerar el PDF de usuario |
| `_CONTEXTO_SESION_CIERRES.md` | Detalle fino de la reconstrucción de la pestaña Cierres (2026-07-28) | Al tocar Cierres — este archivo se resume también más abajo |
| `requirements.txt` | Dependencias Python | Al reinstalar entorno |
| `README.md` | Overview genérico del repo | Rara vez necesario |

**Regla de oro:** si el mapa dice "línea ~2820" y no cuadra, es porque el
archivo se editó después de esa fecha — usar `Grep` para relocalizar, NO
`Read` completo (`app.py` son ~3000 líneas, ~ decenas de miles de tokens).

## Estructura de carpetas del proyecto

```
Dashboard Vista Territorio/
├── app.py                      ← Frontend Streamlit (TODO el dashboard, single-file)
├── build_data.py               ← Pipeline ETL: SQL → parquets → aggs/
├── actualizar.py               ← Orquestador de la actualización semanal
├── extraer_sql.py              ← Extracción de SQL Server a parquets crudos (r25_semXX, r26_semXX, p26_semXX)
├── semana.py                   ← Cálculo de semana actual / calendario EKT
├── generar_pdf.py              ← Genera el PDF de reporte
├── generar_correo_canales.py   ← Correo semanal "Canales Físicos" (separado del dashboard)
├── _crear_word_riesgos.py      ← Genera/actualiza Riesgos y Oportunidades.docx
├── analizar_aggs.py            ← Utilidad de diagnóstico de tamaños/cardinalidad de aggs/
├── estado.json                 ← Estado del build (fase/pct/error) que lee la UI
├── comentarios.json, usuarios.json ← Config auxiliar de la app
│
├── aggs/                       ← TODOS los parquets/json precomputados que lee app.py
│   ├── _consolidado.parquet    ← Fuente maestra, FORMATO LARGO (sem/Serie/monto + cat_*), Serie∈{R25,P26,R26,NVO}
│   ├── _meta.json, pdc_ids.json, pdc_cecos.json, orden_gpo.json, responsables_gpo.json, riesgos.json
│   ├── global.parquet, division.parquet, territorio.parquet, zona.parquet, region.parquet, pdc.parquet,
│   │   grupo_cuentas.parquet, cuentas.parquet, formato.parquet, naturaleza.parquet, agrupador*.parquet,
│   │   segmento1/2.parquet, estatus.parquet, clasificacion2.parquet, trimestre.parquet
│   │   — todos estos SÍ son formato ANCHO (columnas Real_2025/Plan_2026/Nvo_Plan_2026/Real_2026 directas)
│   ├── conciliacion.parquet     ← 41.5M filas, el más pesado — lazy-loaded (_AggsDiferidos)
│   ├── pdc_pospre.parquet, cierres_det.parquet, cierres_pdc.parquet(viejo, no usar) ← lazy-loaded también
│   ├── cierres_expansion.parquet ← el que SÍ usa la pestaña Cierres (Categoria x PDC, formato ancho)
│   ├── forecast_ceco.parquet, forecast_cuenta.parquet
│   └── movimiento.parquet       ← generado pero pestaña Movimiento ya no existe en la UI
│
├── .streamlit/config.toml      ← Config de Streamlit (tema, servidor)
├── .env / .env.ejemplo         ← Credenciales SQL Server (NO subir a git, ya en .gitignore)
├── .tmp/                        ← Logs de intentos de rebuild (rebuild_sem29*.log) — desechables
├── tests/                       ← Suite de pruebas (integridad, drill-down, prorrateo, paleta, smoke)
├── _test_smoke.py               ← Smoke test raíz (rápido, correr tras cambios grandes)
│
├── Excels fuente (NO tocar, son insumo, se leen tal cual):
│   ├── Catálogo de estructura.xlsx      ← catálogo maestro de dimensiones (PDC, División, etc.)
│   ├── Catálogo grupo cuentas.xlsx      ← catálogo de cuentas/grupos
│   ├── FCST VTA RAPIDA.xlsx             ← forecast por cuenta, MALFORMADO (ver bug conocido abajo)
│   ├── Seguimiento Expansion.xlsx       ← copia vieja/local, la fuente real está en OneDrive (ver Cierres abajo)
│   ├── Plan_de_Trabajo_Vista_Territorio.xlsx, Puntos de contacto.xlsx ← insumos de gestión, no de datos
│
├── Riesgos y Oportunidades.docx  ← fuente de riesgos.json (ver CLAUDE_errores_build.md, entrada 2026-07-21)
├── elektra_logo.png              ← logo embebido en PDF/login
├── Dashboard_Documentacion.pdf, Dashboard_Manual_de_Uso.pdf, Manual_Dashboard.html ← entregables generados, no editar a mano
│
├── _archivo/                     ← versión OBSOLETA/histórica del dashboard (Flask+HTML, pre-Streamlit). NO tocar, es arqueología.
│   ├── dashboard_backend.py, dashboard_frontend.html, static/index.html
│   ├── json_backup_pre_medidas/, json_dashboard_consolidado/  ← JSONs viejos de esa versión
│   ├── notebooks_originales/     ← los 3 notebooks (Plan 2026, Real 2025, Real 2026) que dieron origen al pipeline
│   └── *.bat, *.ps1, *.sh de esa era — el usuario NO usa .bat (ver memoria feedback_no_bat)
│
└── _respaldo/                    ← respaldos versionados manuales, ver tabla abajo
```

## Mapeo de `_respaldo/` (snapshots por fecha/hito)

| Carpeta/archivo | Qué es | Cuándo restaurar de aquí |
|---|---|---|
| `app_2026-07-21.py` … `app_2026-07-27_pre-cambios.py` | snapshots sueltos de `app.py` por fecha/hito de esa semana | Si hay que revertir un cambio de UI de una fecha específica |
| `app_vk_2026-07-22.py`, `app_vk_final.py` | variante "VK" (revisar con el usuario qué significa antes de usar) | Solo si el usuario la pide explícitamente |
| `build_data_2026-07-21_ok.py` … `build_data_2026-07-27_pre-agrupa...py` | snapshots de `build_data.py` | Igual que arriba, para el pipeline |
| `actual_20260717_0859/`, `actual_20260720_1034/` | snapshots completos (app+build+actualizar+extraer+semana) | Restauración completa a un punto anterior |
| `actual_20260720_fix_pospre_sin_dividir*` | snapshot justo antes/después del fix de las 12 cuentas PosPre (ver memoria `project_dashboard_territorio_fix_pospre`) | Referencia de ese fix específico |
| `actual_20260720_post_rebuild_fix*` | snapshot post-rebuild de esa fecha | — |
| `aggs_2026-07-24_1543/` | snapshot completo de la carpeta `aggs/` de ese momento | Si un rebuild reciente corrompió aggs y hay que comparar/restaurar |
| `estado_20260728_145716/` | snapshot completo (app+build+actualizar+generar_*+estado.json+CLAUDE_errores_build.md+MANIFEST) previo a la sesión de cuello de botella sem30 | Referencia del estado justo antes de esa sesión de debugging |
| `sem30_final_20260728_155027/` | snapshot **más reciente antes de esta sesión de Cierres** (incluye MANUAL/MANIFEST) — código operativo confirmado funcionando para sem30 | **Este es el respaldo "bueno conocido" más reciente si algo de la sesión de Cierres rompe todo** |
| `cierres_completa_20260728_160259/` | primer intento de Cierres (con bugs: KPIs sueltos, sin gasto real) | Solo arqueología, no restaurar |
| `cierres_completa_20260728_164728/` | snapshot FINAL de la sesión del 28-jul (mapeo ECO/PDC corregido, `NameError: det` corregido) | Arqueología — superado por el snapshot del 29-jul |
| `app_2026-07-29_arbol-cierres-pdc.py`, `build_data_2026-07-29_arbol-cierres-pdc.py` | **snapshot FINAL de esta sesión** (árbol Cierres reconstruido con `cierres_arbol.parquet`, buscador con fix de ID) | **Punto de partida de la próxima sesión — el más nuevo** |
| `generar_correo_canales_2026-07-2....py`, `Riesgos y Oportunidades_pre-sem2....docx` | snapshots sueltos de esos dos entregables | Contexto de canales digitales, no de Vista Territorio |

**Convención de nombres**: `app_FECHA_descripcion.py` = snapshot puntual de
un archivo; `actual_FECHA/`, `estado_FECHA/`, `sem30_final_FECHA/`,
`cierres_completa_FECHA/` = snapshot de **todo el set operativo** (carpeta
completa). Antes de restaurar, comparar `LastWriteTime` y preguntar al
usuario si hay dudas sobre cuál es el punto de retorno correcto — no asumir
que el más reciente es siempre el que se quiere.

## Estado de trabajo — pestaña Cierres (2026-07-29, última sesión)

Componentes actuales:
1. KPIs en tabla (`kpis_tabla()`, mismo estilo que Resumen) — SOLO el número
   por tipo de cierre, sin subtexto.
2. **Una sola tabla** ("Primera tabla: Proyectos") leída del Excel
   "Seguimiento Expansión" (ver mapeo de columnas abajo — **crítico, ya se
   rompió dos veces**), con gasto real cruzado desde `_consolidado.parquet`.
   La "Segunda tabla: Detalle por ECO con gasto" se ELIMINÓ (2026-07-29,
   pedido del usuario, era redundante con la primera).
3. **Árbol nuevo** (2026-07-29): Grupo de Cuenta → Cuenta → Agrupador de
   Reales → **PDC**, con formato completo (Real 2025/Plan 2026/Real
   2026/variaciones, vía `arbol_multicol` genérico) y buscador de texto.
   Filtrado SOLO a los PDC/ECO que aparecen en la tabla de Proyectos de
   arriba (no el universo completo de PDC). Fuente: `cierres_arbol.parquet`
   (agg NUEVO, ver sección de build abajo).
4. Árbol jerárquico separado (`arbol_multicol` sobre `cierres_expansion.parquet`)
   — "Árbol de cierres por estructura organizacional", sin cambios.
5. Tabla final PDC (Categoría/PDC/División/Territorio, `estilizar()`).

**KPI de Resumen**: se quitó la subnota "vs Plan 2026" bajo el valor de
"Real 2026" en `kpis_gasto_html()` — el usuario consideró redundante mostrar
la variación ahí porque ya está en Plan 2026 al lado.

**Validado en esta sesión**: sintaxis OK, `build_data.py --resume --aggs-only`
corrido y validado (9 min, solo generó el agg nuevo, resto saltado), lógica
de datos probada en script aislado, Streamlit levantó sin error. **El
usuario SÍ validó visualmente** y reportó un bug de buscador (ver abajo, ya
corregido). Respaldo de esta versión en `_respaldo/app_2026-07-29_arbol-cierres-pdc.py`
y `_respaldo/build_data_2026-07-29_arbol-cierres-pdc.py`.

### Nuevo agg: `cierres_arbol.parquet` (build_data.py)

`build_cierres_arbol(con, resume=False)` — agrupa `consolidado` por
`["cat_Grupo_de_Cuentas", "cat_Cuentas", "cat_Agrupador_Reales", "cat_PDC"]`
+ sem (10.1M filas). Es un agg NUEVO y separado, no una modificación de
`pdc_pospre` — **`pdc_pospre.parquet` NO tiene `cat_PDC`** (solo territorio:
División/Territorio/Zona/Región) y **`agrupador_reales.parquet` NO tiene
`cat_PDC` ni `cat_Cuentas`** — ningún agg existente cruzaba
PDC individual + Agrupador de Reales antes de esta sesión. Registrado en
`app.py` como `_DIFERIDOS_EXTRA = {"cierres_arbol"}` (carga bajo demanda,
igual que `pdc`/`conciliacion`).

**Soporta `--resume`** igual que `build_aggs()`: si `cierres_arbol.parquet`
ya existe, lo salta. Se llama en `main()` como
`build_cierres_arbol(con, resume=args.resume)`, justo después de
`build_pdc_pospre(con)`. Confirmado: correr
`python build_data.py --resume --aggs-only` deja intactos los 20 aggs
existentes ("ya existe, saltando") y solo genera el nuevo — así es como se
deben agregar aggs pequeños/nuevos de aquí en adelante sin recargar todo.

### Bug del buscador del árbol nuevo (encontrado y corregido, 2026-07-29)

Buscar por el ID numérico del PDC (Eco PDV, ej. "276") no daba resultados
aunque el PDC existiera. Causa: el filtro de búsqueda solo hacía
`.str.contains()` sobre columnas de TEXTO (`cat_Grupo_de_Cuentas`,
`cat_Cuentas`, `cat_Agrupador_Reales`, `cat_PDC`) — pero **`cat_PDC` contiene
el NOMBRE del PDC, no su ID**; el ID vive aparte en `pdc_ids.json`
(`PDC_IDS`, nombre → id). Fix: se agregó una segunda condición que compara
`_idtxt_pdc(nombre) == query` (comparación EXACTA del id, no substring — para
no matchear "276" contra "1276"/"2765"/etc.). Patrón a recordar: **cualquier
buscador nuevo sobre `cat_PDC` debe cubrir tanto el nombre como el ID**, o
quedará con este mismo bug.

### Bug crítico ya resuelto — el mapeo de columnas del Excel

Excel: `OneDrive - Onuris Tenant\Archivos de Karlo De Jesus Juarez Ramirez -
Planeación Financiera\1. Capex y Herramientas\Master Cierres\Seguimiento
Expansión - semana XX.xlsx` (se toma el de mayor `getmtime` vía `glob`),
hoja `"Seguimiento semanal"`. Encabezados reales en **fila 21**:

| Col | Campo | Nota |
|---|---|---|
| B | Proyecto | |
| C | Especialidad | |
| D | Formato agrupado | |
| E | **Formato** | texto: "Casa Ley", "Azulemex"... — **NO es el ECO**, aquí se confundió una vez |
| F | **Eco** | número: 325, 829, 1006... — **este SÍ es el ECO real**, se confundió con E una vez |
| G | PDC | nombre completo, ej. "Casa Ley San Miguel" |
| H | Comentario | |
| I | Plan (1/0) | 1=contemplado desde plan original |
| J | Sem 26 | año anterior |
| K | Sem XX | semana actual (cambia cada semana) |
| L | Conciliación cierres | |

Tabla resumen: filas 6-19 (B=Proyecto, I=Plan, J=Sem26, K=Sem actual), fila 3
tiene el texto "Semana XX". Tabla detalle: filas 22 a ~530.

### Cruce ECO → gasto real (la pieza que costó más iteración)

- `PDC_IDS` (`aggs/pdc_ids.json`, vía `META.get("pdc_ids", {})`) mapea
  **nombre_pdc → id (Eco PDV)**. Se invierte a `id → nombre` en `app.py`
  para cruzar contra la columna F (Eco) del Excel.
- Gasto real vive en `aggs/_consolidado.parquet` (con guion bajo — **no
  existe** `consolidado.parquet` sin guion, eso causó un `FileNotFoundError`
  la primera vez).
- `_consolidado.parquet` es la ÚNICA excepción en formato LARGO dentro de
  `aggs/`: columnas `sem`, `Serie` (∈ `R25`,`P26`,`R26`,`NVO`), `monto`, más
  las `cat_*`. Hay que `group_by(["cat_PDC","Serie"])`, sumar `monto`, y
  **pivotar** `Serie` a columnas antes de tener "Real 2026" como columna
  usable — todos los demás aggs (`global.parquet`, `division.parquet`,
  etc.) ya vienen anchos con `Real_2025`/`Plan_2026`/`Real_2026` directos;
  NO asumir que `_consolidado.parquet` sigue ese mismo patrón.
- El nombre de PDC en el catálogo a veces trae prefijo `"Cerrado "` que el
  Excel no tiene (Excel: "Azulemex Periferico", catálogo:
  "Cerrado Azulemex Periferico") — por eso el cruce es **siempre por ID
  numérico** (columna F ↔ `PDC_IDS` invertido), nunca por texto de nombre.

Verificación ya corrida y confirmada (no repetir la exploración, solo
recordar el resultado): ECO 325 → "Casa Ley San Miguel" → Real 2026 =
432,285.82 MXN; ECO 829 → "Cerrado Azulemex Periferico" → Real 2026 =
363,525.75 MXN.

### Otros fixes de la misma sesión (Sem/Mes, no relacionados a Cierres)

- **Trimestral (`KeyError` en columnas `Vs_*`)**: se hacía `groupby` ANTES
  de calcular `Vs_AA_Abs`/`Vs_Plan_Abs`/etc. Fix: calcular esas columnas
  sobre `t` (copia de `weekly()`) ANTES del `groupby("Trimestre")`.
- **Trimestral sin gráficas**: se agregó el mismo bloque de 3 gráficas que
  ya tenían Semanal/Mensual (acumulado, Real vs Real AA, Real vs Plan).
- **Acumulados sin formato de dinero**: `estilizar()` solo formatea las
  columnas que se le pasan explícitamente en `money=[...]`/`pct=[...]` — la
  lista `acum` (`Acum. Real 2026`, `Acum. Plan 2026`) no estaba incluida.
  Cualquier columna nueva de dinero/porcentaje en una tabla debe agregarse
  a esas listas o queda sin formatear (sin MDP, sin paréntesis/color).

### Pestaña "Sem / Mes" renombrada a "Temporalidad" + Forecast en tabla Trimestral (2026-07-29)

- `SECCIONES` (app.py ~línea 2048) y el `if SEC == ...` correspondiente
  (~línea 2657) ahora usan `"Temporalidad"` en vez de `"Sem / Mes"`.
  `_test_smoke.py` actualizado a juego (debe coincidir siempre con
  `SECCIONES` de `app.py`, ver comentario ahí).
- Tabla Trimestral (dentro de Temporalidad → radio "Trimestral", ~línea
  2683-2724): se agregó columna **Forecast** (+ "Vs Forecast" / "Vs Forecast
  %"), mismo criterio que `Forecast_Cierre` de `_medidas()`/`compute()`:
  Real 2026 acumulado de TODO el año hasta `SMR` + Plan 2026 de las semanas
  aún no ejecutadas (`sem > SMR`). **Es un valor único de cierre de año, el
  mismo en las 5 filas de trimestre** (no se recalcula por Q ni se suma en
  el TOTAL — sumar daría 5x el valor real). Validado con script aislado:
  Real acum (16,567M) + Plan restante (12,382M) = Forecast (28,949M) igual
  en las 5 filas, TOTAL correcto.
- **Fix Q5 espurio (mismo día, reportado por el usuario tras el cambio
  anterior)**: el `groupby("Trimestre")` original calculaba
  `((sem-1)//13+1)`, que genera un **Q5 espurio** de una sola semana (la 53,
  porque 53 no es múltiplo de 13). Fix: se movió `QRANGO_TRI` (antes solo
  definido en la sección Trimestres, línea ~3033) a las constantes globales
  cerca de `MEDIDAS`/`COLOR` (arriba del todo), y la tabla Trimestral de
  Temporalidad ahora mapea semana→Q1-Q4 con ese mismo diccionario
  (`{s: q for q,(lo,hi) in QRANGO_TRI.items() if q!="FY" for s in
  range(lo,hi+1)}`), igual que la pestaña Trimestres — así ambas vistas usan
  la MISMA definición de trimestre y no pueden divergir. `base` se
  reindexa explícitamente a `["Q1","Q2","Q3","Q4"]` para fijar el orden.
  Validado: 4 filas exactas, semana 53 → Q4, suma de Real/Plan de las 4 filas
  coincide con los totales del año.
- `MANUAL_USUARIO.md`: sección 5.7 renombrada a "Temporalidad", contenido
  expandido (antes solo mencionaba semanal) con las 3 granularidades y la
  explicación del Forecast trimestral. Índice (línea ~25) actualizado a
  juego. **Pendiente si se retoma**: el manual completo tiene más pestañas
  desactualizadas (aún lista "Riesgos & Oportunidades" y "Comentarios" como
  vigentes pese a estar eliminadas — ver `generar_pdf.py` línea ~276 con el
  mismo problema) — no se tocó por estar fuera del pedido puntual de esta
  sesión.

## Reglas de entorno (todas las sesiones, no solo Cierres)

- **ThreatLocker** bloquea a veces lectura/escritura recién hecha
  (`PermissionError: [Errno 13]`). Fix: `Stop-Process -Name python -Force`
  y reintentar; a veces requiere aprobación manual del usuario en el tray.
  Las herramientas Read/Edit y `python` normalmente sí funcionan aunque
  PowerShell falle.
- El usuario **inicia Streamlit manualmente** — no dejar procesos
  corriendo en background al cerrar sesión; confirmar que se cerraron.
- PowerShell 5.1: sin heredocs (`<< 'EOF'`), sin `2>&1` con Tee sobre
  ejecutables nativos si se puede evitar, usar `$env:VAR` en vez de
  `VAR=x cmd`.
- El usuario **no usa `.bat`** (política de la organización) — dar siempre
  comandos PowerShell.
- Regenerar `aggs/` (`python build_data.py --aggs-only`) tarda ~15 min
  (usa `_consolidado.parquet` en caché); usar `--resume` para checkpoint si
  se interrumpe. Correr siempre en background. Respaldar `aggs/` antes de
  cambios grandes.

## Proceso recomendado para la próxima corrección (para no repetir el gasto de tokens de esta sesión)

1. Leer este archivo (`CLAUDE_CONTEXTO_MAESTRO.md`) — no releer `app.py`
   completo ni re-explorar el Excel/parquets desde cero.
2. Si el reporte es "tal número/tabla está mal": validar la lógica de datos
   (cruce, agregación, filtro) con un script Python aislado y desechable
   (crear en la carpeta, correr, revisar resultado, borrar) ANTES de tocar
   `app.py` y relanzar Streamlit. Cada ciclo completo de "editar app.py +
   arrancar Streamlit + leer traceback" cuesta mucho más contexto que una
   prueba aislada de 10-20 líneas.
3. Usar `Grep` para ubicar la sección exacta en `app.py`/`build_data.py`
   antes de `Read` — pasar `offset`/`limit` acotado, nunca el archivo
   completo.
4. Al terminar, actualizar la sección correspondiente de este archivo (no
   crear un `_CORRECCIONES_FECHA.md` nuevo cada vez — este documento
   reemplaza esa práctica) y guardar un respaldo en `_respaldo/` con
   nombre descriptivo.
5. Cerrar los procesos Python al terminar (el usuario inicia manualmente).
