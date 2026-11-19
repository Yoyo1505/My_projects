# -*- coding: utf-8 -*-
"""Pruebas de rag/monitoreo. TODOS los datos de este archivo son SINTÉTICOS (solo para pruebas unitarias).

Correr (desde la raíz del proyecto, con el Python que tiene scikit-learn y pytest):
    python -m pytest rag/monitoreo/tests -q
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import polars as pl
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from rag.monitoreo import config as C                      # noqa: E402
from rag.monitoreo import modelo, registro                 # noqa: E402
from rag.monitoreo.atipicos import bloques, detectar, texto_semanas   # noqa: E402
from rag.monitoreo.features import FEATURES, construir, elegibles    # noqa: E402
from rag.monitoreo.variaciones import variaciones          # noqa: E402


def _serie(valores, sems=None, clave="e"):
    sems = sems or list(range(1, len(valores) + 1))
    return pd.DataFrame({clave: "A", "sem": sems, "monto": valores})


def _panel(n_cecos=40, n_sem=30, semilla=0, pico=None):
    """Panel sintético ceco × semana con ruido; `pico`=(ceco, sem, monto) inyecta un valor extremo."""
    rng = np.random.default_rng(semilla)
    filas = []
    for c in range(n_cecos):
        base = rng.uniform(2e5, 2e6)
        for s in range(1, n_sem + 1):
            filas.append((f"C{c}", s, base * rng.uniform(0.9, 1.1), base))
    df = pl.DataFrame(filas, schema=["ceco", "sem", "real", "plan"], orient="row").with_columns(pl.col("sem").cast(pl.Int32))
    if pico:
        df = df.with_columns(pl.when((pl.col("ceco") == pico[0]) & (pl.col("sem") == pico[1])).then(pico[2]).otherwise(pl.col("real")).alias("real"))
    return df


# ------------------------------------------------------------------ estadístico
def test_semanas_no_continuas():
    v = [100.0] * 8 + [100.0, 100.0] + [5000.0] + [100.0] * 5
    s = list(range(1, 9)) + [10, 12, 15, 16, 17, 20, 21, 22]      # hay huecos
    a = detectar(_serie(v, s), "e", piso=100.0, modo="retro")
    assert list(a["sem"]) == [15]


def test_mad_cero_no_divide_entre_cero():
    a = detectar(_serie([100.0] * 12 + [900.0]), "e", piso=100.0, modo="pasado")        # serie constante: MAD=0 y media abs=0
    assert len(a) == 1 and np.isfinite(a["zr"].iloc[0]) and a["metodo"].iloc[0] == "PISO_RELATIVO"
    b = detectar(_serie([100.0, 101.0] * 6 + [900.0]), "e", piso=100.0, modo="pasado")  # MAD>0
    assert b["metodo"].iloc[0] == "MAD"


def test_montos_negativos():
    a = detectar(_serie([-100.0] * 12 + [-5000.0]), "e", piso=100.0, modo="pasado")
    assert len(a) == 1 and a["dif"].iloc[0] < 0


def test_historia_insuficiente_no_marca():
    assert detectar(_serie([100.0, 100.0, 9000.0]), "e", piso=100.0, modo="pasado").empty


def test_materialidad_evita_marcar_ruido_con_mad_diminuto():
    v = [100.0, 100.01, 99.99] * 4 + [101.0]
    assert detectar(_serie(v), "e", piso=100_000.0, modo="pasado").empty


def test_bloque_consecutivo_y_clasificacion():
    # (con >25% de la serie en el bloque, mediana/IQR dejan de ser robustos: límite conocido del método)
    v = [100.0] * 30 + [9000.0, 9100.0, 9200.0, 9000.0, 9100.0, 9000.0] + [100.0] * 3
    a = detectar(_serie(v), "e", piso=100.0, modo="retro")
    b = bloques(a, "e")
    assert len(b) == 1 and b["tipo"].iloc[0] == "CAMBIO_ESTRUCTURAL" and int(b["n"].iloc[0]) == 6


def test_anomalia_puntual():
    a = detectar(_serie([100.0] * 12 + [9000.0] + [100.0] * 3), "e", piso=100.0, modo="retro")
    assert bloques(a, "e")["tipo"].iloc[0] == "PUNTUAL"


def test_texto_semanas():
    assert texto_semanas([6, 7, 8]) == "6 a 8"
    assert texto_semanas([6, 7, 12]) == "6, 7 y 12"
    assert texto_semanas([43]) == "43"


def test_resultado_vacio():
    assert detectar(pd.DataFrame(columns=["e", "sem", "monto"]), "e", piso=1.0).empty
    assert bloques(pd.DataFrame(columns=["e", "sem", "dif", "zr"]), "e").empty


def test_variaciones_n_contra_n1_y_cuadre():
    filas = [("R26", s, g, v) for s in (41, 42, 43) for g, v in (("G1", 100.0 * s), ("G2", 50.0))] + \
            [("P26", s, g, 90.0) for s in (42, 43) for g in ("G1", "G2")]
    base = pd.DataFrame(filas, columns=["Serie", "sem", "cat_Grupo_de_Cuentas", "monto"])

    def ejecutar(sql, prm):
        if "FROM fcst" in sql:
            return pd.DataFrame({"ent": ["G1"], "sem": [43], "f": [7.0]})
        return base.rename(columns={"cat_Grupo_de_Cuentas": "ent"})[["ent", "sem", "Serie", "monto"]]

    v = variaciones(ejecutar, 43, "grupo", tabla="t", tabla_fcst="fcst").set_index("cat_Grupo_de_Cuentas")
    assert v.loc["G1", "Var_Real"] == 4300.0 - 4200.0
    assert v.loc["G1", "Real_vs_Plan"] == 4300.0 - 90.0
    assert v.loc["G1", "FCST_N"] == 7.0
    assert v["Var_Real"].sum() == (4300.0 + 50.0) - (4200.0 + 50.0)      # conciliación: suma de variaciones = variación total


# ------------------------------------------------------------------ features
def test_features_sin_fuga_temporal():
    """Cambiar el FUTURO no altera las features de la semana t."""
    p1 = _panel(5, 24)
    p2 = p1.with_columns(pl.when(pl.col("sem") > 20).then(pl.col("real") * 50).otherwise(pl.col("real")).alias("real"))
    f1, f2 = construir(p1).filter(pl.col("sem") == 20), construir(p2).filter(pl.col("sem") == 20)
    for c in FEATURES:
        assert f1[c].to_list() == f2[c].to_list(), c


def test_features_con_rejilla_marca_semana_ausente():
    p = _panel(2, 12).filter(~((pl.col("ceco") == "C0") & (pl.col("sem") == 6)))
    f = construir(p).filter((pl.col("ceco") == "C0") & (pl.col("sem") == 6))
    assert f.height == 1 and f["presente"][0] is False        # se registra la ausencia, no se oculta


# ------------------------------------------------------------------ modelo
def test_reproducibilidad():
    feat = construir(_panel())
    m1, m2 = modelo.entrenar(feat, 26, semilla=7), modelo.entrenar(feat, 26, semilla=7)
    el = elegibles(feat, C.HISTORIA_MIN)
    assert np.allclose(modelo.puntuar(m1["obj"], el)["score"].to_numpy(), modelo.puntuar(m2["obj"], el)["score"].to_numpy())


def test_modelo_no_entrenado():
    with pytest.raises(modelo.ModeloNoEntrenado):
        modelo.puntuar({}, elegibles(construir(_panel(3, 20)), C.HISTORIA_MIN))


def test_puntuar_con_columnas_faltantes():
    feat = construir(_panel())
    m = modelo.entrenar(feat, 26)
    el = elegibles(feat, C.HISTORIA_MIN).drop("zr8")
    with pytest.raises(ValueError, match="zr8"):
        modelo.puntuar(m["obj"], el)


def test_datos_insuficientes():
    with pytest.raises(ValueError, match="insuficientes"):
        modelo.entrenar(construir(_panel(2, 12)), 11)


def test_detecta_pico_inyectado():
    feat = construir(_panel(pico=("C3", 28, 5e8)))
    m = modelo.entrenar(feat, 26)
    p = modelo.puntuar(m["obj"], elegibles(feat, C.HISTORIA_MIN).filter(pl.col("sem") == 28))
    top = p.sort("score", descending=True).row(0, named=True)
    assert top["ceco"] == "C3" and top["alerta"]


def test_contaminacion_no_entra_al_conjunto_normal():
    """Un evento crítico dentro de la ventana de entrenamiento se excluye del conjunto 'normal'."""
    feat = construir(_panel(pico=("C3", 20, 5e8)))
    meta = modelo.entrenar(feat, 26)["meta"]
    assert meta["filas_excluidas_contaminacion"] >= 1


def test_drift_psi_detecta_cambio_de_distribucion():
    feat = construir(_panel())
    m = modelo.entrenar(feat, 26)
    el = elegibles(feat, C.HISTORIA_MIN)
    X = modelo._matriz(el)
    base = modelo.psi(m["obj"]["psi_ref"], X)
    X2 = X.copy()
    X2[:, FEATURES.index("zr8")] += 8.0
    assert max(base.values()) < C.PSI_ALERTA and modelo.psi(m["obj"]["psi_ref"], X2)["zr8"] > C.PSI_ALERTA


def test_causas_son_texto_y_no_rompen_con_vacio():
    feat = construir(_panel(pico=("C3", 28, 5e8)))
    m = modelo.entrenar(feat, 26)
    p = modelo.puntuar(m["obj"], elegibles(feat, C.HISTORIA_MIN).filter(pl.col("sem") == 28)).filter(pl.col("alerta"))
    assert all(isinstance(t, str) for t in modelo.causas(m["obj"], p)) and modelo.causas(m["obj"], p.head(0)) == []


# ------------------------------------------------------------------ registro
@pytest.fixture
def reg(tmp_path, monkeypatch):
    monkeypatch.setattr(registro, "DIR_MODELOS", tmp_path / "modelos")
    monkeypatch.setattr(registro, "CHAMPION", tmp_path / "champion.json")
    monkeypatch.setattr(registro, "SALIDA", tmp_path)
    return registro


def _modelo_chico():
    m = modelo.entrenar(construir(_panel()), 26)
    return {"Fisico": m}


def test_registro_champion_challenger_y_rollback(reg):
    v1 = reg.guardar(_modelo_chico(), {"fin_entrenamiento": 26})
    assert reg.version_vigente() == v1                       # el primero se vuelve champion
    v2 = reg.guardar(_modelo_chico(), {"fin_entrenamiento": 26})
    assert reg.version_vigente() == v1 and v2 == "v002"      # el siguiente es challenger: no sustituye solo
    reg.promover(v2)
    assert reg.version_vigente() == v2
    assert reg.rollback() == v1 and reg.version_vigente() == v1
    assert "scikit-learn" in reg.meta(v1)["librerias"]       # trazabilidad: librerías, ventana, hiperparámetros, umbral
    assert reg.meta(v1)["canales"]["Fisico"]["semilla"] == C.SEMILLA


def test_registro_sin_modelo(reg):
    with pytest.raises(modelo.ModeloNoEntrenado):
        reg.cargar("Fisico")
    with pytest.raises(ValueError):
        reg.rollback()
