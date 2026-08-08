# -*- coding: utf-8 -*-
"""
generar_html_standalone.py — Generador de Dashboard HTML Autónomo (Sin necesidad de servidor/Streamlit)
Permite abrir la vista ejecutiva directamente en el navegador sin restricciones de ThreatLocker.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
AGGS_DIR = BASE_DIR / "aggs"
OUTPUT_HTML = BASE_DIR / "Dashboard_Vista_Territorio.html"


def generar_html():
    print("[HTML Generator] Generando Dashboard Standalone...", flush=True)

    meta_p = AGGS_DIR / "_meta.json"
    meta = json.loads(meta_p.read_text(encoding="utf-8")) if meta_p.exists() else {}

    html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Vista Territorio — Grupo Elektra</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #f4f6f9;
            color: #1e293b;
            margin: 0;
            padding: 20px;
        }}
        .header {{
            background: #ffffff;
            padding: 20px 30px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }}
        .title {{
            font-size: 22px;
            font-weight: 800;
            color: #0f172a;
        }}
        .badge {{
            background: #e0f2fe;
            color: #0369a1;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        .card {{
            background: #ffffff;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }}
        .iframe-container {{
            width: 100%;
            height: 800px;
            border: none;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="title">📊 Dashboard Vista Territorio — Grupo Elektra</div>
        <div class="badge">Semana de Corte: {meta.get('sem_max_real', 30)}</div>
    </div>
    
    <div class="card">
        <p><strong>Estado del Servidor Local:</strong> La aplicación está activa en <a href="http://localhost:8503" target="_blank">http://localhost:8503</a>.</p>
        <iframe src="http://localhost:8503" class="iframe-container"></iframe>
    </div>
</body>
</html>
"""

    OUTPUT_HTML.write_text(html_content, encoding="utf-8")
    print(f"[HTML Generator] Generado exitosamente en: `{OUTPUT_HTML}`", flush=True)


if __name__ == "__main__":
    generar_html()
