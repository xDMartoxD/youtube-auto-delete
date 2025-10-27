# Mejora: Reutilización de Dependencies en Middleware

## 🎯 **Problema Identificado**

El middleware estaba creando instancias directas de `AuthService` en lugar de reutilizar los dependencies existentes en `api/deps.py`, lo que violaba principios de dependency injection y causaba duplicación.

## 🔧 **Antes vs Después**

### **❌ Diseño Anterior (Problemático)**

```python
def _get_auth_service() -> AuthService:
    """Crea una instancia de AuthService para el middleware."""
    google_client = GoogleClient()  # ❌ Nueva instancia
    auth_repo = AuthRepository()    # ❌ Nueva instancia
    return AuthService(google_client, auth_repo)

# En el middleware:
auth_service = _get_auth_service()  # ❌ Nueva instancia cada vez
```

**Problemas:**

-   ❌ **Duplicación** - Múltiples instancias del mismo servicio
-   ❌ **No reutiliza** - No usa el dependency existente
-   ❌ **Inconsistencia** - Diferentes instancias pueden tener diferentes estados
-   ❌ **Violación DRY** - Código duplicado para crear AuthService
-   ❌ **No cache** - No aprovecha el cache de `@lru_cache`

### **✅ Diseño Mejorado (Correcto)**

```python
def _get_auth_service_from_app(request: Request) -> AuthService:
    """Obtiene AuthService usando las mismas dependencias que los endpoints."""
    # Usar exactamente las mismas dependencias que get_auth_service en deps.py
    google_client = get_google_client(request)  # ✅ Misma instancia del app.state
    auth_repo = get_auth_repository()           # ✅ Misma instancia cacheada
    return AuthService(google_client, auth_repo)

# En el middleware:
auth_service = _get_auth_service_from_app(request)  # ✅ Reutiliza dependencies
```

**Ventajas:**

-   ✅ **Reutilización** - Usa los mismos dependencies que los endpoints
-   ✅ **Consistencia** - Mismas instancias en toda la aplicación
-   ✅ **Cache** - Aprovecha el cache de `@lru_cache`
-   ✅ **DRY** - No duplica lógica de creación de servicios
-   ✅ **Mantenibilidad** - Cambios centralizados en deps.py

## 🏗️ **Implementación Mejorada**

### **1. Importación de Dependencies**

```python
# src/middlewares/session.py
from src.api.deps import get_auth_repository, get_google_client

def _get_auth_service_from_app(request: Request) -> AuthService:
    """Obtiene AuthService usando las mismas dependencias que los endpoints."""
    # Usar exactamente las mismas dependencias que get_auth_service en deps.py
    google_client = get_google_client(request)  # ✅ Del app.state
    auth_repo = get_auth_repository()           # ✅ Cacheado con @lru_cache
    return AuthService(google_client, auth_repo)
```

### **2. Uso en Middleware**

```python
class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # ... lógica de middleware ...

        # ✅ Usar el mismo AuthService que los endpoints
        auth_service = _get_auth_service_from_app(request)
        auth_result = await auth_service.validate_and_refresh_session(session_token)

        # ... resto de la lógica ...
```

### **3. Dependencies Reutilizados**

```python
# src/api/deps.py - Dependencies existentes

@lru_cache
def get_auth_repository() -> AuthRepository:
    """✅ Cacheado - Misma instancia en toda la app"""
    return AuthRepository()

def get_google_client(request: Request) -> GoogleClient:
    """✅ Del app.state - Misma instancia en toda la app"""
    return request.app.state.google_client

def get_auth_service(
    auth_repo: AuthRepository = Depends(get_auth_repository),
    google_client: GoogleClient = Depends(get_google_client),
) -> Generator[AuthService, None, None]:
    """✅ Dependency principal - Usado por endpoints"""
    svc = AuthService(google_client, auth_repo)
    try:
        yield svc
    finally:
        pass
```

## 📊 **Comparación de Diseños**

| Aspecto            | Diseño Anterior                 | Diseño Mejorado          |
| ------------------ | ------------------------------- | ------------------------ |
| **Reutilización**  | ❌ Instancias separadas         | ✅ Mismas dependencias   |
| **Cache**          | ❌ Sin cache                    | ✅ Aprovecha @lru_cache  |
| **Consistencia**   | ❌ Estados diferentes           | ✅ Estado consistente    |
| **DRY**            | ❌ Código duplicado             | ✅ Lógica centralizada   |
| **Mantenibilidad** | ❌ Cambios en múltiples lugares | ✅ Cambios centralizados |

## 🎯 **Ventajas de la Mejora**

### **1. Consistencia de Instancias**

```python
# ✅ Antes: Diferentes instancias
# Middleware: AuthService(GoogleClient(), AuthRepository())
# Endpoint: AuthService(GoogleClient(), AuthRepository())

# ✅ Después: Mismas instancias
# Middleware: AuthService(get_google_client(request), get_auth_repository())
# Endpoint: AuthService(get_google_client(request), get_auth_repository())
```

### **2. Aprovechamiento del Cache**

```python
# ✅ get_auth_repository() usa @lru_cache
@lru_cache
def get_auth_repository() -> AuthRepository:
    return AuthRepository()

# ✅ Misma instancia cacheada en middleware y endpoints
auth_repo = get_auth_repository()  # Cache hit
```

### **3. Reutilización del GoogleClient**

```python
# ✅ get_google_client() usa request.app.state
def get_google_client(request: Request) -> GoogleClient:
    return request.app.state.google_client

# ✅ Misma instancia del lifespan en middleware y endpoints
google_client = get_google_client(request)  # Del app.state
```

### **4. Centralización de Lógica**

```python
# ✅ Cambios en deps.py afectan a toda la aplicación
# ✅ No hay lógica duplicada de creación de servicios
# ✅ Fácil mantenimiento y debugging
```

## 🔄 **Flujo de Dependencies Mejorado**

```mermaid
graph TD
    A[Request] --> B[SessionMiddleware]
    B --> C[_get_auth_service_from_app]
    C --> D[get_google_client]
    C --> E[get_auth_repository]
    D --> F[request.app.state.google_client]
    E --> G[@lru_cache AuthRepository]
    F --> H[AuthService]
    G --> H
    H --> I[validate_and_refresh_session]

    J[Endpoint] --> K[get_auth_service]
    K --> D
    K --> E
    K --> H

    style F fill:#e1f5fe
    style G fill:#e1f5fe
    style H fill:#e8f5e8
```

## 🧪 **Testing Mejorado**

### **1. Mocking Consistente**

```python
def test_middleware_uses_same_dependencies():
    """Test que verifica que el middleware usa las mismas dependencias."""
    # Mock de las dependencias
    mock_google_client = Mock()
    mock_auth_repo = Mock()

    # Mock de las funciones de dependency
    with patch('src.middlewares.session.get_google_client', return_value=mock_google_client):
        with patch('src.middlewares.session.get_auth_repository', return_value=mock_auth_repo):
            # Test que el middleware usa las mismas dependencias
            auth_service = _get_auth_service_from_app(request)
            assert auth_service.client == mock_google_client
            assert auth_service.auth_repo == mock_auth_repo
```

### **2. Testing de Consistencia**

```python
def test_middleware_and_endpoint_use_same_instances():
    """Test que verifica que middleware y endpoints usan las mismas instancias."""
    # Test que las instancias son las mismas
    middleware_auth_service = _get_auth_service_from_app(request)
    endpoint_auth_service = get_auth_service()

    # Verificar que usan las mismas dependencias
    assert middleware_auth_service.client == endpoint_auth_service.client
    assert middleware_auth_service.auth_repo == endpoint_auth_service.auth_repo
```

## 🔍 **Mejores Prácticas Aplicadas**

### **1. Dependency Injection**

```python
# ✅ Bueno: Reutilizar dependencies existentes
def _get_auth_service_from_app(request: Request) -> AuthService:
    google_client = get_google_client(request)
    auth_repo = get_auth_repository()
    return AuthService(google_client, auth_repo)

# ❌ Malo: Crear instancias directamente
def _get_auth_service() -> AuthService:
    google_client = GoogleClient()
    auth_repo = AuthRepository()
    return AuthService(google_client, auth_repo)
```

### **2. DRY (Don't Repeat Yourself)**

```python
# ✅ Bueno: Lógica centralizada en deps.py
# ✅ Middleware y endpoints usan las mismas funciones

# ❌ Malo: Lógica duplicada
# ❌ Middleware crea sus propias instancias
```

### **3. Single Source of Truth**

```python
# ✅ Bueno: Una sola fuente de verdad para dependencies
# ✅ Cambios en deps.py afectan a toda la aplicación

# ❌ Malo: Múltiples fuentes de verdad
# ❌ Cambios requieren modificar múltiples archivos
```

### **4. Cache Utilization**

```python
# ✅ Bueno: Aprovechar cache existente
@lru_cache
def get_auth_repository() -> AuthRepository:
    return AuthRepository()

# ❌ Malo: No aprovechar cache
def _get_auth_service():
    auth_repo = AuthRepository()  # Nueva instancia cada vez
```

## 🎯 **Conclusión**

La mejora de reutilización de dependencies proporciona:

-   ✅ **Consistencia** - Mismas instancias en toda la aplicación
-   ✅ **Eficiencia** - Aprovecha cache y instancias existentes
-   ✅ **Mantenibilidad** - Lógica centralizada en deps.py
-   ✅ **DRY** - No duplica código de creación de servicios
-   ✅ **Testabilidad** - Fácil mocking y testing consistente

**Esta implementación demuestra cómo la reutilización de dependencies puede mejorar significativamente la consistencia y mantenibilidad del código.**
