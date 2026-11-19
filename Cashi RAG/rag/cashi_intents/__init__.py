# -*- coding: utf-8 -*-
"""
rag/cashi_intents — Clasificador de intención de Cashi (datos en ejemplos.json).

Una intención (variación ranking, variación total, desglose, estructura, alertas,
tendencia, conversacional...) se aprende de ejemplos en lenguaje natural, no de
reglas por frase. El clasificador es TF-IDF de caracteres + regresión logística.
Si el modelo no existe, `predecir` devuelve None y Cashi sigue con sus reglas.

Uso:  python -m rag.cashi_intents.entrenar      (reentrena desde ejemplos.json)
"""
