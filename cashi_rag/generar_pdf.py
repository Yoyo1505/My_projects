#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Genera 2 PDFs estilizados para el Dashboard Vista Territorio:
  Dashboard_Documentacion.pdf   -> técnico (arquitectura, build_data.py, app.py)
  Dashboard_Manual_de_Uso.pdf   -> operativo (pestañas, filtros, troubleshooting)

Uso: python generar_pdf.py
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    HRFlowable
)
from reportlab.lib import colors
from datetime import datetime
from pathlib import Path

# ==================== PALETA (idéntica a la del dashboard) ====================
COLOR_PRIMARY = colors.HexColor("#A93226")      # Rojo Elektra
COLOR_PRIMARY_DARK = colors.HexColor("#7B241C")
COLOR_SECONDARY = colors.HexColor("#2E86C1")    # Azul
COLOR_TEXT = colors.HexColor("#2C3E50")
COLOR_MUTED = colors.HexColor("#7F8C8D")
COLOR_LIGHT_BG = colors.HexColor("#F4F6F6")
COLOR_CODE_BG = colors.HexColor("#1B2631")
COLOR_CODE_TEXT = colors.HexColor("#D5F5E3")
COLOR_WARN = colors.HexColor("#B9770E")

VERSION = "3.0"
AUTOR = "Karlo De Jesus Juarez Ramirez"
FECHA_GEN = datetime.now()
BASE = Path(__file__).parent

styles = getSampleStyleSheet()
title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=30, textColor=colors.white,
    spaceAfter=6, alignment=TA_CENTER, fontName='Helvetica-Bold', leading=34)
subtitle_style = ParagraphStyle('ST', parent=styles['Normal'], fontSize=13, textColor=colors.white,
    spaceAfter=10, alignment=TA_CENTER, fontName='Helvetica')
tag_style = ParagraphStyle('TAG', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor("#FADBD8"),
    alignment=TA_CENTER, fontName='Helvetica-Oblique')
h2_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=16, textColor=COLOR_PRIMARY,
    spaceAfter=10, spaceBefore=16, fontName='Helvetica-Bold')
h3_style = ParagraphStyle('H3', parent=styles['Heading3'], fontSize=12.5, textColor=COLOR_SECONDARY,
    spaceAfter=8, spaceBefore=12, fontName='Helvetica-Bold')
normal_style = ParagraphStyle('N', parent=styles['Normal'], fontSize=10, textColor=COLOR_TEXT,
    spaceAfter=7, alignment=TA_JUSTIFY, fontName='Helvetica', leading=14.5)
bullet_style = ParagraphStyle('B', parent=normal_style, leftIndent=12, spaceAfter=5, alignment=TA_LEFT)
toc_h_style = ParagraphStyle('TH', parent=normal_style, fontSize=11.5, textColor=COLOR_PRIMARY,
    fontName='Helvetica-Bold', alignment=TA_LEFT, spaceBefore=10, spaceAfter=4)
toc_item_style = ParagraphStyle('TI', parent=normal_style, fontSize=10, textColor=COLOR_TEXT,
    alignment=TA_LEFT, leftIndent=16, spaceAfter=3)
callout_title_style = ParagraphStyle('CT', parent=normal_style, fontName='Helvetica-Bold',
    textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT, spaceAfter=3)
callout_style = ParagraphStyle('C', parent=normal_style, alignment=TA_LEFT, spaceAfter=0)
code_line_style = ParagraphStyle('CL', parent=styles['Normal'], fontSize=8.5, textColor=COLOR_CODE_TEXT,
    fontName='Courier', leading=12)
faq_q_style = ParagraphStyle('FQ', parent=normal_style, fontName='Helvetica-Bold',
    textColor=COLOR_PRIMARY_DARK, alignment=TA_LEFT, spaceAfter=2)
faq_a_style = ParagraphStyle('FA', parent=normal_style, alignment=TA_LEFT, spaceAfter=10, textColor=COLOR_TEXT)
cell_style = ParagraphStyle('CE', parent=styles['Normal'], fontSize=9, textColor=COLOR_TEXT,
    fontName='Helvetica', leading=12, alignment=TA_LEFT)
cell_header_style = ParagraphStyle('CH', parent=cell_style, textColor=colors.white, fontName='Helvetica-Bold')


def code_block(lines):
    rows = [[Paragraph(l.replace(' ', '&nbsp;'), code_line_style)] for l in lines]
    t = Table(rows, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_CODE_BG),
        ('LEFTPADDING', (0, 0), (-1, -1), 12), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (0, 0), 10), ('BOTTOMPADDING', (-1, -1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -2), 3),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    return t


def callout(title, text, border_color=COLOR_SECONDARY, bg=COLOR_LIGHT_BG):
    inner = Table([[Paragraph(f"<b>{title}</b>", callout_title_style)], [Paragraph(text, callout_style)]],
                  colWidths=[6.15 * inch])
    inner.setStyle(TableStyle([('LEFTPADDING', (0, 0), (-1, -1), 0), ('TOPPADDING', (0, 0), (-1, -1), 0),
                               ('BOTTOMPADDING', (0, 0), (-1, 0), 3)]))
    wrapper = Table([[inner]], colWidths=[6.5 * inch])
    wrapper.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), bg), ('LINEBEFORE', (0, 0), (0, -1), 3, border_color),
        ('LEFTPADDING', (0, 0), (-1, -1), 14), ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 10), ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return wrapper


def styled_table(data, col_widths, header_bg=COLOR_PRIMARY, small=False):
    fsize = 8.5 if small else 9
    hstyle = ParagraphStyle('CHx', parent=cell_header_style, fontSize=fsize)
    bstyle = ParagraphStyle('CBx', parent=cell_style, fontSize=fsize)
    wrapped = [[Paragraph(str(v).replace("\n", "<br/>"), hstyle if r == 0 else bstyle) for v in row]
               for r, row in enumerate(data)]
    t = Table(wrapped, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor("#D5D8DC")),
        ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    return t


def portada(titulo_doc, subtitulo_doc, resumen):
    cover_inner = Table(
        [[Spacer(1, 0.4 * inch)],
         [Paragraph("GRUPO ELEKTRA · PLANEACION FINANCIERA", tag_style)],
         [Spacer(1, 0.35 * inch)],
         [Paragraph("Dashboard Vista Territorio", title_style)],
         [Spacer(1, 0.12 * inch)],
         [Paragraph(subtitulo_doc, subtitle_style)],
         [Spacer(1, 0.5 * inch)]], colWidths=[7 * inch])
    cover_inner.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, -1), COLOR_PRIMARY),
                                     ('ALIGN', (0, 0), (-1, -1), 'CENTER')]))
    info = [
        ["Fecha de generacion", FECHA_GEN.strftime("%d/%m/%Y")],
        ["Version del documento", VERSION],
        ["Componentes cubiertos", "build_data.py  ·  app.py (Streamlit)"],
        ["Autor / Mantenimiento", AUTOR],
    ]
    info_table = Table(info, colWidths=[2.3 * inch, 4.2 * inch])
    info_table.setStyle(TableStyle([
        ('FONT', (0, 0), (0, -1), 'Helvetica-Bold', 10), ('FONT', (1, 0), (1, -1), 'Helvetica', 10),
        ('TEXTCOLOR', (0, 0), (0, -1), COLOR_PRIMARY), ('TEXTCOLOR', (1, 0), (1, -1), COLOR_TEXT),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, COLOR_LIGHT_BG]),
        ('GRID', (0, 0), (-1, -1), 0.75, colors.HexColor("#D5D8DC")),
        ('TOPPADDING', (0, 0), (-1, -1), 9), ('BOTTOMPADDING', (0, 0), (-1, -1), 9),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    return [Spacer(1, 1.6 * inch), cover_inner, Spacer(1, 0.5 * inch), info_table, Spacer(1, 0.5 * inch),
            Paragraph(resumen, ParagraphStyle('CI', parent=normal_style, alignment=TA_CENTER,
                                              textColor=COLOR_MUTED, fontSize=9.5)),
            PageBreak()]


def make_footer(titulo_corto):
    def draw(canvas, doc):
        canvas.saveState()
        page_w, page_h = letter
        canvas.setStrokeColor(colors.HexColor("#D5D8DC"))
        canvas.setLineWidth(0.75)
        canvas.line(0.75 * inch, 0.6 * inch, page_w - 0.75 * inch, 0.6 * inch)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(COLOR_MUTED)
        canvas.drawString(0.75 * inch, 0.45 * inch, "Dashboard Vista Territorio · Grupo Elektra")
        canvas.drawRightString(page_w - 0.75 * inch, 0.45 * inch, f"Pagina {doc.page}")
        if doc.page > 1:
            canvas.setFillColor(COLOR_PRIMARY)
            canvas.rect(0, page_h - 0.35 * inch, page_w, 0.35 * inch, stroke=0, fill=1)
            canvas.setFont("Helvetica-Bold", 9)
            canvas.setFillColor(colors.white)
            canvas.drawString(0.75 * inch, page_h - 0.24 * inch, "DASHBOARD VISTA TERRITORIO")
            canvas.drawRightString(page_w - 0.75 * inch, page_h - 0.24 * inch, f"{titulo_corto} · v{VERSION}")
        canvas.restoreState()
    return draw


def build_pdf(filename, titulo_corto, content):
    out = BASE / filename
    doc = SimpleDocTemplate(str(out), pagesize=letter, rightMargin=0.75 * inch, leftMargin=0.75 * inch,
                            topMargin=0.9 * inch, bottomMargin=0.85 * inch,
                            title=f"Dashboard Vista Territorio - {titulo_corto}", author=AUTOR)
    doc.build(content, onFirstPage=make_footer(titulo_corto), onLaterPages=make_footer(titulo_corto))
    print(f"PDF creado: {out}")


# ==================================================================
# ============================ DOCUMENTO 1: DOCUMENTACION TECNICA ===
# ==================================================================
doc1 = portada(
    "Documentacion Tecnica",
    "Documentacion Tecnica",
    "Este documento describe la arquitectura del Dashboard Vista Territorio: como se "
    "generan los datos, que hace cada script y como estan organizados los archivos. "
    "Dirigido a quien da mantenimiento al pipeline (build_data.py / app.py).",
)

doc1.append(Paragraph("Tabla de Contenidos", h2_style))
doc1.append(HRFlowable(width="100%", thickness=1.2, color=COLOR_PRIMARY, spaceAfter=10))
for t in ["1. Overview del sistema", "2. Script build_data.py", "3. Script app.py",
          "4. Rendimiento y carga diferida", "5. Flujo de actualizacion semanal",
          "6. Configuracion minima", "7. Estructura de carpetas"]:
    doc1.append(Paragraph(t, toc_item_style))
doc1.append(PageBreak())

doc1.append(Paragraph("1. Overview del Sistema", h2_style))
doc1.append(Paragraph(
    "El Dashboard Vista Territorio compara cuatro medidas (Real 2025, Real 2026, Plan 2026 "
    "y Nvo Plan 2026) a lo largo de division, territorio, zona, region, PDC y cuenta contable. "
    "Trabaja en dos etapas encadenadas:", normal_style))
doc1.append(styled_table(
    [["Componente", "Funcion", "Duracion tipica"],
     ["build_data.py", "Lee catalogos y parquets fuente, calcula agregados y los guarda en aggs/.",
      "10-18 min (--rebuild)\n5-10 min (--aggs-only)"],
     ["app.py", "Interfaz Streamlit: lee los parquets de aggs/ y dibuja las pestanas.", "Tiempo real"]],
    [1.15 * inch, 3.75 * inch, 1.6 * inch]))
doc1.append(Spacer(1, 0.1 * inch))
doc1.append(callout("Como pensarlo",
    "build_data.py es la 'cocina' (procesa los datos pesados una sola vez); app.py es el "
    "'comedor' (sirve esos datos ya listos). Por eso no hay que reprocesar todo cada vez que "
    "alguien abre el dashboard."))

doc1.append(Paragraph("2. Script build_data.py", h3_style))
doc1.append(Paragraph("<b>Fuentes de entrada</b>", normal_style))
for item in [
    "Parquets semanales: r25_semNN.parquet, r26_semNN.parquet, p26_semNN.parquet (extraidos de SQL Server via extraer_sql.py)",
    "nvo_plan_2026.parquet: plan alternativo, calendario de 53 semanas",
    "Catalogos Excel <b>dentro de la carpeta del dashboard</b> (no en la raiz de Downloads): "
    "'Catalogo grupo cuentas.xlsx' y 'Catalogo de estructura.xlsx'",
]:
    doc1.append(Paragraph(f"•  {item}", bullet_style))
doc1.append(callout(
    "Los catalogos viven junto al script, no en Downloads",
    "CAT_CUENTAS y CAT_ESTRUCT apuntan a BASE (la carpeta del propio build_data.py). Si "
    "alguien coloca una copia corregida del catalogo en la raiz de Downloads en vez de aqui, "
    "el build seguira leyendo la version vieja sin avisar.",
    border_color=COLOR_WARN, bg=colors.HexColor("#FEF5E7")))

doc1.append(Paragraph("<b>Aggs que genera (carpeta aggs/)</b>", normal_style))
doc1.append(Paragraph(
    "Mas de 25 parquets: agregados por dimension (division, territorio, zona, region, pdc, "
    "grupo_cuentas, cuentas...), el consolidado intermedio (_consolidado.parquet), analisis "
    "especiales (cierres, forecast_ceco, pdc_pospre) y metadatos de control (_meta.json, "
    "orden_gpo.json, responsables_gpo.json, riesgos.json).", normal_style))

doc1.append(Paragraph("<b>pdc_pospre.parquet — agg dedicado al drill-down territorial</b>", normal_style))
doc1.append(Paragraph(
    "Cruza Grupo de Cuentas, Cuenta, Division/Territorio/Zona/Region, PosPre y PDC para las "
    "2 vistas de la pestana Detalle Cuenta. cat_PosPre y cat_Denom_PosPre se concatenan en una "
    "sola columna (cat_PosPre_Full) antes del agrupado: son casi 1:1, tratarlos como 2 niveles "
    "de arbol solo multiplicaba filas sin aportar jerarquia real. Aun asi el agg resulta grande "
    "(~17.7M filas) porque Territorio/Zona/Region en el catalogo NO son una jerarquia limpia "
    "(un mismo Territorio aparece bajo ~20-25 combinaciones de Zona/Region) y se cruza con PDC "
    "(4,115 valores). Ver seccion 4 para como se resuelve esto en app.py.", normal_style))

doc1.append(Paragraph("<b>Como se ejecuta</b>", normal_style))
doc1.append(code_block([
    "python build_data.py --rebuild     # Reconstruir _consolidado desde los parquets fuente",
    "python build_data.py               # Reusa _consolidado.parquet si sigue vigente",
    "python build_data.py --aggs-only   # Recalcula solo aggs/, sin releer fuentes ni catalogos",
    "python build_data.py --semana 30   # Fuerza una semana de corte especifica",
]))
doc1.append(callout("Cuando usar --rebuild",
    "Usa --rebuild si cambiaron los catalogos Excel o los parquets fuente (r25/r26/p26_semNN). "
    "Para regenerar solo un agg puntual sin tocar el consolidado, --aggs-only es mucho mas rapido.",
    border_color=COLOR_WARN, bg=colors.HexColor("#FEF5E7")))

doc1.append(Paragraph("<b>Riesgos y Oportunidades (comentarios de Planeacion)</b>", normal_style))
doc1.append(Paragraph(
    "build_riesgos() lee 'Riesgos y Oportunidades.docx' (en la carpeta del dashboard) y genera "
    "aggs/riesgos.json. Formato del Word: un parrafo 'RIESGOS' abre la seccion de variaciones "
    "negativas, 'OPORTUNIDADES' abre la de positivas; cada parrafo debajo es una vineta. Se "
    "puede regenerar solo, sin correr el build completo:", normal_style))
doc1.append(code_block([
    'python -c "import build_data; build_data.build_riesgos()"',
]))

doc1.append(Paragraph("3. Script app.py", h3_style))
doc1.append(Paragraph(
    "Interfaz Streamlit que lee los parquets de aggs/ y dibuja las pestanas, sin tocar las "
    "fuentes originales. Login por usuario/contrasena (usuarios.json).", normal_style))
doc1.append(Paragraph("<b>Pestanas actuales</b>", normal_style))
doc1.append(Paragraph(
    "Resumen, Div / Terr, Detalle Cuenta, Detalle PDC, PDC &amp; Calor, Forecast CECO, "
    "Sem / Mes, Cierres, Trimestres, Riesgos &amp; Oport., Comentarios.", normal_style))
doc1.append(callout("La pestana 'Movimiento' se retiro",
    "Se elimino de la navegacion y del codigo el 21/07/2026 (a peticion del usuario). "
    "movimiento.parquet se sigue generando en el build por si se necesita para analisis fuera "
    "del dashboard, pero ya no se carga ni se muestra en app.py."))

doc1.append(Paragraph("4. Rendimiento y Carga Diferida", h3_style))
doc1.append(Paragraph(
    "Dos optimizaciones clave para que la app cargue rapido incluso con aggs grandes "
    "(conciliacion 758MB, pdc 193MB, pdc_pospre 331MB):", normal_style))
doc1.append(Paragraph("<b>Carga diferida de aggs pesados</b>", normal_style))
doc1.append(Paragraph(
    "load_all() ya no lee conciliacion.parquet, pdc.parquet ni cierres_det.parquet al "
    "arrancar. La clase _AggsDiferidos los carga (con spinner) la primera vez que una pestana "
    "los pide, vía __missing__. El arranque paso de leer ~1.1 GB a ~25 MB.", normal_style))
doc1.append(Paragraph("<b>Drill-down perezoso (arbol_perezoso)</b>", normal_style))
doc1.append(Paragraph(
    "La pestana Detalle Cuenta usa pdc_pospre.parquet (17.75M filas): pre-armar el arbol "
    "completo en HTML de una sola vez colgaba el navegador. arbol_perezoso() calcula cada "
    "nivel SOLO cuando el usuario abre esa rama (via pl.scan_parquet + filter + collect sobre "
    "el subconjunto ya acotado por los padres elegidos). No usa st.expander (Streamlit no "
    "permite anidarlos mas de 1 nivel); usa st.button + st.session_state para el toggle "
    "abierto/cerrado, y agrupa las hojas de una rama en un solo st.markdown en vez de un "
    "widget por hoja (evita saturar el canal websocket con miles de widgets por rerun).",
    normal_style))
doc1.append(callout("read_xlsx() cacheado",
    "functools.lru_cache evita releer el mismo catalogo Excel 5 veces por corrida de build "
    "(antes se leia una vez por cada funcion que lo necesitaba)."))

doc1.append(Paragraph("5. Flujo de Actualizacion Semanal", h3_style))
flow = [["Paso", "Descripcion"]]
for i, d in enumerate([
    "SQL Server acumula los movimientos de la semana en curso.",
    "extraer_sql.py --check compara filas/monto de SQL vs. el parquet local mas reciente.",
    "Si hay diferencias, extraer_sql.py descarga r25/r26/p26_semNN.parquet nuevos.",
    "python build_data.py --rebuild regenera _consolidado.parquet y todos los aggs.",
    "app.py detecta el nuevo _meta.json (mtime) e invalida su cache automaticamente.",
], start=1):
    flow.append([str(i), d])
doc1.append(styled_table(flow, [0.6 * inch, 5.9 * inch], header_bg=COLOR_SECONDARY))

doc1.append(Paragraph("6. Configuracion Minima", h3_style))
doc1.append(Paragraph("<b>1. usuarios.json</b> con al menos un usuario administrador:", normal_style))
doc1.append(code_block(['{"admin": {"password": "hash_sha256", "rol": "admin"}}']))
doc1.append(Paragraph("<b>2. Catalogos, dentro de la carpeta del dashboard</b>", normal_style))
for cat, req in [("Catalogo grupo cuentas.xlsx", "obligatorio"),
                 ("Catalogo de estructura.xlsx", "obligatorio"),
                 ("Riesgos y Oportunidades.docx", "opcional, habilita comentarios de Planeacion")]:
    doc1.append(Paragraph(f"•  <b>{cat}</b> — {req}", bullet_style))

doc1.append(Paragraph("7. Estructura de Carpetas", h3_style))
doc1.append(code_block([
    "Dashboard Vista Territorio/",
    "|-- build_data.py              # Genera agregados (aggs/)",
    "|-- app.py                     # Interfaz Streamlit",
    "|-- actualizar.py              # Orquesta la extraccion semanal",
    "|-- extraer_sql.py             # Consulta SQL Server",
    "|-- usuarios.json              # Credenciales y roles",
    "|-- Catalogo grupo cuentas.xlsx",
    "|-- Catalogo de estructura.xlsx",
    "|-- Riesgos y Oportunidades.docx",
    "|-- aggs/                      # Parquets de salida (se regeneran)",
    "|-- tests/                     # Pruebas automatizadas",
    "`-- _respaldo/                 # Copias historicas de scripts y docs",
]))

doc1.append(Spacer(1, 0.2 * inch))
doc1.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#D5D8DC"), spaceAfter=8))
doc1.append(Paragraph(
    f"Documento generado automaticamente el {FECHA_GEN.strftime('%d/%m/%Y %H:%M')} · "
    f"Version {VERSION} · Mantenido por {AUTOR}",
    ParagraphStyle('FF1', parent=styles['Normal'], fontSize=8, textColor=COLOR_MUTED, alignment=TA_CENTER)))

build_pdf("Dashboard_Documentacion.pdf", "Documentacion", doc1)


# ==================================================================
# =============================== DOCUMENTO 2: MANUAL DE USO ========
# ==================================================================
doc2 = portada(
    "Manual de Uso",
    "Manual de Uso",
    "Guia operativa para usar el Dashboard Vista Territorio en el dia a dia: como levantarlo, "
    "que muestra cada pestana, como filtrar y que hacer ante los problemas mas comunes.",
)

doc2.append(Paragraph("Tabla de Contenidos", h2_style))
doc2.append(HRFlowable(width="100%", thickness=1.2, color=COLOR_PRIMARY, spaceAfter=10))
for t in ["1. Inicio rapido", "2. Actualizar datos semanalmente", "3. Pestanas del dashboard",
          "4. Filtros", "5. Roles y permisos", "6. Troubleshooting",
          "7. Preguntas frecuentes", "8. Glosario"]:
    doc2.append(Paragraph(t, toc_item_style))
doc2.append(PageBreak())

doc2.append(Paragraph("1. Inicio Rapido", h2_style))
doc2.append(Paragraph("<b>Paso 1 — Generar datos</b> (primera vez o tras cambiar catalogos)", normal_style))
doc2.append(code_block(["cd \"Dashboard Vista Territorio\"", "python build_data.py --rebuild"]))
doc2.append(Paragraph("Puede tardar 10-18 minutos; veras mensajes de progreso en la consola.", normal_style))
doc2.append(Paragraph("<b>Paso 2 — Correr el dashboard</b>", normal_style))
doc2.append(code_block(["streamlit run app.py"]))
doc2.append(Paragraph("Se abre automaticamente en http://localhost:8501", normal_style))
doc2.append(Paragraph("<b>Paso 3 — Iniciar sesion</b>", normal_style))
doc2.append(Paragraph("Usuario y contrasena definidos en usuarios.json.", normal_style))

doc2.append(Paragraph("2. Actualizar Datos Semanalmente", h2_style))
for step in [
    "Confirma que SQL Server ya tiene los datos de la semana en curso.",
    "Corre <b>python extraer_sql.py</b> (o <b>actualizar.py</b>) para bajar los parquets nuevos.",
    "Corre <b>python build_data.py --rebuild</b> para regenerar aggs/ con los datos nuevos.",
    "Si el dashboard ya estaba abierto, recarga el navegador (F5): detecta el _meta.json nuevo solo.",
]:
    doc2.append(Paragraph(f"•  {step}", bullet_style))

doc2.append(Paragraph("3. Pestanas del Dashboard", h2_style))
pestanas = [
    ["Pestana", "Que muestra"],
    ["Resumen", "KPIs principales, graficas de division y grupo de cuentas, evolucion semanal acumulada."],
    ["Div / Terr", "Arbol jerarquico: Division -> Territorio -> Zona -> Region -> PDC, con totales por nivel."],
    ["Detalle Cuenta", "Drill-down por Grupo de Cuentas -> Cuenta -> (Division o Territorio/Region/Zona) -> "
     "PosPre -> PDC. Carga bajo demanda: solo calcula la rama que se expande."],
    ["Detalle PDC", "Listado completo de PDCs con buscador; ideal para ubicar un punto de contacto especifico."],
    ["PDC & Calor", "Histograma de distribucion: cuantos PDCs estan sobre o bajo plan, y por cuanto."],
    ["Forecast CECO", "Proyeccion de cierre por cuenta cruzando el forecast externo con el Real 2026."],
    ["Sem / Mes", "Serie de tiempo semanal o mensual, con boton de descarga a CSV."],
    ["Cierres", "Comparativo de cierre: real acumulado vs. plan, con forecast de cierre proyectado."],
    ["Trimestres", "Vista consolidada por Q1-Q4, util para comparar trimestres no contiguos."],
    ["Riesgos & Oport.", "Comentarios de Planeacion (variaciones positivas/negativas vs AA y Plan, "
     "editables en el Word) + alertas automaticas por division/cuenta/PDC fuera de rango."],
    ["Comentarios", "Notas libres del equipo, guardadas en comentarios.json."],
]
doc2.append(styled_table(pestanas, [1.15 * inch, 5.35 * inch], small=True))
doc2.append(Spacer(1, 0.1 * inch))
doc2.append(callout("Vista Division vs Territorial completo (Detalle Cuenta)",
    "El radio 'Vista' cambia el 4to nivel del arbol: 'Division' es mas corto (Division -> "
    "PosPre -> PDC); 'Territorial completo' agrega Territorio/Region/Zona antes de PosPre. "
    "Ambas mantienen los mismos filtros de busqueda de cuenta y PDC."))

doc2.append(Paragraph("4. Filtros", h2_style))
doc2.append(Paragraph("Los filtros del sidebar aplican de forma global a todas las pestanas.", normal_style))
for f in [
    "<b>Rango de semanas:</b> elige inicio y fin (ej. semana 1 a 29)",
    "<b>Mes:</b> uno o varios meses; el prorrateo diario se calcula automaticamente",
    "<b>Trimestre:</b> Q1-Q4, pueden elegirse varios, incluso no contiguos",
    "<b>Semana individual:</b> analiza una sola semana en aislado",
    "<b>Grupo de cuentas / Cuenta:</b> filtra por categoria o cuenta especifica, aplica global",
]:
    doc2.append(Paragraph(f"•  {f}", bullet_style))

doc2.append(Paragraph("5. Roles y Permisos", h2_style))
roles = [["Rol", "Puede ver", "Puede actualizar datos"],
         ["admin", "Todas las pestanas y divisiones", "Si"],
         ["supervisor", "Todas las pestanas, posible restriccion por division/territorio", "Si"],
         ["user", "Todas las pestanas en modo solo lectura", "No"]]
doc2.append(styled_table(roles, [1.0 * inch, 3.9 * inch, 1.6 * inch]))

doc2.append(Paragraph("6. Troubleshooting", h2_style))
trouble = [["Problema", "Solucion"],
           ["Falta _meta.json", "Corre: python build_data.py --rebuild"],
           ["Datos no actualizados en pantalla", "Recarga el navegador (F5); si persiste, revisa que "
            "aggs/_meta.json tenga fecha reciente"],
           ["Corrijo el catalogo pero no se refleja", "Verifica que estes editando el Excel dentro de la "
            "carpeta del dashboard, no una copia en la raiz de Downloads"],
           ["Sin datos en el rango elegido", "El rango de semanas excede la semana de corte real "
            "(ver sem_max_real en _meta.json)"],
           ["Pestana Detalle Cuenta tarda al abrir una rama", "Normal la primera vez que se visita "
            "(carga conciliacion/pdc en memoria); las siguientes veces es instantaneo"]]
doc2.append(styled_table(trouble, [2.3 * inch, 4.2 * inch]))

doc2.append(Paragraph("7. Preguntas Frecuentes", h2_style))
faqs = [
    ("¿Con que frecuencia se actualizan los datos?",
     "Semanalmente. Se extrae de SQL Server y se corre build_data.py para reflejar la semana nueva."),
    ("¿Como actualizo los comentarios de Riesgos y Oportunidades?",
     "Edita 'Riesgos y Oportunidades.docx' en la carpeta del dashboard (parrafos RIESGOS / "
     "OPORTUNIDADES, uno por vineta) y corre: python -c \"import build_data; "
     "build_data.build_riesgos()\""),
    ("¿Que significa 'Forecast Cierre'?",
     "La proyeccion del gasto al fin del periodo: Real acumulado a la fecha + Plan restante de "
     "las semanas que faltan."),
    ("¿Por que el drill-down de Territorial completo es mas pesado que Division?",
     "Territorio/Zona/Region en el catalogo no son una jerarquia limpia (un mismo Territorio "
     "cae bajo ~20-25 combinaciones de Zona/Region); cruzarlo con PDC genera muchas mas ramas "
     "posibles. El calculo sigue siendo perezoso: solo se paga al expandir cada rama."),
]
for q, a in faqs:
    doc2.append(Paragraph(q, faq_q_style))
    doc2.append(Paragraph(a, faq_a_style))

doc2.append(Paragraph("8. Glosario", h2_style))
gloss = [["Termino", "Significado"],
         ["PDC", "Punto de Contacto: unidad operativa mas granular de la jerarquia territorial."],
         ["PosPre", "Posicion Presupuestal: detalle presupuestal debajo de la Cuenta contable."],
         ["Nvo Plan 2026", "Plan alternativo con calendario de 53 semanas, usado para comparaciones especiales."],
         ["Aggs (agregados)", "Parquets precalculados por build_data.py que el dashboard lee directamente."],
         ["Corte", "Semana hasta la cual hay datos Real disponibles (sem_max_real en _meta.json)."],
         ["Prorrateo", "Distribucion proporcional de un periodo (mes/trimestre) entre sus semanas."]]
doc2.append(styled_table(gloss, [1.6 * inch, 4.9 * inch]))

doc2.append(Spacer(1, 0.2 * inch))
doc2.append(HRFlowable(width="100%", thickness=0.75, color=colors.HexColor("#D5D8DC"), spaceAfter=8))
doc2.append(Paragraph(
    f"Documento generado automaticamente el {FECHA_GEN.strftime('%d/%m/%Y %H:%M')} · "
    f"Version {VERSION} · Mantenido por {AUTOR}",
    ParagraphStyle('FF2', parent=styles['Normal'], fontSize=8, textColor=COLOR_MUTED, alignment=TA_CENTER)))

build_pdf("Dashboard_Manual_de_Uso.pdf", "Manual de Uso", doc2)
