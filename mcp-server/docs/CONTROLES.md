# Matriz de controles del ejemplo

Estado de una referencia educativa. No representa políticas aprobadas del banco.
La evidencia automatizada se encuentra en tests. El responsable indicado es un rol propuesto.

| ID | Lineamiento propuesto | Estado y evidencia | Responsable propuesto |
|---|---|---|---|
| MCP-S01 | Registrar propietario, dominio, datos y criticidad. | Parcial. Dominio de solicitudes sintéticas documentado; propietarios corporativos pendientes. | Dueño del servicio |
| MCP-S02 | Usar SDK mantenido y versiones controladas. | Implementado. SDK 2.3.0 y dependencias exactas; prueba de protocolo y contrato. | Ingeniería |
| MCP-S03 | Publicar contratos de entrada y salida. | Implementado. Tipos estrictos, esquemas, descripciones, snapshot y hash del contrato. | Ingeniería |
| MCP-S04 | Autenticar cada llamada con un token válido. | Implementado en local. Firma, exp, nbf, iat, iss, aud, tid, oid y azp verificados. Entra probado con JWKS simulado. | Identidad e Ingeniería |
| MCP-S05 | Autorizar herramientas y objetos por separado. | Implementado sobre datos ficticios. Pruebas de permisos, acceso cruzado y listado filtrado. | Equipo del dominio |
| MCP-S06 | Obtener la identidad de una fuente validada. | Implementado. tid y oid provienen del JWT verificado. Argumentos extra no pueden sustituir al usuario. | Ingeniería |
| MCP-S07 | Usar permisos mínimos y credenciales adecuadas hacia las APIs. | Pendiente de integración. No existen llamadas a sistemas externos ni reenvío de tokens. | Equipo del dominio |
| MCP-S08 | Minimizar datos entregados y registrados. | Implementado para la demo. Campos permitidos y referencias HMAC en auditoría. Cifrado y retención corporativos pendientes. | Datos y Seguridad |
| MCP-S09 | Controlar operaciones sensibles y reintentos. | Fuera del alcance funcional. Solo consultas; no existen herramientas de escritura. | Dueño del proceso |
| MCP-S10 | Acotar entradas y destinos controlados por el modelo. | Implementado para las dos consultas. IDs con patrón, límites estrictos y sin URLs, SQL o comandos arbitrarios. | Ingeniería y Seguridad |
| MCP-S11 | Controlar cambios de descripciones y esquemas. | Implementado como baseline revisable. Contrato exportado, hash y prueba de cambios. Revisión organizacional pendiente. | Ingeniería |
| MCP-S12 | Restringir accesos de red. | Parcial. Loopback local, Host y Origin permitidos, JWKS fijo y sin redirecciones. Red privada Azure pendiente. | Plataforma |
| MCP-S13 | Limitar frecuencia, concurrencia y duración. | Implementado por proceso. Cuotas globales, pruebas de carga y dimensionamiento pendientes. | Plataforma |
| MCP-S14 | Auditar intentos y resultados sin secretos. | Parcial. JSON a stdout, correlación y HMAC probados. Retención, inmutabilidad y envío central pendientes. | Observabilidad |
| MCP-S15 | Automatizar validación y reversión. | Parcial. Pruebas y workflow de CI incluidos. Pipeline corporativo, análisis de vulnerabilidades y reversión Azure pendientes. | Plataforma e Ingeniería |
| MCP-S16 | Desactivar herramientas ante incidentes. | Implementado mediante ENABLED_TOOLS y reinicio. Desactivación central dinámica pendiente. | Operaciones |
| MCP-S17 | Rechazar tokens de otra API o cliente. | Implementado. Audiencia exacta, emisor fijo y lista de aplicaciones; pruebas negativas. | Identidad |
| MCP-S18 | Separar autenticación delegada y de aplicación. | Implementado como restricción. Solo delegada; app-only se deniega explícitamente. | Identidad |

## Evidencia exigida para adoptar el ejemplo

| Evidencia | Criterio |
|---|---|
| Acceso por objeto | Usuario A no accede al recurso del usuario B. |
| Autenticación | Firma alterada, audiencia incorrecta y token vencido producen rechazo. |
| Scopes | Un cliente no puede ejecutar una herramienta sin su permiso. |
| Minimización | La respuesta contiene únicamente los campos del contrato. |
| Auditoría | Existe correlación y no aparecen el token ni los identificadores de negocio en claro. |
| Integración | El flujo real funciona desde el cliente y la red aprobados del banco. Pendiente. |

## Límites relevantes

- El límite de frecuencia se comparte entre herramientas, por usuario y aplicación, dentro de un proceso.
- Los catálogos y permisos sintéticos se cargan al inicio. Cambiarlos requiere reiniciar.
- Los tokens se verifican en cada llamada. No existe revocación inmediata ni integración de Conditional Access.
- El tiempo máximo es cooperativo. Una futura integración debe usar operaciones asíncronas y tiempos de red acotados.
- Las pruebas de cadenas maliciosas verifican restricciones de entrada. No equivalen a una evaluación completa de prompt injection.
- El HMAC produce seudónimos, no anonimización. La clave y los registros requieren controles corporativos.
- El workflow incluido no ejecuta escaneo de dependencias ni firma de imágenes.

Seguridad y Cumplimiento deben mapear los controles a las políticas vigentes y la normativa aplicable.
No se asignan períodos de retención ni metas de disponibilidad sin requisitos del banco.

