# Territory Dashboard — Data Mappings

This document describes **how dimensions, metrics, files, UI sections, and both runtimes (Streamlit + static HTML)** map to each other.

---

## 1. Runtime map (two versions)

| Layer | Streamlit (Python) | Static web (HTML/JS) |
|-------|--------------------|----------------------|
| Entry | `app.py` | `../docs/territory/index.html` |
| Data | `aggs/*.parquet` + JSON meta | `../docs/territory/data/demo.json` |
| Charts | Plotly | Chart.js (CDN) |
| Drill-down | `arbol_jerarquia` / `arbol_multicol` | Expandable `<details>` hierarchy |
| Seed / rebuild | `python seed_demo_data.py` | Re-export JSON from aggs (see README) |
| Hosting | Local process | GitHub Pages (`/docs`) |

Both share the **same conceptual model** (hierarchies, measures, YTD cut at `sem_max_real`). The static demo is a **compact snapshot** of the synthetic demo; Streamlit can recompute any week range live.

---

## 2. Measure map (metrics)

| Internal key | UI label | Meaning | Year calendar |
|--------------|----------|---------|---------------|
| `Real_2025` | Real 2025 | Actual spend prior year | 2025 (anchor week 1: 2024-12-29) |
| `Real_2026` | Real 2026 | Actual spend current year (cut at SMR) | 2026 (anchor week 1: 2025-12-28) |
| `Plan_2026` | Plan 2026 | Budget / plan | 2026 |
| `Nvo_Plan_2026` | Nvo Plan | Revised plan | 2026 |
| `Forecast_Cierre` | Forecast | Expected year-end (Real YTD + remaining plan, or FCST cross) | 2026 |

### Derived measures (computed in Streamlit)

| Key | Formula (concept) |
|-----|-------------------|
| `Vs_AA_Abs` / `Vs_AA_Pct` | Real_2026 − Real_2025 |
| `Vs_Plan_Abs` / `Vs_Plan_Pct` | Real_2026 − Plan_2026 |
| `Vs_NvoPlan_*` | Real_2026 − Nvo_Plan_2026 |
| `Pct_r26` | Share of Real_2026 within the current aggregation total |
| `Plan_Restante` | Plan on weeks after SMR (used for simple forecast) |

### Chart colors (both UIs)

| Measure | Color |
|---------|-------|
| Real 2025 | `#94a3b8` |
| Real 2026 | `#38bdf8` |
| Plan 2026 | `#a78bfa` |
| Nvo Plan | `#34d399` |
| Forecast | `#fbbf24` |

---

## 3. Dimension map (`DIMS`)

Alias used in code → human label → column in parquet.

| Alias | Label | Column |
|-------|-------|--------|
| `global` | Global | *(none — total)* |
| `agrupa1` | Agrupa 1 | `cat_Agrupa1` |
| `division` | División | `cat_Direccion_Division` |
| `territorio` | Territorio | `cat_Subdireccion_Territorio` |
| `zona` | Zona | `cat_Subdireccion_Zona` |
| `region` | Región | `cat_Subdireccion_Region` |
| `pdc` | PDC | `cat_PDC` |
| `grupo_cuentas` | Grupo de Cuentas | `cat_Grupo_de_Cuentas` |
| `cuentas` | Cuentas | `cat_Cuentas` |
| `pospre` | PosPre | `cat_PosPre` |
| `formato` | Formato | `cat_Formato` |
| `naturaleza` | Naturaleza | `cat_Naturaleza` |
| `agrupador_reales` | Agrupador Reales | `cat_Agrupador_Reales` |
| `agrupa2` / `agrupa3` | Agrupa 2 / 3 | `cat_Agrupa2` / `cat_Agrupa3` |
| `agrupador` | Agrupador | `cat_Agrupador` |
| `clasificacion2` | Clasificación 2 | `cat_Clasificacion_2` |
| `segmento1` / `segmento2` | Segmento 1 / 2 | `cat_Segmento1` / `cat_Segmento2` |
| `estatus` | Estatus | `cat_Estatus` |

Optional filter columns used across views:

| Column | Use |
|--------|-----|
| `cat_Subtipo` | Global filter (subtype) |
| `cat_Prefijo` | Prefijo filter on Div/Terr |
| `ID_CONCEPTO_CUENTA_NIV3` | Account concept id (forecast cross) |
| `Categoria` | Cierres expansion category |

---

## 4. Parent map (`PARENTS`) — avoid merging homonyms

When aggregating a child dimension, **parents are always grouped with it** so the same name under two parents does not collapse.

| Alias | Parent columns (in order) |
|-------|---------------------------|
| `division` | `cat_Agrupa1` |
| `territorio` | `cat_Agrupa1`, `cat_Direccion_Division` |
| `zona` | `cat_Agrupa1`, `cat_Direccion_Division`, `cat_Subdireccion_Territorio` |
| `region` | … + `cat_Subdireccion_Zona` |
| `pdc` | … + `cat_Subdireccion_Region` |
| `grupo_cuentas` | `cat_Agrupa1` |
| `cuentas` | `cat_Agrupa1`, `cat_Grupo_de_Cuentas` |
| `pospre` | `cat_Agrupa1`, `cat_Grupo_de_Cuentas`, `cat_Cuentas` |
| `agrupa2` | `cat_Agrupa1` |
| `agrupa3` | `cat_Agrupa1`, `cat_Agrupa2` |

---

## 5. Hierarchy map (drill-down trees)

### Territorial (`HIER_TERR`) — tab **Div / Terr → General**

```text
agrupa1
  └─ division
       └─ territorio
            └─ zona
                 └─ region
                      └─ pdc
```

### Accounting (`HIER_CTA`) — tab **Div / Terr → Por Cuenta**

```text
grupo_cuentas          (Agrupa 1 filtered via sidebar selector, not a tree level)
  └─ cuentas
       └─ pospre
```

`excluir_padres=("cat_Agrupa1",)` when showing Por Cuenta so groups are not split by Agrupa 1.

### Demo seed hierarchy (synthetic)

```text
Red Comercial (agrupa1)
├─ Division Norte / Centro / Sur / Corporativo / Expansión
│    ├─ Territorio {X} 1
│    │    └─ Zona … → Región … → PDC {X} 1-1, PDC {X} 1-2
│    └─ Territorio {X} 2 → …
└─ Account grain under every PDC:
     Grupo de Cuentas → Cuentas → PosPre
```

### Static HTML hierarchy

`demo.json` → `hierarchy[]`:

```json
{ "name": "Division Norte", "Real_2026": …, "children": [ { "name": "Territorio Norte 1", … } ] }
```

Only **Division → Territory** is expanded in the static UI (compact). Streamlit expands full depth.

---

## 6. File map (`aggs/`)

| File | Grain / content | Used by |
|------|-----------------|---------|
| `global.parquet` | week totals | Resumen, Temporalidad |
| `agrupa1.parquet` | week × Agrupa 1 | Div/Terr root |
| `division.parquet` | week × Agrupa1 × Division (+ prefijo) | Div/Terr, charts |
| `territorio.parquet` | + Territorio | Div/Terr |
| `zona.parquet` | + Zona | Div/Terr |
| `region.parquet` | + Región | Div/Terr |
| `pdc.parquet` | full terr path + Grupo + Cuenta | Trimestres, Detalle PDC |
| `grupo_cuentas.parquet` | week × Agrupa1 × Grupo | Resumen charts |
| `cuentas.parquet` | + Cuenta | Detalle Cuenta, fallback Trimestres |
| `pospre.parquet` | + PosPre | Por Cuenta tree |
| `cierres_expansion.parquet` | Categoria × org × PDC | Cierres org tree |
| `cierres_arbol.parquet` | Grupo × Cuenta × Agrupador × PDC | Cierres follow-up tree |
| `_consolidado.parquet` | PDC × Serie (R25/P26/R26) | Cierres spend join |
| `seguimiento_demo.json` | Projects / ECO / PDC demo | Cierres KPIs + table |
| `_meta.json` | `sem_max_real`, `sem_max_plan`, `demo`, `version_seed` | Load + UI badge |
| `pdc_ids.json` | `PDC name → Eco id` | Cierres ECO map |
| `pdc_cecos.json` | `PDC → [CECO ids]` | Search PDC/CECO |
| `orden_gpo.json` | Grupo → sort order | Table ordering |
| `responsables_gpo.json` | Owner → [grupos] | Sidebar filter |
| `riesgos.json` | Variation comments | Resumen notes |

Other dim parquets (`formato`, `naturaleza`, …) exist for filter compatibility.

---

## 7. Section map (UI tabs)

| Section | Streamlit | Static HTML | Primary sources |
|---------|-----------|-------------|-----------------|
| Resumen | Yes | Yes | global, grupo, division, riesgos |
| Temporalidad | Yes | *(in weekly chart on Resumen)* | global weekly |
| Div / Terr | Yes | Yes (2 levels) | hierarchy aggs / `hierarchy` |
| Detalle Cuenta | Yes | Cuentas table | cuentas / `accounts` |
| Detalle PDC | Yes | — | pdc |
| PDC & Calor | Yes | — | pdc |
| Cierres | Yes (demo JSON) | Yes | seguimiento + cierres_* |
| Trimestres | Yes | Yes (YTD matrices) | pdc or cuentas |

Removed from nav: **Comparación de Versiones**.

---

## 8. Calendar & week map

| Concept | Value |
|---------|--------|
| Weeks per year | 1–53 (EKT style; Q4 absorbs week 53) |
| Q1 | 1–13 |
| Q2 | 14–26 |
| Q3 | 27–39 |
| Q4 | 40–53 |
| FY | 1–53 |
| Demo `sem_max_real` (SMR) | **30** |
| Demo `sem_max_plan` | **53** |
| Real after SMR | Forced to 0 / null in series |

Month filters use **daily proration** of weeks that span two months (`pesos_mes`).

---

## 9. Identity maps (IDs)

| Map | Structure | Purpose |
|-----|-----------|---------|
| `pdc_ids` | `{ "PDC Norte 1-1": 1001, … }` | ECO (Eco PDV) ↔ PDC name |
| `pdc_cecos` | `{ "PDC …": ["CECO-1"], … }` | Cost center search |
| `ID_CONCEPTO_CUENTA_NIV3` | String id on rows | Forecast / account join |

Cierres table uses **ECO** integer → lookup inverse of `pdc_ids` → join spend from `_consolidado`.

---

## 10. Static `demo.json` schema map

| JSON path | Meaning |
|-----------|---------|
| `meta` | SMR, demo flag |
| `kpis` | YTD Real/Plan/Forecast + deltas |
| `weekly` | 53 weeks × measures |
| `by_division` | YTD by division |
| `by_grupo` | YTD by account group |
| `hierarchy` | Division → territories |
| `accounts` | Grupo + cuenta YTD + vs Plan/AA |
| `cierres.resumen` / `cierres.detalle` | Cierres demo |
| `riesgos` | Narrative variation notes |

---

## 11. Homologation map

Dirty catalogs sometimes repeat labels with different casing.  
`_homologar()` builds `{ column: { variant: canonical } }` (fewest uppercase wins).  
Applied on load so filters and trees do not duplicate categories.

---

## 12. End-to-end flow

```text
seed_demo_data.py  ──writes──►  aggs/*.parquet + JSON
        │
        ├─ Streamlit app.py  ──compute() / trees──► interactive UI
        │
        └─ export script     ──writes──► docs/territory/data/demo.json
                                              │
                                              └─ HTML/JS dashboard (GitHub Pages)
```
