# Plan: Chatbot RAG + Alertas Avanzadas — Dashboard Vista Territorio

Fecha: 2026-07-30. No implementado aún — este documento es la propuesta a validar antes de escribir código. No toca `build_data.py` (regla vigente: datos de semana 31 mal subidos, seguimos en semana 30).

---

## 1. Chatbot RAG

### 1.1 Qué debe responder (confirmado con el usuario)
1. Cifras actuales del dashboard (gasto por región/PDC/cuenta, variaciones vs Plan).
2. Histórico/versiones (usa la nueva pestaña Comparación de Versiones y los snapshots en `aggs_versiones/`).
3. Cierres/Seguimiento Expansión (Excel de Master Cierres, `cierres_expansion.parquet`).

Fuera de alcance por ahora: explicación de metodología/definiciones (se puede añadir después con el mismo mecanismo, es la pieza más barata).

### 1.2 Por qué "RAG" no es realmente lo que este chatbot necesita

Hay que ser preciso con el término porque cambia el diseño. RAG clásico (embeddings + vector store) resuelve *"encontrar el fragmento de texto correcto entre miles de documentos"*. Aquí el problema es distinto: los datos ya están estructurados (parquets/Excel), y la pregunta típica ("¿cuánto gastó la región X?") no se resuelve *buscando texto similar*, se resuelve **generando y ejecutando una consulta** sobre esos datos.

Esto es el patrón **"texto-a-consulta" (NL-to-query) + tool use**, no RAG puro. Es lo que ya usan Claude Code, ChatGPT Code Interpreter, y la mayoría de "chat con tus datos" de BI:

- El LLM recibe el **esquema** de los datos (nombres de columnas, valores categóricos posibles, convenciones como MDP/vs Plan) — no todo el contenido.
- El LLM traduce la pregunta del usuario a una función/consulta concreta (ej. `compute('grupo_cuentas', filtros=[('cat_Direccion_Division','Norte')])`).
- Se ejecuta esa consulta contra los parquets reales (Polars/DuckDB), se devuelve el resultado numérico exacto.
- El LLM redacta la respuesta en español a partir del resultado real — nunca inventa el número.

Para la parte 3 (Cierres/Seguimiento, que sí tiene texto libre real: comentarios del Excel, riesgos.json) sí conviene un RAG textual ligero de verdad (buscar por similitud en comentarios). Es la pieza más chica del sistema.

Conclusión de diseño: **híbrido** — "tool use" sobre datos estructurados (la mayoría de las preguntas) + RAG textual ligero solo sobre comentarios/riesgos (texto libre).

### 1.3 Arquitectura propuesta

```
Usuario escribe pregunta en el dashboard (nueva pestaña "Asistente")
        │
        ▼
┌─────────────────────────────────────────────┐
│  app.py: nueva función chat_asistente()      │
│  - arma el prompt de sistema con:            │
│    · esquema de columnas disponibles         │
│    · lista de funciones invocables (tools)   │
│    · semana vigente (SMR), semanas archivadas│
│  - llama a la API de Claude con tool use     │
└─────────────────────────────────────────────┘
        │ Claude decide qué tool llamar
        ▼
┌─────────────────────────────────────────────┐
│  Capa de "tools" (funciones Python puras,    │
│  YA EXISTEN casi todas — se exponen, no se   │
│  reescriben):                                │
│  - compute(agg, filtros, semanas)            │
│  - cierres_rango(...)                        │
│  - _cuentas_comparativo_semana(sem, ekt)     │
│  - buscar_comentario_cierre(texto) [nuevo,   │
│    RAG textual ligero sobre Comentario del   │
│    Excel de Seguimiento]                     │
└─────────────────────────────────────────────┘
        │ resultado numérico/tabla real
        ▼
Claude redacta respuesta en español citando el número exacto
        │
        ▼
Se muestra en el chat + opcional: botón "ver esta cifra en su pestaña"
```

### 1.4 Motor (recomendación, ya que el usuario pidió que yo defina)

**Claude API (Sonnet) con tool use**, por:
- Ya tienes cuenta/uso de Claude (este mismo asistente); la integración es una llamada HTTP simple con el SDK de Anthropic (`anthropic` en Python).
- Tool use es exactamente el patrón NL-to-query que necesitamos — nativo, no hay que ensamblar un parser propio.
- Costo controlable: cada pregunta es 1-3 llamadas (decidir tool → ejecutar → redactar), con prompts cortos porque el "contexto" es el *esquema*, no los datos completos. Estimado: unos centavos de dólar por pregunta, nada comparable al costo de un LLM local mal afinado dando cifras incorrectas.
- Sin esto habría que evaluar un modelo local (Ollama + Llama/Mistral) — viable para *texto* pero mucho más débil en tool-calling confiable con datos financieros; el riesgo de que "alucine" un número en un dashboard financiero es alto y no vale el ahorro.

Requiere: una API key de Anthropic (`ANTHROPIC_API_KEY`), guardada como variable de entorno o en un `.streamlit/secrets.toml` — nunca hardcodeada en `app.py`.

### 1.5 Lo que SÍ es "RAG" aquí: comentarios/riesgos como texto libre

Para preguntas tipo *"¿qué dice el comentario del proyecto tal?"* o *"¿qué riesgos hay relacionados a X?"*:
- Índice simple con **BM25 o TF-IDF** (librería `rank_bm25`, sin dependencias pesadas) sobre:
  - Columna `Comentario` de `tabla_detalle` (Seguimiento Expansión).
  - Texto de `riesgos.json` (ya usado en `generar_correo_canales.py`).
- No hace falta embeddings/vector DB para este volumen (cientos de filas, no millones) — sería sobre-ingeniería. BM25 sobre texto en español funciona bien a esta escala y no depende de ningún servicio externo.

### 1.6 Plan de implementación (fases)

| Fase | Qué se entrega | Depende de |
|---|---|---|
| 1 | `asistente.py` nuevo: definición de tools (envolviendo funciones ya existentes de `app.py`/`build_data.py` sin duplicarlas), prompt de sistema con el esquema | Ninguna — se puede empezar ya |
| 2 | Integración a `app.py`: pestaña "Asistente" con `st.chat_message`/`st.chat_input`, guarda historial en `st.session_state` | Fase 1 |
| 3 | RAG textual (BM25) sobre comentarios/riesgos como tool adicional | Fase 1 |
| 4 | Pulido: límite de preguntas por sesión (costo), manejo de "no sé responder eso" | Fases 1-3 |

Nada de esto requiere tocar `build_data.py` ni correr el build — son archivos/funciones nuevos que leen lo que ya existe en `aggs/`.

---

## 2. Alertas Avanzadas

### 2.1 Tipos confirmados
1. **Variaciones anómalas** vs Plan o vs histórico (ej. una cuenta se desvía mucho más de lo usual).
2. **Discrepancias entre versiones/snapshots** (el caso ya validado hoy: SEMANA_EKT=29 vale distinto en r29 vs r30 → 3.29 MDP de diferencia).
3. **Seguimiento de Cierres**: proyectos atrasados, o divergencia grande entre Plan=1 (Versión Plan) y Plan=0 (Versión Semana Actual).

### 2.2 Motor de detección (sin LLM — reglas + estadística simple)

Las alertas NO necesitan IA generativa para *detectar*; sí puede usarse el LLM después para *redactar* el resumen ejecutivo del hallazgo (opcional, fase tardía). Detección propuesta:

- **Variación anómala**: para cada (cat_Grupo_de_Cuentas, cat_Cuentas) o PDC, calcular `Vs_Plan_Pct` y compararlo contra su propio histórico de semanas anteriores (media + desviación estándar simple, o un umbral fijo pactado con el usuario, ej. "±25% vs Plan y monto > 5 MDP" para evitar ruido de cuentas chicas).
- **Discrepancia entre versiones**: reusa directamente `_cuentas_comparativo_semana(sem, semana_ekt)` de la nueva pestaña — recorre todas las SEMANA_EKT ya cerradas entre dos snapshots consecutivos y marca las que cambiaron más de un umbral (monto y/o %).
- **Cierres atrasados/divergencia Plan**: sobre `tabla_detalle` de Seguimiento Expansión, comparar `Sem_Actual` vs `Plan` por proyecto; señalar los que llevan N semanas sin avanzar o con brecha grande.

Todas son funciones Python puras sobre datos ya existentes — no requieren el LLM para funcionar, lo que las hace confiables y baratas de correr en cada build.

### 2.3 Entrega (confirmado: ambos canales)

- **Pestaña "Alertas" en el dashboard**: tabla con severidad (alta/media/baja), descripción, cifra, y enlace/filtro directo a la pestaña relevante. Se recalcula igual que el resto del dashboard (cacheado con `@st.cache_data`).
- **Correo semanal**: nueva sección en `generar_correo_canales.py` (o script hermano) que inserta las alertas de severidad alta como bloque destacado arriba del correo existente — reusa el mismo HTML/estilo (`COLOR_ROJO`/`COLOR_VERDE`) que ya tiene ese script.

### 2.4 Dónde vive el código

- `alertas.py` (nuevo, junto a `app.py`): funciones de detección puras + una función `generar_alertas() -> pd.DataFrame` que consolida las 3 categorías.
- `app.py`: nueva pestaña "Alertas" que llama a `generar_alertas()` y la muestra en tabla/tarjetas con el estilo `_KPI_CSS`/semáforo ya existente en el proyecto.
- `generar_correo_canales.py`: import de `alertas.generar_alertas()`, inserta bloque si hay alertas de severidad alta.

No toca `build_data.py`: las alertas se calculan al vuelo sobre los parquets que ya existen, igual que la pestaña de Comparación de Versiones.

### 2.5 Plan de implementación (fases)

| Fase | Qué se entrega |
|---|---|
| 1 | `alertas.py`: detección de discrepancias entre versiones (ya tenemos los datos y la función base de hoy) — la más rápida de entregar |
| 2 | Detección de variaciones anómalas vs Plan/histórico (requiere pactar umbrales contigo) |
| 3 | Detección de atrasos en Cierres (Plan vs Sem_Actual) |
| 4 | Pestaña "Alertas" en `app.py` |
| 5 | Integración al correo semanal |

---

## 3. Preguntas abiertas antes de empezar a construir

1. **Umbrales de "anómalo"**: ¿qué % de desviación vs Plan y qué monto mínimo (para no alertar cuentas chicas) te parecen razonables? Necesito un número concreto para la Fase 2 de alertas.
2. **Umbral de discrepancia entre versiones**: ¿qué monto/% de cambio en una semana ya cerrada amerita alerta (ej. >1 MDP o >2%)?
3. **API key de Anthropic**: ¿ya tienes una para este proyecto, o hay que gestionar el alta? Sin esto no puedo avanzar la Fase 1 del chatbot.
4. **Prioridad**: ¿empezamos por Alertas (más rápido, sin dependencias externas) o por el Chatbot (requiere la API key primero)?
