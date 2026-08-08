# Reglas de Negocio Financieras y Territoriales

## 1. Reglas de Presentación Fijas
- **Unidad de Medida**: TODO en **Millones de Pesos (MDP)**. `M(v)` siempre calcula `v / 1e6` y formatea como `X.X MDP`. Nunca utilizar MMDP ni K.
- **Formato Contable Estricto**:
  - Gasto positivo (ejecución / costo): Se presenta entre paréntesis y resaltado en rojo (`.vt-pos`, `#dc2626`). Ej: `(12.5 MDP)`.
  - Ahorro o subejecución (monto negativo o menor al plan): Se presenta sin paréntesis y en tono carbón/azul neutro (`.vt-neg`, `#2b2b2b`). Ej: `-3.4 MDP` o `3.4 MDP` según contexto.
- **Orden Oficial de Columnas Financieras**:
  `Real 2025 | % del Total | Plan 2026 | % del Total | Nvo Plan | % del Total | Real 2026 | % del Total | vs Nvo Plan | vs Nvo Plan % | vs Plan | vs Plan % | vs AA | vs AA % | Forecast | vs Forecast | vs Forecast %`
- **Resaltado Visual**: Columna **Real 2026** siempre resaltada en amarillo suave (`.vt-r26`, `#fffde7`).
- **Señales KPI**: Tarjetas KPI con indicador ▲ (flecha roja, gasto/sobrecosto) y ▼ (flecha azul/verde, ahorro).

## 2. Definición de Medidas y Fórmulas Financieras

### Medidas Base
- `Real_2025`: Gasto acumulado ejecutado en el ejercicio 2025.
- `Plan_2026`: Presupuesto planificado original para 2026.
- `Nvo_Plan_2026`: Presupuesto modificado/redistribuido 2026 (53 semanas, signo invertido `*-1` en el unpivot de origen).
- `Real_2026`: Gasto ejecutado registrado en el ejercicio 2026 (hasta la semana de corte `SMR`).
- `Forecast_Cierre`: Real 2026 acumulado hasta la semana de corte (`sem <= SMR`) + Plan 2026 de semanas no ejecutadas (`sem > SMR`). En vistas cruzadas por cuenta mayor, proviene de `FCST VTA RAPIDA.xlsx`.

### Variaciones y Porcentajes
- `vs Plan (Absoluta)` = `Real 2026 - Plan 2026`
- `vs Plan (%)` = `(vs Plan Absoluta / |Plan 2026|) * 100`
- `vs AA (Absoluta)` = `Real 2026 - Real 2025`
- `vs AA (%)` = `(vs AA Absoluta / |Real 2025|) * 100`
- `vs Nvo Plan (Absoluta)` = `Real 2026 - Nvo Plan 2026`
- `vs Nvo Plan (%)` = `(vs Nvo Plan Absoluta / |Nvo Plan 2026|) * 100`
- `vs Forecast (Absoluta)` = `Real 2026 - Forecast`
- `vs Forecast (%)` = `(vs Forecast Absoluta / |Forecast|) * 100`
- `Cumplimiento Plan (%)` = `(Real 2026 / |Plan 2026|) * 100`
- `% del Total` = `(Monto Nivel / Monto Total Consolidado) * 100`

## 3. Manejo Especial de Catálogos y Joins
- **12 Cuentas con Split PosPre (1:2)**:
  Cuentas: `1140999006`, `1140999025`, `1140999041`, `1150090107`, `6010100047`, `6010600004`, `6200501009`, `6200600017`, `6210100006`, `6210119001`, `6250100004`, `6250100014`.
  - **Regla**: Conservar AMBAS filas duplicadas de la combinación `(Grupo de Cuentas, PosPre)` sin prorratear ni dividir el monto (el movimiento aparece con el 100% bajo ambas posiciones por falta de desglose en la fuente transaccional).
- **Valores Nulos y '0'**:
  - `PDC = '0'` o `null` -> Se sustituye por `'CECO <ID_CENTRO_COSTOS> · <Nombre>'` o `'Sin agrupar'`.
  - `Territorio / Zona / Región = '0'` -> Se sustituyen por `'Sin agrupar'`.
