# -*- coding: utf-8 -*-
"""
rag/cashi_intents/entrenar.py — Entrena el clasificador de intención desde ejemplos.json.

Texto de entrada = normalizar + canonizar con el léxico (rag/lexico), igual que en
el motor. Se reporta exactitud sobre gold.json (frases no vistas en el entrenamiento)
y sobre validación cruzada de los ejemplos.

    python -m rag.cashi_intents.entrenar
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline

from rag.lexico import canonizar

AQUI = Path(__file__).resolve().parent
EJEMPLOS = AQUI / "ejemplos.json"
GOLD = AQUI / "gold.json"
SALIDA = Path(__file__).resolve().parents[2] / "aggs" / "cashi_intents" / "intenciones.joblib"


def normalizar_consulta(texto: str) -> str:
    """Misma normalización que el motor: sin acentos, minúsculas, sin puntuación, con léxico."""
    nfkd = unicodedata.normalize("NFKD", str(texto))
    sin_acentos = "".join(c for c in nfkd if not unicodedata.combining(c))
    limpio = " ".join(sin_acentos.lower().replace("¿", " ").replace("?", " ").split())
    return canonizar(limpio)


GENERADOS = AQUI / "ejemplos_generados.json"
GOLD_REAL = AQUI / "gold_real.json"


def cargar_ejemplos(ruta: Path = EJEMPLOS):
    """Ejemplos escritos a mano + los generados desde plantillas (si existen)."""
    X, y = [], []
    for r in (ruta, GENERADOS):
        if not r.exists():
            continue
        for intencion, frases in json.loads(r.read_text(encoding="utf-8")).items():
            if intencion.startswith("_"):
                continue
            for f in frases:
                X.append(normalizar_consulta(f))
                y.append(intencion)
    return X, y


def construir():
    return make_pipeline(
        TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), sublinear_tf=True),
        LogisticRegression(max_iter=5000, C=10.0, class_weight="balanced"),
    )


def evaluar_gold(modelo, ruta: Path = GOLD) -> dict:
    casos = json.loads(ruta.read_text(encoding="utf-8"))["casos"]
    aciertos, fallos = 0, []
    for c in casos:
        pred = modelo.predict([normalizar_consulta(c["q"])])[0]
        if pred == c["intencion"]:
            aciertos += 1
        else:
            fallos.append({"q": c["q"], "esperada": c["intencion"], "predicha": pred})
    return {"exactitud": aciertos / len(casos), "aciertos": aciertos, "total": len(casos), "fallos": fallos}


def main():
    X, y = cargar_ejemplos()
    modelo = construir()
    n_clases = len(set(y))
    cv = StratifiedKFold(n_splits=min(5, min(y.count(c) for c in set(y))), shuffle=True, random_state=7)
    cv_scores = cross_val_score(construir(), X, y, cv=cv)
    modelo.fit(X, y)
    gold = evaluar_gold(modelo)
    SALIDA.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"modelo": modelo, "intenciones": sorted(set(y))}, SALIDA)
    print(f"ejemplos: {len(X)} | intenciones: {n_clases}")
    print(f"validación cruzada (ejemplos): {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
    print(f"gold (no vistas): {gold['aciertos']}/{gold['total']} = {gold['exactitud']:.3f}")
    for f in gold["fallos"]:
        print(f"  FALLA: {f['q']!r}  esperada={f['esperada']}  predicha={f['predicha']}")
    if GOLD_REAL.exists():
        real = evaluar_gold(modelo, GOLD_REAL)
        print(f"gold_real (independiente): {real['aciertos']}/{real['total']} = {real['exactitud']:.3f}")
        for f in real["fallos"]:
            print(f"  FALLA REAL: {f['q']!r}  esperada={f['esperada']}  predicha={f['predicha']}")
    print(f"modelo guardado en {SALIDA}")
    return gold


if __name__ == "__main__":
    main()
