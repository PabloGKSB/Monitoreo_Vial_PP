"""Validate Supabase access tokens using a configured issuer's public keys."""

from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    issuer: str


class SupabaseVerifier:
    def __init__(self, project_url: str, *, clock_skew_seconds=90):
        parsed = urlparse(project_url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in {"", "/"}):
            raise ValueError("SUPABASE_URL debe ser la URL HTTPS del proyecto, sin rutas ni credenciales")
        self.issuer = project_url.rstrip("/") + "/auth/v1"
        if type(clock_skew_seconds) is not int or not 0 <= clock_skew_seconds <= 120:
            raise ValueError("El margen de reloj JWT debe estar entre 0 y 120 segundos")
        self.clock_skew_seconds = clock_skew_seconds
        self.keys = PyJWKClient(self.issuer + "/.well-known/jwks.json", lifespan=300, timeout=5)

    def verify(self, token: str) -> Identity:
        denied = HTTPException(401, "Token de usuario invalido o vencido", headers={"WWW-Authenticate": "Bearer"})
        if len(token) > 8192:
            raise denied
        try:
            # Never use jku/x5u URLs or algorithm choices outside the configured allowlist.
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in {"ES256", "RS256"} or not isinstance(header.get("kid"), str):
                raise denied
            signing_key = self.keys.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, signing_key.key, algorithms=["ES256", "RS256"],
                                audience="authenticated", issuer=self.issuer,
                                leeway=self.clock_skew_seconds,
                                options={"require": ["exp", "iat", "sub", "iss", "aud"]})
            if claims.get("role") != "authenticated" or claims.get("is_anonymous") is True:
                raise denied
            return Identity(UUID(claims["sub"]), self.issuer)
        except PyJWKClientConnectionError as exc:
            raise HTTPException(503, "No se pudo verificar la identidad; reintentar") from exc
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise denied from exc
