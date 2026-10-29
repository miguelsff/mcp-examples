import json
import secrets
import time

import httpx2 as httpx
import jwt
import pytest

from bank_mcp.audit import Audit
from bank_mcp.auth import JWTVerifier
from bank_mcp.config import DEMO_CLIENT, DEMO_TENANT, USER_A, Settings

API_AUDIENCE = "44444444-4444-4444-8444-444444444444"


@pytest.fixture
def entra_settings(tmp_path):
    grants = tmp_path / "grants.json"
    grants.write_text(json.dumps({"users": {USER_A: ["SOL-1001"]}}))
    return Settings(
        auth_mode="entra",
        app_env="azure",
        public_url="https://mcp.corporativo.example/mcp",
        tenant_id=DEMO_TENANT,
        audience=API_AUDIENCE,
        allowed_client_ids=[DEMO_CLIENT],
        audit_key=secrets.token_urlsafe(48),
        grants_file=grants,
    )


def entra_token(private, settings, **changes):
    now = int(time.time())
    claims = {
        "iss": settings.issuer,
        "aud": settings.audience,
        "sub": "subject",
        "tid": settings.tenant_id,
        "oid": USER_A,
        "azp": DEMO_CLIENT,
        "ver": "2.0",
        "iat": now,
        "nbf": now,
        "exp": now + 900,
        "scp": "mcp.access solicitudes.read",
    }
    claims.update(changes)
    return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "entra-v1"})


async def test_entra_mode_uses_fixed_jwks_and_validates_real_signature(entra_settings, keypair):
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(keypair[0].public_key()))
    public.update(kid="entra-v1", use="sig")
    requests = []

    def handler(request):
        requests.append(str(request.url))
        return httpx.Response(200, json={"keys": [public]})

    verifier = JWTVerifier(entra_settings, Audit(entra_settings.audit_key.get_secret_value()))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        verifier.keys.client = client
        await verifier.keys.refresh()
        result = await verifier.verify_token(entra_token(keypair[0], entra_settings))
        assert result and result.subject == f"{DEMO_TENANT}:{USER_A}"
        assert requests == [entra_settings.jwks_url]
        bad_audience = await verifier.verify_token(
            entra_token(keypair[0], entra_settings, aud="https://graph.microsoft.com")
        )
        assert bad_audience is None


async def test_entra_rejects_app_only_tokens(entra_settings, keypair):
    verifier = JWTVerifier(entra_settings, Audit(entra_settings.audit_key.get_secret_value()))
    verifier.keys.keys = {"entra-v1": keypair[0].public_key()}
    verifier.keys.loaded_at = time.monotonic()
    value = entra_token(
        keypair[0], entra_settings, scp=None, idtyp="app", roles=["Solicitudes.Read.All"]
    )
    assert await verifier.verify_token(value) is None


async def test_entra_does_not_follow_a_jwks_redirect(entra_settings):
    def handler(request):
        return httpx.Response(302, headers={"Location": "https://untrusted.invalid/keys"})

    verifier = JWTVerifier(entra_settings, Audit(entra_settings.audit_key.get_secret_value()))
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler), follow_redirects=False
    ) as client:
        verifier.keys.client = client
        with pytest.raises(httpx.HTTPStatusError):
            await verifier.keys.refresh()


async def test_provider_failure_denies_authentication(entra_settings, keypair, monkeypatch):
    verifier = JWTVerifier(entra_settings, Audit(entra_settings.audit_key.get_secret_value()))

    async def unavailable(kid):
        raise httpx.ConnectError("network unavailable")

    monkeypatch.setattr(verifier.keys, "get", unavailable)
    assert await verifier.verify_token(entra_token(keypair[0], entra_settings)) is None


async def test_stale_jwks_is_not_used_indefinitely(entra_settings, keypair):
    verifier = JWTVerifier(entra_settings, Audit(entra_settings.audit_key.get_secret_value()))
    verifier.keys.keys = {"entra-v1": keypair[0].public_key()}
    verifier.keys.loaded_at = time.monotonic() - 601
    verifier.keys.last_refresh = time.monotonic()
    assert await verifier.verify_token(entra_token(keypair[0], entra_settings)) is None
