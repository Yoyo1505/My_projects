# -*- coding: utf-8 -*-
"""Crea/regenera la plantilla 'Riesgos y Oportunidades.docx' (Word mínimo
válido, sin dependencias). Planeación la edita en Word normal; build_data.py
la lee y la pestaña Riesgos & Oport. muestra su contenido.

Formato esperado dentro del Word:
  - Un párrafo 'RIESGOS' (solo esa palabra) inicia la sección de riesgos.
  - Un párrafo 'OPORTUNIDADES' inicia la de oportunidades.
  - Todo párrafo debajo de cada título es una viñeta de esa sección.
Correr:  python _crear_word_riesgos.py
"""
import zipfile
from pathlib import Path

DOCX = Path(__file__).parent / "Riesgos y Oportunidades.docx"

PARRAFOS = [
    "RIESGOS",
    "Escribe aquí cada riesgo en su propio párrafo (uno por renglón).",
    "Ejemplo: La división Norte supera su plan de gasto por tercera semana consecutiva.",
    "OPORTUNIDADES",
    "Escribe aquí cada oportunidad en su propio párrafo.",
    "Ejemplo: El ahorro en Flete Neto permite reasignar presupuesto a Publicidad.",
]

def _p(texto):
    t = (texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return f'<w:p><w:r><w:t xml:space="preserve">{t}</w:t></w:r></w:p>'

DOCUMENT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:body>' + "".join(_p(t) for t in PARRAFOS) + '</w:body></w:document>'
)

CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType='
    '"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)

RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
    '2006/relationships/officeDocument" Target="word/document.xml"/>'
    '</Relationships>'
)

if __name__ == "__main__":
    if DOCX.exists():
        print(f"Ya existe {DOCX.name} — no lo sobrescribo (bórralo si quieres la plantilla limpia).")
    else:
        with zipfile.ZipFile(DOCX, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", CONTENT_TYPES)
            z.writestr("_rels/.rels", RELS)
            z.writestr("word/document.xml", DOCUMENT)
        print(f"Creado {DOCX}")
