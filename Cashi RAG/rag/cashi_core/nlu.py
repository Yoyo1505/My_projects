# -*- coding: utf-8 -*-
"""rag/cashi_core/nlu.py — Interpretación de la pregunta (NLU): _parse_nlu y semanas."""
from __future__ import annotations

from rag.cashi_core.comun import *  # noqa: F401,F403


class NLUMixin:
    def _parse_nlu(self, raw_query: str, norm_query: str, contexto_previo: Optional[dict] = None) -> dict:
        confianza = 0.5

        # Preguntas descriptivas/de catálogo (definir al inicio del NLU)
        es_estructura = any(kw in norm_query for kw in [
            "que territorios", "cuantos territorios", "cuantos cecos", "cuantos pdv", "cuantos pdvs",
            "que cecos tiene", "que cecos hay", "que pdv tiene", "que pdvs tiene",
            "a que division pertenece", "a que territorio pertenece", "a que zona pertenece", "a que region pertenece",
            "de que division es", "de division es", "de que territorio es", "de territorio es",
            "de que zona es", "de zona es", "de que region es", "de region es",
            "a que grupo pertenece", "a que contraloria pertenece",
            "que contraloria tiene", "que contraloria es", "que contraloria corresponde",
            "contraloria del ceco", "contraloria de este ceco",
            "que cuentas tiene", "que cuentas componen", "que cuentas hay", "cuentas del grupo", "estructura de",
            "jerarquia de", "como esta organizad", "que divisiones hay", "cuantas divisiones", "que grupos de cuentas hay",
            "cuantas zonas", "que zonas", "cuales zonas", "cuales regiones", "que regiones", "cuantas regiones",
            "de que territorio es zona", "de que territorio es region",
            "a que pertenece", "a que nivel pertenece",
        ])
        # Una pregunta de sentido de variación ("qué regiones se pasaron del plan") no es de
        # estructura aunque nombre una dimensión; la estructura pide jerarquía, no desviaciones.
        if es_estructura and ("sobregasto" in norm_query or "ahorro" in norm_query):
            es_estructura = False

        # CECO / Eco PDV — un número suelto en la pregunta puede referirse a
        # cualquiera de los dos identificadores (son catálogos distintos: CECO
        # = ID_CENTRO_COSTOS, Eco PDV = agrupador de punto de contacto físico).
        # Se prueba primero como CECO (comportamiento previo) y, si no matchea
        # ningún CECO válido, como Eco PDV antes de darlo por inexistente —
        # antes cualquier número no-CECO se reportaba como "CECO no localizado"
        # aunque fuera un PDV real (feedback 2026-08-31).
        anios_patron = {str(y) for y in range(1990, 2035)}
        posibles_cecos = re.findall(r"\b(\d{3,7})\b", norm_query)
        ceco_id = None
        ceco_inexistente = None
        eco_pdv_directo = None

        for cand in posibles_cecos:
            if cand not in anios_patron:
                cand_clean = cand.lstrip("0")
                if cand in self.validos_cecos_raw:
                    ceco_id = cand
                    break
                elif cand_clean in self.validos_cecos_clean:
                    ceco_id = self.validos_cecos_clean[cand_clean]
                    break
                elif int(cand) in self.validos_eco_pdv:
                    eco_pdv_directo = int(cand)
                    ceco_inexistente = None  # un candidato previo no-CECO ya se resolvió como Eco PDV
                    break
                else:
                    ceco_inexistente = cand

        div_encontrada, div_tier, div_cands = mejor_entidad(self.map_divisiones, norm_query)
        terr_encontrado, terr_tier, terr_cands = mejor_entidad(self.map_territorios, norm_query)
        zona_encontrada, zona_tier, zona_cands = mejor_entidad(self.map_zonas, norm_query)
        region_encontrada, region_tier, region_cands = mejor_entidad(self.map_regiones, norm_query)
        # Contraloría tiene dos niveles (igual que el tablero): resumen (cat_Contraloria_6,
        # ej. "Contraloria Alfa") y detalle (cat_Contraloria, ej. "Contraloria Alfa Propios").
        # Gana el de mayor tier; en empate, el valor más largo (más específico); si
        # tienen el mismo nombre, el resumen.
        c6, t6, cands6 = mejor_entidad(self.map_contraloria6, norm_query)
        cd, td, candsd = mejor_entidad(self.map_contralogias, norm_query)
        contra_nivel = None
        if c6 and (not cd or t6 > td or (t6 == td and len(c6) >= len(cd))):
            contra_encontrada, contra_tier, contra_nivel = c6, t6, "6"
        elif cd:
            contra_encontrada, contra_tier, contra_nivel = cd, td, "detalle"
        else:
            contra_encontrada, contra_tier = None, 0
        contra_cands = sorted(list(cands6) + list(candsd), key=lambda x: x[1], reverse=True)[:5]
        grupo_encontrado, grupo_tier, grupo_cands = mejor_entidad(self.map_grupos, norm_query)
        cuenta_encontrada, cuenta_tier, cuenta_cands = mejor_entidad(self.map_cuentas, norm_query)
        agrupa1_encontrada, agrupa1_tier, agrupa1_cands = mejor_entidad(self.map_agrupa1, norm_query)
        agrupa2_encontrada, agrupa2_tier, agrupa2_cands = mejor_entidad(self.map_agrupa2, norm_query)
        agrupa3_encontrada, agrupa3_tier, agrupa3_cands = mejor_entidad(self.map_agrupa3, norm_query)
        pdc_encontrado, pdc_tier, pdc_cands = mejor_entidad(self.map_pdc, norm_query)

        # "contraloría Otros": "Otros" existe también como División/Territorio/etc.
        # Si la pregunta nombra explícitamente "contraloría" y otra entidad solo
        # coincidió por tener el MISMO nombre que la contraloría, gana la contraloría.
        if contra_encontrada and "contraloria" in norm_query:
            _n_contra = normalizar_texto(contra_encontrada)
            if terr_encontrado and normalizar_texto(terr_encontrado) == _n_contra: terr_encontrado = None
            if div_encontrada and normalizar_texto(div_encontrada) == _n_contra: div_encontrada = None
            if zona_encontrada and normalizar_texto(zona_encontrada) == _n_contra: zona_encontrada = None
            if region_encontrada and normalizar_texto(region_encontrada) == _n_contra: region_encontrada = None
            if grupo_encontrado and normalizar_texto(grupo_encontrado) == _n_contra: grupo_encontrado = None
            if cuenta_encontrada and normalizar_texto(cuenta_encontrada) == _n_contra: cuenta_encontrada = None

        # Si es una pregunta de ESTRUCTURA (descriptiva con typos), intentar fuzzy
        # matching adicional basado en caracteres si no se encontró la entidad
        # esperada. Ej. "cuantas zonas hay en el terriotiro guerrero" → debe
        # resolver "terriotiro guerrero" a "Territorio Guerrero" aunque sea typo.
        if es_estructura:
            # Extraer fragmento probable de entidad (después de "en ", "de ", etc.)
            frag_ent = None
            for sep in [" en el ", " en la ", " en ", " de ", " del "]:
                if sep in norm_query:
                    frag_ent = norm_query.split(sep)[-1].strip()
                    break
            if not frag_ent:
                frag_ent = norm_query

            if not terr_encontrado and ("zona" in norm_query or "region" in norm_query):
                match = fuzzy_match_typo(frag_ent, self.map_territorios, umbral=0.65)
                if match:
                    terr_encontrado = match
                    terr_tier = 1
            if "zona" in norm_query or "zonas" in norm_query:
                # Extraer palabras que NO son "zona"/"zonas" como candidato a nombre de zona
                palabras_cand = [w for w in re.findall(r"\b\w+\b", frag_ent) if w.lower() not in ["zona", "zonas"]]
                if palabras_cand and not zona_encontrada:
                    zona_cand = " ".join(palabras_cand)
                    match = fuzzy_match_typo(zona_cand, self.map_zonas, umbral=0.60)
                    if match:
                        zona_encontrada = match
                        zona_tier = 1
            if not region_encontrada and "region" in norm_query:
                match = fuzzy_match_typo(frag_ent, self.map_regiones, umbral=0.65)
                if match:
                    region_encontrada = match
                    region_tier = 1
            if not div_encontrada and "division" in norm_query:
                match = fuzzy_match_typo(frag_ent, self.map_divisiones, umbral=0.65)
                if match:
                    div_encontrada = match
                    div_tier = 1

        # Si algún tipo de entidad logró un match de alta confianza (tier 2:
        # substring exacto o cobertura total de tokens), se descartan los
        # matches de OTROS tipos que solo llegaron a tier 1 (fuzzy parcial) —
        # evita que un PDC/cuenta con nombre largo que comparte un par de
        # palabras genéricas con la consulta ("division", "norte", etc.) se
        # cuele como filtro adicional junto a la entidad real y más específica,
        # angostando la consulta SQL de forma silenciosa e inesperada.
        max_tier = max(div_tier, terr_tier, zona_tier, region_tier, contra_tier, grupo_tier, cuenta_tier, agrupa1_tier, agrupa2_tier, agrupa3_tier, pdc_tier)
        if max_tier == 2:
            if div_tier < 2: div_encontrada = None
            if terr_tier < 2: terr_encontrado = None
            if zona_tier < 2: zona_encontrada = None
            if region_tier < 2: region_encontrada = None
            if contra_tier < 2: contra_encontrada = None
            if grupo_tier < 2: grupo_encontrado = None
            if cuenta_tier < 2: cuenta_encontrada = None
            if agrupa1_tier < 2: agrupa1_encontrada = None
            if agrupa2_tier < 2: agrupa2_encontrada = None
            if agrupa3_tier < 2: agrupa3_encontrada = None
            if pdc_tier < 2: pdc_encontrado = None

        # Mismo nombre en dos dimensiones (p. ej. división y territorio "Concentrador"):
        # la palabra que precede al nombre decide. "division X" -> división; "territorio X" -> territorio.
        if div_encontrada and terr_encontrado and normalizar_texto(div_encontrada) == normalizar_texto(terr_encontrado):
            n_ent = re.escape(normalizar_texto(div_encontrada))
            if re.search(rf"\bdivision {n_ent}\b", norm_query):
                terr_encontrado = None
            elif re.search(rf"\bterritorio {n_ent}\b", norm_query):
                div_encontrada = None
        div_pre_ml, terr_pre_ml = div_encontrada, terr_encontrado

        # Resolvedor ML (rag/cashi_ml, 2026-10-08): completa las dimensiones que el mapa
        # no resolvió y descarta menciones parciales del mapa (ver ajustar_con_mapa).
        # Si la frase cabe en dos dimensiones y no hay otra entidad, se pregunta.
        mapa_ml, ml_amb, ml_incierta = ajustar_con_mapa(_canonizar(normalizar_texto(raw_query)), {
            "division": div_encontrada, "territorio": terr_encontrado,
            "zona": zona_encontrada, "region": region_encontrada,
            "grupo_cuentas": grupo_encontrado, "cuenta": cuenta_encontrada,
            "pdc": pdc_encontrado, "agrupador_reales": None,
        })
        div_encontrada, terr_encontrado = mapa_ml["division"], mapa_ml["territorio"]
        zona_encontrada, region_encontrada = mapa_ml["zona"], mapa_ml["region"]
        grupo_encontrado, cuenta_encontrada = mapa_ml["grupo_cuentas"], mapa_ml["cuenta"]
        pdc_encontrado = mapa_ml["pdc"]
        agrupador_encontrado = mapa_ml["agrupador_reales"]
        # El ML no debe anular una mención de dimensión que el mapa sí ancló con su
        # palabra clave ("division X" / "territorio X") sobre el mismo nombre.
        if div_pre_ml and terr_encontrado and normalizar_texto(terr_encontrado) == normalizar_texto(div_pre_ml) \
                and re.search(rf"\bdivision {re.escape(normalizar_texto(div_pre_ml))}\b", norm_query):
            div_encontrada, terr_encontrado = div_pre_ml, None
        elif terr_pre_ml and div_encontrada and normalizar_texto(div_encontrada) == normalizar_texto(terr_pre_ml) \
                and re.search(rf"\bterritorio {re.escape(normalizar_texto(terr_pre_ml))}\b", norm_query):
            terr_encontrado, div_encontrada = terr_pre_ml, None

        # "<dimensión> <nombre>" donde el nombre no existe en esa dimensión (p. ej. "zona
        # centro" sin zona Centro, "division x"): no se responde con otra dimensión ni con
        # el total sin filtro. Se avisa y se ofrecen los valores reales de esa dimensión
        # (incluido "No Clasificado" cuando la dimensión no está clasificada).
        entidad_por_dim = {"division": div_encontrada, "territorio": terr_encontrado,
                           "zona": zona_encontrada, "region": region_encontrada}
        mapa_por_dim = {"division": self.map_divisiones, "territorio": self.map_territorios,
                        "zona": self.map_zonas, "region": self.map_regiones}
        nombres_no_reconocidos = {}
        for dim_nombre, mapa_dim in mapa_por_dim.items():
            m_nombre = re.search(rf"\b{dim_nombre} ((?:(?!(?:por|de|del|y|cada|en|la|el)\b)\w+\s?)+)", norm_query)
            if m_nombre and not entidad_por_dim[dim_nombre]:
                nombres_no_reconocidos[dim_nombre] = m_nombre.group(1).strip()
        # Si el nombre no reconocido lo tomó otra dimensión por una palabra compartida
        # ("zona centro" -> división Centro), esa asignación se descarta.
        _palabras_dim = {"division", "territorio", "zona", "region", "direccion", "de", "del"}
        for dim_nombre, nombre in nombres_no_reconocidos.items():
            palabras = set(nombre.split()) - _palabras_dim
            for otra, valor in entidad_por_dim.items():
                if otra == dim_nombre or not valor:
                    continue
                if palabras & (set(normalizar_texto(valor).split()) - _palabras_dim):
                    if otra == "division": div_encontrada = None
                    elif otra == "territorio": terr_encontrado = None
                    elif otra == "zona": zona_encontrada = None
                    elif otra == "region": region_encontrada = None
        division_no_reconocida = bool(nombres_no_reconocidos)

        # Candidatos "¿quisiste decir...?": solo tienen sentido cuando NINGÚN
        # tipo de entidad llegó a aplicarse (si ya hay un tier>=1 aplicado, los
        # candidatos débiles de otros tipos se ignoran — ya se respondió).
        # EXCEPTO: si es una pregunta descriptiva (es_estructura), ignorar
        # sugerencias de entidades — el usuario pregunta sobre ESTRUCTURA, no
        # sobre un CECO/división específico; typos no importan.
        sugerencias_entidades: List[Tuple[str, str, float]] = []
        if max_tier == 0 and not es_estructura:
            for etiqueta, cands in (
                ("División", div_cands), ("Territorio", terr_cands), ("Zona", zona_cands),
                ("Región", region_cands), ("Contraloría", contra_cands), ("Grupo de Cuentas", grupo_cands),
                ("Cuenta", cuenta_cands), ("Agrupa1", agrupa1_cands), ("Agrupa2", agrupa2_cands), ("Agrupa3", agrupa3_cands), ("PDC", pdc_cands),
            ):
                for valor, ratio in cands:
                    sugerencias_entidades.append((etiqueta, valor, ratio))
            sugerencias_entidades.sort(key=lambda x: x[2], reverse=True)
            sugerencias_entidades = sugerencias_entidades[:5]
        if division_no_reconocida:
            # Nombre no encontrado en su dimensión: ofrecer los valores reales más
            # parecidos de ESA dimensión (no responder con otra ni caer a búsqueda documental).
            etiquetas_dim = {"division": "División", "territorio": "Territorio", "zona": "Zona", "region": "Región"}
            sugerencias_entidades = []
            for dim_nombre, nombre in nombres_no_reconocidos.items():
                parecidas = sorted(
                    ((SequenceMatcher(None, normalizar_texto(nombre), k).ratio(), v)
                     for k, v in mapa_por_dim[dim_nombre].items()), reverse=True)[:5]
                sugerencias_entidades += [(etiquetas_dim[dim_nombre], v, r) for r, v in parecidas]

        m_srv = re.search(r"\b(srv\d+|rtm\d+\w*|\d{4}e)\b", norm_query)
        servicio_id = m_srv.group(1).upper() if m_srv else None

        # Herencia de contexto conversacional (follow-ups tipo "¿y por semana?"
        # o "¿y en 2025?"): solo si la consulta actual NO menciona ningún filtro
        # propio (ni siquiera un CECO inválido, ni un candidato débil tipo
        # "¿quisiste decir?") se reutilizan los filtros de la respuesta
        # anterior. Si hay sugerencias débiles, el usuario claramente intentó
        # nombrar algo nuevo — mejor preguntarle que responder en silencio
        # sobre la entidad del turno pasado. Si menciona una entidad nueva
        # confirmada, esa gana siempre — nunca se mezclan entidades de turnos.
        contexto_aplicado = False
        if contexto_previo and not sugerencias_entidades and not any([
            ceco_id, eco_pdv_directo, ceco_inexistente, div_encontrada, terr_encontrado, zona_encontrada, region_encontrada,
            contra_encontrada, grupo_encontrado, cuenta_encontrada, agrupa1_encontrada, agrupa2_encontrada, agrupa3_encontrada, pdc_encontrado, servicio_id
        ]):
            ceco_id = contexto_previo.get("ceco")
            eco_pdv_directo = contexto_previo.get("eco_pdv_directo")
            div_encontrada = contexto_previo.get("division")
            terr_encontrado = contexto_previo.get("territorio")
            zona_encontrada = contexto_previo.get("zona")
            region_encontrada = contexto_previo.get("region")
            contra_encontrada = contexto_previo.get("contraloria")
            contra_nivel = contexto_previo.get("contraloria_nivel")
            grupo_encontrado = contexto_previo.get("grupo_cuentas")
            cuenta_encontrada = contexto_previo.get("cuenta")
            agrupa1_encontrada = contexto_previo.get("agrupa1")
            agrupa2_encontrada = contexto_previo.get("agrupa2")
            agrupa3_encontrada = contexto_previo.get("agrupa3")
            pdc_encontrado = contexto_previo.get("pdc")
            contexto_aplicado = any([ceco_id, eco_pdv_directo, div_encontrada, terr_encontrado, zona_encontrada, region_encontrada, contra_encontrada, grupo_encontrado, cuenta_encontrada, agrupa1_encontrada, agrupa2_encontrada, agrupa3_encontrada, pdc_encontrado])

        semanas_info = self._parse_semanas(norm_query)

        # Detección de Agrupaciones Multi-Dimensionales (general, no por frase fija)
        dims_solicitadas = _detectar_dimensiones(norm_query)

        # Alertas de sobregasto semanal (2026-09-28): variación semana-contra-
        # semana por Grupo de Cuentas y por CECO/ECO_PDV, contra el promedio
        # histórico de esa misma variación (no el nivel de gasto, como
        # `_query_anomalias_mad` — aquí lo anómalo es el TAMAÑO del aumento/
        # caída de una semana a la siguiente). Ver `_query_alertas_sobregasto`.
        es_alerta_sobregasto = any(kw in norm_query for kw in [
            "alerta de sobregasto", "alertas de sobregasto", "alerta de gasto",
            "sobregasto semanal", "aumento semanal", "aumento inusual",
            "incremento semanal", "incremento inusual", "variacion semanal promedio",
            "que grupos aumentaron", "que ceco aumento", "que cecos aumentaron",
            "aumento por grupo", "alertas automaticas",
            "variacion porcentual", "mayor variacion porcentual", "salto porcentual",
            "que grupo salto mas", "mas saltos", "variacion en porcentaje",
            "porcentaje de variacion", "mayor salto",
        ])
        # Variación en % (2026-09-28, a petición del usuario): FP&A/consultoría
        # recomienda umbral DUAL, nunca solo %, porque un salto de 50% en un
        # rubro chico puede ser irrelevante mientras uno de 5% en un rubro
        # grande sí importa (fuente: Numeric.io, Datarails — "greater than X%
        # AND greater than $Y", no "OR"). Aquí no reemplaza el filtro
        # estadístico ($ P95 + MAD) ya existente, solo cambia el ORDEN cuando
        # el usuario pide explícitamente el ranking porcentual.
        es_orden_pct = any(kw in norm_query for kw in [
            "porcentual", "porcentaje", "en porcentaje", "salto mas", "mas saltos", "%"
        ])
        # Señales / hallazgo ejecutivo de sobregasto de UNA semana (2026-09-29):
        # Real − Plan exacto, alcance, concentración, patrón territorial,
        # factor contable, persistencia, rareza y probabilidad de evento
        # estructural — mismo cálculo que la pestaña "Alertas de Sobregasto"
        # (rag/senales_sobregasto.py). Ver `_query_senales_sobregasto`.
        es_senales = any(kw in norm_query for kw in [
            "senales de sobregasto", "senal de sobregasto", "hallazgo", "resumen ejecutivo de sobregasto",
            "resumen de sobregasto", "sobregasto de la semana", "diagnostico de sobregasto",
            "probabilidad estructural", "evento estructural", "es estructural",
        ])
        es_anomalia = any(kw in norm_query for kw in ["anomalia", "atipico", "outlier", "irregularidad", "mad", "pico"])
        # "mas variacion"/"mayor variacion" (calibración 2026-08-31, iteración 6-7):
        # preguntas reales tipo "Que PDV/CECO de <territorio> tuvo mas variacion en
        # <cuenta>?" — antes caían silenciosamente en la ruta financiera estándar
        # (un solo agregado, sin ranking). Ver `_query_top_desviaciones` para el
        # soporte de agrupación por PDV adicional a CECO.
        es_top = any(kw in norm_query for kw in [
            "top", "ranking", "mayores desviaciones", "mas excedidos", "sobreconsumo",
            "mas variacion", "mayor variacion", "tuvo mas variacion", "variacion mas alta",
            "cual tuvo mas variacion", "mas volatil", "mayor volatilidad",
            "se paso del plan", "se pasaron del plan", "se paso de presupuesto",
            "se pasaron de presupuesto", "excedieron el plan", "excedio el plan",
            "rebasaron el plan", "rebaso el plan", "sobrepasaron el presupuesto",
            "sobrepaso el presupuesto", "se salieron del plan", "quien se paso del plan",
            "que ceco se paso", "que cecos se pasaron", "que pdv se paso", "que pdvs se pasaron",
            "cecos con sobregasto", "ceco con sobregasto", "pdv con sobregasto", "pdvs con sobregasto",
            "cecos con sobreconsumo", "pdvs con sobreconsumo",
        ])
        # "sobreconsumo/excedidos/top" son direccionales (buscan sobregasto,
        # el signo importa); "variacion/volatilidad" son simétricos (favorable
        # o desfavorable, importa la magnitud). Ver `_query_top_desviaciones`.
        es_top_absoluto = any(kw in norm_query for kw in [
            "mas variacion", "mayor variacion", "tuvo mas variacion", "variacion mas alta",
            "cual tuvo mas variacion", "mas volatil", "mayor volatilidad"
        ])
        # "se pasaron del plan"/"excedieron" implican SOLO sobregasto real
        # (Real > Plan), no cualquier variación — a diferencia de "top
        # variación" que es simétrico. Ver uso en `_query_top_desviaciones`.
        es_solo_sobregasto_real = any(kw in norm_query for kw in [
            "se paso del plan", "se pasaron del plan", "se paso de presupuesto",
            "se pasaron de presupuesto", "excedieron el plan", "excedio el plan",
            "rebasaron el plan", "rebaso el plan", "sobrepasaron el presupuesto",
            "sobrepaso el presupuesto", "se salieron del plan", "quien se paso del plan",
            "que ceco se paso", "que cecos se pasaron", "que pdv se paso", "que pdvs se pasaron",
            "sobreconsumo", "mas excedidos",
            "cecos con sobregasto", "ceco con sobregasto", "pdv con sobregasto", "pdvs con sobregasto",
            "cecos con sobreconsumo", "pdvs con sobreconsumo",
        ])
        # Ranking por concepto (no por frase): "sobregasto" + CECO/PDV + "más" o un número
        # ("5 ceco con mas sobregasto de nomina"). Lo canónico del léxico ya llega aquí.
        es_ranking_concepto = ("sobregasto" in norm_query
                               and any(k in norm_query for k in ("ceco", "pdv"))
                               and bool(re.search(r"\b(mas|top|\d+)\b", norm_query)))
        if es_ranking_concepto:
            es_top = True
            es_solo_sobregasto_real = True
        # Ranking por NIVEL de gasto (no por desviación vs Plan) — "qué CECO
        # tiene más gasto de nómina" (2026-09-28, a petición del usuario):
        # antes "<cuenta/grupo> por ceco" caía a `multidimensional` y
        # regresaba TODOS los CECOs sin ordenar (miles de filas), sin ranking
        # útil. Ver `_query_top_gasto_entidad`.
        es_top_gasto = any(kw in norm_query for kw in [
            "mas gasto de", "mas gasto en", "mayor gasto de", "mayor gasto en",
            "con mas gasto", "con mayor gasto", "mas gastan", "que ceco gasta mas",
            "que cecos gastan mas", "que pdv gasta mas", "cecos con mas gasto",
            "cecos con mayor gasto", "top gasto",
        ])
        # Agrupación objetivo del ranking de variación: PDV si la pregunta lo
        # menciona explícitamente (token completo, no como parte de otra
        # palabra) y no menciona CECO a la vez; CECO en cualquier otro caso
        # (comportamiento previo, sin cambios).
        _tokens_query = set(re.findall(r"\w+", norm_query))
        agrupar_variacion_por = "pdv" if (
            ({"pdv", "pdvs", "pdc", "pdcs"} & _tokens_query) and "ceco" not in _tokens_query
        ) else "ceco"
        # Ranking de ahorro ("la cuenta con más ahorro vs plan"): más negativo primero.
        # Por cuenta cuando se pide "cuenta(s)" y no se nombra CECO/PDV.
        es_ranking_ahorro = "ahorro" in norm_query and bool(re.search(r"\b(mas|top|\d+)\b", norm_query))
        if es_ranking_ahorro:
            es_top = True
        if (es_ranking_ahorro or es_ranking_concepto) and ({"cuenta", "cuentas"} & _tokens_query) \
                and not ({"ceco", "cecos", "pdv", "pdvs"} & _tokens_query):
            agrupar_variacion_por = "cuenta"

        # Marco de variación general: medida (vs plan / vs año anterior), sentido (ahorro,
        # sobregasto o variación), dimensión y ranking. Las palabras llegan ya canonizadas
        # por el léxico (rag/lexico), así que aquí solo se leen los términos canónicos.
        var_dir = "ahorro" if "ahorro" in _tokens_query else ("sobregasto" if "sobregasto" in _tokens_query else None)
        # "se pasaron del plan" llega como "sobregasto" (el léxico reemplaza la frase), así que
        # sin otra referencia explícita, el sentido de ahorro/sobregasto se mide contra el plan.
        var_ref = "plan" if "plan" in _tokens_query else ("aa" if "aa" in _tokens_query else
                                                          ("plan" if var_dir else None))
        var_rank = bool(
            re.search(r"\b(top|mas|mayor|mayores|menor|menores)\b", norm_query)
            or re.search(r"\b(?:los|las|top)\s+\d{1,2}\b", norm_query)
            or re.search(r"\b\d{1,2}\s+(?:mas|cecos?|pdvs?|cuentas?|territorios|divisiones|zonas|regiones|grupos)\b", norm_query)
        )
        var_dim = None
        # Solo dimensiones agrupables por variación (no semana/mes, que son periodos)
        _terminos_var = [t for t, d in _TERMINOS_DIMENSION.items() if d in VAR_DIM_COLUMNAS]
        m_dim = re.search(r"\b(" + "|".join(sorted(map(re.escape, _terminos_var), key=len, reverse=True)) + r")\b", norm_query)
        if m_dim:
            var_dim = _TERMINOS_DIMENSION[m_dim.group(1)]
        # La dimensión solo agrupa si se pide ranking ("cuáles territorios..."); si no, es un filtro.
        if not var_rank:
            var_dim = None
        # Sin alertas, señales, anomalías ni top de gasto: esas rutas tienen su propia lógica.
        var_frame = bool(var_ref in ("plan", "aa") and (var_dir or "variacion" in _tokens_query)
                         and not (es_alerta_sobregasto or es_senales or es_anomalia or es_top_gasto))
        # "qué regiones se pasaron del plan": una pregunta "cuáles/qué <dimensión>" pide ranking
        if not var_rank and re.search(r"\b(?:cuales|cual|que|quienes)\s+(?:\w+\s+)?(?:" + "|".join(
                map(re.escape, _terminos_var)) + r")\b", norm_query):
            var_rank = True
            var_dim = var_dim or _TERMINOS_DIMENSION.get(
                re.search(r"\b(" + "|".join(sorted(map(re.escape, _terminos_var), key=len, reverse=True)) + r")\b", norm_query).group(1))
        # "80/20" nunca aparece en norm_query: normalizar_texto() convierte
        # cualquier puntuación (incluida "/") en espacio antes de esta
        # comparación, así que se compara contra la forma ya normalizada
        # "80 20" — el literal "80/20" quedaba como código muerto inalcanzable.
        es_pareto = any(kw in norm_query for kw in ["pareto", "80 20", "concentracion de gasto", "sobregasto acumulado"])

        es_tendencia_mensual = ("mes" in dims_solicitadas) or any(kw in norm_query for kw in [
            "por mes", "por meses", "desglose mensual", "facturacion por mes", "desglose por mes",
            "evolucion mensual", "historico mensual", "gasto por mes", "mes a mes", "mensual"
        ])
        es_tendencia_semanal = ("semana" in dims_solicitadas) or any(kw in norm_query for kw in [
            "tendencia", "evolucion", "semanal", "comportamiento por semana",
            "por semana", "por semanas", "desglose por semana", "desglose semanal",
            "gasto por semana", "semana por semana", "semana a semana", "detalle semanal"
        ])

        es_sem_vs_sem = any(kw in norm_query for kw in ["semana vs semana", "sem vs sem", "vs semana", "comparar semanas"]) or len(semanas_info.get("semanas_especificas", [])) == 2
        es_ultimas_4 = any(kw in norm_query for kw in ["ultimas 4", "ultimas 4 semanas", "4 semanas vs", "mes reciente vs anterior"])
        es_real26_vs_real25 = any(kw in norm_query for kw in ["2026 vs 2025", "real 2026 vs real 2025", "vs ano anterior", "versus 2025", "ano contra ano"])
        # "eco pdv" se quitó de este disparador (2026-08-31): con Eco PDV ya
        # resuelto como entidad normal (`eco_pdv_directo`/`pdc`), cualquier
        # pregunta financiera normal que dijera "eco pdv" o "pdv" — p.ej.
        # "gasto para eco pdv 6031" — se secuestraba hacia este diagnóstico de
        # calidad de datos en vez de responder el gasto pedido. Se mantienen
        # solo frases inequívocamente de auditoría/diagnóstico.
        es_match_ceco = any(kw in norm_query for kw in [
            "sin match", "mapeo ceco", "respaldo ceco", "respaldo eco pdv",
            "match de ceco", "cecos sin match", "auditoria de match"
        ])
        es_linaje = any(kw in norm_query for kw in ["linaje", "calidad de datos", "auditoria de datos", "conciliacion", "fuente datos"])
        es_doc_kw = any(kw in norm_query for kw in ["regla", "manual", "metodologia", "radar", "homologacion", "criterio", "documento", "definicion"])

        # Detectar queries de variación entre métricas de Presupuesto 2027
        # Métricas: SIE (Reglas_2026) | CONTA (Ordinario_2026) | COMPARABILIDAD/PPTO (Ppto_2026) | FCST (Fcst_Oficial_2026)
        _METRICAS_KW = {
            "sie": "Reglas_2026",
            "conta": "Ordinario_2026",
            "contabilidad": "Ordinario_2026",
            "ordinario": "Ordinario_2026",
            "comparabilidad": "Ppto_2026",
            "ppto": "Ppto_2026",
            "presupuesto 2026": "Ppto_2026",
            "fcst": "Fcst_Oficial_2026",
            "forecast": "Fcst_Oficial_2026",
        }
        _metricas_en_query = [(_METRICAS_KW[kw], kw) for kw in _METRICAS_KW if kw in norm_query]
        # Desduplicar por columna (varios alias pueden apuntar a la misma)
        _seen_cols: set = set()
        _metricas_unicas = []
        for col, kw in _metricas_en_query:
            if col not in _seen_cols:
                _seen_cols.add(col)
                _metricas_unicas.append((col, kw))
        es_variacion_ppto = (
            len(_metricas_unicas) >= 2 and
            any(kw in norm_query for kw in ["vs", "variacion", "diferencia", "contra", "comparar", "versus"])
        )
        metricas_variacion = [col for col, _ in _metricas_unicas]  # orden de aparición

        # Variaciones operativas por semana (2026-10-27): "variaciones de la semana 43", "de la 1 a la 43",
        # "¿qué semanas fueron atípicas?", "brincó". Compara N contra N-1 (Real, Plan, FCST SIE) por grupo de
        # cuentas y lista CECOs/semanas atípicos. Solo si nombran una semana o piden semanas atípicas, y sin
        # referencia explícita a plan/año anterior ni sobregasto/ahorro (esas siguen en `variacion_general`).
        # También sin semana cuando piden atípicos/saltos de una entidad ("atípicos para costo activo fijo",
        # "qué CECOs saltan en nómina"): analiza todo el año hasta la última semana real.
        _hay_entidad = any([grupo_encontrado, cuenta_encontrada, div_encontrada, terr_encontrado,
                            zona_encontrada, region_encontrada, ceco_id])
        es_var_semanal = bool(
            re.search(r"\b(variacion(?:es)?|variaron|atipic\w*|anomal\w*|brinc\w*|salt\w*)\b", norm_query)
            and (re.search(r"\bsem\w*\s+(?:de\s+la\s+|del?\s+)?\d+", norm_query)
                 or re.search(r"\bsemanas?\s+atipic\w*|\b(?:que|cuales|cuantas)\s+semanas\b", norm_query)
                 or (_hay_entidad and re.search(r"\b(atipic\w*|brinc\w*|salt\w*)\b", norm_query)))
            and not (var_ref in ("plan", "aa") and var_dir)
            and "ppto" not in norm_query and "presupuesto 2027" not in norm_query
        )

        # Canal pedido en el texto (solo frases inequívocas: "Fraude Digital" es un grupo de cuentas, no el canal).
        if re.search(r"\bambos canales\b|\btodos los canales\b|\bfisico y digital\b|\bdigital y fisico\b|\bfisicos y digitales\b|\bdigitales y fisicos\b", norm_query):
            canal_texto = "Ambos"
        elif re.search(r"\bcanal(?:es)? digital(?:es)?\b|\bdigitales\b|\ben digital\b", norm_query):
            canal_texto = "Digital"
        elif re.search(r"\bcanal(?:es)? fisicos?\b|\bfisicos\b|\ben fisico\b", norm_query):
            canal_texto = "Fisico"
        else:
            canal_texto = None
        # "digital" como canal no es la cuenta "Fraude Digital" (solo se conserva si nombran "fraude").
        if canal_texto and "fraude" not in norm_query:
            if cuenta_encontrada and "digital" in str(cuenta_encontrada).lower():
                cuenta_encontrada = None
            if grupo_encontrado and "digital" in str(grupo_encontrado).lower():
                grupo_encontrado = None
            if agrupador_encontrado and "digital" in str(agrupador_encontrado).lower():
                agrupador_encontrado = None
            # El canal pedido explica la palabra "digital"/"fisico": no ofrecer "¿quisiste decir Fraude Digital?".
            sugerencias_entidades = [s for s in sugerencias_entidades if "digital" not in str(s[1]).lower()]

        # Determinación de Ruta
        if es_variacion_ppto:
            ruta = "variacion_ppto"
            confianza = 0.95
        elif es_estructura:
            ruta = "estructura"
            confianza = 0.95
        elif es_senales:
            ruta = "senales_sobregasto"
            confianza = 0.95
        elif es_var_semanal:
            ruta = "variaciones_semana"
            confianza = 0.93
        elif var_frame:
            # Variación contra plan/año anterior (total o ranking): va antes que el desglose
            # por dimensión, para que "cuáles divisiones tienen mayor sobregasto" no caiga a un desglose.
            ruta = "variacion_general"
            confianza = 0.92
        elif len(dims_solicitadas) >= 2 and not division_no_reconocida:
            ruta = "multidimensional"
            confianza = 0.95
        elif es_alerta_sobregasto:
            ruta = "alertas_sobregasto"
            confianza = 0.95
        elif es_anomalia:
            ruta = "anomalias"
            confianza = 0.95
        elif es_top_gasto:
            ruta = "top_gasto_entidad"
            confianza = 0.90
        elif es_top:
            ruta = "top_desviaciones"
            confianza = 0.90
        elif es_pareto:
            ruta = "pareto"
            confianza = 0.90
        elif es_tendencia_mensual and len(dims_solicitadas) <= 1:
            ruta = "tendencia_mensual"
            confianza = 0.92
        elif es_tendencia_semanal and len(dims_solicitadas) <= 1:
            ruta = "tendencia_semanal"
            confianza = 0.90
        elif es_sem_vs_sem:
            ruta = "semana_vs_semana"
            confianza = 0.88
        elif es_ultimas_4:
            ruta = "ultimas_4_vs_anteriores"
            confianza = 0.88
        elif es_real26_vs_real25:
            ruta = "real_2026_vs_real_2025"
            confianza = 0.92
        elif len(dims_solicitadas) == 1 and dims_solicitadas[0] not in ("semana", "mes") and not ceco_inexistente and not division_no_reconocida and not (
            # Desglose de UNA dimensión: sin entidad de esa misma dimensión.
            # "gasto por territorio semana 39" / "gasto por división", y también
            # "gasto division norte por territorio" (entidad de OTRA dimensión
            # filtra; la dimensión pedida desglosa). Antes, con cualquier entidad
            # presente caía al desglose por grupo de cuentas.
            {"territorio": terr_encontrado, "division": div_encontrada, "zona": zona_encontrada,
             "region": region_encontrada, "grupo_cuentas": grupo_encontrado, "cuenta": cuenta_encontrada,
             "pdc": pdc_encontrado, "ceco": ceco_id or eco_pdv_directo}.get(dims_solicitadas[0])
        ):
            ruta = "multidimensional"
            confianza = 0.90
        elif es_match_ceco:
            ruta = "cecos_sin_match"
            confianza = 0.95
        elif es_linaje:
            ruta = "calidad_linaje"
            confianza = 0.95
        elif servicio_id:
            ruta = "servicio_detalle"
            confianza = 0.95
        elif any([ceco_id, eco_pdv_directo, ceco_inexistente, div_encontrada, terr_encontrado, zona_encontrada, region_encontrada, contra_encontrada, grupo_encontrado, cuenta_encontrada, pdc_encontrado, agrupador_encontrado, canal_texto]):
            ruta = "mixta" if es_doc_kw and not canal_texto else "financiera"
            confianza = 0.88
        elif es_doc_kw:
            ruta = "documental"
            confianza = 0.90
        elif ml_amb:
            # El resolvedor ML encontró la misma frase en dos dimensiones del catálogo
            # (p. ej. "telefono": cuenta o agrupador de reales). Se pregunta.
            ruta = "aclaracion"
            confianza = 0.7
        elif sugerencias_entidades:
            # El texto parece nombrar una división/territorio/cuenta/PDC real
            # pero ninguna coincidencia fue lo bastante fuerte para aplicarse
            # (ver UMBRAL_AUTO_APLICAR) — mejor preguntar "¿quisiste decir...?"
            # que adivinar en silencio o devolver el consolidado global.
            ruta = "sugerencia_entidad"
            confianza = 0.5
        else:
            ruta = "sin_coincidencias"
            confianza = 0.30

        # Clasificador de intención (rag/cashi_intents): solo como respaldo. Si las reglas dejaron
        # la consulta en una ruta genérica y el modelo está seguro, se usa su intención.
        pred_intencion = None
        # Con "forecast" en la pregunta no se asume plan: el marco de variación aún no soporta forecast.
        if ruta in ("financiera", "mixta", "sin_coincidencias", "documental") and not ceco_inexistente \
                and "forecast" not in norm_query:
            try:
                from rag.cashi_intents.inferir import predecir as _predecir_intencion
                pred = _predecir_intencion(raw_query)
            except Exception:  # pragma: no cover
                pred = None
            if pred and pred[1] >= UMBRAL_INTENCION_ML:
                pred_intencion = pred[0]
                if pred_intencion in ("variacion_ranking", "variacion_total"):
                    var_ref = var_ref or "plan"
                    var_frame = True
                    var_rank = var_rank or pred_intencion == "variacion_ranking"
                    if not var_rank:
                        var_dim = None
                    ruta = "variacion_general"
                    confianza = 0.85
                elif pred_intencion == "alertas":
                    ruta = "alertas_sobregasto"
                    confianza = 0.80
                elif pred_intencion == "tendencia":
                    ruta = "tendencia_semanal" if "semana" in norm_query else "tendencia_mensual"
                    confianza = 0.80

        return {
            "intencion_ml": pred_intencion,
            "ruta": ruta,
            "confianza": confianza,
            "ceco": ceco_id,
            "eco_pdv_directo": eco_pdv_directo,
            "ceco_inexistente": ceco_inexistente,
            "division": div_encontrada,
            "territorio": terr_encontrado,
            "zona": zona_encontrada,
            "region": region_encontrada,
            "contraloria": contra_encontrada,
            "contraloria_nivel": contra_nivel,
            "grupo_cuentas": grupo_encontrado,
            "cuenta": cuenta_encontrada,
            "agrupador_reales": agrupador_encontrado,
            "ml_opciones": ml_amb,
            "ml_incierta": ml_incierta,
            "agrupa1": agrupa1_encontrada,
            "agrupa2": agrupa2_encontrada,
            "agrupa3": agrupa3_encontrada,
            "pdc": pdc_encontrado,
            "servicio_id": servicio_id,
            "dims_solicitadas": dims_solicitadas,
            "agrupar_variacion_por": agrupar_variacion_por,
            "solo_sobregasto_real": es_solo_sobregasto_real,
            "solo_ahorro_real": es_ranking_ahorro,
            "orden_ascendente": es_ranking_ahorro,
            "canal_texto": canal_texto,
            "var_frame": var_frame, "var_ref": var_ref, "var_dir": var_dir,
            "var_dim": var_dim, "var_rank": var_rank,
            "orden_variacion_pct": es_orden_pct,
            "orden_variacion_absoluta": es_top_absoluto,
            "semanas": semanas_info,
            "top_n": _leer_top_n(norm_query),
            "escenarios": ["R26", "P26", "R25"],
            "contexto_aplicado": contexto_aplicado,
            "sugerencias_entidades": sugerencias_entidades,
            "metricas_variacion": metricas_variacion,
        }

    def _parse_semanas(self, norm_query: str) -> dict:
        # Rango explícito: "semana 1 a la 37", "semanas 5 al 20", "entre la semana 10 y la 25"
        m_rango = re.search(r"semanas?\s*(\d{1,2})\s*(?:a|al|-|hasta|y)\s*(?:la|el)?\s*(\d{1,2})", norm_query)
        if m_rango:
            s1, s2 = int(m_rango.group(1)), int(m_rango.group(2))
            return {"tipo": "rango", "inicio": min(s1, s2), "fin": min(max(s1, s2), self.sem_max_plan)}
        # Acumulado por cota: "hasta la semana 30", "hasta semana 30"
        m_hasta = re.search(r"hasta\s*(?:la\s+)?semanas?\s*(\d{1,2})", norm_query)
        if m_hasta:
            return {"tipo": "rango", "inicio": 1, "fin": min(int(m_hasta.group(1)), self.sem_max_plan)}
        # Primeras / últimas N semanas: "primeras 37 semanas", "ultimas 6 semanas"
        m_prim = re.search(r"\bprimeras?\s*(\d{1,2})\s*semanas?\b", norm_query)
        if m_prim:
            return {"tipo": "rango", "inicio": 1, "fin": min(int(m_prim.group(1)), self.sem_max_plan)}
        m_ult = re.search(r"\bultimas?\s*(\d{1,2})\s*semanas?\b", norm_query)
        if m_ult:
            n = int(m_ult.group(1))
            fin = self.sem_max_real
            return {"tipo": "rango", "inicio": max(1, fin - n + 1), "fin": fin}

        m_sems = re.findall(r"semanas?\s*(\d{1,2})", norm_query)
        if len(m_sems) >= 2:
            s_list = sorted([int(s) for s in m_sems])
            return {"tipo": "especificas", "semanas_especificas": s_list, "inicio": s_list[0], "fin": s_list[-1]}

        if len(m_sems) == 1:
            s1 = int(m_sems[0])
            # "acumulado a la semana 39" (vista Acumulado de la presentación) = 1..39
            if "acumulad" in norm_query:
                return {"tipo": "acumulado", "inicio": 1, "fin": s1}
            return {"tipo": "individual", "inicio": s1, "fin": s1}

        m_q = re.search(r"\b(q[1-4]|trimestre\s*[1-4])\b", norm_query)
        if m_q:
            q_num = int(re.search(r"[1-4]", m_q.group(1)).group(0))
            ranges = {1: (1, 13), 2: (14, 26), 3: (27, 39), 4: (40, 53)}
            s_ini, s_fin = ranges[q_num]
            return {"tipo": "trimestre", "inicio": s_ini, "fin": min(s_fin, self.sem_max_plan), "q": f"Q{q_num}"}

        return {"tipo": "acumulado", "inicio": 1, "fin": self.sem_max_real}
