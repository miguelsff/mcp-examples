# Configuración para Azure

Ruta propuesta: contenedor del servidor en Azure Container Apps.
La selección permite reutilizar el SDK oficial y los controles locales.
El paquete incluye un Dockerfile; no crea recursos ni despliega servicios.

## Requisitos previos

1. Seleccione la suscripción y el ambiente aprobados del banco.
2. Confirme región, residencia de datos, cuota y conectividad.
3. Use un registro de imágenes y un ambiente de Container Apps aprobados.
4. Registre una API y los clientes permitidos en Microsoft Entra ID.
5. Defina permisos de negocio para los usuarios de prueba.
6. Obtenga la aprobación del circuito corporativo de despliegue.

## Registro de la API en Entra

Configure access tokens v2 para la API.
Defina los permisos delegados mcp.access, solicitudes.read y solicitudes.list.
Autorice los clientes y gestione el consentimiento según las políticas del banco.
El flujo del cliente debe obtener un access token para esta API.

AZURE_API_AUDIENCE debe contener el client ID de la API, en formato UUID.
ALLOWED_CLIENT_IDS contiene los client ID de las aplicaciones que llaman.
La aplicación valida oid y tid. No utiliza el correo para autorizar.

Los tokens app-only se rechazan. Esta entrega no incorpora permisos de aplicación.
La configuración de un agente Foundry con identidad propia requiere ese trabajo adicional.

## Variables de ambiente

| Variable | Valor requerido |
|---|---|
| APP_ENV | azure |
| AUTH_MODE | entra |
| PUBLIC_URL | URL HTTPS exacta del servicio, terminada en /mcp |
| AZURE_TENANT_ID | UUID del tenant aprobado |
| AZURE_API_AUDIENCE | Client ID de la API, no el de Microsoft Graph |
| ALLOWED_CLIENT_IDS | Client ID permitidos, separados por comas |
| AUDIT_HMAC_KEY | Secreto aleatorio de al menos 32 bytes, inyectado desde el almacén aprobado |
| GRANTS_FILE | Ruta del archivo de permisos sintéticos dentro del contenedor |
| ALLOWED_ORIGINS | Orígenes exactos de clientes web, si corresponde |
| ENABLED_TOOLS | Herramientas habilitadas, separadas por comas |
| RATE_LIMIT | Máximo de llamadas por usuario y cliente en una ventana de 60 segundos |
| TOOL_TIMEOUT_SECONDS | Tiempo máximo por herramienta; valor inicial de demo: 3 segundos |

Los límites anteriores son valores de demostración. No son metas de servicio del banco.

Ejemplo de plantilla de configuración, sin valores secretos:

~~~text
APP_ENV=azure
AUTH_MODE=entra
PUBLIC_URL=https://<fqdn-aprobado>/mcp
AZURE_TENANT_ID=<tenant-uuid>
AZURE_API_AUDIENCE=<api-client-id-uuid>
ALLOWED_CLIENT_IDS=<cliente-aprobado-uuid>
AUDIT_HMAC_KEY=<referencia-a-secreto>
GRANTS_FILE=/app/config/grants.example.json
ENABLED_TOOLS=obtener_solicitud,listar_mis_solicitudes
~~~

No use literalmente los marcadores anteriores. No almacene secretos dentro de la imagen.
Cambie los UUID del archivo de permisos por los oid de usuarios autorizados del tenant.
Conserve únicamente los IDs sintéticos SOL-1001, SOL-1002 y SOL-2001.
Ese archivo es una implementación de demostración, no un sistema de autorización corporativo.

## Construir el contenedor

~~~bash
docker build --tag mcp-solicitudes-demo:0.1.0 .
~~~

La imagen se ejecuta como usuario 10001.
La imagen no contiene la carpeta .demo ni claves de firma.
Antes de adoptarla, fije la imagen base por digest y ejecute los análisis corporativos.
El contenedor no fue construido en este entorno de trabajo porque Docker no está disponible.

## Configuración de Container Apps

| Control | Configuración a revisar |
|---|---|
| Ingreso | Puerto de destino 8000, TLS en el ingreso y acceso según el diseño corporativo. |
| Red | Entrada privada o restringida y ruta comprobada desde el consumidor o Gateway. |
| Host | PUBLIC_URL debe coincidir con el Host que recibe la aplicación. |
| Salida | Permitir login.microsoftonline.com para obtener claves públicas. |
| Identidad | Usar identidad administrada para el registro y secretos cuando los servicios lo permitan. |
| Secretos | Inyectar AUDIT_HMAC_KEY desde el almacén aprobado. |
| Salud | /health/live y /health/ready. |
| Registros | Enviar stdout al destino corporativo con acceso y retención aprobados. |
| Escalado | Validar carga y sustituir límites locales por controles distribuidos cuando corresponda. |

El proceso valida el JWT. No confía en headers de identidad agregados por un cliente.
No se habilita proxy_headers. Los headers reenviados no modifican la identidad autenticada.
Si el Gateway cambia la audiencia, el contrato de identidad del backend debe quedar definido y probado.
La API final conserva su autorización por objeto.

## OAuth y descubrimiento

El SDK publica metadata de recurso protegido y challenges de autenticación.
El servidor valida la audiencia Entra explícitamente aunque difiera de su URL pública.
La compatibilidad del descubrimiento, consentimiento y adquisición de tokens depende del cliente.
Pruebe ese flujo con el cliente corporativo antes de declararlo soportado.
Esta entrega no implementa endpoints de login ni de emisión de tokens.

## Verificación y reversión

1. Pruebe salud desde la red del consumidor.
2. Verifique un rechazo sin token.
3. Pruebe un token delegado real con los permisos correctos.
4. Verifique acceso propio y denegación de recurso ajeno.
5. Busque los eventos correlacionados en el destino corporativo.
6. Compruebe permisos sobre el archivo de configuración y el secreto.
7. Revierta a la revisión anterior si falla la validación.

El ejemplo no escribe datos. Revertir la imagen no equivale a recuperar datos de futuras herramientas de escritura.

Fuentes:

- https://learn.microsoft.com/en-us/azure/container-apps/mcp-overview
- https://learn.microsoft.com/en-us/entra/identity-platform/claims-validation
- https://learn.microsoft.com/en-us/entra/identity-platform/access-token-claims-reference
- https://py.sdk.modelcontextprotocol.io/run/authorization/

