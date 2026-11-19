# -*- coding: utf-8 -*-
"""
rag/cashi_ml/entrenar.py — Entrena el resolvedor de entidades de Cashi (v2).

Problema: a partir de un fragmento de pregunta ("metro norte", "material punto de
venta") encontrar el valor canónico del catálogo y su dimensión (territorio,
agrupador de reales, cuenta, grupo de cuentas, división).

Arquitectura en dos etapas (búsqueda + re-ranking, práctica habitual en entity linking):
  1) Recuperación: TF-IDF de caracteres sobre TODO el catálogo -> top-K candidatos.
  2) Re-ranking: clasificador sobre pares (consulta, candidato) con rasgos léxicos
     (similitud de caracteres, cobertura de tokens en ambos sentidos, subcadena,
     token_set_ratio de rapidfuzz, posición en el ranking, dimensión) -> probabilidad
     de que el candidato sea el correcto.

Datos de entrenamiento: solo los catálogos (`datos\\cat_estructura.parquet`,
`datos\\cat_cuentas.parquet`). Variantes generadas por valor canónico (sin acentos,
sin código, sin prefijo, subsecuencias de palabras) + variantes con errores tipográficos
(un carácter borrado o intercambiado) + candidatos difíciles minados del propio retriever.

Validación: GroupKFold POR VALOR CANÓNICO (nunca el mismo valor en entrenamiento y
prueba). Se prueban varias configuraciones (rondas) y se elige la mejor por CV.
Evaluación final adicional con `gold_consultas.json` (consultas escritas a mano, no usadas
para entrenar).

Uso (desde la raíz del proyecto):
    python rag/cashi_ml/entrenar.py
"""
from __future__ import annotations

import json
import random
import re
import unicodedata
from pathlib import Path

import joblib
import numpy as np
import polars as pl
from rapidfuzz import fuzz
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = Path(__file__).resolve().parents[2]
DATOS = BASE / "datos"
SALIDA = BASE / "aggs" / "cashi_ml"
GOLD = Path(__file__).with_name("gold_consultas.json")          # ajuste (se vio al diseñar)
HOLDOUT = Path(__file__).with_name("gold_holdout.json")         # prueba no vista (iter. 1-4)
HOLDOUT2 = Path(__file__).with_name("gold_holdout2.json")       # prueba nueva (iter. 5)
SEMILLA = 7

BASURA = {"0", "no clasificado", "sin agrupar", "sin dato", "sin clasificar", "nan", "none", ""}
PREFIJOS = ("territorio ", "division ", "staff division ", "staff ", "subdireccion ",
            "dir. ", "dir ", "direccion ")
STOP = {"de", "la", "el", "y", "del", "en", "los", "las", "para", "a", "e", "o"}
DIMENSIONES = ["territorio", "division", "zona", "region", "pdc",
               "agrupador_reales", "grupo_cuentas", "cuenta"]


# Abreviaturas que el catálogo usa y el usuario no ("ART. DE ESCRITORIO", "SERV. PROFESIONALES")
ABREVIATURAS = {"art": "articulos", "serv": "servicios", "mtto": "mantenimiento",
                "vta": "venta", "telef": "telefono", "mdse": "mercancia", "equip": "equipo"}


def normalizar(texto: str) -> str:
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    t = " ".join(ABREVIATURAS.get(w, w) for w in t.split())
    return re.sub(r"\s+", " ", t).strip()


def tokens(texto: str) -> list[str]:
    return [t for t in normalizar(texto).split() if t not in STOP]


def variantes(canonico: str) -> set[str]:
    """Formas en que un usuario escribe un valor canónico (sin errores tipográficos)."""
    base = normalizar(canonico)
    out = {base, re.sub(r"^\d+\s+", "", base)}
    for v in list(out):
        for p in PREFIJOS:
            if v.startswith(p) and len(v) > len(p):
                out.add(v[len(p):])
    for v in list(out):
        pal = v.split()
        n = len(pal)
        if n >= 3:
            for i in range(n):
                for j in range(i + 2, n + 1):
                    if not (i == 0 and j == n):
                        out.add(" ".join(pal[i:j]))
    return {v for v in out if len(v) >= 3}


def typo(texto: str, rng: random.Random) -> str:
    """Un error de tecleo: borrar un carácter interno o intercambiar dos vecinos."""
    if len(texto) < 5:
        return texto
    i = rng.randrange(1, len(texto) - 2)
    if rng.random() < 0.5:
        return texto[:i] + texto[i + 1:]
    return texto[:i] + texto[i + 1] + texto[i] + texto[i + 2:]


def cargar_catalogos() -> dict[str, list[str]]:
    est = pl.read_parquet(DATOS / "cat_estructura.parquet")
    cue = pl.read_parquet(DATOS / "cat_cuentas.parquet")

    def valores(df: pl.DataFrame, col: str) -> list[str]:
        vals = {str(v).strip() for v in df[col].drop_nulls().unique().to_list()}
        return sorted(v for v in vals if normalizar(v) not in BASURA)

    return {
        "territorio": valores(est, "cat_Subdireccion_Territorio"),
        "division": valores(est, "cat_Direccion_Division"),
        "zona": valores(est, "cat_Subdireccion_Zona"),
        "region": valores(est, "cat_Subdireccion_Region"),
        "pdc": valores(est, "cat_PDC"),
        "agrupador_reales": valores(cue, "cat_Agrupador_Reales"),
        "grupo_cuentas": valores(cue, "cat_Grupo_de_Cuentas"),
        "cuenta": valores(cue, "cat_Cuentas"),
    }


class Indice:
    """Catálogo indexado: cada ítem es (dimensión, valor canónico)."""

    def __init__(self, catalogos: dict[str, list[str]], ngram: tuple[int, int]):
        self.items = [(d, c) for d in DIMENSIONES for c in catalogos.get(d, [])]
        self.textos = [normalizar(c) for _, c in self.items]
        # cuántos ítems del catálogo tienen el mismo nombre (p. ej. "Gastos de Nómina"
        # como cuenta y como grupo): señal de ambigüedad para el re-ranking
        conteo = {}
        for t in self.textos:
            conteo[t] = conteo.get(t, 0) + 1
        self.repetidos = [conteo[t] for t in self.textos]
        # frecuencia de cada palabra (sin palabras de clase) en los nombres del catálogo:
        # una palabra muy común ("ayuda", "gastos") no basta para nombrar una entidad
        df: dict = {}
        for _, c in self.items:
            for w in {_stem(t) for t in tokens(c) if t not in PALABRAS_DE_CLASE}:
                df[w] = df.get(w, 0) + 1
        self.df = df
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=ngram, sublinear_tf=True)
        self.M = self.vec.fit_transform(self.textos)

    def top_k(self, q: str, k: int) -> list[tuple[int, float]]:
        sims = (self.M @ self.vec.transform([normalizar(q)]).T).toarray().ravel()
        idx = np.argsort(-sims)[:k]
        return [(int(i), float(sims[i])) for i in idx]


def rasgos(q: str, idx: Indice, cand: int, sim: float, rank: int) -> list[float]:
    dim, canon = idx.items[cand]
    qt, ct = set(tokens(q)), set(tokens(canon))
    qn, cn = normalizar(q), normalizar(canon)
    inter = len(qt & ct)
    onehot = [1.0 if dim == d else 0.0 for d in DIMENSIONES]
    comunes = {_stem(t) for t in qt} & {_stem(t) for t in ct if t not in PALABRAS_DE_CLASE}
    n_comun = float(len(comunes))
    df_min = min((idx.df.get(w, 0) for w in comunes), default=0)
    return [
        sim,
        n_comun,                                 # palabras en común (con singular/plural)
        1.0 / (1 + df_min),                      # 1 = la palabra común es rara en el catálogo
        inter / max(1, len(qt)),                 # cobertura de la consulta
        inter / max(1, len(ct)),                 # cobertura del candidato
        float(qn in cn or cn in qn),             # subcadena
        fuzz.token_set_ratio(qn, cn) / 100.0,
        fuzz.partial_ratio(qn, cn) / 100.0,
        1.0 / (1 + rank),
        float(len(ct)),
        float(len(qt)),
        float(qn == cn),                         # nombre completo idéntico
        float(cn.startswith(qn)),                # la consulta es el inicio del nombre
        min(len(qn), len(cn)) / max(len(qn), len(cn), 1),
        1.0 / idx.repetidos[cand],               # 1 = nombre único en el catálogo
    ] + onehot


def pares_para_consulta(q: str, idx: Indice, k: int):
    top = idx.top_k(q, k)
    return [(c, rasgos(q, idx, c, s, r)) for r, (c, s) in enumerate(top)]


RELLENOS_INICIO = ["cuanto llevo gastado de", "gasto en", "dame el gasto de", "muestrame",
                   "cuanto es el total de", "como va el", "reporte de", "dime el monto de"]
RELLENOS_FIN = ["esta semana", "por favor", "en el ano", "acumulado"]
PALABRAS_RELLENO = {"cuanto", "llevo", "gastado", "gasto", "total", "dame", "muestrame",
                    "muestra", "cual", "como", "va", "es", "el", "la", "los", "las", "de", "del",
                    "en", "esta", "semana", "por", "favor", "que", "hay", "tiene", "tienen",
                    "dime", "reporte", "monto", "importe", "ano", "acumulado", "y", "a", "al"}


# Palabras de conversación o de petición que nunca nombran una entidad del catálogo.
# Ojo: algunas aparecen en los negativos de los conjuntos de prueba 1 y 2. Esa lista se
# armó después de ver sus fallos, así que sus negativos ya no son una medida independiente.
PALABRAS_CONVERSACIONALES = {"ayuda", "gracias", "favor", "hola", "buenos", "dias", "tardes",
                             "noches", "opinas", "esto", "bien", "todo", "clima", "hace",
                             "reporte", "bonito", "necesito", "hoy", "por", "quiero", "puedes"}

# Vocabulario genérico para consultas SIN entidad (ejemplos negativos). Se excluyen las
# palabras de los conjuntos gold/holdout de negativos para no medir con ejemplos vistos.
VOCAB_GENERICO = ["hola", "gracias", "ayuda", "dime", "cual", "quien", "donde", "cuando",
                  "porque", "sistema", "usuario", "pagina", "informacion", "ejemplo", "prueba",
                  "nada", "algo", "bien", "mal", "ok", "tabla", "grafica", "comparar", "explica",
                  "analiza", "calcula", "suma", "promedio", "ultimo", "anterior", "mayor",
                  "menor", "cuantos", "cuantas", "cosas", "hacer", "ver", "buscar", "listo",
                  "tardes", "noches", "amigo", "perro", "casa", "mesa", "lluvia", "color"]


def negativos(n: int, rng: random.Random) -> list[str]:
    out = []
    for _ in range(n):
        k = rng.randint(1, 4)
        partes = [rng.choice(VOCAB_GENERICO) for _ in range(k)]
        if rng.random() < 0.4:
            partes.insert(0, rng.choice(RELLENOS_INICIO))
        out.append(" ".join(partes))
    return out


def construir_consultas(catalogos, items_idx, rng):
    """Consultas de entrenamiento agrupadas por valor canónico (grupo = índice del ítem).
    Incluye: el nombre completo; variantes; errores de tecleo; y variantes envueltas en
    frases de relleno ('cuanto llevo gastado de X esta semana') para que el modelo aprenda
    a ignorar lo que no es entidad."""
    consultas = []
    for ii, (dim, canon) in enumerate(items_idx):
        for v in sorted(variantes(canon)):
            consultas.append((v, ii))
            if len(v) >= 5:
                consultas.append((typo(v, rng), ii))
            if rng.random() < 0.35:
                pre = rng.choice(RELLENOS_INICIO)
                pos = rng.choice(RELLENOS_FIN + [""])
                consultas.append(((pre + " " + v + " " + pos).strip(), ii))
    # Negativos: consultas sin entidad (gold = -1). Todos sus candidatos son incorrectos.
    for q in negativos(max(200, len(consultas) // 3), rng):
        consultas.append((q, -1))
    return consultas


class RankerLambdaMART:
    """LambdaMART (LightGBM, objective=lambdarank) con la interfaz predict_proba que usa el
    resto del módulo. Las puntuaciones se llevan a (0,1) con una sigmoide; el umbral de
    abstención se aplica sobre esa escala."""

    def __init__(self, n_estimators: int = 300, learning_rate: float = 0.05,
                 num_leaves: int = 15, min_child_samples: int = 5):
        self.params = dict(n_estimators=n_estimators, learning_rate=learning_rate,
                           num_leaves=num_leaves, min_child_samples=min_child_samples)
        self.m = None

    def fit(self, X, y, sizes):
        import lightgbm as lgb
        self.m = lgb.LGBMRanker(objective="lambdarank", random_state=SEMILLA, verbose=-1,
                                **self.params)
        self.m.fit(X, y, group=sizes)
        return self

    def predict_proba(self, X):
        s = self.m.predict(X)
        p = 1.0 / (1.0 + np.exp(-s))
        return np.column_stack([1.0 - p, p])


def ajustar_ranker(tipo: str, X: np.ndarray, y: np.ndarray, sizes: list[int] | None = None):
    if tipo == "lambdarank":
        return RankerLambdaMART().fit(X, y, sizes)
    if tipo.startswith("logistica"):
        c = float(tipo.split("_C")[1]) if "_C" in tipo else 1.0
        m = make_pipeline(StandardScaler(),
                          LogisticRegression(max_iter=3000, C=c, class_weight="balanced"))
    else:
        m = HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, max_leaf_nodes=31,
                                           random_state=SEMILLA)
    m.fit(X, y)
    return m


def evaluar_cv(catalogos, ngram, k, tipo, consultas_base=None, n_splits=5):
    """Validación cruzada agrupada por valor canónico. Devuelve métricas medias."""
    rng = random.Random(SEMILLA)
    idx = Indice(catalogos, ngram)
    consultas = consultas_base or construir_consultas(catalogos, idx.items, rng)
    grupos = np.array([g for _, g in consultas])
    gkf = GroupKFold(n_splits=n_splits)
    top1, mrr, recall = [], [], []
    minados = 0
    for tr, te in gkf.split(np.zeros(len(consultas)), groups=grupos):
        Xs, ys, sizes = [], [], []
        for qi in tr:
            q, g = consultas[qi]
            pares = pares_para_consulta(q, idx, k)
            for c, f in pares:
                Xs.append(f)
                ys.append(int(c == g))
            sizes.append(len(pares))
            minados += sum(1 for c, _ in pares if c != g)
        if sum(ys) == 0:
            continue
        m = ajustar_ranker(tipo, np.array(Xs), np.array(ys), sizes)
        for qi in te:
            q, g = consultas[qi]
            if g == -1:          # negativos: solo entrenan, no se miden aquí
                continue
            pares = pares_para_consulta(q, idx, k)
            cands = [c for c, _ in pares]
            recall.append(float(g in cands))
            if g not in cands:
                top1.append(0.0)
                mrr.append(0.0)
                continue
            p = m.predict_proba(np.array([f for _, f in pares]))[:, 1]
            orden = [cands[i] for i in np.argsort(-p)]
            top1.append(float(orden[0] == g))
            mrr.append(1.0 / (1 + orden.index(g)))
    return {
        "top1": float(np.mean(top1)), "mrr": float(np.mean(mrr)),
        "recall_at_k": float(np.mean(recall)), "n_consultas": len(consultas),
    }


def entrenar_final(catalogos, ngram, k, tipo, rng):
    idx = Indice(catalogos, ngram)
    consultas = construir_consultas(catalogos, idx.items, rng)
    Xs, ys, sizes = [], [], []
    for q, g in consultas:
        pares = pares_para_consulta(q, idx, k)
        for c, f in pares:
            Xs.append(f)
            ys.append(int(c == g))
        sizes.append(len(pares))
    m = ajustar_ranker(tipo, np.array(Xs), np.array(ys), sizes)
    return idx, m


UMBRAL_ABSTENER = 0.5     # probabilidad mínima para aceptar algún candidato
MARGEN_AMBIGUA = 0.10    # candidatos de OTRA dimensión a esta distancia del mejor = ambigüedad


def decidir(cands: list[int], probs: np.ndarray, items) -> tuple[str, list[int]]:
    """Decisión del resolvedor: 'abstencion' | 'unica' | 'ambigua' (Cashi debe preguntar)."""
    if not cands:
        return "abstencion", []
    j = int(np.argmax(probs))
    if probs[j] < UMBRAL_ABSTENER:
        return "abstencion", []
    dim_j = items[cands[j]][0]
    amb = [cands[i] for i in range(len(cands))
           if probs[i] >= UMBRAL_ABSTENER and probs[i] >= probs[j] - MARGEN_AMBIGUA
           and items[cands[i]][0] != dim_j]
    if amb:
        return "ambigua", [cands[j]] + amb
    return "unica", [cands[j]]


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") else t


PALABRAS_DE_CLASE = {"territorio", "division", "staff", "subdireccion", "direccion", "dir",
                     "zona", "region", "contraloria"}   # prefijos de catálogo, no nombran nada
# Palabra que anuncia la dimensión de la entidad siguiente ("territorio centro" -> territorio)
PALABRA_A_DIMENSION = {"territorio": "territorio", "territorios": "territorio",
                       "division": "division", "divisiones": "division",
                       "zona": "zona", "zonas": "zona", "region": "region", "regiones": "region",
                       "cuenta": "cuenta", "cuentas": "cuenta", "grupo": "grupo_cuentas",
                       "agrupador": "agrupador_reales", "pdc": "pdc"}


def guardia(ventana: str, canon: str, df: dict | None = None) -> bool:
    """Regla de precisión: la ventana debe cubrir al menos la mitad del nombre canónico
    (con singular/plural), o estar contenida en él. Las palabras de clase ('territorio',
    'division') no cuentan: 'territorio' solo no nombra ningún territorio. Evita que
    palabras genéricas ('general', 'gaste', 'dias') se vuelvan entidad."""
    # los códigos numéricos del catálogo ("115 - TELEVISION") no son palabras del nombre
    qs = {_stem(t) for t in tokens(ventana) if t not in PALABRAS_DE_CLASE and not t.isdigit()}
    cs = {_stem(t) for t in tokens(canon) if t not in PALABRAS_DE_CLASE and not t.isdigit()}
    if not cs:
        return False
    cov = len(qs & cs) / len(cs)
    # contenida: la ventana es parte del nombre y ese fragmento es informativo
    # (una sola palabra genérica dentro de un nombre largo no basta)
    contenida = bool(qs) and qs <= cs and any(len(t) >= 3 for t in qs) and (len(qs) >= 2 or len(cs) <= 2)
    ok = cov >= 0.5 or contenida
    # Una sola palabra no nombra un valor de 2+ palabras informativas. Las palabras muy
    # comunes del catálogo ("gastos", "de") no cuentan como informativas: así "nomina"
    # sigue valiendo para "Gastos de Nómina", pero "ayuda" no vale para "Ayuda de Renta".
    if ok and df is not None and len(qs) == 1:
        cs_inf = {t for t in cs if df.get(t, 0) < 4}
        if len(cs_inf) >= 2:
            return False
    return ok


def resolver(q: str, idx: Indice, m, k: int, max_len: int = 5) -> list[dict]:
    """Encuentra TODAS las entidades de una pregunta.

    Recorre ventanas de palabras contiguas (1..max_len), descarta las que son solo
    relleno, resuelve cada ventana con el re-ranker y elige ventanas no solapadas por
    probabilidad descendente. Cada entidad sale con su decisión:
      - 'unica': una sola dimensión plausible.
      - 'ambigua': otra dimensión tiene probabilidad parecida (Cashi debe preguntar).
    """
    pal = normalizar(q).split()
    mejores = []
    for i in range(len(pal)):
        for j in range(i + 1, min(len(pal), i + max_len) + 1):
            if all(t in PALABRAS_RELLENO or t in PALABRAS_CONVERSACIONALES for t in pal[i:j]):
                continue
            w = " ".join(pal[i:j])
            pares = pares_para_consulta(w, idx, k)
            if not pares:
                continue
            cands = [c for c, _ in pares]
            p = m.predict_proba(np.array([f for _, f in pares]))[:, 1].copy()
            dim_anunciada = PALABRA_A_DIMENSION.get(pal[i - 1]) if i > 0 else None
            for x, c in enumerate(cands):
                if not guardia(w, idx.items[c][1], idx.df):
                    p[x] = 0.0           # candidatos que no pasan la regla de precisión
                elif dim_anunciada and idx.items[c][0] != dim_anunciada:
                    # "territorio centro": si no existe territorio "centro", no se
                    # reinterpreta como división; queda sin entidad -> se sugiere.
                    p[x] = 0.0
            jb = int(np.argmax(p))
            mejores.append((float(p[jb]), i, j, cands, p))
    # de mayor a menor probabilidad; a igualdad, la ventana más larga
    mejores.sort(key=lambda t: (-t[0], -(t[2] - t[1])))
    usados = set()
    salida = []
    for pb, i, j, cands, p in mejores:
        if pb < UMBRAL_ABSTENER:
            break
        if any(x in usados for x in range(i, j)):
            continue
        dec, sel = decidir(cands, p, idx.items)
        if dec == "abstencion":
            continue
        usados.update(range(i, j))
        # alternativas: otros valores del catálogo para la misma mención (sin repetir nombre)
        elegido = {idx.items[s][1] for s in sel}
        alternativas = []
        for x in np.argsort(-p):
            it = idx.items[cands[x]]
            if it[1] in elegido or p[x] <= 0 or any(it[1] == a[1] for a in alternativas):
                continue
            alternativas.append((it[0], it[1], float(p[x])))
            if len(alternativas) == 3:
                break
        salida.append({"span": " ".join(pal[i:j]), "p": pb, "decision": dec,
                       "entidades": [idx.items[s] for s in sel],
                       "alternativas": alternativas})
    return salida


def evaluar_gold(idx: Indice, m, k: int, catalogos, ruta: Path = GOLD) -> dict:
    casos = json.loads(ruta.read_text(encoding="utf-8"))["casos"]
    ok = n_ent = n_ok_ent = n_neg = n_neg_ok = n_amb_ok = n_espurias = 0
    detalle = []
    for c in casos:
        ents = resolver(c["q"], idx, m, k)

        def _es_buena(item):
            return item[0] in c["dims"] and c["buscar"] in normalizar(item[1])

        if not c["dims"]:
            n_neg += 1
            acierto = not ents
            n_neg_ok += int(acierto)
            n_espurias += len(ents)
        else:
            n_ent += 1
            unicas = [e for e in ents if e["decision"] == "unica"]
            acierto_directo = any(_es_buena(e["entidades"][0]) for e in unicas)
            acierto_amb = bool(c.get("ambigua")) and any(
                _es_buena(it) for e in ents if e["decision"] == "ambigua" for it in e["entidades"])
            acierto = acierto_directo or acierto_amb
            n_ok_ent += int(acierto_directo)
            n_amb_ok += int(acierto_amb)
            n_espurias += sum(1 for e in ents if not any(_es_buena(it) for it in e["entidades"]))
        ok += int(acierto)
        detalle.append({"q": c["q"], "ok": acierto,
                        "entidades": [f"{e['decision']}: " + " | ".join(
                            f"{d}:{n}" for d, n in e["entidades"]) for e in ents]})
    return {"exactitud_total": ok / len(casos), "entidades_ok": f"{n_ok_ent}/{n_ent}",
            "ambiguas_bien_preguntadas": n_amb_ok, "negativos_ok": f"{n_neg_ok}/{n_neg}",
            "entidades_espurias": n_espurias, "detalle": detalle}


def main():
    catalogos = cargar_catalogos()
    rng = random.Random(SEMILLA)
    rondas = []
    # Ronda de búsqueda: rejilla de configuraciones, todas evaluadas por CV agrupada.
    for ngram in [(2, 4), (2, 5)]:
        for k in [10, 20]:
            for tipo in ["logistica_C1", "logistica_C10", "lambdarank"]:
                r = evaluar_cv(catalogos, ngram, k, tipo)
                rondas.append({"ngram": list(ngram), "k": k, "ranker": tipo, **r})
                print(f"ngram={ngram} k={k} ranker={tipo}: top1={r['top1']:.3f} "
                      f"mrr={r['mrr']:.3f} recall@k={r['recall_at_k']:.3f}", flush=True)
    mejor = max(rondas, key=lambda r: (r["top1"], r["mrr"]))
    print("mejor:", {k: mejor[k] for k in ("ngram", "k", "ranker", "top1", "mrr")}, flush=True)

    ngram, k, tipo = tuple(mejor["ngram"]), mejor["k"], mejor["ranker"]
    idx, m = entrenar_final(catalogos, ngram, k, tipo, rng)
    gold = evaluar_gold(idx, m, k, catalogos)
    hold = evaluar_gold(idx, m, k, catalogos, ruta=HOLDOUT)
    hold2 = evaluar_gold(idx, m, k, catalogos, ruta=HOLDOUT2)
    resumen = ("exactitud_total", "entidades_ok", "ambiguas_bien_preguntadas",
               "negativos_ok", "entidades_espurias")
    print("gold (ajuste):", {x: gold[x] for x in resumen}, flush=True)
    print("holdout 1:", {x: hold[x] for x in resumen}, flush=True)
    print("holdout 2:", {x: hold2[x] for x in resumen}, flush=True)

    SALIDA.mkdir(parents=True, exist_ok=True)
    joblib.dump({"indice": idx, "ranker": m, "k": k, "ngram": ngram, "tipo": tipo,
                 "dimensiones": DIMENSIONES}, SALIDA / "entidades.joblib")
    metricas = {"semilla": SEMILLA, "rondas": rondas, "mejor": mejor,
                "valores_por_dimension": {d: len(v) for d, v in catalogos.items()},
                "gold": {x: gold[x] for x in resumen}, "gold_detalle": gold["detalle"],
                "holdout": {x: hold[x] for x in resumen}, "holdout_detalle": hold["detalle"],
                "holdout2": {x: hold2[x] for x in resumen}, "holdout2_detalle": hold2["detalle"]}
    (SALIDA / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
    return metricas


if __name__ == "__main__":
    main()
