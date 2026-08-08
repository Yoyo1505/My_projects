# Diccionario de Datos y Catálogos Maestros

## 1. Agregado Consolidado (`aggs/_consolidado.parquet`)

| Columna | Tipo de Dato | Descripción |
|---|---|---|
| `sem` | `INTEGER` | Número de semana EKT del ejercicio (1 a 53). |
| `Serie` | `VARCHAR` | Serie temporal del registro: `R25` (Real 2025), `P26` (Plan 2026), `R26` (Real 2026), `NVO` (Nvo Plan 2026). |
| `monto` | `DOUBLE` | Importe acumulado del movimiento en Pesos Mexicanos (MXN). |
| `ID_CENTRO_COSTOS` | `VARCHAR` | Identificador único del Centro de Costos (CECO). |
| `ID_CONCEPTO_CUENTA_NIV3` | `VARCHAR` | Identificador de la Cuenta Mayor (Nivel 3). |
| `cat_Grupo_de_Cuentas` | `VARCHAR` | Agrupación ejecutiva del Grupo de Cuentas. |
| `cat_Cuentas` | `VARCHAR` | Nombre formal de la Cuenta Contable. |
| `cat_Direccion_Division` | `VARCHAR` | División territorial / organizacional. |
| `cat_Subdireccion_Territorio` | `VARCHAR` | Territorio geográfico. |
| `cat_Subdireccion_Zona` | `VARCHAR` | Zona dentro del territorio. |
| `cat_Subdireccion_Region` | `VARCHAR` | Región específica. |
| `cat_PDC` | `VARCHAR` | Punto de Contacto (Eco PDV o CECO). |
| `TRIMESTRE` | `VARCHAR` | Trimestre del ejercicio (`Q1`, `Q2`, `Q3`, `Q4`). |

## 2. Catálogos Involucrados
- **Catálogo de Estructura** (`Catálogo de estructura.xlsx`): Mapea CECO a jerarquía territorial y organizativa.
- **Catálogo Grupo Cuentas** (`Catálogo grupo cuentas.xlsx`): Mapea Cta Mayor a jerarquía contable y posición presupuestal.
- **Puntos de Contacto** (`Puntos de contacto.xlsx`): Asocia nombres de PDC con su Eco PDV ID.
