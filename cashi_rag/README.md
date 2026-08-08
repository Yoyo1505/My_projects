# Cashi — Sistema RAG financiero

**Cashi** es un sistema de **RAG (Retrieval-Augmented Generation)** orientado a asistencia financiera: indexación local de contexto, consulta semántica y respuestas ancladas a documentos/datos del dominio, sin depender de hardcode de cifras en la capa de presentación.

## Qué resuelve

- Recuperación de contexto financiero relevante (índices locales)
- Consulta vía API / scripts (`rag/query.py`, `rag/server_api.py`)
- Construcción de índices rápidos (`rag/build_fast_json.py`, `rag/indexer.py`)
- Integración con flujos de dashboard y agregados precomputados

## Stack

- Python  
- Motor RAG local (`rag/financial_rag.py`)  
- Streamlit / HTML asistentes (`rag_asistente_*.html`)  
- Polars / DuckDB / agregados en `aggs/` (datos pesados **fuera de git**)

## Estructura

```
cashi_rag/
├── rag/                    # Núcleo RAG
│   ├── financial_rag.py
│   ├── indexer.py
│   ├── query.py
│   ├── server_api.py
│   └── build_fast_json.py
├── app.py                  # UI asociada
├── app/services/           # Cálculos y motor de datos
├── aggs/                   # Metadatos / índices (parcial)
├── docs/
├── RAG_GUIDE.md
├── ARCHITECTURE.md
├── requirements.txt
├── .env.ejemplo
└── DATA.md                 # Cómo montar secretos y datos locales
```

## Inicio rápido

```powershell
cd cashi_rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.ejemplo .env
# Coloca índices/aggs locales según DATA.md
streamlit run app.py --server.port 8502
```

## Documentación

| Archivo | Contenido |
|---------|-----------|
| [RAG_GUIDE.md](RAG_GUIDE.md) | Guía del asistente RAG |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes del sistema |
| [SECURITY.md](SECURITY.md) | Operación local-first y buenas prácticas |
| [DATA.md](DATA.md) | Secretos y datasets fuera del repo |
| [INSTALLATION.md](INSTALLATION.md) | Instalación |

## Datos y secretos (fuera del repositorio)

No se versionan:

- `.env` (SQL / credenciales)
- `usuarios.json`
- Parquets y catálogos grandes
- Zips `*_App_y_Aggs`

Ver [DATA.md](DATA.md).
