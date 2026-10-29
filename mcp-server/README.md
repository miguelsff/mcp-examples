# MCP Server de ejemplo para revisión técnica

Versión 0.1.0 · 28 de octubre de 2026 · Datos completamente ficticios.

Servidor Python con dos herramientas de consulta. Sirve como referencia inicial de lineamientos verificables.
No necesita Foundry, un agente ni un modelo para ejecutarse.

## Qué incluye

- SDK oficial MCP 2.3.0 y Streamable HTTP en /mcp.
- Tokens JWT RS256, con validación de firma, audiencia, emisor, tenant, cliente y vigencia.
- Scopes por herramienta y permisos por solicitud.
- Entradas estrictas y salidas estructuradas con campos permitidos.
- Auditoría JSON con referencias HMAC e identificadores de correlación.
- Límites de cuerpo, frecuencia y concurrencia; tiempo máximo por herramienta.
- Dockerfile para evaluar el alojamiento en Azure Container Apps.
- Pruebas automatizadas y matriz de controles implementados y pendientes.

El ejemplo implementa únicamente consultas. No realiza pagos, cambios de datos ni consultas a sistemas del banco.

## Inicio rápido en Windows PowerShell

Requiere Python 3.12 o superior. Abra una terminal dentro de la carpeta del proyecto.

~~~powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock
.\.venv\Scripts\python.exe scripts/demo.py init
.\.venv\Scripts\python.exe -m bank_mcp
~~~

El servidor escucha únicamente en http://127.0.0.1:8000.
La inicialización crea claves nuevas dentro de .demo. No sobrescribe claves existentes.
Esa carpeta queda excluida del repositorio y del contenedor.
En Windows, restrinja sus permisos mediante las ACL corporativas del equipo.

En una segunda terminal:

~~~powershell
.\.venv\Scripts\python.exe scripts/demo.py smoke
~~~

Resultado esperado:

~~~text
OK: descubrimiento MCP, consulta propia, recurso ajeno denegado y listado filtrado.
~~~

En Linux o macOS, sustituya el ejecutable anterior por .venv/bin/python.

## Demostración para los compañeros

| Perfil ficticio | Solicitudes autorizadas |
|---|---|
| Ana | SOL-1001 y SOL-1002 |
| Bruno | SOL-2001 |

1. Liste las herramientas disponibles.
2. Consulte SOL-1001 con el token de Ana.
3. Intente consultar SOL-2001 con el mismo token.
4. Observe la denegación y la auditoría.
5. Repita SOL-2001 con el token de Bruno.

El servidor devuelve el mismo error para una solicitud ajena y una inexistente.
El cliente no puede declarar otro usuario mediante los argumentos de una herramienta.

## Probar con MCP Inspector

Esta conexión es manual y utiliza tokens preemitidos para la demo.
No incluye un servidor OAuth de inicio de sesión.
El emisor issuer.demo.invalid es ficticio y no tiene endpoints de autorización.

Requiere Node.js 22.19 o superior.

~~~powershell
npx @modelcontextprotocol/inspector
~~~

Obtenga un token local de quince minutos:

~~~powershell
.\.venv\Scripts\python.exe scripts/demo.py token --user ana
~~~

Configure el Inspector:

| Campo | Valor |
|---|---|
| Transporte | Streamable HTTP |
| URL | http://127.0.0.1:8000/mcp |
| Header Authorization | Bearer seguido del token generado |

Pruebe las herramientas con estos argumentos:

~~~json
{"solicitud_id":"SOL-1001"}
~~~

~~~json
{"limite":5}
~~~

Si su cliente envía Origin, configure ALLOWED_ORIGINS con el origen exacto y reinicie el servidor.
La configuración predeterminada rechaza orígenes enviados que no estén autorizados.

## Cómo se aplican los permisos

La llamada debe superar cuatro comprobaciones independientes:

1. El token debe ser válido y estar destinado a esta API.
2. La aplicación cliente debe estar autorizada.
3. El token debe incluir mcp.access y el scope de la herramienta.
4. El usuario debe tener acceso a la solicitud concreta.

| Herramienta | Scope adicional |
|---|---|
| obtener_solicitud | solicitudes.read |
| listar_mis_solicitudes | solicitudes.list |

El listado de herramientas se filtra por scopes y configuración.
La ejecución vuelve a comprobar el permiso aunque el cliente conozca el nombre.
La caché del catálogo es privada y su TTL es cero.
Las anotaciones readOnlyHint son informativas. La seguridad la aplican las comprobaciones del servidor.

Esta versión solo acepta permisos delegados de usuario.
Los tokens de aplicación sin usuario se deniegan.
Un agente Foundry con identidad de aplicación necesitará una política explícita y una ampliación del ejemplo.

## Ejecutar las comprobaciones

~~~powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
~~~

El cliente de scripts/demo.py es una utilidad de comprobación del servidor.
No constituye el diseño del futuro MCP Client corporativo.

## Archivos principales

| Archivo | Responsabilidad |
|---|---|
| bank_mcp/server.py | Aplicación HTTP, catálogo MCP y herramientas |
| bank_mcp/auth.py | Validación JWT y claves de confianza |
| bank_mcp/controls.py | Scopes, validación, límites y auditoría de llamadas |
| bank_mcp/domain.py | Datos sintéticos y autorización por objeto |
| bank_mcp/audit.py | Eventos estructurados sin tokens ni datos del cliente |
| docs/CONTROLES.md | Matriz de lineamientos y evidencia |
| docs/AZURE.md | Configuración de Entra y ruta de despliegue |
| docs/ARQUITECTURA.md | Componentes, decisiones y límites |
| docs/VALIDACION.md | Pruebas ejecutadas y verificaciones pendientes |
| docs/arquitectura.drawio | Diagrama editable |

## Alcance antes de producción

Quedan pendientes la integración con las APIs y permisos del banco, la red corporativa y la auditoría central.
También quedan pendientes la validación real en Entra, las pruebas de carga y la aprobación de Seguridad.
La matriz detalla estas diferencias. Este ejemplo no acredita cumplimiento regulatorio.

## Fuentes técnicas

Consultadas el 28 de octubre de 2026.

- SDK oficial y versiones: https://py.sdk.modelcontextprotocol.io/
- Autenticación del SDK: https://py.sdk.modelcontextprotocol.io/run/authorization/
- Herramientas MCP: https://modelcontextprotocol.io/specification/latest/server/tools
- Seguridad MCP: https://modelcontextprotocol.io/specification/latest/basic/security_best_practices
- Claims de Entra: https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- Alojamiento en Azure: https://learn.microsoft.com/en-us/azure/container-apps/mcp-overview
- Seguridad MCP de OWASP: https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html

