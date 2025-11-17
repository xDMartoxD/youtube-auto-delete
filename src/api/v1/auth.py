from fastapi import APIRouter, Depends, status, Response

from src.api.deps import (
    auth_service_dependency,
    current_session_dependency,
)
from src.schemas.auth import (
    GoogleCodeLogin,
    AuthSuccessResponse,
    SessionValidation,
    UserInfo,
)


router = APIRouter()


@router.post(
    "/exchange", status_code=status.HTTP_200_OK, response_model=AuthSuccessResponse
)
async def code_login(
    google_code_login: GoogleCodeLogin,
    response: Response,
    auth_service: auth_service_dependency,
) -> AuthSuccessResponse:
    """
    Intercambia un código de autorización de Google por tokens y crea una sesión.

    - **code**: Código de autorización obtenido de Google OAuth
    - **redirect_uri**: URI de redirección registrada en Google Console

    Retorna información del usuario autenticado y establece una cookie de sesión.
    """
    user_data, session_token, refresh_expires_at = await auth_service.exchange_code(
        google_code_login.code, google_code_login.redirect_uri
    )

    # El endpoint maneja HTTP, el servicio solo retorna datos
    cookie_data = auth_service.get_session_cookie_data(
        session_token, refresh_expires_at
    )

    response.set_cookie(**cookie_data.model_dump())

    return AuthSuccessResponse(
        message="Authentication successful",
        user=UserInfo(
            sub=user_data.sub,
            email=user_data.email,
            name=user_data.name,
            picture=user_data.picture,
        ),
        session_created=True,
    )


@router.post("/logout", status_code=status.HTTP_202_ACCEPTED)
async def logout(
    response: Response,
    auth_service: auth_service_dependency,
    session: current_session_dependency,
) -> dict:
    """
    Logout the current user by clearing the session cookie.
    """

    await auth_service.logout(session)
    response.delete_cookie(
        key="session_token",
        path="/",
        httponly=True,
        secure=True,
        samesite="strict",
    )
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=AuthSuccessResponse)
async def get_user_profile(
    auth_service: auth_service_dependency,
    session: current_session_dependency,
):
    """
    Get current user profile information.

    **Authentication Required**: This endpoint requires a valid session cookie.
    The session cookie is automatically set after successful login via `/auth/exchange`.

    **Cookie Details**:
    - Name: `session_token`
    - Type: HTTP-only cookie
    - Security: Secure, SameSite=Strict
    """
    user_data = await auth_service.get_user_profile(session["access_token"])
    return AuthSuccessResponse(
        message="Authentication successful",
        user=UserInfo(
            sub=user_data.sub,
            email=user_data.email,
            name=user_data.name,
            picture=user_data.picture,
        ),
        session_created=True,
    )
