# -*- coding: utf-8 -*-
"""Parámetros de detección. Todo ajustable sin tocar la lógica."""

HISTORIA_MIN = 8          # semanas previas mínimas para evaluar una semana de un CECO / grupo
ZR_UMBRAL = 3.5           # z robusto (0.6745·(x−mediana)/MAD) a partir del cual la semana es inusual
IMPACTO_MIN_CECO = 100_000.0     # MXN: desviación mínima contra su mediana para que un CECO cuente
IMPACTO_MIN_GRUPO = 1_000_000.0  # MXN: igual, para un grupo de cuentas
IMPACTO_MIN_TOTAL = 5_000_000.0  # MXN: igual, para el total semanal
TOP_N = 10                # filas que muestra Cashi por defecto

# --- Modelo no supervisado (Isolation Forest + PCA). Nada de esto se reentrena solo: lo decide `train`. ---
SEMILLA = 42
N_ARBOLES = 200
SEM_CALIBRACION = 4          # últimas semanas del entrenamiento que se reservan para fijar el umbral
CUANTIL_ALERTA = 0.995       # umbral = cuantil del score del ensemble en la calibración (capacidad operativa)
ZR_CONTAMINACION = 6.0       # filas con |ZR| ≥ esto y material NO entran al conjunto "normal" de entrenamiento
SEMANAS_BACKTEST = 6         # backtesting walk-forward (reentrena con el pasado y puntúa la semana siguiente)
PSI_VIGILAR, PSI_ALERTA = 0.10, 0.25
MIN_FILAS_ENTRENAMIENTO = 300
