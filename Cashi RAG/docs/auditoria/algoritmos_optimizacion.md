# Evaluación de Algoritmos Avanzados y Computación Cuántica

## 1. Problemas Combinatorios e Investigación de Operaciones

En el ámbito de la planeación financiera y redistribución presupuestal (ejemplo: optimización de apertura/cierre de PDCs, prorrateo de Capex por territorio y balanceo de variaciones), se evaluaron las siguientes aproximaciones:

### Comparativa de Enfoques de Optimización

| Enfoque | Técnica | Aplicabilidad en Vista Territorio | Latencia / Rendimiento |
|---|---|---|---|
| **Programación Lineal / Mixta (MILP)** | OR-Tools / SciPy `linprog` | Redistribución del Nvo Plan 2026 entre PDCs bajo restricciones de presupuesto. | **Excelente** (< 200 ms). Solución exacta garantizada. |
| **Búsqueda Local / Simulated Annealing** | Metaheurísticas de optimización | Agrupación y clasificación óptima de PDCs por patrón de gasto. | **Buena** (< 1.5 s). Heurística rápida. |
| **Quantum-Inspired (QUBO / Ising)** | Formulación Cuántica Simulada | Optimización cuadrática sin restricciones para selección de portafolio de proyectos. | **Moderada** (Simulador en CPU). Requiere formulación matricial. |

## 2. Decisión Arquitectónica
- Se selecciona **Programación Entera Mixta (MILP)** mediante la biblioteca estándar de Python y OR-Tools / SciPy para cualquier problema de optimización presupuestal.
- Los modelos **Quantum-Inspired** quedan formulados conceptualmente para escenarios futuros de selección de proyectos Capex con restricciones cuadráticas, sin introducir complejidad decorativa no requerida en la versión operativa actual.
