# Guía de Instalación y Operación Local

## Requisitos Previos
1. **Sistema Operativo**: Windows 10, Windows 11 o Windows Server.
2. **Python**: Versión 3.9 o superior (3.10 recomendada).
3. **PowerShell**: 5.1 o superior.

## Pasos de Instalación Rápida

### Opción A: Uso de Scripts Automatizados BAT (Recomendado)

1. **Instalar dependencias**:
   Ejecute en la carpeta raíz el script:
   ```cmd
   scripts\01_instalar.bat
   ```
2. **Validar el entorno**:
   ```cmd
   scripts\02_validar_entorno.bat
   ```
3. **Actualizar agregados de datos (opcional si ya existen parquets en aggs/)**:
   ```cmd
   scripts\03_actualizar_datos.bat
   ```
4. **Construir/Reconstruir el índice RAG local**:
   ```cmd
   scripts\05_reconstruir_rag.bat
   ```
5. **Lanzar la aplicación**:
   ```cmd
   scripts\04_ejecutar_aplicacion.bat
   ```
   La aplicación abrirá en el navegador en `http://localhost:8501`.

### Opción B: Ejecución Manual en Terminal

```powershell
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Reconstruir agregados de datos
python build_data.py --resume --aggs-only

# 3. Indizar documentación para el RAG
python rag/indexer.py

# 4. Lanzar Streamlit
streamlit run app.py --server.port 8501
```
