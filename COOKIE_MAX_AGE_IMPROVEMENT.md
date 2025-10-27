# Mejora: Cookie max_age basado en Refresh Token

## 🎯 **Problema Identificado**

Anteriormente, la cookie de sesión tenía un `max_age` hardcodeado de 900 segundos (15 minutos), independientemente de la duración real del refresh token.

### **Problemas del Enfoque Anterior:**
- ❌ **Inconsistencia** - Cookie y refresh token con duraciones diferentes
- ❌ **Sesiones cortas** - Cookie expiraba antes que el refresh token
- ❌ **Experiencia pobre** - Usuarios tenían que re-autenticarse innecesariamente
- ❌ **Desperdicio de recursos** - Refresh tokens válidos no utilizados

## ✅ **Solución Implementada**

### **1. Cálculo Dinámico de max_age**

```python
def set_session_cookie(self, response: Response, session_token: str, refresh_expires_at: int) -> None:
    """Establece la cookie de sesión en la respuesta HTTP."""
    # Calcular max_age basado en refresh_expires_at
    current_time = int(time.time())
    max_age = max(0, refresh_expires_at - current_time)
    
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=max_age,  # Duración basada en refresh token
        path="/",
    )
```

### **2. Retorno de refresh_expires_at**

```python
async def exchange_code(
    self, code: str, redirect_uri: str
) -> tuple[GoogleUserResponse, str, int]:
    """
    Exchange code and persist user data.
    Returns user data, session token, and refresh_expires_at.
    """
    # ... lógica de exchange ...
    
    # Retornar datos del usuario, token de sesión y refresh_expires_at
    return user_response, session_token, token_model.refresh_expires_at
```

### **3. Uso en Endpoint**

```python
@router.post("/exchange")
async def code_login(
    google_code_login: GoogleCodeLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthSuccessResponse:
    user_data, session_token, refresh_expires_at = await auth_service.exchange_code(
        google_code_login.code, google_code_login.redirect_uri
    )

    # Establecer cookie de sesión con duración basada en refresh token
    auth_service.set_session_cookie(response, session_token, refresh_expires_at)
    
    return AuthSuccessResponse(...)
```

## 📊 **Comparación: Antes vs Después**

### **Antes (Hardcoded)**
```python
# Cookie siempre expira en 15 minutos
max_age=900  # 15 minutos fijos
```

**Problemas:**
- ❌ Cookie expira en 15 min
- ❌ Refresh token válido por 6 meses
- ❌ Usuario debe re-autenticarse cada 15 min
- ❌ Desperdicio del refresh token

### **Después (Dinámico)**
```python
# Cookie expira cuando expira el refresh token
max_age = refresh_expires_at - current_time
```

**Beneficios:**
- ✅ Cookie expira cuando refresh token expira
- ✅ Sesión dura tanto como el refresh token
- ✅ Usuario no necesita re-autenticarse
- ✅ Aprovecha toda la duración del refresh token

## 🎯 **Ejemplos Prácticos**

### **Caso 1: Refresh Token de 6 meses**
```python
# Refresh token expira en 6 meses
refresh_expires_at = 1640995200  # 6 meses desde ahora
current_time = 1609459200        # Ahora

max_age = 1640995200 - 1609459200 = 31536000  # 6 meses
# Cookie durará 6 meses
```

### **Caso 2: Refresh Token próximo a expirar**
```python
# Refresh token expira en 1 hora
refresh_expires_at = 1609462800  # 1 hora desde ahora
current_time = 1609459200        # Ahora

max_age = 1609462800 - 1609459200 = 3600  # 1 hora
# Cookie durará 1 hora
```

### **Caso 3: Refresh Token ya expirado**
```python
# Refresh token ya expirado
refresh_expires_at = 1609455600  # 1 hora atrás
current_time = 1609459200        # Ahora

max_age = max(0, 1609455600 - 1609459200) = 0  # 0 segundos
# Cookie expira inmediatamente
```

## 🔧 **Beneficios de la Mejora**

### **1. Consistencia**
- ✅ **Sincronización** - Cookie y refresh token expiran juntos
- ✅ **Coherencia** - No hay discrepancias de tiempo
- ✅ **Predecibilidad** - Comportamiento consistente

### **2. Experiencia de Usuario**
- ✅ **Sesiones largas** - Usuario no necesita re-autenticarse
- ✅ **Sin interrupciones** - Trabajo continuo sin interrupciones
- ✅ **Eficiencia** - Aprovecha toda la duración del token

### **3. Seguridad**
- ✅ **Misma duración** - No hay ventanas de seguridad adicionales
- ✅ **Control granular** - Cookie expira cuando debe expirar
- ✅ **Sin vulnerabilidades** - No hay tokens válidos sin sesión

### **4. Arquitectura**
- ✅ **Lógica centralizada** - Un solo lugar para calcular duración
- ✅ **Mantenibilidad** - Fácil de entender y modificar
- ✅ **Escalabilidad** - Funciona con cualquier duración de token

## 🧪 **Testing de la Mejora**

### **Test 1: Cookie con Refresh Token Válido**
```python
async def test_cookie_max_age_with_valid_refresh():
    # Mock refresh token que expira en 1 hora
    refresh_expires_at = int(time.time()) + 3600
    
    # Llamar set_session_cookie
    auth_service.set_session_cookie(response, session_token, refresh_expires_at)
    
    # Verificar que max_age sea aproximadamente 3600
    assert response.cookies["session_token"]["max_age"] == 3600
```

### **Test 2: Cookie con Refresh Token Expirado**
```python
async def test_cookie_max_age_with_expired_refresh():
    # Mock refresh token ya expirado
    refresh_expires_at = int(time.time()) - 3600
    
    # Llamar set_session_cookie
    auth_service.set_session_cookie(response, session_token, refresh_expires_at)
    
    # Verificar que max_age sea 0
    assert response.cookies["session_token"]["max_age"] == 0
```

### **Test 3: Cookie con Refresh Token de Larga Duración**
```python
async def test_cookie_max_age_with_long_refresh():
    # Mock refresh token que expira en 6 meses
    refresh_expires_at = int(time.time()) + (6 * 30 * 24 * 3600)
    
    # Llamar set_session_cookie
    auth_service.set_session_cookie(response, session_token, refresh_expires_at)
    
    # Verificar que max_age sea aproximadamente 6 meses
    expected_max_age = 6 * 30 * 24 * 3600
    assert abs(response.cookies["session_token"]["max_age"] - expected_max_age) < 60
```

## 📋 **Configuración por Entorno**

### **Desarrollo**
```python
# Refresh tokens de larga duración para desarrollo
refresh_token_expires_in = 30 * 24 * 3600  # 30 días
```

### **Producción**
```python
# Refresh tokens de duración estándar para producción
refresh_token_expires_in = 6 * 30 * 24 * 3600  # 6 meses
```

### **Testing**
```python
# Refresh tokens cortos para testing
refresh_token_expires_in = 3600  # 1 hora
```

## 🎯 **Recomendaciones**

### **1. Monitoreo**
- Monitorear duraciones de cookies en logs
- Alertar si hay discrepancias grandes
- Trackear patrones de expiración

### **2. Configuración**
- Considerar límites máximos para cookies
- Implementar validación de duraciones
- Documentar políticas de duración

### **3. Seguridad**
- Revisar duraciones de refresh tokens
- Implementar rotación de tokens
- Monitorear sesiones anómalas

## 💡 **Conclusión**

Esta mejora asegura que:

- ✅ **Cookie y refresh token** tengan la misma duración
- ✅ **Usuarios** no necesiten re-autenticarse innecesariamente
- ✅ **Recursos** se aprovechen al máximo
- ✅ **Experiencia** sea consistente y fluida

**¡La implementación está completa y funcionando!** 🎉
