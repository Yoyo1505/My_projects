# -*- coding: utf-8 -*-
"""
rag/senales_sobregasto.py — Señales de sobregasto de UNA semana, en texto.

Compartido por la pestaña "Alertas de Sobregasto" (Dash) y por Cashi, para
que ambos digan exactamente lo mismo. No depende de ninguna conexión: quien
llama pasa `ejecutar(sql, params) -> DataFrame`, la tabla/vista fuente, la
columna de monto y el WHERE de sus filtros (sin la condición de semana).

Reglas (plantilla de Planeación Financiera):
- Sobregasto = Real 2026 − Plan 2026 exacto del alcance filtrado (neto). No
  se usa LIMIT en ningún total.
- Máximo 3 unidades en concentración, 1 patrón territorial, 1 factor
  contable, 1 acción. Los % de dimensiones distintas NO se suman: cada uno se
  expresa sobre el exceso de su propia dimensión, y el cruce se reporta como
  "se concentra en la intersección de …".
- Persistencia = semanas consecutivas (terminando en la semana analizada) con
  Real > Plan. Rareza = Z robusto (1.4826·MAD) de la desviación de la semana
  contra las semanas previas del año.
- Probabilidad de evento estructural:
    ALTA  = persistencia ≥ 4 semanas + exceso distribuido + desviación relevante
    MEDIA = persistencia de 2–3 semanas, o evidencia mixta
    BAJA  = 1 semana, pocos elementos (≤ 3) o sin exceso neto
    No determinada = sin Plan o sin historia suficiente
- No se declara causalidad.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

# Desviación "relevante" = exceso neto de al menos este % del Plan del alcance.
UMBRAL_RELEVANCIA_PCT = 1.0
# "Distribuido" = las 3 principales unidades explican menos de este % del
# exceso bruto Y hay al menos MIN_UNIDADES_DISTRIBUIDO unidades con exceso.
UMBRAL_CONCENTRACION_PCT = 50.0
MIN_UNIDADES_DISTRIBUIDO = 10
# Z robusto a partir del cual la semana se considera inusual.
UMBRAL_Z_RAREZA = 2.5
# Semanas previas mínimas para calcular rareza.
MIN_SEMANAS_HISTORIA = 6

ENTIDADES = {
    "ceco": ("ID_CENTRO_COSTOS", "CECO", "CECOs"),
    "pdv": ("ECO_PDV", "PDV", "PDVs"),
    "division": ("cat_Direccion_Division", "División", "Divisiones"),
    "cuenta": ("cat_Cuentas", "Cuenta", "Cuentas"),
    "grupo": ("cat_Grupo_de_Cuentas", "Grupo de Cuentas", "Grupos de Cuentas"),
}


def _mdp(v: float) -> str:
    return f"${v / 1e6:,.2f} MDP"


def _z_robusto(valor: float, historia: np.ndarray) -> Optional[float]:
    if len(historia) < MIN_SEMANAS_HISTORIA:
        return None
    med = float(np.median(historia))
    mad = float(np.median(np.abs(historia - med)))
    if mad == 0:
        return None
    return (valor - med) / (1.4826 * mad)


def _semanas_txt(n: int, ventana: int) -> str:
    """La racha por unidad solo se mide dentro de la ventana: si la llena, es "N+"."""
    if n >= ventana:
        return f"{ventana}+ semanas"
    return "1 semana" if n == 1 else f"{n} semanas"


def _etiqueta_default(x: Any) -> str:
    if isinstance(x, float) and x.is_integer():
        return str(int(x))
    return str(x)


def _racha(serie_desv: List[float]) -> int:
    """Semanas consecutivas con desviación > 0 contando hacia atrás desde la última."""
    n = 0
    for v in reversed(serie_desv):
        if v > 0:
            n += 1
        else:
            break
    return n


def calcular_senales(
    ejecutar: Callable[[str, list], pd.DataFrame],
    tabla: str,
    m_col: str,
    where_extra: str,
    params: list,
    semana: int,
    entidad: str = "ceco",
    ventana: int = 8,
    etiquetar: Optional[Callable[[Any], str]] = None,
    rama_map: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """`where_extra`: condiciones adicionales que empiezan con " AND " (o "").
    `params`: parámetros de los `?` de where_extra (se repiten por consulta)."""
    ent_col, ent_sing, ent_plur = ENTIDADES.get(entidad, ENTIDADES["ceco"])
    etiquetar = etiquetar or _etiqueta_default
    semana = int(semana)
    r26 = f"SUM(CASE WHEN Serie = 'R26' THEN {m_col} ELSE 0 END)"
    p26 = f"SUM(CASE WHEN Serie = 'P26' THEN {m_col} ELSE 0 END)"

    # 1. Serie semanal del alcance completo (semana 1..N) — magnitud, persistencia, rareza.
    df_serie = ejecutar(f"""
        SELECT sem, {r26} AS R, {p26} AS P
        FROM {tabla}
        WHERE sem BETWEEN 1 AND {semana} {where_extra}
        GROUP BY sem ORDER BY sem
    """, list(params))

    base = {"semana": semana, "entidad": ent_sing}
    if df_serie is None or df_serie.empty or semana not in set(df_serie["sem"].astype(int)):
        return {**base, "probabilidad": "No determinada", "texto": f"Sin registros de Real ni Plan en la semana {semana} para los filtros activos.",
                "neto": 0.0, "plan": 0.0, "pct": None}

    df_serie = df_serie.sort_values("sem")
    df_serie["D"] = df_serie["R"] - df_serie["P"]
    fila = df_serie[df_serie["sem"].astype(int) == semana].iloc[0]
    real, plan, neto = float(fila["R"]), float(fila["P"]), float(fila["D"])
    pct = (neto / abs(plan) * 100) if plan else None
    persistencia = _racha(df_serie["D"].tolist())
    historia = df_serie[df_serie["sem"].astype(int) < semana]["D"].to_numpy(dtype=float)
    z = _z_robusto(neto, historia)

    # 2. Unidades (entidad elegida) en la ventana — alcance, concentración, persistencia por unidad.
    s_ini = max(1, semana - ventana + 1)
    df_ent = ejecutar(f"""
        SELECT sem, {ent_col} AS Entidad, {r26} AS R, {p26} AS P
        FROM {tabla}
        WHERE sem BETWEEN {s_ini} AND {semana} {where_extra}
        GROUP BY 1, 2
    """, list(params))
    df_ent["D"] = df_ent["R"] - df_ent["P"]
    sem_n = df_ent[df_ent["sem"].astype(int) == semana]
    activos = sem_n[(sem_n["R"] != 0) | (sem_n["P"] != 0)]
    con_exceso = activos[activos["D"] > 0].sort_values("D", ascending=False)
    universo = int(len(activos))
    n_exceso = int(len(con_exceso))
    bruto = float(con_exceso["D"].sum())
    extension_pct = (n_exceso / universo * 100) if universo else 0.0

    piv = df_ent.pivot_table(index="Entidad", columns="sem", values="D", aggfunc="sum").reindex(
        columns=range(s_ini, semana + 1), fill_value=0.0).fillna(0.0)
    top = []
    for _, r in con_exceso.head(3).iterrows():
        racha = _racha(piv.loc[r["Entidad"]].tolist()) if r["Entidad"] in piv.index else 1
        top.append({
            "id": r["Entidad"],
            "nombre": etiquetar(r["Entidad"]),
            "monto": float(r["D"]),
            "pct_bruto": (float(r["D"]) / bruto * 100) if bruto else 0.0,
            "persistencia": racha,
        })
    conc_top3 = sum(t["pct_bruto"] for t in top)

    # 3. Territorio × Grupo de Cuentas en la semana — patrón territorial, factor contable, intersección.
    # Con `rama_map` (CECO -> rama padre más chica del árbol de estructura) el patrón
    # territorial es la rama más chica y el factor contable la Cuenta, no los nodos grandes
    # (Territorio / Grupo de Cuentas). Sin mapa se conserva el comportamiento anterior.
    if rama_map:
        df_tg = ejecutar(f"""
            SELECT CAST(ID_CENTRO_COSTOS AS VARCHAR) AS Ceco, cat_Cuentas AS Grupo, {r26} - {p26} AS D
            FROM {tabla}
            WHERE sem = {semana} {where_extra}
            GROUP BY 1, 2
        """, list(params))
        if df_tg is not None and not df_tg.empty:
            df_tg["Terr"] = df_tg["Ceco"].map(rama_map).fillna("Sin rama en la estructura")
            df_tg = df_tg.groupby(["Terr", "Grupo"], as_index=False)["D"].sum()
    else:
        df_tg = ejecutar(f"""
            SELECT cat_Subdireccion_Territorio AS Terr, cat_Grupo_de_Cuentas AS Grupo, {r26} - {p26} AS D
            FROM {tabla}
            WHERE sem = {semana} {where_extra}
            GROUP BY 1, 2
        """, list(params))
    nom_terr = "Rama" if rama_map else "Territorio"
    nom_gpo = "Cuenta" if rama_map else "Grupo de Cuentas"
    patron_terr = factor_cont = interseccion = None
    # Solo celdas Territorio × Grupo con Real > Plan: así territorio, grupo e
    # intersección se miden sobre la MISMA base (exceso de las celdas) y una
    # celda nunca queda por encima del total de su territorio (con el neto, un
    # territorio con +0.06 podía contener una celda de +0.71).
    celdas = df_tg[df_tg["D"] > 0] if df_tg is not None and not df_tg.empty else pd.DataFrame()
    if not celdas.empty:
        base_celdas = float(celdas["D"].sum())
        por_terr = celdas.groupby("Terr")["D"].sum().sort_values(ascending=False)
        patron_terr = (por_terr.index[0], float(por_terr.iloc[0]), float(por_terr.iloc[0] / base_celdas * 100))
        por_gpo = celdas.groupby("Grupo")["D"].sum().sort_values(ascending=False)
        factor_cont = (por_gpo.index[0], float(por_gpo.iloc[0]), float(por_gpo.iloc[0] / base_celdas * 100))
        celda = celdas.sort_values("D", ascending=False).iloc[0]
        interseccion = (celda["Terr"], celda["Grupo"], float(celda["D"]), float(celda["D"] / base_celdas * 100))

    # 4. Probabilidad de evento estructural (reglas de la plantilla).
    relevante = pct is not None and pct >= UMBRAL_RELEVANCIA_PCT
    distribuido = conc_top3 < UMBRAL_CONCENTRACION_PCT and n_exceso >= MIN_UNIDADES_DISTRIBUIDO
    # Unidad principal que ya trae ≥ 4 semanas seguidas con exceso y pesa ≥ 10%
    # del exceso bruto: si el alcance total apenas entra en exceso, la
    # evidencia es mixta (no "puntual").
    persistentes = [t for t in top if t["persistencia"] >= 4 and t["pct_bruto"] >= 10]
    if not plan or len(df_serie) < 2:
        prob, razon = "No determinada", "no hay Plan o historia suficiente para evaluarla"
    elif neto <= 0:
        prob, razon = "Baja", "el alcance filtrado no tiene exceso neto; el exceso es de unidades puntuales"
    elif persistencia <= 1 and persistentes:
        p = persistentes[0]
        prob, razon = "Media", (f"evidencia mixta: el alcance total apenas entra en exceso esta semana, pero {ent_sing} "
                                f"{p['nombre']} ({p['pct_bruto']:.0f}% del exceso bruto) lleva {_semanas_txt(p['persistencia'], ventana)} seguidas")
    elif persistencia <= 1 or n_exceso <= 3:
        prob, razon = "Baja", ("primera semana con exceso" if persistencia <= 1 else f"solo {n_exceso} {ent_plur.lower()} con exceso")
    elif persistencia >= 4 and distribuido and relevante:
        prob, razon = "Alta", f"{persistencia} semanas consecutivas con exceso, distribuido en {n_exceso} {ent_plur.lower()} y ≥ {UMBRAL_RELEVANCIA_PCT:.0f}% del Plan"
    else:
        faltan = []
        if persistencia < 4:
            faltan.append(f"persistencia de {persistencia} semanas")
        if not distribuido:
            faltan.append(f"exceso concentrado ({conc_top3:.0f}% en 3 {ent_plur.lower()})")
        if not relevante:
            faltan.append(f"desviación menor a {UMBRAL_RELEVANCIA_PCT:.0f}% del Plan")
        prob, razon = "Media", "evidencia mixta: " + ", ".join(faltan)

    # 5. Acción (una sola).
    foco = top[0]["nombre"] if top else None
    if interseccion:
        foco_txt = f"{interseccion[1]} en {interseccion[0]}"
    elif foco:
        foco_txt = f"{ent_sing} {foco}"
    else:
        foco_txt = "el alcance filtrado"
    if prob == "Alta":
        accion = f"Solicitar a los responsables de {foco_txt} la explicación y un plan de corrección antes del siguiente cierre semanal."
    elif prob == "Media":
        accion = f"Validar con el responsable de {foco_txt} si el exceso es operativo o contable (reclasificación, provisión) y revisar de nuevo la próxima semana."
    elif prob == "Baja":
        accion = f"Revisar puntualmente {foco_txt}; si no se repite la próxima semana, no requiere escalamiento."
    else:
        accion = "Completar la información de Plan/historia antes de concluir."

    # 6. Texto (formato de salida de la plantilla).
    lineas = []
    if neto > 0:
        lineas.append(f"Se detectó exceso de {_mdp(neto)} vs Plan ({pct:+.1f}%) en la semana {semana}." if pct is not None
                      else f"Se detectó exceso de {_mdp(neto)} en la semana {semana} (sin Plan registrado).")
    else:
        lineas.append(f"Sin exceso neto en la semana {semana}: Real − Plan = {_mdp(neto)}" + (f" ({pct:+.1f}%)." if pct is not None else "."))
    lineas.append("")
    lineas.append("Alcance:")
    lineas.append(f"• {n_exceso:,} de {universo:,} {ent_plur} con movimiento en la semana tienen exceso ({extension_pct:.1f}%); exceso bruto de esas unidades: {_mdp(bruto)}.")
    if top:
        lineas.append(f"• Las {len(top)} principales explican {conc_top3:.1f}% del exceso bruto:")
        for t in top:
            lineas.append(f"   – {ent_sing} {t['nombre']}: {_mdp(t['monto'])} ({t['pct_bruto']:.1f}%), {_semanas_txt(t['persistencia'], ventana)} seguidas con exceso")
    if patron_terr:
        lineas.append(f"• Base {nom_terr.lower()} × {nom_gpo.lower()} (solo combinaciones con Real > Plan):")
        lineas.append(f"   – Patrón {'de rama' if rama_map else 'territorial'}: {patron_terr[0]} ({_mdp(patron_terr[1])}, {patron_terr[2]:.1f}%).")
    if factor_cont:
        lineas.append(f"   – Factor contable: {factor_cont[0]} ({_mdp(factor_cont[1])}, {factor_cont[2]:.1f}%).")
    if interseccion:
        lineas.append(f"   – Se concentra en la intersección de {interseccion[0]} y {interseccion[1]} ({_mdp(interseccion[2])}, {interseccion[3]:.1f}%).")
    lineas.append("")
    diag = [f"Real {_mdp(real)} vs Plan {_mdp(plan)}"]
    diag.append(f"{persistencia} semana(s) consecutivas con Real > Plan en el alcance" if persistencia else "sin exceso neto esta semana")
    if z is None:
        diag.append("rareza no determinada (historia insuficiente o sin variación)")
    else:
        diag.append(f"Z robusto {z:+.1f} ({'inusual' if abs(z) >= UMBRAL_Z_RAREZA else 'dentro de lo habitual'} vs semanas previas)")
    lineas.append("Diagnóstico: " + "; ".join(diag) + ". Los datos muestran dónde está el exceso, no su causa.")
    lineas.append("")
    lineas.append(f"Probabilidad de evento estructural: {prob.upper() if prob != 'No determinada' else prob} — {razon}.")
    lineas.append("")
    lineas.append(f"Acción recomendada: {accion}")

    return {
        **base,
        "real": real, "plan": plan, "neto": neto, "pct": pct,
        "exceso_bruto": bruto, "unidades_exceso": n_exceso, "universo": universo, "extension_pct": extension_pct,
        "top": top, "concentracion_top3_pct": conc_top3,
        "patron_territorial": patron_terr, "factor_contable": factor_cont, "interseccion": interseccion,
        "persistencia": persistencia, "z_robusto": z,
        "probabilidad": prob, "razon": razon, "accion": accion,
        "texto": "\n".join(lineas),
    }
