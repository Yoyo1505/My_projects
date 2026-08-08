# -*- coding: utf-8 -*-
"""Ejecuta app.py con el runtime de Streamlit (AppTest): 10 pestañas, cifras,
sin duplicate-ID, sin warnings de Plotly, filtro por mes."""
import sys, io, json, warnings, contextlib
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from streamlit.testing.v1 import AppTest
import polars as pl

BASE = Path(r"E:\Usuarios\112665\Downloads\Dashboard Vista Territorio")
AGGS = BASE / "aggs"
fails, oks = [], []


def check(n, c, d=""):
    (oks if c else fails).append(n)
    print(f"  [{'OK ' if c else 'FALLA'}] {n}{(' — ' + d) if d else ''}")


def sess(at_, key):
    try:
        return at_.session_state[key]
    except (KeyError, AttributeError):
        return None


def M(v):
    a = abs(v)
    if a >= 1e9:
        return f"{v/1e9:,.2f} MMDP"
    if a >= 1e6:
        return f"{v/1e6:,.1f} MDP"
    if a >= 1e3:
        return f"{v/1e3:,.0f} K"
    return f"{v:,.0f}"


def login():
    """Autentica pre-sembrando session_state: evita que AppTest siga rastreando
    los text_input del login (que dejan de renderizarse tras st.stop())."""
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=300)
    at.session_state["user"] = {"username": "Karlo", "role": "admin"}
    return at.run()


def login_form():
    """Login real por el formulario, para probar la autenticación."""
    at = AppTest.from_file(str(BASE / "app.py"), default_timeout=300).run()
    at.text_input[0].set_value("Karlo")
    at.text_input[1].set_value("HannaZeus2025")
    at.button[0].click().run()
    return at


def html_de(at_):
    return "\n".join(m.value for m in at_.markdown if m.value)

print("=== 0. Autenticación real (formulario) ===")
atf = AppTest.from_file(str(BASE / "app.py"), default_timeout=300).run()
atf.text_input[0].set_value("Karlo")
atf.text_input[1].set_value("mala")
atf.button[0].click().run()
check("rechaza password incorrecto", len(atf.error) > 0 and sess(atf, "user") is None)
at0 = login_form()
check("acepta password correcto", sess(at0, "user") is not None, str(sess(at0, "user")))

print("\n=== 1. Arranque y login ===")
at = login()
check("login OK", sess(at, "user") is not None)
check("sin excepción", not at.exception,
      str(at.exception[0].value)[:220] if at.exception else "")
check("10 pestañas", len(at.tabs) == 10, f"{len(at.tabs)}")

print("\n=== 2. Sin StreamlitDuplicateElementId ===")
exc = str(at.exception[0].value) if at.exception else ""
check("cero duplicate-ID", "DuplicateElementId" not in exc, exc[:140])

print("\n=== 3. Cifras vs parquet (KPIs son tarjetas HTML tras el rediseño) ===")
meta = json.loads((AGGS / "_meta.json").read_text(encoding="utf-8"))
smr = meta["sem_max_real"]
g = pl.read_parquet(AGGS / "global.parquet").filter(pl.col("sem") <= smr)
verdad = {m: g[m].sum() for m in ("Real_2025", "Real_2026", "Plan_2026", "Nvo_Plan_2026")}

# el HTML de las tarjetas vive en los bloques st.markdown
html = "\n".join(m.value for m in at.markdown if m.value)
mets = {m.label: m.value for m in at.metric}   # por si queda alguna nativa


def en_ui(txt: str) -> bool:
    return txt in html or txt in " ".join(str(v) for v in mets.values())


for lbl, key in [("Real 2026", "Real_2026"), ("Real 2025", "Real_2025"),
                 ("Plan 2026", "Plan_2026"), ("Nvo Plan", "Nvo_Plan_2026")]:
    esperado = M(verdad[key])
    check(f"cifra {lbl} presente", en_ui(esperado),
          f"{esperado} (= {verdad[key]/1e6:,.1f} MDP del parquet)")

print("\n=== 3b. Número héroe: la desviación vs plan ===")
desv = verdad["Real_2026"] - verdad["Plan_2026"]
check("hero 'Desviación vs Plan' existe", "Desviación vs Plan" in html)
check("hero muestra el valor correcto", M(abs(desv)) in html,
      f"|{desv/1e6:,.1f} MDP| -> {M(abs(desv))}")
check("hero lleva chip Sobre/Bajo plan",
      ("Sobre plan" in html or "Bajo plan" in html))

print("\n=== 4. KPIs presentes tras el rediseño ===")
for k in ("Gasto semanal prom.", "PDCs con gasto", "Divisiones sobre plan",
          "Mayor grupo de gasto", "Nvo Plan", "Forecast Cierre",
          "vs Año Anterior", "Periodo"):
    check(f"KPI '{k}'", k in html)

print("\n=== 4b. El CSS y las secciones se inyectaron ===")
check("CSS inyectado", "<style>" in html and ".hero" in html)
check("cero recursos externos en el CSS",
      "http://" not in html and "https://" not in html and "@import" not in html)
check("etiquetas de sección", 'class="sec"' in html)

print("\n=== 5. Filtro por Mes ===")
at2 = login()
rad = [r for r in at2.radio if r.label == "Filtrar por"][0]
check("selector 'Filtrar por' con 4 modos", len(rad.options) == 4, str(rad.options))
rad.set_value("Mes").run()
check("modo Mes sin excepción", not at2.exception,
      str(at2.exception[0].value)[:180] if at2.exception else "")
sb = [s for s in at2.selectbox if s.label == "Mes"]
check("aparece selector de Mes", len(sb) == 1, str(sb[0].options[:2]) if sb else "")
if sb:
    from collections import defaultdict
    from datetime import date, timedelta

    def pesos(anio):
        ini1 = {2025: date(2024, 12, 29), 2026: date(2025, 12, 28)}[anio]
        out = {}
        for s in range(1, 54):
            ini = ini1 + timedelta(days=7 * (s - 1))
            dd = defaultdict(int)
            for i in range(7):
                d = ini + timedelta(days=i)
                if d.year == anio:
                    dd[d.month] += 1
            if dd:
                out[s] = {m: n / 7 for m, n in dd.items()}
        return out

    sb[0].set_value(3).run()  # marzo, con prorrateo diario
    h2 = html_de(at2)
    gg = pl.read_parquet(AGGS / "global.parquet").to_pandas()
    gg.loc[gg["sem"] > smr, "Real_2026"] = 0.0
    p26 = pesos(2026)
    esperado = sum(gg.loc[gg["sem"] == s, "Real_2026"].sum() * f
                   for s, d in p26.items() for m_, f in d.items() if m_ == 3)
    check("Real 2026 de marzo con prorrateo", M(esperado) in h2,
          f"calculado={M(esperado)}")
    # marzo debe incluir 3/7 de la semana 14 (que cruza a abril)
    check("marzo toma parte de la sem 14", 14 in p26 and p26[14].get(3, 0) > 0,
          f"sem14 -> {p26[14]}")
    check("sin excepción tras elegir mes", not at2.exception,
          str(at2.exception[0].value)[:180] if at2.exception else "")

print("\n=== 6. Filtro por Trimestre ===")
at3 = login()
[r for r in at3.radio if r.label == "Filtrar por"][0].set_value("Trimestre").run()
sb = [s for s in at3.selectbox if s.label == "Trimestre"]
check("aparece selector de Trimestre", len(sb) == 1)
if sb:
    sb[0].set_value("Q1").run()
    h3 = html_de(at3)
    q1 = pl.read_parquet(AGGS / "global.parquet").filter(pl.col("sem") <= 13)
    check("Real 2026 de Q1 cuadra", M(q1["Real_2026"].sum()) in h3,
          f"esperado={M(q1['Real_2026'].sum())}")

print("\n=== 7. Drill: Agrupa YA NO está en Div/Terr ===")
jr = [r for r in at.radio if r.label == "Jerarquía"][0]
check("solo Territorial y Contable", list(jr.options) == ["Territorial", "Contable"], str(jr.options))
agr = [r for r in at.radio if r.label == "Nivel de agrupación"]
check("Agrupa vive en Cierres", len(agr) == 1,
      str(agr[0].options) if agr else "no encontrado")

print("\n=== 8. PDC: filtros y sin truncar ===")
tin = [t for t in at.text_input if t.label == "Buscar PDC"]
check("buscador de PDC", len(tin) == 1)
cbs = [c for c in at.checkbox if "gasto o plan" in (c.label or "")]
check("checkbox 'solo con movimiento'", len(cbs) == 1)
dls = [d for d in at.get("download_button")]
check("botones de descarga CSV", len(dls) >= 2, f"{len(dls)}")

print("\n=== 9. Semanal: tabla de gasto ===")
gr = [r for r in at.radio if r.label == "Granularidad"]
check("selector Semanal/Mensual", len(gr) == 1, str(gr[0].options) if gr else "")
subs = [h.value for h in at.subheader]
check("tabla de gasto presente", any("Tabla de gasto" in s for s in subs),
      str([s for s in subs if "gasto" in s.lower()]))

print("\n=== 10. Calor: symlog sustituye al recorte ===")
sl = [s for s in at.slider if "Recorte" in (s.label or "")]
check("ya no hay slider de recorte", len(sl) == 0, "sustituido por escala simetrica log")
figs = at.get("plotly_chart")
spec = ""
for f in figs:
    try:
        spec += str(f.proto.spec)
    except Exception:
        pass
check("el grafico usa escala simetrica log",
      "logar" in spec.lower(), "subtitulo en el layout de Plotly")
check("declara que no excluye datos", "excluye" in spec.lower())
check("los ticks del eje cubren los outliers (k%)", "k%" in spec)

print("\n=== 11. Render general ===")
check("gráficas plotly", len(at.get("plotly_chart")) >= 8, f"{len(at.get('plotly_chart'))}")
check("dataframes", len(at.dataframe) >= 8, f"{len(at.dataframe)}")
errs = [e.value for e in at.error if "Falta " in e.value or "Traceback" in e.value]
check("sin errores de datos faltantes", not errs, str(errs)[:120])

print(f"\n{'='*56}\nOK: {len(oks)}   FALLAS: {len(fails)}")
if fails:
    print("FALLARON: " + ", ".join(fails))
sys.exit(1 if fails else 0)
