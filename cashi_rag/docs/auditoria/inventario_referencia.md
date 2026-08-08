# Inventario del Proyecto de Referencia: Servidor Administración y Finanzas

## Overview
- **Ruta de origen**: `E:\Usuarios\112665\Downloads\Servidor administración y finanzas - copia`
- **Propósito**: Servidor local HTTP, automatización de reportes de gasto, administración de usuarios, ejecución de extracciones SAP y dashboards estáticos HTML/JS.

## Componentes Principales

### 1. Servidor Local HTTP y Control de Accesos
- `servidor.py` (13.5 KB):
  - Servidor Python basado en `http.server` y `socketserver`.
  - Gestiona autenticación basada en `usuarios.json`.
  - Enruta peticiones para consultar HTMLs pre-renderizados de dashboards.
  - Ofrece endpoints para desencadenar actualizaciones semanales de datos.

### 2. Scripts de Ejecución Operativa (BAT / CMD)
- `INICIAR_SERVIDOR.bat`: Levanta el servidor local HTTP en puerto configurado.
- `EJECUTAR_ACTUALIZACION.bat`: Ejecuta la actualización semanal de datos de gasto.
- `ACTUALIZAR_SEMANA.bat`: Incrementa la semana activa y desencadena rebuilds.
- `CALIBRAR_MAPPING.bat`: Ejecuta la calibración de mapeos entre catálogos.
- `GESTIONAR_USUARIOS.bat`: Administra credenciales y permisos de usuarios.
- `MEJORAR_HTMLS.bat`: Aplica optimizaciones de layout y formateo a reportes HTML.

### 3. Pipeline de Actualización y Inyección de Datos
- `actualizar_semana.py` (28.3 KB) / `EJECUTAR_ACTUALIZACION.py` (6.9 KB):
  - Orquestadores ejecutivos con logging detallado en `actualizaciones.log`.
  - Procesan entradas desde la carpeta `entrada/` y generan JSONs de datos.
- `extractor_sap_simple.py` (15.8 KB):
  - Módulo extractor para conectar a vistas SAP y descargar registros de CECOs y cuentas.
- `calibrar_mapping.py` (3.9 KB):
  - Script que valida y mapea llaves entre catálogos corporativos y estructuras ejecutivas.
- `inyectar_dashboard_gasto.py` / `mejorar_htmls.py` / `regenerar_htmls.py`:
  - Inyectan estructuras JSON procesadas directamente en las plantillas HTML standalone (`index.html`, `dashboard_Gasto.html`, `superdashboard_gasto.html`).

### 4. Generador de Manuales y Documentación
- `generar_manual.py` (43.0 KB):
  - Compila documentación ejecutiva a partir de plantillas HTML en `MANUAL.html` y `MANUAL.pdf` (vía pdfkit/wkhtmltopdf).

### 5. Documentación Técnica en `MD's/`
- `MD's/ARQUITECTURA_AUTOMATIZACION.md` (9.0 KB): Arquitectura general de la suite de automatización.
- `MD's/ESTADO_REPORTES.md` (4.6 KB): Estado de compilación y entregables de reportes.
- `MD's/README_GASTO_AUTOMATIZACION.md` (4.5 KB): Guía de operabilidad rápida.
- `MD's/SINCRONIZACION_COMPLETADA.md` (5.4 KB): Registro de sincronización entre SAP y parquets.
- `MD's/UPDATE_DATOS_GASTO.md` (3.8 KB): Instructivo de actualización incremental.
