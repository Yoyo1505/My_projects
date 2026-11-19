# -*- coding: utf-8 -*-
"""
rag/server_api.py — Servidor HTTP RAG (127.0.0.1:8507 por defecto)

Expone un API HTTP ligero disponible para cualquier equipo en la red local (LAN/Intranet)
para realizar consultas financieras y de código, y sirve `rag/cashi_web/index.html` —
una interfaz de chat standalone (HTML/CSS/JS puro, sin Streamlit) para no depender
del rerun completo del script gigante de `codigo/app.py` solo para hablar con Cashi.

Uso:
    python rag/server_api.py [puerto]
    -> abrir http://localhost:8507/ en esta máquina
    -> abrir http://<IP de esta máquina>:8507/ desde otra máquina en la misma red
       (requiere CASHI_HOST=0.0.0.0; usa también CASHI_API_TOKEN)
"""
from __future__ import annotations

import hmac
import json
import os
import sys
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Agregar la raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import rag.financial_rag as fin_rag
import rag.query as code_rag

_ENGINE: fin_rag.UnifiedCashiRAGEngine | None = None
_WEB_DIR = Path(__file__).parent / "cashi_web"
_INDEX_HTML = _WEB_DIR / "index.html"
PUERTO_DEFAULT = 8507
# Seguridad: por defecto solo localhost; exponer en LAN requiere CASHI_HOST=0.0.0.0 y,
# de preferencia, CASHI_API_TOKEN (cabecera Authorization: Bearer <token> en /api y POST).
HOST_DEFAULT = os.environ.get("CASHI_HOST", "127.0.0.1")
API_TOKEN = os.environ.get("CASHI_API_TOKEN", "")
CORS_ORIGIN = os.environ.get("CASHI_CORS_ORIGIN", "")  # vacío = sin CORS (mismo origen)
MAX_Q_CHARS = 2000


def _get_engine() -> fin_rag.UnifiedCashiRAGEngine:
    """Instancia única del motor Cashi, reutilizada entre requests HTTP."""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = fin_rag.UnifiedCashiRAGEngine()
    return _ENGINE


class RAGRequestHandler(BaseHTTPRequestHandler):
    def _responder_json(self, response: dict, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if CORS_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
        self.end_headers()
        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    def _responder_html(self):
        try:
            contenido = _INDEX_HTML.read_bytes()
        except OSError:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"No se encontro rag/cashi_web/index.html")
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(contenido)

    def _autorizado(self) -> bool:
        if not API_TOKEN:
            return True
        enviado = self.headers.get("Authorization", "").removeprefix("Bearer ").strip()
        if hmac.compare_digest(enviado, API_TOKEN):
            return True
        self._responder_json({"error": "unauthorized"}, 401)
        return False

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._responder_json({
                "status": "ok",
                "engine": "cashi-rag",
                "demo_data": (Path(__file__).parent.parent / "aggs" / "_consolidado.parquet").exists(),
            })
            return

        # Sirve la interfaz web standalone en / (o /index.html) cuando no
        # viene una consulta (?q=...) — así http://<host>:8507/ abre el
        # chat directo en el navegador, y http://<host>:8507/?q=... (o
        # /api) sigue funcionando igual que antes para consumo programático.
        if "q" not in params and parsed.path in ("/", "/index.html", "/cashi"):
            self._responder_html()
            return

        if not self._autorizado():
            return
        q = params.get("q", [""])[0][:MAX_Q_CHARS]
        mode = params.get("mode", ["financial"])[0]
        if mode not in ("financial", "code"):
            self._responder_json({"error": "mode must be 'financial' or 'code'"}, 400)
            return

        if mode == "code":
            res_text = code_rag.ask(q, top_k=5)
            response = {"type": "code", "query": q, "result": res_text}
        else:
            response = _get_engine().process_query(q)

        self._responder_json(response)

    def do_POST(self):
        if not self._autorizado():
            return
        content_len = int(self.headers.get("Content-Length", 0))
        if content_len <= 0:
            self._responder_json({"error": "JSON body is required"}, 400)
            return
        if content_len > 1_000_000:
            self._responder_json({"error": "Request body exceeds 1 MB"}, 413)
            return
        try:
            post_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(post_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._responder_json({"error": "Invalid JSON"}, 400)
            return

        q = data.get("q", "") if isinstance(data, dict) else ""
        mode = data.get("mode", "financial") if isinstance(data, dict) else "financial"
        contexto_previo = data.get("contexto_previo") if isinstance(data, dict) else None
        if not isinstance(q, str) or not q.strip() or len(q) > MAX_Q_CHARS:
            self._responder_json({"error": f"q must be a non-empty string (max {MAX_Q_CHARS} chars)"}, 400)
            return
        if mode not in ("financial", "code"):
            self._responder_json({"error": "mode must be 'financial' or 'code'"}, 400)
            return

        started = time.perf_counter()
        if mode == "code":
            res_text = code_rag.ask(q, top_k=5)
            response = {"type": "code", "query": q, "result": res_text}
        else:
            response = _get_engine().process_query(q, contexto_previo=contexto_previo)
        response["latency_ms"] = round((time.perf_counter() - started) * 1000, 2)
        self._responder_json(response)

    def do_OPTIONS(self):
        # Preflight CORS — la página puede abrirse desde file:// o un puerto
        # distinto al del servidor; sin esto el navegador bloquea el fetch.
        self.send_response(204)
        if CORS_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", CORS_ORIGIN)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silencia el log default de BaseHTTPRequestHandler a stderr por cada request


def run_server(host: str = HOST_DEFAULT, port: int = PUERTO_DEFAULT):
    server_address = (host, port)
    httpd = ThreadingHTTPServer(server_address, RAGRequestHandler)
    host_local = "localhost" if host == "0.0.0.0" else host
    print(f"[RAG Server] Escuchando en http://{host}:{port} ...", flush=True)
    print(f"[Cashi Web] Chat standalone (esta máquina): http://{host_local}:{port}/", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[RAG Server] Deteniendo servidor.", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    import sys
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else PUERTO_DEFAULT
    run_server(port=port_arg)
