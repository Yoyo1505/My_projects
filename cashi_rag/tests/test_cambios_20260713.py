# -*- coding: utf-8 -*-
"""Valida los 2 pendientes del 2026-07-13 tarde:
1) filtro global de Cuenta en el sidebar (junto a Grupo de Cuentas)
2) árbol de Cierres con 4 niveles: Agrupa3 -> Grupo de Cuentas -> Territorio -> División
"""
import sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest

BASE = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
fails = []


def check(n, c, d=""):
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")
    if not c:
        fails.append(n)


def login_en(seccion):
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=300)
    at.session_state["user"] = {"username": "Karlo", "role": "admin"}
    at.session_state["nav_sec"] = [seccion]
    return at.run()


print("=== Filtro de Cuenta en sidebar ===")
at = login_en("Resumen")
check("sin excepción", not at.exception,
      str(at.exception[0].value)[:300] if at.exception else "")

ms_labels = [m.label for m in at.sidebar.multiselect]
check("existe multiselect 'Grupo de Cuentas'", "Grupo de Cuentas" in ms_labels, str(ms_labels))
check("existe multiselect 'Cuenta'", "Cuenta" in ms_labels, str(ms_labels))

cta_widget = next((m for m in at.sidebar.multiselect if m.label == "Cuenta"), None)
check("'Cuenta' tiene opciones", cta_widget is not None and len(cta_widget.options) > 0,
      str(len(cta_widget.options)) if cta_widget else "no encontrado")

if cta_widget and cta_widget.options:
    cta_widget.set_value([cta_widget.options[0]]).run()
    check("sin excepción tras filtrar por Cuenta", not at.exception,
          str(at.exception[0].value)[:300] if at.exception else "")

print("\n=== Árbol de Cierres: 4 niveles Agrupa3 -> GPO -> Territorio -> División ===")
at2 = login_en("Cierres")
check("sin excepción en Cierres", not at2.exception,
      str(at2.exception[0].value)[:300] if at2.exception else "")

md = "\n".join(m.value for m in at2.markdown if m.value)
import re
m = re.search(r"Detalle Jerárquico:[^\n<]*", md)
check("título de árbol dice 4 niveles correctos",
      m is not None and "Tipo" in m.group(0) and "Territorio" in m.group(0)
      and "División" in m.group(0), m.group(0) if m else "no encontrado")
check("ya NO menciona Cuenta en el título del árbol",
      "Tipo → GPO → Cuenta" not in md, "todavía aparece Cuenta")
check("ya NO menciona Región en el título del árbol",
      "→ Región" not in md, "todavía aparece Región")

print(f"\n{'TODO OK' if not fails else f'{len(fails)} FALLAS: ' + str(fails)}")
sys.exit(1 if fails else 0)
