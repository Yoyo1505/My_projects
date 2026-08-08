# Mapa de Datos y Linaje de Información

## Flujo End-to-End de Datos

```
[SQL Server VistaRapida / Parquets r25, r26, p26] ──────┐
[Nvo Plan 2026 parquet (unpivot 53 sem, *-1)] ─────────┼──> [build_data.py (DuckDB)]
[Catálogo de estructura.xlsx] ──────────────────────────┤
[Catálogo grupo cuentas.xlsx] ──────────────────────────┤
[Puntos de contacto.xlsx / FCST VTA RAPIDA.xlsx] ───────┘
                               │
                               ▼
               [aggs/_consolidado.parquet] (Formato Largo, 1.4GB)
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[aggs/*.parquet (Precalculados Ancho)]  [aggs/*.json (Metadatos/IDs)]
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                 [app/services/data_service.py]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
[Interfaz Streamlit (Vistas/Árboles)]     [Sistema RAG Local]
```

## Linaje Detallado por Componente
1. **Extracción y Origen**:
   - `r25_semXX.parquet`, `r26_semXX.parquet`, `p26_semXX.parquet`: Extraídos de SQL Server (`VistaRapida`) mediante `extraer_sql.py`.
   - `nvo_plan_2026.parquet`: Archivo en formato ancho con 53 columnas de semanas (`Nvo Plan Sem 1` .. `Nvo Plan Sem 53`). En `build_data.py` se despivota a formato largo y se multiplica por `-1` para igualar la convención contable.
2. **Catálogos y Enriquecimiento**:
   - `Catálogo grupo cuentas.xlsx`: Mapea `ID_CONCEPTO_CUENTA_NIV3` -> `Grupo de Cuentas`, `Cuentas`, `Naturaleza`, `PosPre`, `Denom.PosPre`, `Responsable Interno`, `Agrupador Reales`.
   - `Catálogo de estructura.xlsx`: Mapea `ID_CENTRO_COSTOS` -> `Dirección / División`, `Subdirección / Territorio`, `Subdirección / Zona`, `Subdirección / Región`, `PDC`, `Formato`, `Agrupa 1, 2, 3`, `Agrupadores`, `Estatus`.
3. **Consolidado Transaccional**:
   - `aggs/_consolidado.parquet`: Tabla maestra unificada con columnas `sem`, `Serie` (`R25`, `P26`, `R26`, `NVO`), `monto`, `ID_CENTRO_COSTOS`, `ID_CONCEPTO_CUENTA_NIV3` y todas las dimensiones asociadas con prefijo `cat_*`.
4. **Agregados Precalculados**:
   - `global.parquet`, `division.parquet`, `territorio.parquet`, `zona.parquet`, `region.parquet`, `pdc.parquet`, `grupo_cuentas.parquet`, `cuentas.parquet`, `formato.parquet`, `naturaleza.parquet`, `agrupador.parquet`, `agrupadores.parquet`, `segmento1.parquet`, `segmento2.parquet`, `estatus.parquet`, `clasificacion2.parquet`, `trimestre.parquet`, `pdc_pospre.parquet`, `cierres_expansion.parquet`, `cierres_arbol.parquet`, `forecast_cuenta.parquet`, `forecast_ceco.parquet`.
