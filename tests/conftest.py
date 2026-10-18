import json
import time
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric import ec
import jwt
import pytest

from src.auth import SupabaseVerifier


@pytest.fixture
def identities(monkeypatch):
    private = ec.generate_private_key(ec.SECP256R1())
    public = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private.public_key()))
    public.update(kid="fixture-key", alg="ES256", use="sig")
    verifier = SupabaseVerifier("https://fixture.supabase.co")
    monkeypatch.setattr(verifier.keys, "fetch_data", lambda: {"keys": [public]})
    owner_a, owner_b = uuid4(), uuid4()

    def token(user_id=owner_a, **changes):
        now = int(time.time())
        claims = {"sub": str(user_id), "iss": verifier.issuer, "aud": "authenticated",
                  "role": "authenticated", "iat": now, "exp": now+600}
        claims.update(changes)
        claims = {key: value for key, value in claims.items() if value is not None}
        return jwt.encode(claims, private, algorithm="ES256", headers={"kid": "fixture-key"})

    return verifier, token, owner_a, owner_b
