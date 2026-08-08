# -*- coding: utf-8 -*-
"""Valida el prorrateo diario contra el ejemplo del usuario y contra los parquets."""
import sys, io, json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import polars as pl

A = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio\aggs")
ANCLA = {2025: date(2024, 12, 29), 2026: date(2025, 12, 28)}
ANIO = {"Real_2025": 2025, "Real_2026": 2026, "Plan_2026": 2026, "Nvo_Plan_2026": 2026}
MEDIDAS = ["Real_2025", "Plan_2026", "Real_2026", "Nvo_Plan_2026"]
fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


def pesos_mes(anio):
    ini1 = ANCLA[anio]
    out = {}
    for s in range(1, 54):
        ini = ini1 + timedelta(days=7 * (s - 1))
        dias = defaultdict(int)
        for i in range(7):
            d = ini + timedelta(days=i)
            if d.year == anio:
                dias[d.month] += 1
        if dias:
            out[s] = {m: n / 7 for m, n in dias.items()}
    return out


print("=== 1. El ejemplo del usuario: sem 27 de 2026 ===")
p26 = pesos_mes(2026)
ini27 = ANCLA[2026] + timedelta(days=7 * 26)
print(f"  sem 27 = {ini27} a {ini27 + timedelta(days=6)}")
check("sem 27 toca junio y julio", set(p26[27]) == {6, 7}, str(p26[27]))
check("junio recibe 3/7", abs(p26[27][6] - 3 / 7) < 1e-9, f"{p26[27][6]*7:.0f} días")
check("julio recibe 4/7", abs(p26[27][7] - 4 / 7) < 1e-9, f"{p26[27][7]*7:.0f} días")

print("\n=== 2. Cada semana reparte exactamente 1.0 (salvo bordes de año) ===")
malas = [s for s, d in p26.items() if abs(sum(d.values()) - 1.0) > 1e-9]
print(f"  semanas con peso != 1.0: {malas} (esperado: 1 y 53, cruzan el año)")
check("solo las semanas de borde suman <1", set(malas) <= {1, 53}, str(malas))
check("sem 1 aporta 3/7 a enero", abs(p26[1][1] - 3 / 7) < 1e-9, f"{p26[1][1]*7:.0f} días")

print("\n=== 3. Prorrateo vs suma bruta (global) ===")
g = pl.read_parquet(A / "global.parquet").to_pandas()
smr = json.loads((A / "_meta.json").read_text(encoding="utf-8"))["sem_max_real"]
g.loc[g["sem"] > smr, "Real_2026"] = None

mens = defaultdict(lambda: defaultdict(float))
for med in MEDIDAS:
    p = pesos_mes(ANIO[med])
    for _, r in g.iterrows():
        s, v = int(r["sem"]), r[med]
        if s not in p or v != v:  # NaN
            continue
        for m, f in p[s].items():
            mens[m][med] += float(v) * f

print(f"{'Mes':>10} {'Real 2025':>14} {'Real 2026':>14} {'Plan 2026':>14}")
for m in range(1, 13):
    print(f"{m:>10} {mens[m]['Real_2025']/1e6:>14,.1f} "
          f"{mens[m]['Real_2026']/1e6:>14,.1f} {mens[m]['Plan_2026']/1e6:>14,.1f}")

for med in ("Real_2025", "Plan_2026", "Nvo_Plan_2026"):
    tot_bruto = g[med].sum()
    tot_mens = sum(mens[m][med] for m in range(1, 13))
    perdido = tot_bruto - tot_mens
    anio = ANIO[med]
    p = pesos_mes(anio)
    fuera = sum(g.loc[g["sem"] == s, med].sum() * (1 - sum(d.values()))
                for s, d in p.items() if sum(d.values()) < 1)
    check(f"{med}: lo no asignado == días fuera del año",
          abs(perdido - fuera) < 1.0,
          f"perdido={perdido/1e6:,.1f}M  esperado={fuera/1e6:,.1f}M")

print("\n=== 4. Real 2026: junio+julio del mes 6/7 usan la sem 27 partida ===")
r27 = g.loc[g["sem"] == 27, "Real_2026"].iloc[0]
jun_de_27 = r27 * 3 / 7
jul_de_27 = r27 * 4 / 7
print(f"  Real 2026 sem 27 = {r27/1e6:,.1f} M")
print(f"    -> junio recibe {jun_de_27/1e6:,.1f} M (3/7)")
print(f"    -> julio recibe {jul_de_27/1e6:,.1f} M (4/7)")
check("suma de las dos partes == total de la semana", abs(jun_de_27 + jul_de_27 - r27) < 1e-6)
check("julio > junio (4 días vs 3)", jul_de_27 > jun_de_27)

print("\n=== 5. Real 2026 no aporta a meses después del corte ===")
p = pesos_mes(2026)
meses_con_real = [m for m in range(1, 13) if mens[m]["Real_2026"] > 1]
mes_corte = max(p[smr], key=p[smr].get)
print(f"  corte sem {smr} -> mes dominante {mes_corte}")
print(f"  meses con Real 2026: {meses_con_real}")
check("no hay Real 2026 después del mes de corte",
      max(meses_con_real) <= mes_corte + 1, str(meses_con_real))

print(f"\n{'='*56}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
