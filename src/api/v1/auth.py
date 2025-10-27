from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from src.api.deps import get_auth_service
from src.domain.schemas.auth import GoogleCodeLogin, AuthSuccessResponse, UserInfo
from src.domain.services.auth import AuthService

router = APIRouter()


@router.post(
    "/exchange", status_code=status.HTTP_200_OK, response_model=AuthSuccessResponse
)
async def code_login(
    google_code_login: GoogleCodeLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
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


@router.get("/me", response_model=AuthSuccessResponse)
async def get_user_profile(
    request: Request, auth_service: AuthService = Depends(get_auth_service)
):
    user_data = await auth_service.get_user_profile(request.state.user_sub)

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
