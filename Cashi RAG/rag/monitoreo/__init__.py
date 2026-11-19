# -*- coding: utf-8 -*-
"""rag/monitoreo — variaciones semana contra semana y semanas atípicas (Real, Plan, FCST SIE).

Lo comparten la pestaña "Señales de Sobregasto" y Cashi. No abre conexiones: quien llama
pasa `ejecutar(sql, params) -> DataFrame` (mismo patrón que `rag/senales_sobregasto.py`).
"""
