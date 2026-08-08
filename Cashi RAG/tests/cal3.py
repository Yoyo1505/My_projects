# -*- coding: utf-8 -*-
"""Deduce la fecha ancla desde el dato del usuario:
   'la semana 27 de 2026 tiene 3 días de junio y 4 de julio'."""
import sys, io
from collections import defaultdict
from datetime import date, timedelta
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


def semana_dias(inicio_sem1: date, sem: int):
    ini = inicio_sem1 + timedelta(days=7 * (sem - 1))
    d = defaultdict(int)
    for i in range(7):
        d[(ini + timedelta(days=i)).month] += 1
    return ini, dict(d)


print("Buscando el inicio de la semana 1 de 2026 tal que la sem 27 = 3 días jun + 4 días jul\n")
cands = []
for off in range(-15, 16):
    ini1 = date(2025, 12, 25) + timedelta(days=off)
    _, dias = semana_dias(ini1, 27)
    if dias.get(6) == 3 and dias.get(7) == 4:
        ini27, _ = semana_dias(ini1, 27)
        cands.append((ini1, ini27))

for ini1, ini27 in cands:
    print(f"  sem1 inicia {ini1} ({ini1.strftime('%A')})  ->  sem27 = {ini27} a {ini27+timedelta(days=6)}")

if not cands:
    print("  NINGUNA fecha ancla reproduce ese reparto -> revisar el supuesto")
    sys.exit(1)

ANCLA = cands[0][0]
print(f"\n>>> ANCLA 2026: semana 1 empieza el {ANCLA} ({ANCLA.strftime('%A')})")

print("\n=== Calendario EKT 2026 · semanas partidas entre 2 meses ===")
MESES_N = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
for s in range(1, 54):
    ini, dias = semana_dias(ANCLA, s)
    if len(dias) > 1:
        det = "  ".join(f"{d}d {MESES_N[m]}" for m, d in sorted(dias.items()))
        print(f"  sem {s:>2} ({ini} a {ini+timedelta(days=6)}): {det}")

print("\n=== Peso de cada semana por mes (fracción de días) ===")
peso = defaultdict(dict)   # mes -> {sem: fraccion}
for s in range(1, 54):
    _, dias = semana_dias(ANCLA, s)
    for m, d in dias.items():
        peso[m][s] = d / 7

for m in sorted(peso):
    sems = peso[m]
    total = sum(sems.values())
    print(f"  {MESES_N[m]}: {len(sems)} semanas, suma de pesos = {total:.3f} "
          f"({', '.join(f'{s}:{f:.2f}' for s, f in sorted(sems.items()))})")

print("\n=== Control: la suma de todos los pesos debe ser 53 ===")
tot = sum(f for m in peso for f in peso[m].values())
print(f"  suma = {tot:.4f}  ({'OK' if abs(tot-53) < 1e-9 else 'FALLA'})")

# Y 2025 (para Real 2025) — mismo esquema, 52 o 53 semanas
print("\n=== Ancla 2025 (Real 2025) ===")
# la semana 1 de 2026 empieza ANCLA; la sem 1 de 2025 = ANCLA - 52 o 53 semanas
for nsem in (52, 53):
    a25 = ANCLA - timedelta(days=7 * nsem)
    print(f"  si 2025 tuvo {nsem} semanas -> sem1 2025 = {a25} ({a25.strftime('%A')})")
