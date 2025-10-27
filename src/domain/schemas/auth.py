from pydantic import BaseModel
from typing import TypedDict


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str
    refresh_token_expires_in: int
    id_token: str

    model_config = {"extra": "allow"}


class GoogleCodeLogin(BaseModel):
    code: str
    redirect_uri: str


class UserInfo(BaseModel):
    """Información del usuario autenticado."""

    sub: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthSuccessResponse(BaseModel):
    """Respuesta exitosa de autenticación."""

    message: str
    user: UserInfo
    session_created: bool = True


class GoogleUserInfo(BaseModel):
    """Respuesta directa de Google UserInfo API."""

    id: str
    email: str
    verified_email: bool
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    picture: str | None = None

    model_config = {"extra": "allow"}


class GoogleUserResponse(BaseModel):
    iss: str
    azp: str
    aud: str
    sub: str
    email: str
    email_verified: bool
    at_hash: str | None = None
    name: str | None = None
    picture: str | None = None
    given_name: str | None = None
    family_name: str | None = None
    iat: int
    exp: int

    model_config = {"extra": "allow"}

    @classmethod
    def from_user_info(
        cls, user_info: GoogleUserInfo, iss: str, aud: str, iat: int, exp: int
    ) -> "GoogleUserResponse":
        """Convierte GoogleUserInfo a GoogleUserResponse usando id como sub."""
        return cls(
            iss=iss,
            azp=aud,  # Usar aud como azp
            aud=aud,
            sub=user_info.id,  # id se convierte en sub
            email=user_info.email,
            email_verified=user_info.verified_email,
            name=user_info.name,
            picture=user_info.picture,
            given_name=user_info.given_name,
            family_name=user_info.family_name,
            iat=iat,
            exp=exp,
        )


class SessionPayload(TypedDict):
    sub: str
    jti: str
    refresh_at: int
    exp: int
    iat: int


class SessionCookieData(BaseModel):
    key: str
    value: str
    httponly: bool
    secure: bool
    samesite: str
    max_age: int
    path: str


class SessionValidationSuccess(TypedDict):
    """TypedDict para respuesta exitosa de validación de sesión."""

    authenticated: bool
    user_sub: str
    session_id: str
    access_token: str
    token_refreshed: bool
    new_session_token: str
    refresh_expires_at: int | None
