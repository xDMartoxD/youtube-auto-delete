"""Domain service for session business rules."""

from datetime import datetime, timezone

from src.domain.entities.session import Session
from src.domain.aggregates.user_aggregate import UserAggregate


class SessionService:
    """
    Servicio de dominio - contiene SOLO lógica de negocio para sesiones.
    NO sabe cómo se guarda en DB o cómo se llama a APIs.
    """

    def should_refresh_token(
        self, session: Session, current_time: datetime | None = None
    ) -> bool:
        """
        Decide si un token debe ser refrescado.
        Regla de negocio: refrescar si el access token está expirado pero el refresh token no.
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # Si el refresh token está expirado, no se puede refrescar
        if session.is_fully_expired(current_time):
            return False

        # Refrescar si el access token está expirado
        return session.needs_refresh(current_time)

    def is_session_expired(
        self, session: Session, current_time: datetime | None = None
    ) -> bool:
        """
        Verifica si una sesión está completamente expirada.
        Regla de negocio: ambos tokens deben estar expirados.
        """
        return session.is_fully_expired(current_time)

    def validate_session(self, session: Session) -> Session:
        """
        Valida que una sesión sea válida.
        Regla de negocio: la sesión debe tener refresh token válido.
        """
        if not session.is_valid():
            raise ValueError("Session is expired")
        return session

    def can_refresh_session(self, user: UserAggregate) -> bool:
        """
        Verifica si se puede refrescar la sesión de un usuario.
        Regla de negocio: debe tener sesión activa y válida.
        """
        if not user.has_active_session():
            return False
        return user.get_session().is_valid()

