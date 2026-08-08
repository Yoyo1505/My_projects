# -*- coding: utf-8 -*-
"""
rag/server_api.py — Servidor HTTP RAG Red Local (0.0.0.0:8000)

Expone un API HTTP ligero disponible para cualquier equipo en la red local (LAN/Intranet)
para realizar consultas financieras y de código.
"""
from __future__ import annotations

import json
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Agregar la raíz del proyecto al sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.resolve()))

import rag.financial_rag as fin_rag
import rag.query as code_rag


class RAGRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        q = params.get("q", [""])[0]
        mode = params.get("mode", ["financial"])[0]

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if mode == "code":
            res_text = code_rag.ask(q, top_k=5)
            response = {"type": "code", "query": q, "result": res_text}
        else:
            engine = fin_rag.FinancialRAGEngine()
            response = engine.query(q)

        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_len).decode("utf-8")
        data = json.loads(post_body) if post_body else {}

        q = data.get("q", "")
        mode = data.get("mode", "financial")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        if mode == "code":
            res_text = code_rag.ask(q, top_k=5)
            response = {"type": "code", "query": q, "result": res_text}
        else:
            engine = fin_rag.FinancialRAGEngine()
            response = engine.query(q)

        self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))


def run_server(host: str = "0.0.0.0", port: int = 8000):
    server_address = (host, port)
    httpd = HTTPServer(server_address, RAGRequestHandler)
    print(f"[RAG Server] Servidor RAG Red Local escuchando en http://{host}:{port} ...", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[RAG Server] Deteniendo servidor.", flush=True)
        httpd.server_close()


if __name__ == "__main__":
    import sys
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port=port_arg)
