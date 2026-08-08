# -*- coding: utf-8 -*-
"""Valida la paleta: contraste WCAG sobre el fondo oscuro y separación
perceptual entre colores, incluida simulación de daltonismo (deutan/protan)."""
import sys, io, math
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from estilo import PALETA, SERIE, SEMANTICA

fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def lin(c):
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminancia(h):
    r, g, b = hex2rgb(h)
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contraste(a, b):
    l1, l2 = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def simular(h, tipo):
    """Brettel/Viénot aproximado sobre RGB lineal."""
    r, g, b = (lin(x) for x in hex2rgb(h))
    if tipo == "deutan":     # sin conos M (verde) — el más común
        rr = 0.625 * r + 0.375 * g
        gg = 0.700 * r + 0.300 * g
        bb = 0.300 * g + 0.700 * b
    else:                    # protan — sin conos L (rojo)
        rr = 0.567 * r + 0.433 * g
        gg = 0.558 * r + 0.442 * g
        bb = 0.242 * g + 0.758 * b
    f = lambda c: max(0.0, min(1.0, c))
    return (f(rr), f(gg), f(bb))


def dist(c1, c2):
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(c1, c2)))


print("=== 1. Contraste de texto sobre el fondo (WCAG) ===")
for n, c in [("txt principal", PALETA["txt"]), ("txt_dim", PALETA["txt_dim"])]:
    r = contraste(c, PALETA["bg"])
    check(f"{n} >= 4.5:1", r >= 4.5, f"{r:.2f}:1")
r = contraste(PALETA["txt_faint"], PALETA["bg"])
check("txt_faint >= 3:1 (solo texto grande/decorativo)", r >= 3.0, f"{r:.2f}:1")

print("\n=== 2. Los 4 colores de serie se ven sobre el fondo ===")
for k, c in SERIE.items():
    r = contraste(c, PALETA["bg"])
    check(f"{k:14s} >= 3:1", r >= 3.0, f"{c} -> {r:.2f}:1")

print("\n=== 3. Las series se distinguen entre sí (visión normal) ===")
ks = list(SERIE)
peor = (99, "", "")
for i in range(len(ks)):
    for j in range(i + 1, len(ks)):
        a, b = SERIE[ks[i]], SERIE[ks[j]]
        d = dist([lin(x) for x in hex2rgb(a)], [lin(x) for x in hex2rgb(b)])
        if d < peor[0]:
            peor = (d, ks[i], ks[j])
check("todo par de series difiere > 0.10", peor[0] > 0.10,
      f"peor par: {peor[1]} vs {peor[2]} = {peor[0]:.3f}")

print("\n=== 4. Semántica bueno/malo bajo daltonismo ===")
print("    (el par crítico: teal 'ahorro' vs carmín 'sobre plan')")
for tipo in ("deutan", "protan"):
    a = simular(SEMANTICA["bueno"], tipo)
    b = simular(SEMANTICA["malo"], tipo)
    d = dist(a, b)
    check(f"{tipo}: bueno vs malo distinguibles", d > 0.12, f"distancia {d:.3f}")
    # además deben diferir en luminancia, no solo en tono
    la = 0.2126*a[0] + 0.7152*a[1] + 0.0722*a[2]
    lb = 0.2126*b[0] + 0.7152*b[1] + 0.0722*b[2]
    check(f"{tipo}: difieren en luminancia", abs(la - lb) > 0.06, f"ΔL {abs(la-lb):.3f}")

print("\n=== 5. Series bajo daltonismo ===")
for tipo in ("deutan", "protan"):
    peor = (99, "", "")
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            d = dist(simular(SERIE[ks[i]], tipo), simular(SERIE[ks[j]], tipo))
            if d < peor[0]:
                peor = (d, ks[i], ks[j])
    check(f"{tipo}: series separadas", peor[0] > 0.07,
          f"peor: {peor[1]} vs {peor[2]} = {peor[0]:.3f}")

print("\n=== 6. Sin colisión serie/semántica ===")
choques = []
for sk, sv in SERIE.items():
    for mk in ("bueno", "malo"):
        d = dist([lin(x) for x in hex2rgb(sv)], [lin(x) for x in hex2rgb(SEMANTICA[mk])])
        if d < 0.10:
            choques.append(f"{sk}~{mk} ({d:.3f})")
check("ninguna serie se confunde con bueno/malo", not choques, str(choques))

print(f"\n{'='*56}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
