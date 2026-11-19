# -*- coding: utf-8 -*-
"""Registro de versiones del modelo: guardar, champion/challenger, promover y rollback, con trazabilidad.

aggs/monitoreo/modelos/vNNN/{modelo_<canal>.joblib, meta.json}  y  aggs/monitoreo/champion.json
Un modelo nuevo es siempre "challenger": solo pasa a champion con `promover` (aprobación humana explícita)
o si todavía no hay champion.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import platform
from typing import List, Optional

from .datos import SALIDA
from .modelo import ModeloNoEntrenado

DIR_MODELOS = SALIDA / "modelos"
CHAMPION = SALIDA / "champion.json"


def hash_datos(*paneles) -> str:
    """Huella de los datos de entrenamiento (todos los paneles) y de la configuración."""
    from . import config as C
    h = hashlib.sha256()
    for p in paneles:
        h.update(p.sort(["ceco", "sem"]).to_pandas().to_csv(index=False).encode())
    h.update(json.dumps({k: v for k, v in vars(C).items() if k.isupper()}, sort_keys=True, default=str).encode())
    return h.hexdigest()[:16]


def _leer_champion() -> dict:
    if CHAMPION.exists():
        return json.loads(CHAMPION.read_text(encoding="utf-8"))
    return {"version": None, "historial": []}


def versiones() -> List[str]:
    return sorted(p.name for p in DIR_MODELOS.glob("v*") if p.is_dir()) if DIR_MODELOS.exists() else []


def siguiente_version() -> str:
    v = versiones()
    return f"v{int(v[-1][1:]) + 1:03d}" if v else "v001"


def guardar(modelos: dict, meta_global: dict) -> str:
    """`modelos`: {canal: {"obj": ..., "meta": ...}}. Crea la versión (challenger) y devuelve su nombre."""
    import joblib
    import sklearn
    v = siguiente_version()
    carpeta = DIR_MODELOS / v
    carpeta.mkdir(parents=True, exist_ok=True)
    for canal, m in modelos.items():
        joblib.dump(m["obj"], carpeta / f"modelo_{canal}.joblib", compress=3)
    meta = {**meta_global, "version": v, "fecha": dt.datetime.now().isoformat(timespec="seconds"),
            "librerias": {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "joblib": joblib.__version__},
            "canales": {c: m["meta"] for c, m in modelos.items()}}
    (carpeta / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    if _leer_champion()["version"] is None:
        promover(v, "primer modelo (sin champion previo)")
    return v


def promover(version: str, motivo: str = "aprobación manual") -> None:
    if version not in versiones():
        raise ValueError(f"La versión {version} no existe. Disponibles: {versiones()}")
    ch = _leer_champion()
    ch["historial"].append({"version": ch["version"], "reemplazada": dt.datetime.now().isoformat(timespec="seconds"), "motivo": motivo})
    ch["version"] = version
    SALIDA.mkdir(parents=True, exist_ok=True)
    CHAMPION.write_text(json.dumps(ch, indent=2, ensure_ascii=False), encoding="utf-8")


def rollback() -> str:
    """Regresa al champion anterior (el último distinto del vigente que siga existiendo)."""
    ch = _leer_champion()
    for h in reversed(ch["historial"]):
        if h["version"] and h["version"] != ch["version"] and h["version"] in versiones():
            promover(h["version"], f"rollback desde {ch['version']}")
            return h["version"]
    raise ValueError("No hay una versión anterior a la cual regresar.")


def version_vigente() -> Optional[str]:
    return _leer_champion()["version"]


def meta(version: Optional[str] = None) -> dict:
    v = version or version_vigente()
    if not v:
        raise ModeloNoEntrenado("No hay modelo entrenado: corre `python -m rag.monitoreo train` primero.")
    return json.loads((DIR_MODELOS / v / "meta.json").read_text(encoding="utf-8"))


def cargar(canal: str, version: Optional[str] = None) -> dict:
    import joblib
    v = version or version_vigente()
    if not v:
        raise ModeloNoEntrenado("No hay modelo entrenado: corre `python -m rag.monitoreo train` primero.")
    ruta = DIR_MODELOS / v / f"modelo_{canal}.joblib"
    if not ruta.exists():
        raise ModeloNoEntrenado(f"La versión {v} no tiene modelo para el canal {canal}.")
    return joblib.load(ruta)
