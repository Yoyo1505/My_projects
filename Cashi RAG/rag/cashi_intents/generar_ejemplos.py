# -*- coding: utf-8 -*-
"""
rag/cashi_intents/generar_ejemplos.py — Genera ejemplos de entrenamiento desde plantillas y
los nombres reales del catálogo (cuentas, grupos, divisiones, territorios, contralorías, CECOs).

Salida: ejemplos_generados.json (lo lee entrenar.py junto con ejemplos.json). Las preguntas
de gold_real.json NO se usan aquí: son la prueba independiente.

    python -m rag.cashi_intents.generar_ejemplos
"""
from __future__ import annotations

import json
import random
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SALIDA = AQUI / "ejemplos_generados.json"
POR_PLANTILLA = 6
SEMILLA = 11

# {c}=cuenta/grupo/contraloría, {t}=territorio, {d}=división, {k}=ceco, {e}=cualquier entidad con prefijo
PLANTILLAS = {
    "gasto_total": [
        "dame el gasto de {e}", "gasto de {c} de {t}", "cuanto se ha gastado en {e}", "total real 2026 de {e}",
        "el gasto de {c} para {d}", "gasto acumulado de {e}", "cuanto suma {e}", "monto de {c} en {d}",
        "gastos de {c}", "{c} real 2026", "cuanto va de {c} en {t}", "dime el gasto total de {e}",
        "que gasto lleva {e}", "gasto de {c} para el ceco {k}", "total gastado por {e}",
    ],
    "desglose_dimension": [
        "dame el gasto de {e} por semana", "gasto de {e} por mes", "gasto de {d} por territorio",
        "desglosa el gasto de {c} por division", "gasto de {t} por zona", "gasto de {c} por territorio",
        "dame el gasto de {e} por cuenta", "gasto de {d} por grupo de cuentas", "gasto semanal de {e}",
        "dame el gasto de {e} por ceco", "reparte el gasto de {c} por semana", "gasto mensual de {e}",
    ],
    "gasto_ranking": [
        "que ceco gasta mas en {e}", "top 10 cecos de {e}", "cual territorio gasta mas en {c}",
        "las 5 cuentas con mas gasto de {e}", "que division gasta mas en {c}", "top 5 pdv por gasto en {e}",
        "cual es la cuenta que mas gasta en {t}", "los 3 cecos con mayor gasto de {d}", "top 10 cecos",
        "ranking de gasto por territorio", "cuales son las cuentas con mas gasto",
    ],
    "variacion_ranking": [
        "que cecos se pasaron del plan en {e}", "top 5 cuentas con mayor variacion vs plan en {e}",
        "que territorios ahorraron mas en {c}", "las 10 cuentas con mayor sobregasto en {d}",
        "ranking de variaciones vs plan de {e}", "que cuentas tienen mas desviacion contra el plan",
        "top variaciones contra el año anterior de {e}", "mayores ahorros de {e}",
        "cuales cecos mas se pasaron en {t}", "top variaciones vs plan por {c}",
    ],
    "variacion_total": [
        "cuanto vario {e} vs plan", "variacion de {e} contra el año anterior", "como vamos en {e} contra plan",
        "diferencia de {e} vs presupuesto", "cuanto nos pasamos en {e}", "cuanto ahorramos en {e}",
        "estamos arriba o abajo del plan en {e}", "variacion total de {e} en la semana 30",
        "dame la variacion de {e}", "desviacion de {e} contra real 2025",
    ],
    "estructura": [
        "que territorios tiene {d}", "de que division es {t}", "a que division pertenece el ceco {k}",
        "cuantas zonas hay en {t}", "que contraloria tiene el ceco {k}", "de que territorio es el ceco {k}",
        "cuantos territorios tiene {d}", "que cuentas tiene el grupo {c}", "cuantos cecos hay en {t}",
        "dime a que territorio pertenece el ceco {k}", "que divisiones hay",
    ],
    "alertas": [
        "alertas de sobregasto en {e}", "hay anomalias en {e}", "senales de sobregasto de {d}",
        "que aumento inusual hubo en {t}", "que grupos de cuentas aumentaron esta semana en {d}",
        "alertas de la semana 38 para {e}", "detecta anomalias en {c}",
    ],
    "tendencia": [
        "tendencia semanal de {e}", "como evoluciono {e} por mes", "grafica de {e} semana a semana",
        "comportamiento mensual de {e}", "evolucion de {c} en {t}", "tendencia de {e} en el año",
    ],
}


def _catalogo():
    from rag.financial_rag import UnifiedCashiRAGEngine
    e = UnifiedCashiRAGEngine()
    uniq = lambda m: sorted({str(v) for v in m.values() if str(v) not in ("0", "No Clasificado", "Otros")})
    cuentas = uniq(e.map_cuentas) + uniq(e.map_grupos) + uniq(e.map_contraloria6)
    divisiones = ["la " + v.lower() for v in uniq(e.map_divisiones)]
    territorios = [v.lower() for v in uniq(e.map_territorios)]
    cecos = sorted(e.validos_cecos_clean)
    return cuentas, divisiones, territorios, cecos


def main():
    rnd = random.Random(SEMILLA)
    cuentas, divisiones, territorios, cecos = _catalogo()
    salida = {}
    for intencion, plantillas in PLANTILLAS.items():
        frases = set()
        for p in plantillas:
            for _ in range(POR_PLANTILLA):
                c, d, t, k = rnd.choice(cuentas), rnd.choice(divisiones), rnd.choice(territorios), rnd.choice(cecos)
                e = rnd.choice([c.lower(), d, t, f"el ceco {k}", f"{c.lower()} de {d}"])
                frases.add(p.format(c=c.lower(), d=d, t=t, k=k, e=e))
        salida[intencion] = sorted(frases)
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print({k: len(v) for k, v in salida.items()})


if __name__ == "__main__":
    main()
