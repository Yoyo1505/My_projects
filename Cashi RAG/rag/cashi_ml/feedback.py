# -*- coding: utf-8 -*-
"""
rag/cashi_ml/feedback.py — Registro de 👍/👎 de las respuestas de Cashi.

Cada valoración es una línea JSON en `datos\\cashi_feedback.jsonl` (una por clic). Si un
usuario cambia de opinión sobre la misma respuesta, cuenta la última (campo `turno`).
Las etiquetas sirven para reentrenar el modelo con preguntas reales.
"""
from __future__ import annotations

import datetime as _dt
import json
import logging
import threading
from pathlib import Path

RUTA = Path(__file__).resolve().parents[2] / "datos" / "cashi_feedback.jsonl"
log = logging.getLogger(__name__)
_lock = threading.Lock()


def registrar(pregunta: str, res: dict, valoracion: int, usuario: str, turno: str,
              fuente: str) -> bool:
    """valoracion: +1 (buena respuesta) o -1 (mala respuesta). Nunca lanza excepción."""
    try:
        linea = {
            "ts": _dt.datetime.now().isoformat(timespec="seconds"),
            "usuario": usuario,
            "turno": turno,
            "fuente": fuente,
            "pregunta": pregunta[:300],
            "tipo_respuesta": res.get("tipo_respuesta"),
            "intencion": res.get("intencion_detectada"),
            "titulo": str(res.get("titulo", ""))[:200],
            "filtros": {k: v for k, v in (res.get("filtros_resueltos") or {}).items() if v},
            "valoracion": 1 if valoracion > 0 else -1,
        }
        RUTA.parent.mkdir(parents=True, exist_ok=True)
        with _lock:
            with open(RUTA, "a", encoding="utf-8") as f:
                f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        log.warning("cashi feedback: no se pudo registrar (%s)", e)
        return False


def resumen() -> dict:
    """Conteo por valoración usando solo la última valoración de cada turno."""
    ultimas: dict = {}
    try:
        with open(RUTA, encoding="utf-8") as f:
            for linea in f:
                if linea.strip():
                    r = json.loads(linea)
                    ultimas[(r.get("fuente"), r.get("turno"))] = r["valoracion"]
    except FileNotFoundError:
        pass
    buenas = sum(1 for v in ultimas.values() if v > 0)
    return {"turnos": len(ultimas), "buenas": buenas, "malas": len(ultimas) - buenas}
