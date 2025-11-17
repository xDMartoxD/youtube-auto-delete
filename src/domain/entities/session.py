"""Session entity - represents a user session with business logic."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Self

from src.domain.value_objects.token_expiration import TokenExpiration


@dataclass(slots=True, frozen=False)
class Session:
    """
    Entidad de dominio - representa una sesión de usuario.
    Contiene SOLO lógica de negocio, sin dependencias de infraestructura.
    """

    user_id: str
    access_token: str
    refresh_token: str
    expires_at: int  # Unix timestamp
    refresh_expires_at: int  # Unix timestamp
    session_id: str | None = None

    @classmethod
    def create(
        cls,
        user_id: str,
        access_token: str,
        refresh_token: str,
        expires_at: int,
        refresh_expires_at: int,
        session_id: str | None = None,
    ) -> Self:
        """Create a new session entity."""
        return cls(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            session_id=session_id,
        )

    @property
    def expiration(self) -> TokenExpiration:
        """Get token expiration as value object."""
        return TokenExpiration(
            expires_at=self.expires_at,
            refresh_expires_at=self.refresh_expires_at,
        )

    def needs_refresh(self, current_time: datetime | None = None) -> bool:
        """
        Regla de negocio: el token necesita refrescarse si está expirado.

        Args:
            current_time: Tiempo actual (opcional, usa datetime.now() si no se proporciona)

        Returns:
            True si el access token necesita ser refrescado
        """
        return self.expiration.is_expired(current_time)

    def is_fully_expired(self, current_time: datetime | None = None) -> bool:
        """
        Regla de negocio: sesión completamente expirada si ambos tokens expiraron.

        Args:
            current_time: Tiempo actual (opcional)

        Returns:
            True si ambos tokens (access y refresh) están expirados
        """
        return self.expiration.is_fully_expired(current_time)

    def is_valid(self, current_time: datetime | None = None) -> bool:
        """
        Regla de negocio: sesión válida si el refresh token no ha expirado.

        Args:
            current_time: Tiempo actual (opcional)

        Returns:
            True si la sesión es válida (refresh token no expirado)
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)
        return not self.expiration.is_refresh_expired(current_time)

    def update_access_token(self, new_access_token: str, new_expires_at: int) -> None:
        """
        Actualiza el access token y su expiración.
        Regla de negocio: solo se puede actualizar si la sesión es válida.
        """
        if not self.is_valid():
            raise ValueError("Cannot update access token: session is expired")

        self.access_token = new_access_token
        self.expires_at = new_expires_at

