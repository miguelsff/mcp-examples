# Arquitectura y decisiones

Estado: implementado y probado localmente, con integración corporativa pendiente.
La entrega desarrolla únicamente el MCP Server.

## Componentes

| Componente | Responsabilidad | Límite de confianza |
|---|---|---|
| Inspector o utilidad de prueba | Descubrir herramientas y enviar llamadas. | Sus argumentos y headers se consideran no confiables. |
| Emisor de identidad | Firmar access tokens. Demo local o Entra configurado. | Solo se aceptan emisor, tenant y claves configurados. |
| Servidor MCP | Validar identidad, scopes, argumentos, límites y salida. | No delega autorización al modelo. |
| Repositorio sintético | Autorizar por objeto y entregar datos ficticios. | Reemplazable por una API de negocio con sus propios controles. |
| Auditoría | Registrar intentos, decisiones y resultados con correlación. | stdout local; destino corporativo pendiente. |

El diagrama editable se encuentra en arquitectura.drawio.
La vista describe el ejemplo ejecutado. El Gateway corporativo se diseñará después.

## Flujo de una consulta

1. El cliente presenta un access token y los argumentos.
2. El servidor valida la firma y los claims.
3. El SDK exige mcp.access.
4. El control de herramientas valida el scope y los argumentos.
5. El repositorio comprueba el acceso al objeto.
6. El servidor devuelve únicamente el modelo de salida aprobado.
7. La auditoría registra el resultado sin incluir el token o los datos del cliente.

## Decisiones registradas

| ID | Decisión | Motivo y consecuencia |
|---|---|---|
| DEC-01 | Usar Python y SDK MCP oficial. | Permite probar el protocolo y controlar autenticación y middleware. |
| DEC-02 | Utilizar Streamable HTTP sin estado de sesión de aplicación. | Facilita la comprobación remota y el alojamiento en contenedores. |
| DEC-03 | Implementar dos herramientas de consulta. | Reduce el alcance inicial. Operaciones transaccionales quedan pendientes. |
| DEC-04 | Separar scope de acceso por objeto. | Un permiso de herramienta no concede acceso a todas las solicitudes. |
| DEC-05 | Admitir solo usuario delegado. | Evita convertir una identidad de aplicación en un usuario de negocio. |
| DEC-06 | Validar Entra dentro del servidor. | El backend conserva un control verificable cuando se agregue el Gateway. |
| DEC-07 | Usar datos sintéticos y permisos locales. | Permite demostrar denegaciones sin acceder a sistemas del banco. |
| DEC-08 | Limitar la demo de identidad a loopback. | Evita publicar accidentalmente el emisor y las claves de demostración. |
| DEC-09 | Preparar un contenedor para Azure Container Apps. | Mantiene el mismo código del servidor; requiere configuración y validación en Azure. |

## Supuestos y pendientes

| ID | Supuesto o pendiente | Efecto |
|---|---|---|
| SUP-01 | Python está permitido en el entorno corporativo. | Si no lo está, conservar contratos y controles al adaptar el lenguaje. |
| SUP-02 | Las primeras herramientas son de consulta. | No se modelan aprobaciones de pagos o cambios. |
| PEN-01 | Falta identificar la API real y su política por objeto. | El repositorio sintético no puede usarse para datos del banco. |
| PEN-02 | Faltan tenant, clientes, red y parámetros aprobados. | No se desplegó ni validó la integración real. |
| PEN-03 | Faltan metas de carga, disponibilidad y recuperación. | No se afirma capacidad de producción. |
| PEN-04 | Falta el contrato con MCP Client y MCP Gateway. | Deben probarse audiencia, delegación, headers, límites y correlación. |
| PEN-05 | Faltan responsables y aprobación de Seguridad. | El ejemplo permanece como referencia técnica. |
