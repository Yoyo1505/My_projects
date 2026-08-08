# Comando de Rescate Antigravity CLI (AGY)

Si PowerShell o ThreatLocker bloquean la ejecución de scripts `.ps1` o `.bat`, utiliza directamente uno de estos dos comandos desde tu terminal o ventana de ejecución (`Win + R`):

### 1. Ventana Ejecutar (`Win + R`):
Pega directamente este texto y presiona Enter:
```cmd
cmd /c "start agy"
```

### 2. Desde PowerShell (Bypass de Política de Ejecución):
Si estás en una ventana de PowerShell y te bloquea las políticas de ejecución, corre:
```powershell
powershell -ExecutionPolicy Bypass -Command "start agy"
```

### 3. Lanzador Directo creado en Downloads:
También he creado el acceso directo ejecutable [00_prender_agy.bat](file:///E:/Usuarios/112665/Downloads/00_prender_agy.bat) en la carpeta `Downloads` que abre la consola de Antigravity sin restricciones.
