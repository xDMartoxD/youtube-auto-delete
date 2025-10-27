# db/models/user.py
from dataclasses import dataclass
from typing import Dict, Any, Literal
from src.domain.schemas.auth import GoogleAuthResponse, GoogleUserResponse
from src.db.core import Types
from uuid import uuid4


@dataclass
class TokenModel:
    PK: str
    SK: str
    type: Literal[Types.TOKEN]
    provider: Literal["google"]
    token_id: str
    access_token: str
    refresh_token: str
    token_type: Literal["Bearer"]
    expires_in: int
    refresh_token_expires_in: int
    issued_at: int
    expires_at: int
    refresh_expires_at: int
    GSI2PK: str
    GSI2SK: str
    ttl: int

    @classmethod
    def from_dto(
        cls, auth_dto: GoogleAuthResponse, user_dto: GoogleUserResponse
    ) -> "TokenModel":

        # issued_at: prefer campos del DTO, si no usar ahora
        issued_at = user_dto.iat

        expires_in = auth_dto.expires_in
        refresh_token_expires_in = auth_dto.refresh_token_expires_in

        expires_at = issued_at + expires_in
        refresh_expires_at = issued_at + refresh_token_expires_in

        # token_id: prefer campo explícito, luego id_token/access_token prefix, fallback a uuid
        raw_token_id = (
            getattr(auth_dto, "token_id", None)
            or getattr(auth_dto, "id_token", None)
            or getattr(auth_dto, "access_token", None)
        )
        if raw_token_id:
            token_id = str(raw_token_id)[:16]
        else:
            token_id = uuid4().hex[:8]

        return cls(
            PK=f"{Types.USER.value}#{user_dto.sub}",
            SK=f"{Types.TOKEN.value}",
            type=Types.TOKEN.value,
            provider="google",
            token_id=token_id,
            access_token=getattr(auth_dto, "access_token", ""),
            refresh_token=getattr(auth_dto, "refresh_token", ""),
            token_type=getattr(auth_dto, "token_type", "Bearer"),
            expires_in=expires_in,
            refresh_token_expires_in=refresh_token_expires_in,
            issued_at=issued_at,
            expires_at=expires_at,
            refresh_expires_at=refresh_expires_at,
            GSI2PK=f"{Types.TOKEN.value}#{token_id}",
            GSI2SK=f"{Types.USER.value}#{user_dto.sub}",
            ttl=refresh_expires_at,
        )

    def to_item(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}
