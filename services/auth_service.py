"""Auth0 JWT token validation service for FastAPI."""

from __future__ import annotations

import logging
from typing import Any

import requests
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict
import jwt

from config import AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_AUDIENCE

logger = logging.getLogger(__name__)


class TokenPayload(BaseModel):
    """Decoded token payload."""

    model_config = ConfigDict(extra="ignore")

    sub: str
    aud: str | list[str] | None = None
    iss: str | None = None
    exp: int | None = None
    iat: int | None = None
    email: str | None = None
    name: str | None = None
    picture: str | None = None


class AuthService:
    """Service to validate Auth0 JWT tokens."""

    def __init__(
        self,
        domain: str | None = None,
        client_id: str | None = None,
        audience: str | None = None,
    ) -> None:
        self._domain = domain or AUTH0_DOMAIN
        self._client_id = client_id or AUTH0_CLIENT_ID
        self._audience = audience or AUTH0_AUDIENCE
        self._jwks: dict[str, Any] | None = None

    def _get_jwks(self) -> dict[str, Any]:
        """Fetch and cache JWKS from Auth0."""
        if self._jwks is not None:
            return self._jwks

        try:
            jwks_url = f"https://{self._domain}/.well-known/jwks.json"
            response = requests.get(jwks_url, timeout=10)
            response.raise_for_status()
            self._jwks = response.json()
            return self._jwks
        except requests.RequestException as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise HTTPException(status_code=500, detail="Failed to validate token")

    def _get_signing_key(self, token: str) -> dict[str, Any]:
        """Get the signing key for the token from JWKS."""
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.exceptions.DecodeError:
            raise HTTPException(status_code=401, detail="Invalid token format")

        jwks = self._get_jwks()

        for key in jwks.get("keys", []):
            if key.get("kid") == unverified_header.get("kid"):
                return key

        raise HTTPException(status_code=401, detail="Unable to find appropriate key")

    def validate_token(self, token: str) -> TokenPayload:
        """Validate and decode an Auth0 JWT token.

        Args:
            token: The JWT token string

        Returns:
            TokenPayload with the decoded claims

        Raises:
            HTTPException: If token is invalid or expired
        """
        if not all([self._domain, self._client_id, self._audience]):
            logger.warning("Auth0 not fully configured - skipping validation")
            raise HTTPException(status_code=500, detail="Auth0 not configured")

        try:
            signing_key = self._get_signing_key(token)

            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=f"https://{self._domain}/",
                options={
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                },
            )

            return TokenPayload(**payload)
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token has expired")
        except jwt.InvalidAudienceError:
            raise HTTPException(status_code=401, detail="Invalid audience")
        except jwt.InvalidIssuerError:
            raise HTTPException(status_code=401, detail="Invalid issuer")
        except jwt.PyJWTError as e:
            logger.error(f"Token validation failed: {e}")
            raise HTTPException(status_code=401, detail="Invalid token")


# Singleton instance
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get or create Auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# Security scheme for OpenAPI
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> TokenPayload:
    """Dependency to get the current authenticated user.

    Usage:
        @app.get("/protected")
        async def protected(user: TokenPayload = Depends(get_current_user)):
            return {"user": user.sub}
    """
    # Allow bypassing auth if not configured (for development)
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID:
        return TokenPayload(sub="dev-user")

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    auth_service = get_auth_service()
    return auth_service.validate_token(credentials.credentials)


async def get_current_user_with_subject_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> tuple[TokenPayload, str]:
    """Like get_current_user but also returns the raw Bearer token for Token Vault subject_token exchange."""
    if not AUTH0_DOMAIN or not AUTH0_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Token Vault flows require Auth0 (set AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_AUDIENCE).",
        )
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    auth_service = get_auth_service()
    payload = auth_service.validate_token(credentials.credentials)
    return payload, credentials.credentials