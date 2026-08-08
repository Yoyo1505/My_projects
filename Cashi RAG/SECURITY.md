# Políticas y Auditoría de Seguridad: Dashboard Vista Territorio

## 1. Operación 100% Local-First
- El sistema opera de manera **totalmente local y aislada**, sin enviar datos transaccionales, cifras financieras ni consultas a servicios en la nube de terceros.
- Las variables de entorno con credenciales de base de datos se leen desde el archivo `.env` local, el cual está excluido en `.gitignore`.

## 2. Prevención de Inyección y Path Traversal
- **Consultas DuckDB / SQL**: Todas las consultas utilizan parámetros parametrizados o vistas estructuradas pre-compiladas, evitando la concatenación de entradas de usuario no saneadas.
- **Rutas de Archivos**: Todas las operaciones con el sistema de archivos utilizan la biblioteca estándar `pathlib.Path`, sanitizando los nombres de archivo para prevenir vulnerabilidades de Path Traversal (`../`).

## 3. RAG y Prompt Injection
- El motor RAG local implementa una separación estricta entre el contenido recuperado de los documentos y el contexto de consulta del usuario.
- Los documentos son parseados como texto plano sin ejecutar scripts embebidos ni macros.
