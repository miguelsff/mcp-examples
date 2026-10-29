"""Aplicación ASGI con MCP remoto, autenticación y herramientas de solo lectura."""

import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.settings import AuthSettings
from mcp.server.transport_security import TransportSecuritySettings
from mcp_types import ToolAnnotations
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from bank_mcp.audit import Audit, correlation_id
from bank_mcp.auth import JWTVerifier
from bank_mcp.config import BASE_SCOPE, Settings
from bank_mcp.controls import ToolControls
from bank_mcp.domain import (
    Limit,
    ListaSolicitudes,
    RequestId,
    Solicitud,
    SyntheticRepository,
)


class RequestEnvelope:
    """Genera correlación propia y desactiva el almacenamiento HTTP de respuestas."""

    def __init__(self, app, audit: Audit):
        self.app, self.audit = app, audit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        context_token = correlation_id.set(str(uuid4()))
        status = 500

        async def send_safe(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = [
                    (key, value)
                    for key, value in message.get("headers", [])
                    if key.lower() not in (b"cache-control", b"x-correlation-id")
                ]
                headers.extend(
                    [
                        (b"cache-control", b"no-store"),
                        (b"x-content-type-options", b"nosniff"),
                        (b"x-correlation-id", correlation_id.get().encode()),
                    ]
                )
                message = {**message, "headers": headers}
            await send(message)

        try:
            await self.app(scope, receive, send_safe)
        finally:
            if scope.get("path") == "/mcp":
                self.audit.emit("http_request", "completed", http_status=status)
            correlation_id.reset(context_token)


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()
    audit = Audit(settings.audit_key.get_secret_value())
    verifier = JWTVerifier(settings, audit)
    repository = SyntheticRepository(settings)
    controls = ToolControls(settings, audit)

    mcp = MCPServer(
        "solicitudes-demo",
        version="0.1.0",
        description="Consulta de solicitudes ficticias con acceso limitado al usuario autenticado.",
        token_verifier=verifier,
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(settings.issuer),
            resource_server_url=AnyHttpUrl(settings.public_url),
            required_scopes=[BASE_SCOPE],
            # Entra usa el client ID de la API como aud, distinto de PUBLIC_URL.
            # JWTVerifier comprueba aud de forma obligatoria antes de devolver AccessToken.
            validate_token_resource=False,
        ),
        middleware=[controls],
    )
    annotations = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )

    @mcp.tool(annotations=annotations)
    async def obtener_solicitud(solicitud_id: RequestId) -> Solicitud:
        """Consulta una solicitud ficticia asignada al usuario autenticado."""
        token = get_access_token()
        if not token or not token.subject:
            raise PermissionError("No hay identidad autenticada.")
        return await repository.get(token.subject, solicitud_id)

    @mcp.tool(annotations=annotations)
    async def listar_mis_solicitudes(limite: Limit = 5) -> ListaSolicitudes:
        """Lista hasta diez solicitudes ficticias asignadas al usuario autenticado."""
        token = get_access_token()
        if not token or not token.subject:
            raise PermissionError("No hay identidad autenticada.")
        return await repository.list_for(token.subject, limite)

    from urllib.parse import urlsplit

    public = urlsplit(settings.public_url)
    allowed_hosts = [public.netloc]
    if settings.auth_mode == "demo":
        allowed_hosts.extend(["localhost:8000", "127.0.0.1:8000"])
    app = mcp.streamable_http_app(
        stateless_http=True,
        json_response=True,
        max_request_body_size=settings.max_request_bytes,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=allowed_hosts,
            allowed_origins=settings.allowed_origins,
        ),
    )

    async def live(_: Request):
        return JSONResponse({"status": "ok"})

    async def ready(_: Request):
        available = bool(verifier.keys.keys) and (
            settings.auth_mode == "demo" or time.monotonic() - verifier.keys.loaded_at <= 600
        )
        return JSONResponse(
            {"status": "ready" if available else "not_ready"},
            status_code=200 if available else 503,
        )

    app.routes.extend(
        [
            Route("/health/live", live, methods=["GET"]),
            Route("/health/ready", ready, methods=["GET"]),
        ]
    )
    sdk_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current_app):
        try:
            await verifier.keys.start()
            async with sdk_lifespan(current_app):
                yield
        finally:
            await verifier.keys.close()

    app.router.lifespan_context = lifespan
    app.state.mcp = mcp
    app.state.repository = repository
    app.state.verifier = verifier
    app.state.settings = settings
    app.state.controls = controls
    wrapped = RequestEnvelope(app, audit)
    wrapped.state = app.state
    return wrapped


def configure_logging():
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("bank_mcp.audit").setLevel(logging.INFO)
    # Evita que librerías registren parámetros en fallos de herramientas.
    logging.getLogger("mcp").setLevel(logging.CRITICAL)
