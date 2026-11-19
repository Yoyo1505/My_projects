# Cashi knowledge base (synthetic demo)

Guide for Cashi and its users: structure of the demo dataset created by `seed_demo_data.py`, what the data means and how to ask. All figures are synthetic.

## Series and weeks

- **R26** = Real 2026, **P26** = Plan 2026, **R25** = Real 2025 (previous year).
- **Overspend / variance vs plan** = Real 2026 - Plan 2026. Positive = over plan (unfavourable), negative = saving.
- **Variance vs previous year** = Real 2026 - Real 2025 for the same weeks.
- The last closed real week comes from `aggs/_meta.json` (`sem_max_real`), not from the maximum week in the data.
- Amounts are in pesos; answers display millions (MDP).

## Territorial structure

Division > Territory > Cost center. The demo has 3 divisions (Direccion Norte, Direccion Centro, Direccion Sur) and 6 territories with one cost center each.

## Accounting structure

Account group > Account. The demo has 5 groups: Gastos de Nomina, Renta y Servicios, Mantenimiento, Fletes y Transportes and Publicidad, with one account each.

## Comptroller grouping

Two levels, summary and detail. The demo has three summary groups (Contraloria A, B and C), each mapped to a detail group (Contraloria 6A, 6B and 6C).

## How to ask

- Name the entity as it appears in the dashboard ("Territorio Jalisco", "Gastos de Nomina").
- Combine filters with weeks: "gasto de nomina en direccion norte semana 38".
- Ranking questions: "top 5 territorios por gasto". Variance questions: "variacion contra presupuesto por division".
- Known limitation: "division centro" (without the word "Direccion") is not recognised as a division filter.
