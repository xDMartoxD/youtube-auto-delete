"""Signed `state` values for OAuth flows with third-party providers."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from src.core.config import config

STATE_TTL = timedelta(minutes=10)
_AUDIENCE = "provider-connect"


class OAuthStateService:
    """
    Encodes who started an OAuth flow in a short-lived signed token.

    The callback trusts only the signed `state`, which both identifies the user
    and protects against forged callbacks (CSRF).
    """

    def issue(self, user_id: str, provider: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "provider": provider,
            "aud": _AUDIENCE,
            "jti": uuid4().hex,
            "iat": now,
            "exp": now + STATE_TTL,
        }
        return jwt.encode(payload, config.jwt_secret, algorithm="HS256")

    def verify(self, state: str, provider: str) -> str:
        """Return the user id, or raise ValueError if the state is invalid or expired."""
        try:
            payload = jwt.decode(
                state, config.jwt_secret, algorithms=["HS256"], audience=_AUDIENCE
            )
        except jwt.PyJWTError as e:
            raise ValueError(f"Invalid OAuth state: {e}") from e
        if payload.get("provider") != provider:
            raise ValueError("OAuth state was issued for another provider")
        return payload["sub"]
