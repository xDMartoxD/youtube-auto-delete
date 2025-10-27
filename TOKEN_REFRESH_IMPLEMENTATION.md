# Implementación de Token Refresh - YouTube Service

## 🎯 **Propósito**

El método `_get_valid_access_token` maneja automáticamente la renovación de tokens de acceso de YouTube cuando es necesario, asegurando que el servicio siempre tenga un token válido.

## 🔧 **Funcionalidades Implementadas**

### **1. Verificación de Expiración**

-   ✅ **Verifica access token** - Comprueba si está expirado
-   ✅ **Verifica refresh token** - Asegura que el refresh token sea válido
-   ✅ **Manejo de tiempo** - Usa timestamps UTC para precisión

### **2. Refresh Automático**

-   ✅ **Refresh transparente** - Se ejecuta automáticamente cuando es necesario
-   ✅ **Actualización de DB** - Persiste los nuevos tokens en DynamoDB
-   ✅ **Manejo de errores** - Gestiona fallos de refresh gracefully

### **3. Logging Detallado**

-   ✅ **Logs informativos** - Registra operaciones de refresh
-   ✅ **Logs de error** - Captura y registra errores
-   ✅ **Debug logs** - Información detallada para debugging

## 📋 **Flujo de Funcionamiento**

### **1. Verificación Inicial**

```python
# Obtener datos del token desde la base de datos
token_data = await self.auth_repo.get_token_by_sub(self.user_sub)
if not token_data:
    raise AuthenticationFailedError("No token found for user")
```

### **2. Verificación de Expiración**

```python
current_time = datetime.now(timezone.utc).timestamp()

# Verificar si el access token está expirado
if token_data.expires_at and current_time >= token_data.expires_at:
    # Token expirado, proceder con refresh
```

### **3. Verificación de Refresh Token**

```python
# Verificar si el refresh token también está expirado
if (token_data.refresh_expires_at and
    current_time >= token_data.refresh_expires_at):
    raise AuthenticationFailedError(
        "Both access and refresh tokens expired. Please re-authenticate."
    )
```

### **4. Refresh del Token**

```python
# Refrescar el access token usando el refresh token
refresh_response = await self.google_client.refresh_access_token(
    token_data.refresh_token
)
```

### **5. Actualización en Base de Datos**

```python
# Actualizar los datos del token en la base de datos
update_data = {
    "access_token": refresh_response.access_token,
    "expires_at": int(time.time()) + refresh_response.expires_in,
    "issued_at": int(time.time()),
}

# Si el refresh token cambió, actualizarlo también
if hasattr(refresh_response, 'refresh_token') and refresh_response.refresh_token:
    update_data["refresh_token"] = refresh_response.refresh_token

await self.auth_repo.update_token(self.user_sub, update_data)
```

## 🚀 **Casos de Uso**

### **1. Token Válido**

```python
# Si el token aún es válido, lo retorna directamente
logger.debug(f"Using valid access token for user: {self.user_sub}")
return token_data.access_token
```

### **2. Token Expirado - Refresh Exitoso**

```python
# Log de refresh exitoso
logger.info(f"Successfully refreshed access token for user: {self.user_sub}")
return refresh_response.access_token
```

### **3. Ambos Tokens Expirados**

```python
# Error cuando ambos tokens están expirados
logger.error(f"Both access and refresh tokens expired for user: {self.user_sub}")
raise AuthenticationFailedError(
    "Both access and refresh tokens expired. Please re-authenticate."
)
```

### **4. Error en Refresh**

```python
# Manejo de errores durante el refresh
logger.error(f"Failed to refresh token for user {self.user_sub}: {str(e)}")
raise AuthenticationFailedError(
    "Failed to refresh access token. Please re-authenticate."
)
```

## 🧪 **Testing del Método**

### **1. Test de Token Válido**

```python
async def test_valid_token():
    # Mock token data con expires_at en el futuro
    token_data = TokenModel(
        expires_at=int(time.time()) + 3600,  # 1 hora en el futuro
        access_token="valid_token"
    )

    # El método debería retornar el token sin refresh
    result = await youtube_service._get_valid_access_token()
    assert result == "valid_token"
```

### **2. Test de Token Expirado - Refresh Exitoso**

```python
async def test_expired_token_refresh_success():
    # Mock token data con expires_at en el pasado
    token_data = TokenModel(
        expires_at=int(time.time()) - 3600,  # 1 hora en el pasado
        refresh_token="valid_refresh_token"
    )

    # Mock refresh response
    refresh_response = GoogleAuthResponse(
        access_token="new_access_token",
        expires_in=3600
    )

    # El método debería refrescar y retornar el nuevo token
    result = await youtube_service._get_valid_access_token()
    assert result == "new_access_token"
```

### **3. Test de Ambos Tokens Expirados**

```python
async def test_both_tokens_expired():
    # Mock token data con ambos tokens expirados
    token_data = TokenModel(
        expires_at=int(time.time()) - 3600,
        refresh_expires_at=int(time.time()) - 3600
    )

    # El método debería lanzar AuthenticationFailedError
    with pytest.raises(AuthenticationFailedError):
        await youtube_service._get_valid_access_token()
```

## 📊 **Beneficios de la Implementación**

### **1. Transparencia**

-   ✅ **Automático** - No requiere intervención manual
-   ✅ **Transparente** - Los endpoints no necesitan manejar refresh
-   ✅ **Seamless** - El usuario no nota el refresh

### **2. Robustez**

-   ✅ **Manejo de errores** - Gestiona todos los casos de fallo
-   ✅ **Logging** - Registra todas las operaciones
-   ✅ **Validación** - Verifica tokens antes de usar

### **3. Eficiencia**

-   ✅ **Lazy refresh** - Solo refresca cuando es necesario
-   ✅ **Caching** - Reutiliza tokens válidos
-   ✅ **Performance** - Minimiza llamadas a APIs

## 🔍 **Logs de Ejemplo**

### **Token Válido**

```
DEBUG: Using valid access token for user: 123456789
```

### **Refresh Exitoso**

```
INFO: Access token expired for user: 123456789, refreshing...
INFO: Successfully refreshed access token for user: 123456789
```

### **Ambos Tokens Expirados**

```
ERROR: Both access and refresh tokens expired for user: 123456789
```

### **Error en Refresh**

```
ERROR: Failed to refresh token for user 123456789: HTTP 400 Bad Request
```

## 📋 **Configuración Requerida**

### **Variables de Entorno**

```bash
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
```

### **Dependencias**

-   ✅ `GoogleClient` - Para refresh de tokens
-   ✅ `AuthRepository` - Para persistencia
-   ✅ `AuthenticationFailedError` - Para manejo de errores

## 🎯 **Uso en el Servicio**

```python
# El método se llama automáticamente en _initialize()
async def _initialize(self):
    if self._initialized:
        return

    # Obtener token válido (con refresh automático si es necesario)
    self._access_token = await self._get_valid_access_token()

    # Crear cliente YouTube con token válido
    self._youtube_client = build(
        "youtube", "v3", credentials=Credentials(self._access_token)
    )

    self._initialized = True
```

## 💡 **Recomendaciones**

### **1. Monitoreo**

-   Monitorear logs de refresh para detectar problemas
-   Alertar si hay muchos refreshes fallidos
-   Trackear frecuencia de refresh por usuario

### **2. Optimización**

-   Considerar refresh proactivo antes de expiración
-   Implementar cache de tokens válidos
-   Optimizar queries a la base de datos

### **3. Seguridad**

-   Rotar refresh tokens periódicamente
-   Implementar rate limiting en refresh
-   Logs de seguridad para auditoría

**¡El método está completamente implementado y listo para usar!** 🎉
