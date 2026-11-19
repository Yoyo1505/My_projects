# -*- coding: utf-8 -*-
"""Comandos del modelo no supervisado (corren con el Python que tiene scikit-learn; el tablero solo lee la salida).

  python -m rag.monitoreo train [--fin N] [--promover]   entrena un challenger (+ backtesting) y lo registra
  python -m rag.monitoreo score                          puntúa con el champion → aggs/monitoreo/scores.parquet y estado.json
  python -m rag.monitoreo estado                         versión vigente, drift y si conviene reentrenar
  python -m rag.monitoreo promover vNNN                  champion = vNNN (aprobación humana)
  python -m rag.monitoreo rollback                       regresa al champion anterior

`train` NUNCA corre solo ni al llegar datos: es un paso explícito. `score` solo calcula features nuevas y puntúa.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys

import polars as pl

from . import config as C
from . import datos, registro
from .features import construir, elegibles
from .modelo import ModeloNoEntrenado, backtest, causas, entrenar, psi, puntuar, _matriz

CANALES = ["Fisico", "Digital"]


def _preparar(con, canal, hasta):
    panel = datos.leer_panel(con, canal, hasta)
    return panel, construir(panel)


def cmd_train(a) -> int:
    smr = datos.sem_max_real()
    fin = a.fin or smr
    con = datos.conectar()
    modelos, paneles, bt = {}, [], {}
    for canal in CANALES:
        panel, feat = _preparar(con, canal, fin)
        if panel.is_empty():
            print(f"[{canal}] sin datos: se omite")
            continue
        paneles.append(panel)
        print(f"[{canal}] panel {panel.height:,} filas · entrenando hasta la semana {fin} ...")
        modelos[canal] = entrenar(feat, fin)
        bt[canal] = backtest(feat, fin)
        modelos[canal]["meta"]["backtesting_walk_forward"] = bt[canal]
        for f in bt[canal]:
            print(f"   backtest sem {f['sem']}: {f['alertas']} alertas ({f['tasa_alertas'] * 100:.2f}%) · Jaccard vs estadístico "
                  f"{f['jaccard_vs_estadistico'] if f['jaccard_vs_estadistico'] is None else round(f['jaccard_vs_estadistico'], 2)} · "
                  f"Spearman vs modelo previo {f['spearman_vs_modelo_previo'] if f['spearman_vs_modelo_previo'] is None else round(f['spearman_vs_modelo_previo'], 3)}")
    if not modelos:
        print("No hay datos para entrenar.")
        return 1
    v = registro.guardar(modelos, {"sem_max_real": smr, "fin_entrenamiento": fin, "hash_datos_config": registro.hash_datos(*paneles)})
    if a.promover:
        registro.promover(v, "aprobación manual (--promover)")
    print(f"Versión {v} guardada. Champion vigente: {registro.version_vigente()}"
          + ("" if registro.version_vigente() == v else f"  (es challenger; para usarla: python -m rag.monitoreo promover {v})"))
    return 0


def cmd_score(a) -> int:
    smr = datos.sem_max_real()
    try:
        v = registro.version_vigente()
        m = registro.meta(v)
    except ModeloNoEntrenado as e:
        print(e)
        return 1
    con = datos.conectar()
    filas, estado = [], {"version": v, "fecha_scoring": dt.datetime.now().isoformat(timespec="seconds"),
                         "sem_max_real": smr, "entrenado_hasta": m["fin_entrenamiento"], "canales": {}}
    for canal in CANALES:
        try:
            obj = registro.cargar(canal, v)
        except ModeloNoEntrenado:
            continue
        panel, feat = _preparar(con, canal, smr)
        el = elegibles(feat, C.HISTORIA_MIN)
        p = puntuar(obj, el)
        al = p.filter(pl.col("alerta"))
        txt = causas(obj, al)
        al = al.with_columns(pl.Series("causas", txt, dtype=pl.String)) if txt else al.with_columns(pl.lit("").alias("causas"))
        guard = pl.concat([al.select(["ceco", "sem", "real", "score", "score_if", "score_pca", "concordancia", "alerta", "causas"]),
                           p.filter(~pl.col("alerta") & (pl.col("score") >= 0.95))
                           .select(["ceco", "sem", "real", "score", "score_if", "score_pca", "concordancia", "alerta"])
                           .with_columns(pl.lit("").alias("causas"))])
        filas.append(guard.with_columns(pl.lit(canal).alias("canal"), pl.lit(v).alias("version")))
        # Drift (PSI de las features de las últimas 4 semanas contra el entrenamiento) y tasa de alertas.
        rec = p.filter(pl.col("sem") > smr - 4)
        psis = psi(obj["psi_ref"], _matriz(rec)) if rec.height else {}
        pmax = max(psis.values()) if psis else 0.0
        drift = "ALERTA" if pmax >= C.PSI_ALERTA else ("VIGILAR" if pmax >= C.PSI_VIGILAR else "OK")
        tasa = float(rec["alerta"].mean()) if rec.height else 0.0
        esperada = 1.0 - C.CUANTIL_ALERTA
        por_sem = {int(s): int(n) for s, n in p.group_by("sem").agg(pl.col("alerta").sum()).sort("sem").iter_rows()}
        motivos = []
        if drift == "ALERTA":
            motivos.append(f"drift de features (PSI máx {pmax:.2f})")
        if tasa > 3 * esperada:
            motivos.append(f"las alertas de las últimas 4 semanas ({tasa * 100:.2f}%) triplican lo esperado ({esperada * 100:.2f}%)")
        if smr - m["fin_entrenamiento"] >= 8:
            motivos.append(f"hay {smr - m['fin_entrenamiento']} semanas completas nuevas desde el entrenamiento")
        estado["canales"][canal] = {
            "filas_puntuadas": int(p.height), "alertas_total": int(al.height), "alertas_ult4": int(rec["alerta"].sum()) if rec.height else 0,
            "tasa_alertas_ult4": tasa, "tasa_esperada": esperada, "psi_max": pmax,
            "psi_top3": dict(sorted(psis.items(), key=lambda kv: -kv[1])[:3]), "drift": drift,
            "alertas_por_semana": por_sem, "sugerir_reentrenar": bool(motivos), "motivos": motivos}
        print(f"[{canal}] {p.height:,} filas puntuadas · {al.height} alertas · drift {drift} (PSI máx {pmax:.2f}) · últimas 4 sem: {tasa * 100:.2f}% alertas")
    if not filas:
        print("No se generó ningún score.")
        return 1
    datos.SALIDA.mkdir(parents=True, exist_ok=True)
    pl.concat(filas, how="diagonal").write_parquet(datos.SALIDA / "scores.parquet", compression="zstd")
    (datos.SALIDA / "estado.json").write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Escrito: {datos.SALIDA / 'scores.parquet'} y estado.json")
    return 0


def cmd_estado(_a) -> int:
    ruta = datos.SALIDA / "estado.json"
    print(f"Versiones: {registro.versiones()} · champion: {registro.version_vigente()}")
    if ruta.exists():
        print(ruta.read_text(encoding="utf-8"))
    else:
        print("Aún no hay estado: corre `score`.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m rag.monitoreo", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    t = sp.add_parser("train")
    t.add_argument("--fin", type=int, help="última semana de entrenamiento (por defecto sem_max_real)")
    t.add_argument("--promover", action="store_true", help="el challenger pasa a champion (aprobación humana)")
    sp.add_parser("score")
    sp.add_parser("estado")
    p = sp.add_parser("promover")
    p.add_argument("version")
    sp.add_parser("rollback")
    a = ap.parse_args(argv)
    if a.cmd == "train":
        return cmd_train(a)
    if a.cmd == "score":
        return cmd_score(a)
    if a.cmd == "estado":
        return cmd_estado(a)
    if a.cmd == "promover":
        registro.promover(a.version)
        print(f"Champion: {registro.version_vigente()}")
        return 0
    if a.cmd == "rollback":
        print(f"Champion: {registro.rollback()}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
