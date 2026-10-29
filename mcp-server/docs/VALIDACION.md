# Validación de la entrega 0.1.0

Fecha: 28 de octubre de 2026, hora de Lima.
Ambiente ejecutado: Linux, Python 3.12 y dependencias fijadas en los archivos lock.

## Resultados ejecutados

| Comprobación | Resultado |
|---|---|
| Pruebas automatizadas | 43 passed |
| Ruff | All checks passed |
| Formato de Python | Aplicado y validado |
| MCP remoto sobre HTTP local | Descubrimiento, consulta propia, rechazo de recurso ajeno y listado filtrado correctos |
| Identidad local | JWT RS256 con firma real y claves generadas durante la prueba |
| Entra | Verificación criptográfica y proveedor JWKS probado con transporte simulado |
| Contrato de herramientas | Snapshot revisable y prueba de coincidencia |
| Diagrama draw.io | XML, IDs y referencias estructurales válidos |

## Casos cubiertos

- Datos propios y denegación de datos de otro usuario.
- Respuesta indistinguible para recurso ajeno e inexistente.
- Filtro del listado por identidad autenticada.
- Scopes insuficientes y desactivación de herramientas.
- Firma alterada, emisor, audiencia, tenant y cliente incorrectos.
- Tokens vencidos, tokens futuros y rechazo de identidades app-only.
- IDs inválidos, campos extra, tipos incorrectos y cadenas de ataque.
- Límite de filas, frecuencia, concurrencia, cuerpo HTTP y tiempo de ejecución.
- Host y Origin no autorizados.
- Auditoría correlacionada sin token o identificador de negocio en claro.
- JWKS de ubicación fija, redirección rechazada, error de proveedor y claves demasiado antiguas.

## Validaciones no ejecutadas

- Construcción y escaneo de imagen Docker: Docker no está disponible en el entorno.
- Ejecución en Windows: los comandos están preparados para PowerShell, pero se ejecutó en Linux.
- Despliegue en Azure y validación de red privada.
- Autenticación real en un tenant de Entra y consentimiento del cliente.
- Conexión real con Foundry, MCP Inspector o un Gateway corporativo.
- Auditoría central, retención, alertas, carga y recuperación.
- Análisis de vulnerabilidades y revisión independiente de seguridad.
- Revisión visual del diagrama dentro del editor draw.io.

Los resultados demuestran el comportamiento del ejemplo. No acreditan cumplimiento regulatorio ni aptitud de producción.
