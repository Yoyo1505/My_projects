# Security Notes

Review focused on Forward Deployed / Applied AI Engineer concerns: secrets, exposed services, LLM/RAG input handling, and data hygiene. Last review: 2026-11-19.

## Findings and status
| # | Finding | Severity | Status |
|---|---|---|---|
| 1 | `Cashi RAG/rag/server_api.py` bound to `0.0.0.0` with `Access-Control-Allow-Origin: *` and no auth, exposing the RAG API to the whole LAN and any web page | High | Fixed: binds to `127.0.0.1`; LAN needs `CASHI_HOST`; optional bearer token `CASHI_API_TOKEN`; CORS only if `CASHI_CORS_ORIGIN` is set |
| 2 | Unbounded query length and unvalidated `mode` on the GET path (resource abuse) | Medium | Fixed: 2000-char cap, `mode` validated on GET and POST |
| 3 | Plain-text API key file in a local working copy of the LLM agent folder (`ollama api key.txt`) | High if committed | Not tracked in this repo (checked tracked files and history); `.gitignore` now blocks `*key*.txt` and `.env*`. Rotate the key if it was ever shared |
| 4 | LLM/RAG output rendered in the web UI | Medium | Checked: every field goes through `escapeHtml` before `innerHTML` |
| 5 | Streamlit pages use `unsafe_allow_html=True` | Low | Content is app-generated from local data; do not feed it untrusted text |
| 6 | Prompt injection via retrieved documents | Medium | Inherent to RAG; the support agent keeps authorization checks outside the LLM (`test_authorization.py`). Treat retrieved text as data |
| 7 | Downloaded datasets cached in the repo tree | Low | Git-ignored (`data/`) |

## Practices
- Secrets only through environment variables; never commit `.env` or key files.
- Pin and review dependencies (`pip-audit`) before deploying for a client.
- Remaining work: per-user auth and rate limiting on the RAG server, and structured request logging with PII redaction.
