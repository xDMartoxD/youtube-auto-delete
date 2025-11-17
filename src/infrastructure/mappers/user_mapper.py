"""Mapper for converting between UserAggregate and TokenModel."""

from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.value_objects.email import Email
from src.infrastructure.persistence.models.token_model import TokenModel


class UserMapper:
    """Mapper for converting between domain UserAggregate and persistence TokenModel."""

    @staticmethod
    def to_domain(
        token_model: TokenModel, email: str | None = None, name: str | None = None, picture: str | None = None
    ) -> UserAggregate:
        """
        Convert TokenModel to UserAggregate.
        
        Args:
            token_model: TokenModel from persistence
            email: User email (not stored in TokenModel, must be provided)
            name: User name (optional)
            picture: User picture (optional)
        """
        # Extract user_id from PK (format: "USER#{user_id}")
        user_id = token_model.PK.split("#")[1] if "#" in token_model.PK else token_model.PK

        # Email is required for UserAggregate
        if not email:
            # Use a placeholder if email not provided (shouldn't happen in normal flow)
            email = f"{user_id}@unknown.com"

        # Create user aggregate
        user = UserAggregate.create(
            user_id=user_id,
            email=email,
            name=name,
            picture=picture,
        )

        # Create session if we have token data
        if token_model.access_token and token_model.refresh_token:
            user.create_session(
                access_token=token_model.access_token,
                refresh_token=token_model.refresh_token,
                expires_at=token_model.expires_at,
                refresh_expires_at=token_model.refresh_expires_at,
                session_id=None,  # TokenModel doesn't have session_id
            )

        return user

    @staticmethod
    def to_persistence(
        user: UserAggregate, token_model_base: TokenModel
    ) -> TokenModel:
        """
        Convert UserAggregate to TokenModel.
        Requires a base TokenModel for fields not in the aggregate.
        """
        if not user.session:
            raise ValueError("Cannot convert UserAggregate to TokenModel: no session")

        # Update the base model with session data from aggregate
        return TokenModel(
            PK=token_model_base.PK,
            SK=token_model_base.SK,
            type=token_model_base.type,
            provider=token_model_base.provider,
            token_id=token_model_base.token_id,
            access_token=user.session.access_token,
            refresh_token=user.session.refresh_token,
            token_type=token_model_base.token_type,
            expires_in=token_model_base.expires_in,
            refresh_token_expires_in=token_model_base.refresh_token_expires_in,
            issued_at=token_model_base.issued_at,
            expires_at=user.session.expires_at,
            refresh_expires_at=user.session.refresh_expires_at,
            GSI2PK=token_model_base.GSI2PK,
            GSI2SK=token_model_base.GSI2SK,
            ttl=user.session.refresh_expires_at,
        )

