"""DynamoDB implementation of IUserRepository."""

import logging
from typing import Dict, Any
from datetime import datetime, timezone

from src.domain.aggregates.user_aggregate import UserAggregate
from src.domain.repositories.user_repository import IUserRepository
from src.infrastructure.persistence.base_repository import BaseRepository
from src.infrastructure.persistence.models.token_model import TokenModel
from src.infrastructure.persistence.dynamodb.types import Types
from src.infrastructure.mappers.user_mapper import UserMapper
from src.infrastructure.services.cache_service import CacheService
from src.core.config import config

logger = logging.getLogger(__name__)


class DynamoDBUserRepository(BaseRepository[TokenModel], IUserRepository):
    """DynamoDB implementation of IUserRepository."""

    def __init__(self, cache_service: CacheService | None = None) -> None:
        super().__init__()
        self.cache_service = cache_service or CacheService()
        self.session_cache_ttl = config.cache_ttl_user_session

    def _prepare_item(self, item: TokenModel) -> Dict[str, Any]:
        """Prepare TokenModel for DynamoDB."""
        return item.to_item()

    async def save(
        self, user: UserAggregate, token_model: TokenModel | None = None
    ) -> None:
        """
        Save or update a user aggregate.
        
        Args:
            user: User aggregate to save
            token_model: Optional TokenModel for initial insert. If not provided,
                        will look for existing token to update.
        """
        if not user.session:
            raise ValueError("Cannot save user without session")

        # Get existing token model if it exists
        existing_token = await self.get_token_by_sub(user.user_id)

        if existing_token:
            # Update existing token
            token_model = UserMapper.to_persistence(user, existing_token)
        elif token_model:
            # Initial insert: use provided token_model and update with session data
            token_model = UserMapper.to_persistence(user, token_model)
        else:
            # No existing token and no token_model provided
            raise ValueError(
                "Cannot save user without existing TokenModel or provided token_model. "
                "Either provide token_model for initial insert, or ensure token exists."
            )

        await self.insert(token_model)
        # Invalidate cache after update
        await self._invalidate_session_cache(user.user_id)

    async def find_by_id(self, user_id: str) -> UserAggregate | None:
        """Find a user by ID."""
        token_model = await self.get_token_by_sub(user_id)
        if not token_model:
            return None

        # We need email, name, picture from somewhere - they're not in TokenModel
        # In a real implementation, we might need a separate UserProfile table
        # For now, we'll use placeholders and the application layer should provide them
        return UserMapper.to_domain(token_model, email=None, name=None, picture=None)

    async def find_by_email(self, email: str) -> UserAggregate | None:
        """Find a user by email."""
        # TokenModel doesn't store email, so we can't search by email directly
        # This would require a GSI or separate table in a real implementation
        # For now, return None - this method may not be fully implementable with current schema
        logger.warning(
            "find_by_email not fully supported with current TokenModel schema"
        )
        return None

    async def delete(self, user_id: str) -> None:
        """Delete a user."""
        key = {"PK": f"{Types.USER.value}#{user_id}", "SK": Types.TOKEN.value}
        await self.delete_item(key)
        # Invalidate cache after delete
        await self._invalidate_session_cache(user_id)

    # Helper methods for backward compatibility
    async def get_token_by_sub(self, sub: str) -> TokenModel | None:
        """Get token by user sub (for internal use)."""
        # Try to get from cache first
        cached_data = await self.cache_service.get("user_session", user_id=sub)

        if cached_data:
            logger.debug(f"Cache hit for user session: {sub}")
            try:
                token_model = TokenModel(**cached_data)
                # Validate token expiration before returning from cache
                current_timestamp = int(datetime.now(timezone.utc).timestamp())

                # If refresh token is expired, token is invalid - invalidate cache and fetch fresh
                if current_timestamp >= token_model.refresh_expires_at:
                    logger.info(
                        f"Token expired in cache for user {sub} (refresh_expires_at: {token_model.refresh_expires_at}). "
                        "Invalidating cache and fetching from DB."
                    )
                    await self._invalidate_session_cache(sub)
                    # Fall through to fetch from DB
                else:
                    # Token is still valid, return from cache
                    return token_model
            except Exception as e:
                logger.warning(f"Error deserializing cached token for user {sub}: {e}")
                # Fall through to fetch from DB

        # Cache miss or expired - fetch from DynamoDB
        logger.debug(f"Cache miss/expired for user session: {sub}")
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}
        item = await self.get_item(key)

        if item:
            token_model = TokenModel(**item)
            # Calculate cache TTL based on token expiration
            # Use the minimum of: configured TTL or time until refresh token expires
            current_timestamp = int(datetime.now(timezone.utc).timestamp())
            time_until_refresh_expiry = (
                token_model.refresh_expires_at - current_timestamp
            )

            # Only cache if token is not already expired
            if time_until_refresh_expiry > 0:
                # Use minimum of configured TTL or time until refresh expires (with 60s buffer)
                cache_ttl = min(
                    self.session_cache_ttl, max(60, time_until_refresh_expiry - 60)
                )

                # Cache the result
                await self.cache_service.set(
                    "user_session",
                    item,  # item is already a dict
                    cache_ttl,
                    user_id=sub,
                )
                logger.debug(f"Cached token for user {sub} with TTL: {cache_ttl}s")
            else:
                logger.debug(f"Token already expired for user {sub}, not caching")

            return token_model
        return None

    async def insert_token_model(self, token_model: TokenModel) -> None:
        """Insert a new TokenModel (for initial token creation)."""
        await self.insert(token_model)
        # Invalidate cache after insert
        user_id = (
            token_model.PK.split("#")[1] if "#" in token_model.PK else token_model.PK
        )
        await self._invalidate_session_cache(user_id)

    async def update_token(self, sub: str, token_data: Dict[str, Any]) -> None:
        """Update token data (for internal use)."""
        key = {"PK": f"{Types.USER.value}#{sub}", "SK": Types.TOKEN.value}

        update_expression = "SET "
        expression_attribute_values: Dict[str, Any] = {}
        expression_attribute_names: Dict[str, str] = {}

        for i, (field, value) in enumerate(token_data.items()):
            if i > 0:
                update_expression += ", "
            placeholder = f":val{i}"
            name_placeholder = f"#{field}"
            update_expression += f"{name_placeholder} = {placeholder}"
            expression_attribute_values[placeholder] = value
            expression_attribute_names[name_placeholder] = field

        await self.update_item(
            key=key,
            update_expression=update_expression,
            expression_attribute_values=expression_attribute_values,
            expression_attribute_names=expression_attribute_names,
        )
        # Invalidate cache after update
        await self._invalidate_session_cache(sub)

    async def _invalidate_session_cache(self, user_id: str) -> None:
        """Invalidate session cache for a user."""
        try:
            await self.cache_service.invalidate("user_session", user_id=user_id)
            logger.debug(f"Invalidated session cache for user: {user_id}")
        except Exception as e:
            logger.warning(f"Error invalidating session cache for user {user_id}: {e}")
