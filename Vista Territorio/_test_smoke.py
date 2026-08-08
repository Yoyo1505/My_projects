# -*- coding: utf-8 -*-
"""Smoke test: login + todas las secciones del menú sin excepciones (AppTest)."""
import json
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

BASE = Path(__file__).parent
# "Plan + Real" oculta del menú temporalmente (2026-07-24) — no se prueba
# mientras esté fuera de SECCIONES en app.py.
# 2026-07-27: "Riesgos & Oport." eliminada (sus tablas viven en Resumen);
# "Sem / Mes" movida al segundo lugar. Debe coincidir con SECCIONES de app.py.
# 2026-07-29: "Sem / Mes" renombrada a "Temporalidad".
SECCIONES = ["Resumen", "Temporalidad", "Div / Terr", "Detalle Cuenta", "Detalle PDC",
             "PDC & Calor", "Cierres", "Trimestres"]

usuario = json.loads((BASE / "usuarios.json").read_text(encoding="utf-8"))
u = next(iter(usuario))

fallas = []
for sec in SECCIONES:
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=180)
    at.session_state["user"] = {"username": u, "role": usuario[u].get("rol", "admin")}
    at.session_state["nav_sec"] = sec
    at.run()
    if at.exception:
        fallas.append((sec, at.exception[0].value))
        print(f"[FALLA] {sec}: {at.exception[0].value}")
    else:
        print(f"[OK]    {sec}")

if fallas:
    sys.exit(1)
print("\nTodas las secciones pasan.")
