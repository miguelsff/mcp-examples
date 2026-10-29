"""Auditoría mínima sin tokens, parámetros libres ni datos de clientes."""

import hashlib
import hmac
import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime

correlation_id: ContextVar[str] = ContextVar("correlation_id", default="internal")
LOGGER = logging.getLogger("bank_mcp.audit")


class Audit:
    def __init__(self, key: str):
        self._key = key.encode()

    def reference(self, namespace: str, value: str) -> str:
        return hmac.new(self._key, f"{namespace}:{value}".encode(), hashlib.sha256).hexdigest()[:24]

    def emit(
        self,
        event: str,
        outcome: str,
        *,
        tool: str | None = None,
        principal: str | None = None,
        client: str | None = None,
        resource: str | None = None,
        duration_ms: float | None = None,
        http_status: int | None = None,
    ):
        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "service": "mcp-solicitudes-demo",
            "version": "0.1.0",
            "event": event,
            "outcome": outcome,
            "correlation_id": correlation_id.get(),
        }
        if tool:
            record["tool"] = tool
        for name, value in (("principal", principal), ("client", client), ("resource", resource)):
            if value:
                record[f"{name}_ref"] = self.reference(name, value)
        if duration_ms is not None:
            record["duration_ms"] = round(duration_ms, 2)
        if http_status is not None:
            record["http_status"] = http_status
        LOGGER.info(json.dumps(record, ensure_ascii=True, separators=(",", ":")))
