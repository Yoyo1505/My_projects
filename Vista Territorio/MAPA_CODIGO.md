# Mapa rápido de app.py

Consultar esto ANTES de tocar código — evita re-explorar el archivo cada vez.
Líneas aproximadas, verificar con Grep si el archivo se editó desde la última actualización de este mapa (2026-07-28).
Ver también `CLAUDE_CONTEXTO_MAESTRO.md` — índice de TODA la documentación del proyecto y mapeo de `_respaldo/`.

## Reglas de presentación FIJAS (2026-07-27, pedido del usuario)
- **TODO en millones de pesos.** `M()` siempre formatea `x/1e6` + " MDP" — nunca MMDP ni K, ni en KPIs ni en drill-downs ni en tarjetas. Si aparece otra escala, es un bug.
- **Orden oficial de columnas** en TODAS las tablas y TODOS los drill-downs, con o sin filtro:
  `Real 2025 | % del Total | Plan 2026 | % del Total | Nvo Plan | % del Total | Real 2026 | % del Total | vs Nvo Plan | vs Nvo Plan % | vs Plan | vs Plan % | vs AA | vs AA % | Forecast | vs Forecast | vs Forecast %`
  Se controla en `_VS_COMBINADAS` / `_VS_SIN_FC` + `fmt_tabla()` + `_get_arbol_head()`. Ojo: **Forecast va DESPUÉS de vs AA % y ANTES de vs Forecast**.
- **Títulos de gráficas cortos**: "<Dimensión> acumulado" (ej. "Grupo de Cuentas acumulado", "Agrupador acumulado"). Nada de "Reales (barras) vs Planes (línea)".
- **Bajo cada gráfica** va `nota_filtro()` avisando qué pedazo se está mostrando si hay filtro activo.
- **Drill-downs sin flechas ni barras de color por nivel**: solo sangría, peso de texto y el resaltado de fondo de la rama abierta. El botón lateral del árbol perezoso es `+`/`−` (no puede quitarse: es el único control de expansión).
- Real 2026 resaltado amarillo (`.vt-r26`, `#fffde7`) en tablas y árboles.
- Convención contable: positivo=rojo+paréntesis, negativo=carbón sin paréntesis (`_css_gasto`).
- Reales = barras, Plan/NvoPlan/Forecast = línea punteada (`barras()`/`lineas()`).
- **La paleta NO se cambia.** Cualquier color nuevo sale de los ya definidos.

## Motor de cálculo (~líneas 367-660)
- `_medidas()` — fórmulas centrales: Real/Plan/NvoPlan/Real26, %del Total, vs AA/Plan/NvoPlan/Forecast.
- `_forecast_cruzado_por_cuenta()` — cruce de FCST VTA RAPIDA.xlsx por ID_CONCEPTO_CUENTA_NIV3. Solo si `alias in _ALIAS_FORECAST_CUENTA = {"global","grupo_cuentas","cuentas"}`.
- `compute()` — agregación estándar por alias de `DIMS`.
- `_agregar_df()` — agregación genérica sobre un DataFrame filtrado + gcols explícitas (árboles multinivel/perezosos).
- `arbol_multicol()` — árbol HTML sobre un agg/fuente con columnas que cruzan dimensiones (Cierres, Trimestres).
- `cierres_rango()` — agrega `cierres_expansion.parquet`.

## Formato, KPIs y helpers
- `M()` / `MC()` / `P()` / `PC()` — formato contable. **`M()` = millones siempre.**
- `logo_b64()` (~línea 331) — `elektra_logo.png` como data-URI. Se usa en login, encabezado y PDF.
- `_desc_filtros()` / `nota_filtro()` (~línea 745) — texto del filtro activo; `chart()` llama a `nota_filtro()` automáticamente. Cada pestaña con filtros locales escribe `st.session_state["_filtros_vista"]`.
- `fmt_tabla()` — Styler para `st.dataframe` con el orden oficial.
- `_ARBOL_CSS` — TODO el CSS de los árboles. Ancho de columna del árbol se edita aquí (`grid-template-columns`, 14 cols dato / 17 con inc_fc).
- `_fila_arbol()` / `_fila_total_arbol()` — HTML de fila. Los `<span>` deben coincidir con `_get_arbol_head()`.
- `arbol_jerarquia()` — Div/Terr. `arbol_perezoso()` — Detalle Cuenta, Detalle PDC, Resumen.
- `estilizar()` — Styler para tablas manuales (Sem/Mes, Cierres).
- `tabla()` — wrapper de `fmt_tabla` + `st.dataframe`. **Si piden "no cortar texto" en una TABLA, es aquí (`column_config`).**
- `kpis_gasto_html()` + `_senal()` + `_KPI_CSS` — KPIs de gasto del Resumen: 5 tarjetas, cada una con su variación (monto **y** %) debajo, con flecha ▲ (rojo, gasto arriba) / ▼ (verde, ahorro).
- `kpis_tabla()` + `_KPITBL_CSS` — KPIs juntos como tabla estilizada compacta. Lo usan PDC & Calor y Cierres.
- `tablas_variaciones()` + `_split_subsecciones()` / `_parsear_notas()` / `_leer_riesgos()` — las 4 tablas del Word (positivas/negativas × vs AA/vs Plan). Viven al final del **Resumen**.
- `html_resumen_pdf()` + `_PDF_CSS` — documento imprimible del Resumen (logo embebido, CSS inline, `onload=window.print()`). El usuario elige "Guardar como PDF". Se eligió HTML→imprimir en vez de reportlab porque **kaleido no está instalado** y sin él no se pueden incrustar las gráficas Plotly en un PDF nativo.

## Pestañas — `SECCIONES` define el menú
Orden actual: **Resumen, Sem / Mes, Div / Terr, Detalle Cuenta, Detalle PDC, PDC & Calor, Cierres, Trimestres**.
1. **Resumen** — KPIs de gasto con señal + drill-down "Desglose completo" (Grupo → Cuenta, `arbol_perezoso`) + 2 gráficas + las 4 tablas de variaciones + botón de descarga a PDF. **Sin KPI de "Operación", sin cuadro aparte de "Variaciones", sin tabla plana de Grupo de Cuentas.**
2. **Sem / Mes** — tabla vía `estilizar()` + gráficas de línea.
3. **Div / Terr** — radio **"General"** (`HIER_TERR`) / **"Por Cuenta"** (`HIER_CTA` SIN la rama `grupo_cuentas`) → `arbol_jerarquia()`.
4. **Detalle Cuenta** — sin radio de vistas: solo "Desglose completo" hasta Región (`arbol_perezoso` sobre `pdc_pospre`), sin notas al pie.
5. **Detalle PDC** — radio General (tabla)/Detalle (árbol). El **ID va pegado al nombre** (`con_id`, "4821 · Nombre"), no en columna aparte, y las filas se ordenan por ese ID. El nombre crudo se conserva en `_pdc_raw` para que los filtros sigan cruzando contra el catálogo.
6. **PDC & Calor** — KPIs con `kpis_tabla()` → histograma → tablas **"Top 25 Sobre Plan"** y **"Bottom 25 Sobre Plan"**. Tiene buscador por PDC/CECO (`buscador_pdc_ceco`).
7. **Plan + Real** — OCULTA del menú desde 2026-07-24, código intacto.
8. **Cierres** — reconstruida 2026-07-28. KPIs `kpis_tabla()` (solo número, sin subtexto) leídos directo del Excel "Seguimiento Expansión" (OneDrive, `_leer_seguimiento_excel()`) + 2 tablas del Excel con gasto real cruzado (ECO col. F del Excel → `PDC_IDS` invertido → `cat_PDC` en `_consolidado.parquet` pivotado por `Serie`) + árbol `arbol_multicol` sobre `cierres_expansion.parquet` + tabla final PDC `estilizar()`. **Detalle completo, mapeo de columnas del Excel y bugs ya resueltos: ver `CLAUDE_CONTEXTO_MAESTRO.md`.**
9. **Trimestres** — 2 árboles `arbol_multicol("pdc", ...)` lado a lado.
- **"Riesgos & Oport." ELIMINADA (2026-07-27)**: sus 4 tablas se movieron al Resumen; las alertas automáticas y las listas de riesgos/oportunidades se descartaron por completo.

## Fuentes de datos (build_data.py)
- `pdc_pospre.parquet` — Detalle Cuenta y drill-down del Resumen. Agrupa1, Grupo, Cuentas, División, Territorio, Zona, Región, PosPre_Full.
- `pdc.parquet` — Detalle PDC vista Detalle, Trimestres. Sin `ID_CONCEPTO_CUENTA_NIV3` (no cruza Forecast del Excel).
- `cierres_expansion.parquet` — Cierres. Categoria (Excel Seguimiento Expansión) x PDC, cruzado por NOMBRE.
- `forecast_cuenta.parquet` — Forecast por Cta Mayor. Solo cruza en `global`/`grupo_cuentas`/`cuentas`.
- `forecast_ceco.parquet` — fuente vieja de "Plan + Real", intacta pero pestaña oculta.
- `riesgos.json` — texto del Word "Riesgos y Oportunidades.docx" para las 4 tablas del Resumen.

## Reglas de negocio fijas (no cambiar sin confirmar)
- Forecast por cuenta SOLO en Resumen y vistas con `ID_CONCEPTO_CUENTA_NIV3` — nunca en territoriales/PDC.
- Las 12 cuentas con PosPre duplicado aparecen con el **monto completo en ambas posiciones** (no se divide).

## Al regenerar aggs
`python build_data.py --aggs-only` tarda ~15 min (usa `_consolidado.parquet` en caché). Correr en background (`run_in_background: true`). Respaldar `aggs/` antes de cambios grandes (`_respaldo/aggs_<fecha>/`).

## Después de cualquier cambio de CSS/HTML
**Reiniciar el proceso de Streamlit** (matar PID en 8501, volver a correr) — el auto-reload NO siempre toma cambios en constantes de CSS embebidas en funciones cacheadas. Verificar con:
```powershell
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" | Where-Object { $_.CommandLine -like '*streamlit*' }
```

## Nota de entorno
ThreatLocker bloquea la LECTURA por PowerShell de archivos recién editados (`Acceso denegado` / Errno 13). Las herramientas Read/Edit y `python` sí leen sin problema — usar esas, no `[System.IO.File]::ReadAllLines`.
