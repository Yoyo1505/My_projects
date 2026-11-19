# -*- coding: utf-8 -*-
"""
rag/pruebas_cashi.py — Batería de regresión de Cashi, de la consulta más
sencilla a la más compleja (ver rag/conocimiento/CONOCIMIENTO_CASHI.md).

Uso (desde la raíz del proyecto):  python rag/pruebas_cashi.py
Revisa que cada pregunta caiga en la ruta esperada, no truene, traiga datos
y tarde menos de LIMITE_S. Sale con código 1 si algo falla.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import rag.financial_rag as fr  # noqa: E402

LIMITE_S = 3.0

# (pregunta, texto que debe aparecer en `intencion_detectada`)
CASOS = [
    # 1. Totales
    ("cuanto gasto division norte", "Consulta Financiera Estructurada"),
    ("gasto de nomina en division centro semana 38", "Consulta Financiera Estructurada"),
    ("cuanto gasto el pdv 6031", "Consulta Financiera Estructurada"),
    # 1b. Contraloría (resumen y detalle; antes caía a búsqueda documental)
    ("dame el gasto de contraloria presta prenda", "Consulta Financiera Estructurada"),
    ("gasto de contraloria BAZ Propios", "Consulta Financiera Estructurada"),
    ("gasto de contraloria baz en la division norte", "Consulta Financiera Estructurada"),
    ("contraloria otros semanas 30 a 39", "Consulta Financiera Estructurada"),
    # 2. Estructura
    ("que territorios tiene division norte", "Consulta de Estructura"),
    ("a que division pertenece el ceco 238139", "Consulta de Estructura"),
    ("cuantos pdv tiene territorio jalisco", "Consulta de Estructura"),
    ("que cuentas tiene gastos de operacion", "Consulta de Estructura"),
    # 3. Tiempo
    ("tendencia semanal de division centro", "Tendencia Semanal"),
    ("desglose mensual de gastos de nomina", "Desglose Mensual"),
    ("semana 37 vs semana 38 division norte", "Comparativa Semana 37 vs Semana 38"),
    ("ultimas 4 semanas division norte", "4 Semanas Recientes"),
    ("2026 vs 2025 division sur", "Real 2026 vs Real 2025"),
    # 4. Rankings
    ("top cecos que se pasaron del plan en division norte", "Mayor Variación vs Plan"),
    ("top pdvs que se pasaron del plan en territorio jalisco", "PDVs con Mayor Variación"),
    ("que ceco tiene mas gasto de nomina", "Mayor Gasto"),
    # 5. Cruces
    ("gasto por territorio por semana division sur", "Multi-Dimensional"),
    ("dame el gasto de la division norte por territorio", "Multi-Dimensional"),
    # 6. Concentración
    ("pareto de division norte", "Pareto"),
    # 7. Anomalías y alertas
    ("anomalias division norte", "Anomalías"),
    ("alertas de sobregasto", "Alertas de Sobregasto por Variación"),
    ("alertas de sobregasto division norte", "Alertas de Sobregasto por Variación"),
    # 7b. Gasto por versión archivada (datos/r26_semNN.parquet)
    ("dame el gasto con la version de la semana 40", "Gasto por versión archivada"),
    ("gasto de la semana 30 con la version r26sem40", "Gasto por versión archivada"),
    # 8. Señales
    ("senales de sobregasto division centro", "Señales de Sobregasto"),
    ("senales de sobregasto semana 38 por pdv", "Señales de Sobregasto"),
    # 8b. Variaciones operativas por semana y semanas atípicas (2026-10-27)
    ("dame las variaciones de la semana 43", "Variaciones semana contra semana"),
    ("variaciones de la semana 1 a la 43", "Variaciones semana contra semana"),
    ("que semanas fueron atipicas", "Variaciones semana contra semana"),
    ("variaciones de la semana 43 de la division norte", "Variaciones semana contra semana"),
    ("variaciones de la semana 43 en ambos canales", "Variaciones semana contra semana"),
    ("semanas atipicas del canal digital", "Variaciones semana contra semana"),
    ("dame los atipicos para costo de activo fijo", "Variaciones semana contra semana"),
    ("que cecos saltan en gastos de nomina", "Variaciones semana contra semana"),
    # 9. Multi-dimensional con agrupador de reales (2026-10-09)
    ("gasto de luz por agrupador de reales para el territorio metro norte por semana", "Agrupador_reales x Semana"),
]


def main() -> int:
    t0 = time.perf_counter()
    motor = fr.UnifiedCashiRAGEngine()
    print(f"Motor listo en {time.perf_counter() - t0:.1f}s · semana real {motor.sem_max_real} · "
          f"fuente {'dashboard.duckdb' if motor.fuente_nativa else 'parquet'} · agregados {sorted(motor.rollups_disponibles)}")
    fallas = 0
    for pregunta, esperado in CASOS:
        t = time.perf_counter()
        try:
            r = motor.process_query(pregunta)
            dt = time.perf_counter() - t
            intencion = r.get("intencion_detectada", "")
            problemas = []
            if esperado not in intencion:
                problemas.append(f"ruta '{intencion}'")
            if r.get("tipo_respuesta") == "sin_coincidencias":
                problemas.append("sin datos")
            if dt > LIMITE_S:
                problemas.append(f"lenta {dt:.1f}s")
        except Exception as e:  # noqa: BLE001
            dt, problemas = time.perf_counter() - t, [f"error {e!r}"]
        fallas += bool(problemas)
        print(f"{'FALLA' if problemas else 'ok   '} {dt:5.2f}s  {pregunta}" + (f"  -> {'; '.join(problemas)}" if problemas else ""))
    print(f"\n{len(CASOS) - fallas}/{len(CASOS)} correctas")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
