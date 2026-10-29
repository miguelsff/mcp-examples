"""Utilidad de desarrollo. Emite credenciales de demo fuera del servidor MCP."""

import argparse
import asyncio
import json
import os
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx2 as httpx
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from bank_mcp.config import DEMO_CLIENT, DEMO_TENANT, USER_A, USER_B, Settings


def initialize():
    directory = Path(".demo")
    directory.mkdir(mode=0o700, exist_ok=True)
    names = ("private.pem", "public.pem", "config.json")
    if any((directory / name).exists() for name in names):
        raise SystemExit("Ya existe una configuración. Se conservaron las claves.")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    values = {
        "private.pem": key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
        "public.pem": key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ),
        "config.json": json.dumps(
            {
                "tenant_id": DEMO_TENANT,
                "audience": "api://mcp-solicitudes-demo",
                "allowed_client_ids": [DEMO_CLIENT],
                "demo_public_key": ".demo/public.pem",
                "audit_key": secrets.token_urlsafe(48),
            },
            indent=2,
        ).encode(),
    }
    for name, data in values.items():
        path = directory / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
    print("Demo creada. Inicie el servidor con: python -m bank_mcp")


def make_token(user="ana", scopes=None, **overrides):
    settings = Settings.from_env()
    if settings.auth_mode != "demo":
        raise SystemExit("Esta utilidad solo emite tokens del emisor ficticio.")
    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.audience,
        "sub": USER_A if user == "ana" else USER_B,
        "tid": settings.tenant_id,
        "oid": USER_A if user == "ana" else USER_B,
        "azp": DEMO_CLIENT,
        "ver": "2.0",
        "iat": now,
        "nbf": now,
        "exp": now + 900,
        "scp": " ".join(
            scopes
            if scopes is not None
            else [
                "mcp.access",
                "solicitudes.read",
                "solicitudes.list",
            ]
        ),
    }
    claims.update(overrides)
    return jwt.encode(
        claims,
        Path(".demo/private.pem").read_bytes(),
        algorithm="RS256",
        headers={"kid": "demo-v1"},
    )


async def smoke():
    settings = Settings.from_env()
    headers = {"Authorization": f"Bearer {make_token()}"}
    async with httpx.AsyncClient(headers=headers, timeout=10, trust_env=False) as http:
        async with streamable_http_client(settings.public_url, http_client=http) as (read, write):
            async with ClientSession(read, write) as client:
                tools = await client.list_tools()
                assert {tool.name for tool in tools.tools} == {
                    "obtener_solicitud",
                    "listar_mis_solicitudes",
                }
                own = await client.call_tool("obtener_solicitud", {"solicitud_id": "SOL-1001"})
                assert not own.is_error and own.structured_content["solicitud_id"] == "SOL-1001"
                denied = await client.call_tool("obtener_solicitud", {"solicitud_id": "SOL-2001"})
                assert denied.is_error
                listed = await client.call_tool("listar_mis_solicitudes", {"limite": 5})
                assert not listed.is_error
                assert {
                    item["solicitud_id"] for item in listed.structured_content["solicitudes"]
                } == {"SOL-1001", "SOL-1002"}
    print("OK: descubrimiento MCP, consulta propia, recurso ajeno denegado y listado filtrado.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init")
    token = commands.add_parser("token")
    token.add_argument("--user", choices=["ana", "bruno"], default="ana")
    token.add_argument("--scope", action="append", dest="scopes")
    commands.add_parser("smoke")
    args = parser.parse_args()
    if args.command == "init":
        initialize()
    elif args.command == "token":
        print(make_token(args.user, args.scopes))
    else:
        asyncio.run(smoke())


if __name__ == "__main__":
    main()
