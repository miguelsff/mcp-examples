"""Valida JWT RS256. Las claves se obtienen de una ubicación de confianza."""

import asyncio
import json
import time
from typing import Any
from uuid import UUID

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from mcp.server.auth.provider import AccessToken

from bank_mcp.audit import Audit
from bank_mcp.config import Settings


class TrustedKeys:
    """Caché acotada. Nunca utiliza jku, x5u ni URLs recibidas en un token."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.keys: dict[str, Any] = {}
        self.loaded_at = 0.0
        self.last_refresh = 0.0
        self.lock = asyncio.Lock()
        self.client: httpx.AsyncClient | None = None
        if settings.auth_mode == "demo":
            key = serialization.load_pem_public_key(settings.demo_public_key.read_bytes())
            if not isinstance(key, RSAPublicKey) or key.key_size < 2048:
                raise ValueError("La demo requiere una clave pública RSA de al menos 2048 bits.")
            self.keys["demo-v1"] = key
            self.loaded_at = time.monotonic()

    async def start(self):
        if self.settings.auth_mode == "entra":
            self.client = httpx.AsyncClient(timeout=5, follow_redirects=False, trust_env=False)
            await self.refresh()

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def refresh(self):
        if self.client is None:
            raise RuntimeError("El proveedor de claves no está iniciado.")
        self.last_refresh = time.monotonic()
        async with self.client.stream("GET", self.settings.jwks_url) as response:
            response.raise_for_status()
            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > 131072:
                    raise ValueError("JWKS excede el límite.")
        document = json.loads(data)
        keys = {}
        for item in document["keys"][:20]:
            if item.get("kty") == "RSA" and item.get("use", "sig") == "sig":
                key = jwt.PyJWK.from_dict(item, algorithm="RS256").key
                if key.key_size >= 2048:
                    keys[item["kid"]] = key
        if not keys:
            raise ValueError("JWKS sin claves RSA válidas.")
        self.keys, self.loaded_at = keys, time.monotonic()

    async def get(self, kid: str):
        if self.settings.auth_mode == "demo":
            return self.keys.get(kid)
        now = time.monotonic()
        if kid not in self.keys or now - self.loaded_at > 300:
            async with self.lock:
                now = time.monotonic()
                # Limita actualizaciones provocadas por kid desconocidos.
                if now - self.last_refresh >= 10:
                    await self.refresh()
        if time.monotonic() - self.loaded_at > 600:
            return None
        return self.keys.get(kid)


class JWTVerifier:
    def __init__(self, settings: Settings, audit: Audit):
        self.settings, self.audit = settings, audit
        self.keys = TrustedKeys(settings)

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            if len(token) > 8192:
                raise ValueError("Token excede el límite.")
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise ValueError("Algoritmo o identificador de clave inválido.")
            key = await self.keys.get(header["kid"])
            if key is None:
                raise ValueError("Clave desconocida.")
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.settings.audience,
                issuer=self.settings.issuer,
                leeway=5,
                options={
                    "require": ["exp", "iat", "nbf", "iss", "aud", "sub", "tid", "oid", "azp"],
                    "strict_aud": True,
                },
            )
            if claims["tid"] != self.settings.tenant_id or claims.get("ver") != "2.0":
                raise ValueError("Tenant o versión inválidos.")
            UUID(claims["oid"])
            if claims["azp"] not in self.settings.allowed_client_ids:
                raise ValueError("Aplicación no autorizada.")
            # Esta versión admite únicamente permisos delegados de usuario.
            if claims.get("idtyp") == "app" or not isinstance(claims.get("scp"), str):
                raise ValueError("Se requiere un access token delegado.")
            scopes = claims["scp"].split()
            if not scopes:
                raise ValueError("Se requieren scopes.")
            return AccessToken(
                token=token,
                client_id=claims["azp"],
                scopes=scopes,
                expires_at=int(claims["exp"]),
                resource=self.settings.audience,
                subject=f"{claims['tid']}:{claims['oid']}",
                claims={"iss": claims["iss"], "tid": claims["tid"], "oid": claims["oid"]},
            )
        except (jwt.PyJWTError, ValueError, KeyError, TypeError):
            self.audit.emit("authentication", "rejected")
            return None
        except Exception:
            # Fallos de red o proveedor: denegar sin incluir secretos ni detalles internos.
            self.audit.emit("authentication", "provider_unavailable")
            return None
