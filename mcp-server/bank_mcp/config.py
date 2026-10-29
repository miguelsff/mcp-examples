"""Configuración explícita. La demo solo admite una URL de loopback."""

import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator

DEMO_TENANT = "11111111-1111-4111-8111-111111111111"
DEMO_CLIENT = "22222222-2222-4222-8222-222222222222"
USER_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
USER_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
BASE_SCOPE = "mcp.access"
TOOL_SCOPES = {
    "obtener_solicitud": "solicitudes.read",
    "listar_mis_solicitudes": "solicitudes.list",
}


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    auth_mode: Literal["demo", "entra"] = "demo"
    app_env: Literal["local", "azure"] = "local"
    public_url: str = "http://127.0.0.1:8000/mcp"
    tenant_id: str = DEMO_TENANT
    audience: str = "api://mcp-solicitudes-demo"
    allowed_client_ids: list[str] = Field(default_factory=lambda: [DEMO_CLIENT])
    demo_public_key: Path = Path(".demo/public.pem")
    audit_key: SecretStr
    grants_file: Path | None = None
    allowed_origins: list[str] = Field(default_factory=list)
    enabled_tools: list[str] = Field(default_factory=lambda: list(TOOL_SCOPES))
    rate_limit: int = Field(default=30, ge=1, le=10000)
    rate_window_seconds: float = Field(default=60, gt=0, le=3600)
    tool_timeout_seconds: float = Field(default=3, gt=0, le=30)
    max_concurrent_tools: int = Field(default=8, ge=1, le=100)
    max_request_bytes: int = Field(default=16384, ge=1024, le=1048576)

    @model_validator(mode="after")
    def validate_security(self):
        url = urlsplit(self.public_url)
        if (
            url.path != "/mcp"
            or url.query
            or url.fragment
            or url.username
            or url.password
            or not url.hostname
        ):
            raise ValueError("PUBLIC_URL debe ser una URL absoluta terminada en /mcp.")
        UUID(self.tenant_id)
        if not self.allowed_client_ids:
            raise ValueError("Configure al menos un cliente autorizado.")
        for value in self.allowed_client_ids:
            UUID(value)
        if len(self.audit_key.get_secret_value().encode()) < 32:
            raise ValueError("AUDIT_HMAC_KEY requiere al menos 32 bytes.")
        if not self.audience or set(self.enabled_tools) - set(TOOL_SCOPES):
            raise ValueError("Audiencia o herramientas inválidas.")
        if self.auth_mode == "demo":
            if self.app_env != "local" or url.hostname not in ("127.0.0.1", "localhost", "::1"):
                raise ValueError("La identidad de demo solo admite el ambiente local y loopback.")
            if url.scheme != "http":
                raise ValueError("La demo local usa HTTP sobre loopback.")
        else:
            if url.scheme != "https":
                raise ValueError("Entra requiere PUBLIC_URL HTTPS.")
            if self.grants_file is None:
                raise ValueError("Entra requiere GRANTS_FILE con permisos de negocio explícitos.")
            UUID(self.audience)  # Access tokens v2: client ID de la API.
        return self

    @property
    def issuer(self) -> str:
        if self.auth_mode == "demo":
            return "https://issuer.demo.invalid"
        return f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"

    @property
    def jwks_url(self) -> str:
        return f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"

    @classmethod
    def from_env(cls):
        mode = os.getenv("AUTH_MODE", "demo")
        if mode == "demo":
            path = Path(os.getenv("DEMO_CONFIG", ".demo/config.json"))
            if not path.is_file():
                raise ValueError("Primero ejecute: python scripts/demo.py init")
            values = json.loads(path.read_text(encoding="utf-8"))
        else:
            values = {}
        values.update(
            auth_mode=mode,
            app_env=os.getenv("APP_ENV", "local"),
        )
        mapping = {
            "PUBLIC_URL": "public_url",
            "AZURE_TENANT_ID": "tenant_id",
            "AZURE_API_AUDIENCE": "audience",
            "AUDIT_HMAC_KEY": "audit_key",
            "GRANTS_FILE": "grants_file",
            "RATE_LIMIT": "rate_limit",
            "TOOL_TIMEOUT_SECONDS": "tool_timeout_seconds",
        }
        for env, field in mapping.items():
            if env in os.environ:
                values[field] = os.environ[env]
        for env, field in {
            "ALLOWED_CLIENT_IDS": "allowed_client_ids",
            "ALLOWED_ORIGINS": "allowed_origins",
            "ENABLED_TOOLS": "enabled_tools",
        }.items():
            if env in os.environ:
                values[field] = [x.strip() for x in os.environ[env].split(",") if x.strip()]
        return cls.model_validate(values)
