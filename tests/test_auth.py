import time

from fastapi import HTTPException
import jwt
from jwt.exceptions import PyJWKClientConnectionError
import pytest

from src.auth import SupabaseVerifier


def test_signed_user_identity(identities):
    verifier, token, owner_a, _ = identities
    identity = verifier.verify(token())
    assert identity.user_id == owner_a
    assert identity.issuer == "https://fixture.supabase.co/auth/v1"


def test_clock_skew_is_bounded_and_expiry_is_still_enforced(identities):
    verifier, token, *_ = identities
    now = int(time.time())
    assert verifier.verify(token(iat=now+70))
    for claims in ({"iat":now+121}, {"exp":now-121}):
        with pytest.raises(HTTPException) as error:
            verifier.verify(token(**claims))
        assert error.value.status_code == 401


@pytest.mark.parametrize('margin', [-1, 121, '90', True])
def test_invalid_clock_skew_configuration(margin):
    with pytest.raises(ValueError, match='reloj JWT'):
        SupabaseVerifier('https://fixture.supabase.co', clock_skew_seconds=margin)


@pytest.mark.parametrize("changes", [
    {"exp": 1}, {"exp": None}, {"sub": "not-a-uuid"}, {"iss": "https://other.supabase.co/auth/v1"},
    {"aud": "other"}, {"role": "service_role"}, {"is_anonymous": True},
    {"iat": int(time.time())+10000}, {"sub": None},
])
def test_rejects_invalid_claims(identities, changes):
    verifier, token, _, _ = identities
    with pytest.raises(HTTPException) as error:
        verifier.verify(token(**changes))
    assert error.value.status_code == 401


def test_rejects_unsigned_hmac_and_changed_signature(identities):
    verifier, token, _, _ = identities
    valid = token()
    pieces = valid.split(".")
    invalid = ".".join(pieces[:2]+["AAAA"])
    for candidate in ("not-a-token", "x"*9000, invalid,
                      jwt.encode({"sub": "fake"}, "wrong"*8, algorithm="HS256")):
        with pytest.raises(HTTPException) as error:
            verifier.verify(candidate)
        assert error.value.status_code == 401


def test_jwks_outage_is_not_an_auth_bypass(identities, monkeypatch):
    verifier, token, _, _ = identities
    def unavailable(*args):
        raise PyJWKClientConnectionError("internal network information")
    monkeypatch.setattr(verifier.keys, "get_signing_key_from_jwt", unavailable)
    with pytest.raises(HTTPException) as error:
        verifier.verify(token())
    assert error.value.status_code == 503
    assert "internal" not in str(error.value.detail)


@pytest.mark.parametrize("url", ["http://fixture.supabase.co", "https://user:pass@fixture.supabase.co", "https://fixture.supabase.co/unsafe"])
def test_auth_rejects_unsafe_configuration(url):
    with pytest.raises(ValueError):
        SupabaseVerifier(url)
