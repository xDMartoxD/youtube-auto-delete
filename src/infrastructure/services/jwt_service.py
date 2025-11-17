"""JWT service - infrastructure service for JWT encoding/decoding."""

import jwt
import time
import uuid
from typing import Any

from src.core.config import config
from src.schemas.auth import SessionPayload
from src.core.exceptions import AuthenticationFailedError


class JWTService:
    """
    Infrastructure service for JWT operations.
    Encapsulates JWT encoding/decoding logic.
    """

    def encode(
        self,
        user_id: str,
        expires_at: int,
        session_id: str | None = None,
        issued_at: int | None = None,
    ) -> str:
        """
        Generate a JWT session token.

        Args:
            user_id: User identifier (sub claim)
            expires_at: Expiration timestamp
            session_id: Optional session ID (jti claim)
            issued_at: Optional issued at timestamp

        Returns:
            Encoded JWT token string
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        if issued_at is None:
            issued_at = int(time.time())

        payload: SessionPayload = {
            "sub": user_id,
            "jti": session_id,
            "iat": issued_at,
            "exp": expires_at,
        }

        return jwt.encode(dict(payload), config.jwt_secret, algorithm="HS256")

    def decode(self, token: str) -> dict[str, Any]:
        """
        Decode and validate a JWT session token.

        Args:
            token: JWT token string

        Returns:
            Decoded payload dictionary

        Raises:
            AuthenticationFailedError: If token is invalid or expired
        """
        try:
            payload: SessionPayload = jwt.decode(
                token, config.jwt_secret, algorithms=["HS256"]
            )
            return dict(payload)
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailedError(message="Session token expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationFailedError(message=f"Invalid session token: {str(e)}")

