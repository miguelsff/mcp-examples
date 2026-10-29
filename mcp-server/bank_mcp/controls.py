"""Controles por llamada. La autorización no depende de instrucciones del modelo."""

import asyncio
import time
from dataclasses import replace
from typing import Any

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.context import ServerRequestContext
from mcp_types import CallToolResult, ListToolsResult, TextContent
from pydantic import ValidationError

from bank_mcp.audit import Audit
from bank_mcp.config import TOOL_SCOPES, Settings
from bank_mcp.domain import GetInput, ListInput

INPUTS = {"obtener_solicitud": GetInput, "listar_mis_solicitudes": ListInput}


def error_result(code: str) -> CallToolResult:
    return CallToolResult(content=[TextContent(text=code)], is_error=True)


class LocalRateLimiter:
    """Límite por principal y aplicación; estado acotado a un proceso."""

    def __init__(self, limit: int, window: float):
        self.limit, self.window = limit, window
        self.entries: dict[str, tuple[float, int]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        if key not in self.entries and len(self.entries) >= 1024:
            self.entries = {k: v for k, v in self.entries.items() if now - v[0] < self.window}
            if len(self.entries) >= 1024:
                return False
        start, count = self.entries.get(key, (now, 0))
        if now - start >= self.window:
            start, count = now, 0
        self.entries[key] = (start, count + 1)
        return count < self.limit


class ToolControls:
    def __init__(self, settings: Settings, audit: Audit):
        self.settings, self.audit = settings, audit
        self.limiter = LocalRateLimiter(settings.rate_limit, settings.rate_window_seconds)
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_tools)

    async def __call__(self, ctx: ServerRequestContext[Any, Any], call_next):
        token = get_access_token()
        if ctx.method == "tools/list":
            result = ListToolsResult.model_validate(await call_next(ctx))
            result.tools = [
                tool
                for tool in result.tools
                if token
                and tool.name in self.settings.enabled_tools
                and TOOL_SCOPES.get(tool.name) in token.scopes
            ]
            result.cache_scope, result.ttl_ms = "private", 0
            return result
        if ctx.method != "tools/call":
            return await call_next(ctx)

        start = time.monotonic()
        params = dict(ctx.params or {})
        name = params.get("name")
        tool = name if isinstance(name, str) and name in TOOL_SCOPES else "unknown"
        principal = token.subject if token else None
        client = token.client_id if token else None
        resource = None
        outcome = "rejected"

        def reject(code: str):
            nonlocal outcome
            outcome = code
            return error_result(code)

        try:
            if not token or not principal:
                return reject("NO_AUTORIZADO")
            if tool not in self.settings.enabled_tools:
                return reject("HERRAMIENTA_NO_DISPONIBLE")
            if TOOL_SCOPES[tool] not in token.scopes:
                return reject("PERMISO_INSUFICIENTE")
            if not self.limiter.allow(f"{principal}:{client}"):
                return reject("LIMITE_EXCEDIDO")
            try:
                args = INPUTS[tool].model_validate(params.get("arguments", {}))
            except (ValidationError, ValueError, TypeError):
                return reject("PARAMETROS_INVALIDOS")
            arguments = args.model_dump()
            resource = arguments.get("solicitud_id")
            self.audit.emit(
                "tool_attempt",
                "accepted",
                tool=tool,
                principal=principal,
                client=client,
                resource=resource,
            )
            try:
                await asyncio.wait_for(self.semaphore.acquire(), timeout=0.05)
            except TimeoutError:
                return reject("CAPACIDAD_EXCEDIDA")
            try:
                async with asyncio.timeout(self.settings.tool_timeout_seconds):
                    result = CallToolResult.model_validate(
                        await call_next(replace(ctx, params={**params, "arguments": arguments}))
                    )
            finally:
                self.semaphore.release()
            outcome = "tool_error" if result.is_error else "success"
            return result
        except TimeoutError:
            return reject("TIEMPO_EXCEDIDO")
        except Exception:
            return reject("ERROR_INTERNO")
        finally:
            self.audit.emit(
                "tool_completed",
                outcome,
                tool=tool,
                principal=principal,
                client=client,
                resource=resource,
                duration_ms=(time.monotonic() - start) * 1000,
            )
