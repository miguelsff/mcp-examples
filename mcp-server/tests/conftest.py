import json
import secrets
import time
from contextlib import asynccontextmanager

import httpx2 as httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from bank_mcp.config import DEMO_CLIENT, DEMO_TENANT, USER_A, Settings
from bank_mcp.server import create_app


@pytest.fixture
def keypair(tmp_path):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_path = tmp_path / "public.pem"
    public_path.write_bytes(
        private.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    return private, public_path


@pytest.fixture
def settings(keypair):
    return Settings(demo_public_key=keypair[1], audit_key=secrets.token_urlsafe(48))


@pytest.fixture
def token(keypair, settings):
    def issue(**changes):
        now = int(time.time())
        claims = {
            "iss": settings.issuer,
            "aud": settings.audience,
            "sub": USER_A,
            "tid": DEMO_TENANT,
            "oid": USER_A,
            "azp": DEMO_CLIENT,
            "ver": "2.0",
            "iat": now,
            "nbf": now,
            "exp": now + 900,
            "scp": "mcp.access solicitudes.read solicitudes.list",
        }
        claims.update(changes)
        return jwt.encode(claims, keypair[0], algorithm="RS256", headers={"kid": "demo-v1"})

    return issue


@asynccontextmanager
async def http_for(settings):
    app = create_app(settings)
    async with app.app.router.lifespan_context(app.app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://127.0.0.1:8000",
            timeout=10,
        ) as http:
            yield app, http


@asynccontextmanager
async def mcp_for(http, bearer):
    http.headers["Authorization"] = f"Bearer {bearer}"
    async with streamable_http_client("http://127.0.0.1:8000/mcp", http_client=http) as (
        read,
        write,
    ):
        async with ClientSession(read, write) as client:
            yield client


def tool_text(result):
    return "\n".join(item.text for item in result.content if item.type == "text")


def parsed_audit(caplog):
    return [
        json.loads(record.message) for record in caplog.records if record.name == "bank_mcp.audit"
    ]
