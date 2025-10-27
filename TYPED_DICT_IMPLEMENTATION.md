# Tipado Mejorado: TypedDict para Autenticación

## 🎯 **Mejoras de Tipado Implementadas**

Se han agregado TypedDict para mejorar el tipado estático y la experiencia de desarrollo en el sistema de autenticación.

## 🔧 **1. TypedDict para AuthenticationResult**

### **Definición del TypedDict**

```python
class AuthenticationResult(TypedDict):
    """Resultado de la validación de autenticación."""
    authenticated: bool
    user_sub: Optional[str]
    session_id: Optional[str]
    access_token: Optional[str]
    token_data: Optional[TokenModel]
    token_refreshed: bool
    new_session_token: Optional[str]
    refresh_expires_at: Optional[int]
    error: Optional[str]
    status_code: Optional[int]
```

### **Uso en AuthService**

```python
class AuthService:
    async def validate_and_refresh_session(self, session_token: str) -> AuthenticationResult:
        """
        Valida el token de sesión y refresca el access token si es necesario.
        Retorna información completa para el middleware.
        """
        try:
            # ... lógica de validación ...

            return {
                "authenticated": True,
                "user_sub": user_sub,
                "session_id": session_id,
                "access_token": current_access_token,
                "token_data": updated_token_data,
                "token_refreshed": token_refreshed,
                "new_session_token": new_session_token,
                "refresh_expires_at": refresh_expires_at,
                "error": None,
                "status_code": None,
            }
        except jwt.ExpiredSignatureError:
            return {
                "authenticated": False,
                "user_sub": None,
                "session_id": None,
                "access_token": None,
                "token_data": None,
                "token_refreshed": False,
                "new_session_token": None,
                "refresh_expires_at": None,
                "error": "Session expired",
                "status_code": 401,
            }
```

## 🔧 **2. TypedDict para RequestState**

### **Definición del TypedDict**

```python
class RequestState(TypedDict):
    """Estado del request después de la autenticación."""
    user_sub: Optional[str]
    session_id: Optional[str]
    access_token: Optional[str]
    token_data: Optional[TokenModel]
    token_refreshed: bool
    new_session_token: Optional[str]
```

### **Función Helper para Request State**

```python
def get_request_state(request: Request) -> RequestState:
    """Obtiene el estado del request con tipado correcto."""
    return RequestState(
        user_sub=getattr(request.state, 'user_sub', None),
        session_id=getattr(request.state, 'session_id', None),
        access_token=getattr(request.state, 'access_token', None),
        token_data=getattr(request.state, 'token_data', None),
        token_refreshed=getattr(request.state, 'token_refreshed', False),
        new_session_token=getattr(request.state, 'new_session_token', None),
    )
```

## 🔧 **3. Dependency para Request State**

### **Dependency Function**

```python
def get_request_state_dependency(request: Request) -> RequestState:
    """Dependency para obtener el estado del request con tipado correcto."""
    return get_request_state(request)
```

### **Uso en Endpoints**

```python
@router.get("/user-info", status_code=status.HTTP_200_OK)
async def get_user_info(
    request_state: RequestState = Depends(get_request_state_dependency),
) -> dict:
    """Get current user information from request state."""
    return {
        "user_sub": request_state["user_sub"],
        "session_id": request_state["session_id"],
        "token_refreshed": request_state["token_refreshed"],
    }
```

## 🔧 **4. Dependency Mejorado para YouTube Service**

### **Dependency con Tipado**

```python
async def get_youtube_service_for_user(
    request: Request,
    google_client: GoogleClient = Depends(get_google_client),
    auth_repo: AuthRepository = Depends(get_auth_repository),
    request_state: RequestState = Depends(get_request_state_dependency),
) -> YoutubeService:
    """Create and initialize YouTube service for authenticated user."""
    if not request_state["user_sub"]:
        raise HTTPException(status_code=401, detail="Authentication required")

    service = YoutubeService(
        google_client,
        auth_repo,
        request_state["user_sub"],
        request_state["access_token"]
    )
    await service.initialize()
    return service
```

## 🎯 **Ventajas del Tipado Mejorado**

### **1. Type Safety**

```python
# ✅ Antes: Sin tipado
def process_auth_result(result: dict):
    user_sub = result["user_sub"]  # ❌ No hay verificación de tipos
    if result["authenticated"]:    # ❌ No hay verificación de tipos
        pass

# ✅ Después: Con TypedDict
def process_auth_result(result: AuthenticationResult):
    user_sub = result["user_sub"]  # ✅ Tipo verificado: Optional[str]
    if result["authenticated"]:    # ✅ Tipo verificado: bool
        pass
```

### **2. IntelliSense Mejorado**

```python
# ✅ El IDE ahora proporciona autocompletado
auth_result: AuthenticationResult = await auth_service.validate_and_refresh_session(token)

# ✅ Autocompletado disponible para todas las claves
auth_result["authenticated"]  # ✅ bool
auth_result["user_sub"]       # ✅ Optional[str]
auth_result["token_data"]     # ✅ Optional[TokenModel]
```

### **3. Detección de Errores en Tiempo de Desarrollo**

```python
# ❌ Error detectado por el linter
auth_result: AuthenticationResult = {
    "authenticated": True,
    "user_sub": "123",
    "invalid_key": "value",  # ❌ Error: clave no existe en TypedDict
}

# ❌ Error detectado por el linter
auth_result: AuthenticationResult = {
    "authenticated": "true",  # ❌ Error: tipo incorrecto (str en lugar de bool)
    "user_sub": "123",
}
```

### **4. Documentación Automática**

```python
# ✅ Los TypedDict sirven como documentación
class AuthenticationResult(TypedDict):
    """Resultado de la validación de autenticación."""
    authenticated: bool                    # ✅ Indica si la autenticación fue exitosa
    user_sub: Optional[str]               # ✅ ID del usuario (puede ser None)
    session_id: Optional[str]              # ✅ ID de la sesión (puede ser None)
    access_token: Optional[str]            # ✅ Token de acceso (puede ser None)
    token_data: Optional[TokenModel]       # ✅ Datos completos del token (puede ser None)
    token_refreshed: bool                  # ✅ Indica si el token fue refrescado
    new_session_token: Optional[str]       # ✅ Nuevo token de sesión (puede ser None)
    refresh_expires_at: Optional[int]      # ✅ Timestamp de expiración del refresh token
    error: Optional[str]                   # ✅ Mensaje de error (puede ser None)
    status_code: Optional[int]             # ✅ Código de estado HTTP (puede ser None)
```

## 📊 **Comparación: Antes vs Después**

| Aspecto             | Antes                   | Después                              |
| ------------------- | ----------------------- | ------------------------------------ |
| **Type Safety**     | ❌ `dict` sin tipado    | ✅ `TypedDict` con tipos específicos |
| **IntelliSense**    | ❌ Sin autocompletado   | ✅ Autocompletado completo           |
| **Error Detection** | ❌ Errores en runtime   | ✅ Errores en tiempo de desarrollo   |
| **Documentation**   | ❌ Comentarios manuales | ✅ Documentación automática          |
| **Refactoring**     | ❌ Propenso a errores   | ✅ Refactoring seguro                |

## 🧪 **Ejemplos de Uso**

### **1. En Middleware**

```python
class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ... lógica de middleware ...

        # ✅ Tipado correcto del resultado
        auth_result: AuthenticationResult = await auth_service.validate_and_refresh_session(session_token)

        if not auth_result["authenticated"]:
            return JSONResponse(
                content={"detail": auth_result["error"]},
                status_code=auth_result["status_code"],
            )

        # ✅ Tipado correcto al asignar al request.state
        request.state.user_sub = auth_result["user_sub"]
        request.state.access_token = auth_result["access_token"]
        # ...
```

### **2. En Endpoints**

```python
@router.get("/profile")
async def get_profile(
    request_state: RequestState = Depends(get_request_state_dependency),
) -> dict:
    """Get user profile using typed request state."""
    # ✅ Tipado correcto del request state
    if not request_state["user_sub"]:
        raise HTTPException(status_code=401, detail="Authentication required")

    return {
        "user_id": request_state["user_sub"],
        "session_id": request_state["session_id"],
        "token_refreshed": request_state["token_refreshed"],
    }
```

### **3. En Tests**

```python
def test_auth_service_returns_typed_result():
    """Test que verifica que el servicio retorna el tipo correcto."""
    auth_service = AuthService(mock_client, mock_repo)

    # ✅ El resultado está tipado
    result: AuthenticationResult = await auth_service.validate_and_refresh_session("token")

    # ✅ Verificaciones de tipo
    assert isinstance(result["authenticated"], bool)
    assert isinstance(result["user_sub"], (str, type(None)))
    assert isinstance(result["token_refreshed"], bool)
```

## 🔍 **Mejores Prácticas**

### **1. Usar TypedDict para Estructuras de Datos**

```python
# ✅ Bueno: TypedDict para estructuras complejas
class UserProfile(TypedDict):
    id: str
    email: str
    name: Optional[str]
    created_at: datetime

# ❌ Malo: dict sin tipado
def get_user_profile() -> dict:
    return {"id": "123", "email": "user@example.com"}
```

### **2. Documentar TypedDict**

```python
# ✅ Bueno: Documentación clara
class AuthenticationResult(TypedDict):
    """
    Resultado de la validación de autenticación.

    Attributes:
        authenticated: Indica si la autenticación fue exitosa
        user_sub: ID del usuario (None si no autenticado)
        token_refreshed: Indica si el token fue refrescado automáticamente
    """
    authenticated: bool
    user_sub: Optional[str]
    token_refreshed: bool
```

### **3. Usar Optional para Campos Opcionales**

```python
# ✅ Bueno: Campos opcionales claramente marcados
class RequestState(TypedDict):
    user_sub: Optional[str]        # Puede ser None si no autenticado
    access_token: Optional[str]    # Puede ser None si no autenticado
    token_refreshed: bool          # Siempre presente
```

### **4. Validar Tipos en Runtime (Opcional)**

```python
# ✅ Opcional: Validación en runtime para casos críticos
def validate_auth_result(result: dict) -> AuthenticationResult:
    """Valida que el resultado tenga la estructura correcta."""
    required_keys = {"authenticated", "user_sub", "token_refreshed"}
    if not required_keys.issubset(result.keys()):
        raise ValueError("Invalid authentication result structure")

    return result  # type: ignore
```

## 🎯 **Conclusión**

El tipado mejorado con TypedDict proporciona:

-   ✅ **Type Safety** - Detección de errores en tiempo de desarrollo
-   ✅ **Mejor DX** - IntelliSense y autocompletado mejorados
-   ✅ **Documentación** - Tipos sirven como documentación automática
-   ✅ **Refactoring Seguro** - Cambios de estructura detectados automáticamente
-   ✅ **Mantenibilidad** - Código más fácil de mantener y entender

**Esta implementación demuestra cómo el tipado estático puede mejorar significativamente la calidad del código y la experiencia de desarrollo.**
