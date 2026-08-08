# Guía del Sistema RAG Local (Retrieval-Augmented Generation)

## Descripción
El sistema RAG local permite realizar consultas de lenguaje natural sobre el código fuente, la documentación técnica, los manuales de usuario, las reglas de negocio y los esquemas de datos del proyecto **Dashboard Vista Territorio**.

Funciona 100% de manera local, utilizando indexación por fragmentos semánticos y recuperación híbrida basada en **BM25 / TF-IDF** con citación exacta de archivos y líneas.

## Estructura del RAG
- `rag/indexer.py`: Extrae fragmentos de archivos `.md` y `.py`, limpia tokens en español, calcula frecuencias de términos y genera `rag/index_store.json`.
- `rag/query.py`: Recibe una consulta, aplica ponderación BM25/IDF y devuelve los mejores fragmentos ordenados con enlaces markdown formateados.

## Cómo Usar el RAG en la Terminal

```powershell
# Reconstruir el índice
python rag/indexer.py

# Consultar el RAG desde consola
python rag/query.py "formula de variaciones vs plan 2026"
```

## Ejemplo de Respuesta del RAG
```markdown
### Resultados RAG para: 'formula de variaciones vs plan 2026'

1. [docs/auditoria/reglas_negocio.md](file:///docs/auditoria/reglas_negocio.md#L22-L33) — Variaciones y Porcentajes (Score: 1.2758)
- `vs Plan (Absoluta)` = `Real 2026 - Plan 2026`
- `vs Plan (%)` = `(vs Plan Absoluta / |Plan 2026|) * 100`
```
