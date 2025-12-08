from pydantic import BaseModel
from typing import TypedDict


class GoogleAuthResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    expires_in: int
    token_type: str
    refresh_token_expires_in: int | None = None
    id_token: str
    scope: str | None = None

    model_config = {"extra": "allow"}


class GoogleCodeLogin(BaseModel):
    code: str
    redirect_uri: str


class UserInfo(BaseModel):
    """Authenticated user information."""

    sub: str
    email: str
    name: str | None = None
    picture: str | None = None


class AuthSuccessResponse(BaseModel):
    """Successful authentication response."""

    message: str
    user: UserInfo
    session_created: bool = True


class GoogleUserInfo(BaseModel):
    """Direct response from Google UserInfo API."""

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
        """Converts GoogleUserInfo to GoogleUserResponse using id as sub."""
        return cls(
            iss=iss,
            azp=aud,  # Use aud as azp
            aud=aud,
            sub=user_info.id,  # id is converted to sub
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


class SessionValidation(TypedDict):
    """TypedDict for successful session validation response."""

    authenticated: bool
    user_sub: str
    session_id: str
    access_token: str
    token_refreshed: bool
    new_session_token: str | None
    refresh_expires_at: int | None
