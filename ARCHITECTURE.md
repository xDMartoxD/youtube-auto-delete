# Arquitectura del Proyecto

Este documento describe la arquitectura del proyecto YouTube Auto Delete API, basada en **Clean Architecture** y **Domain-Driven Design (DDD)**.

## 📐 Principios Arquitectónicos

### Clean Architecture

El proyecto sigue los principios de Clean Architecture de Robert C. Martin, organizando el código en capas concéntricas:

1. **Domain Layer** (Núcleo): Lógica de negocio pura, sin dependencias externas
2. **Application Layer**: Orquesta casos de uso, coordina domain e infrastructure
3. **Infrastructure Layer**: Implementaciones técnicas (DB, APIs externas, cache)
4. **API Layer**: Presentación, endpoints HTTP

### Domain-Driven Design

- **Agregados**: `UserAggregate` encapsula usuario y sesión con invariantes
- **Entidades**: `Session`, `Suggestion` con identidad única
- **Value Objects**: `Email`, `DateRange`, `TokenExpiration` (inmutables)
- **Servicios de Dominio**: Lógica de negocio que no pertenece a una entidad específica
- **Repositorios**: Interfaces en domain, implementaciones en infrastructure

## 🏛️ Estructura de Capas

```
┌─────────────────────────────────────────┐
│         API Layer (FastAPI)             │
│  - Routers                              │
│  - Dependencies                         │
│  - Middlewares                          │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Application Layer                  │
│  - Application Services                 │
│  - Orquestación de casos de uso         │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│         Domain Layer                    │
│  - Aggregates                           │
│  - Entities                             │
│  - Value Objects                        │
│  - Domain Services                      │
│  - Repository Interfaces                │
└─────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────┐
│      Infrastructure Layer               │
│  - Repository Implementations           │
│  - External Services                    │
│  - Persistence Models                   │
│  - Mappers                              │
└─────────────────────────────────────────┘
```

## 📁 Organización del Código

### `/src/api/` - Capa de Presentación

**Responsabilidad**: Manejar requests HTTP, validación de entrada, respuestas.

```
api/
├── v1/              # Versionado de API
│   ├── auth.py      # Endpoints de autenticación
│   ├── youtube.py   # Endpoints de YouTube
│   ├── suggestions.py
│   └── health.py
├── deps.py          # Dependency injection de FastAPI
└── utils.py         # Utilidades de API
```

**Características**:
- Routers de FastAPI
- Validación con Pydantic schemas
- Dependency injection para servicios
- Manejo de cookies HTTP-only

### `/src/application/` - Capa de Aplicación

**Responsabilidad**: Orquestar casos de uso, coordinar domain e infrastructure.

```
application/
└── services/
    ├── auth_service.py         # Autenticación y sesiones
    ├── youtube_service.py      # Operaciones con YouTube
    └── suggestions_service.py  # Gestión de sugerencias
```

**Principios**:
- **NO contiene lógica de negocio** (esa va en domain)
- Coordina llamadas entre domain e infrastructure
- Maneja transacciones y efectos secundarios
- Transforma entre DTOs y entidades de dominio

**Ejemplo**:
```python
class AuthService:
    async def exchange_code(self, code: str, redirect_uri: str):
        # 1. INFRAESTRUCTURA: Llamar a Google API
        auth_response = await self.client.exchange_code(code, redirect_uri)
        
        # 2. DOMINIO: Crear agregado
        user = UserAggregate.create(...)
        session = user.create_session(...)
        
        # 3. INFRAESTRUCTURA: Persistir
        await self.user_repo.save(user)
        
        # 4. Retornar resultado
        return user_data, session_token
```

### `/src/domain/` - Capa de Dominio

**Responsabilidad**: Lógica de negocio pura, reglas del dominio.

```
domain/
├── aggregates/          # Agregados (entidades raíz)
│   └── user_aggregate.py
├── entities/            # Entidades de dominio
│   ├── session.py
│   └── suggestion.py
├── value_objects/       # Objetos de valor (inmutables)
│   ├── email.py
│   ├── date_range.py
│   └── token_expiration.py
├── services/            # Servicios de dominio
│   ├── session_service.py
│   ├── video_filter_service.py
│   └── suggestion_service.py
├── repositories/        # Interfaces de repositorios
│   ├── user_repository.py
│   └── suggestion_repository.py
└── events/              # Eventos de dominio
    ├── user_authenticated.py
    └── session_refreshed.py
```

#### Agregados

**UserAggregate**: Encapsula usuario y sesión con invariantes de negocio.

```python
@dataclass
class UserAggregate:
    user_id: str
    email: Email
    session: Session | None
    
    def create_session(...) -> Session:
        # Invariante: Solo una sesión activa
        self.session = Session.create(...)
        return self.session
    
    def refresh_session(...):
        # Invariante: Solo refrescar si sesión válida
        if not self.session or not self.session.is_valid():
            raise ValueError("Cannot refresh")
        self.session.update_access_token(...)
```

#### Value Objects

Objetos inmutables que encapsulan validación:

```python
@dataclass(frozen=True)
class Email:
    value: str
    
    def __post_init__(self):
        if not self._is_valid(self.value):
            raise ValueError("Invalid email")
```

#### Servicios de Dominio

Lógica de negocio que no pertenece a una entidad:

```python
class VideoFilterService:
    def filter_by_date_range(self, items, date_from, date_to):
        # Regla de negocio: Filtrar videos por fecha
        # NO depende de infraestructura
```

### `/src/infrastructure/` - Capa de Infraestructura

**Responsabilidad**: Implementaciones técnicas, detalles de frameworks.

```
infrastructure/
├── repositories/        # Implementaciones de repositorios
│   ├── dynamodb_user_repository.py
│   └── dynamodb_suggestion_repository.py
├── persistence/         # Modelos de persistencia
│   ├── models/
│   └── dynamodb/
├── external_services/   # Clientes de APIs externas
│   └── google_client.py
├── services/            # Servicios técnicos
│   ├── cache_service.py
│   └── jwt_service.py
└── mappers/             # Transformadores domain ↔ persistence
    ├── user_mapper.py
    └── suggestion_mapper.py
```

**Principios**:
- Implementa interfaces definidas en domain
- Maneja detalles técnicos (DynamoDB, Redis, HTTP)
- Aísla al resto de la aplicación de frameworks

### `/src/core/` - Configuración Central

```
core/
├── config.py        # Configuración con Pydantic Settings
├── exceptions.py    # Sistema de excepciones centralizado
├── logging.py       # Configuración de logging
├── cache.py         # Cliente Redis
└── lifespan.py      # Lifecycle de FastAPI
```

### `/src/schemas/` - DTOs y Validación

Modelos Pydantic para:
- Validación de requests/responses
- Serialización JSON
- Documentación OpenAPI

```
schemas/
├── auth.py          # Schemas de autenticación
├── youtube.py        # Schemas de YouTube
└── suggestions.py    # Schemas de sugerencias
```

## 🔄 Flujo de Datos

### Ejemplo: Obtener Playlists de Usuario

```
1. Request HTTP
   ↓
2. Router (api/v1/youtube.py)
   - Valida parámetros con Pydantic
   - Obtiene sesión del dependency injection
   ↓
3. Application Service (application/services/youtube_service.py)
   - Verifica caché
   - Si no hay caché, llama a YouTube API
   - Aplica filtros de dominio si es necesario
   - Guarda en caché
   ↓
4. Domain Service (domain/services/video_filter_service.py)
   - Aplica reglas de negocio (filtrado por fecha)
   ↓
5. Infrastructure (infrastructure/external_services/google_client.py)
   - Llama a YouTube API
   ↓
6. Response HTTP
```

## 🔌 Dependency Injection

FastAPI maneja la inyección de dependencias:

```python
# api/deps.py
def get_auth_service(
    user_repo: IUserRepository = Depends(_get_user_repository),
    google_client: GoogleClient = Depends(_get_google_client),
) -> Generator[AuthService, None, None]:
    session_service = SessionService()
    jwt_service = JWTService()
    
    svc = AuthService(
        client=google_client,
        user_repo=user_repo,
        session_service=session_service,
        jwt_service=jwt_service,
    )
    yield svc
```

## 🗄️ Persistencia

### DynamoDB

- **Modelo**: Single-table design con PK/SK
- **Tipos**: `USER#<sub>`, `TOKEN`, `SUGGESTION#<id>`
- **Repositorios**: Implementan interfaces de domain

### Redis/Valkey

- **Uso**: Caché de respuestas de YouTube API
- **TTL**: Configurable por tipo de dato
- **Estrategia**: Cache-aside pattern

## 🛡️ Manejo de Errores

Sistema centralizado con registry pattern:

```python
@register_exception(401, "Authentication failed")
class AuthenticationFailedError(YoutubeAutoDeleteApiError):
    pass
```

## 🧪 Testing

### Estrategia

- **Unit Tests**: Domain layer (sin dependencias)
- **Integration Tests**: API endpoints con mocks
- **Fixtures**: Reutilizables en `tests/conftest.py`

### Estructura

```
tests/
├── unit/
│   ├── test_services/      # Tests de application services
│   └── test_core/          # Tests de core
└── integration/
    └── test_api/           # Tests de endpoints
```

## 📊 Diagrama de Dependencias

```
API Layer
  ↓ depends on
Application Layer
  ↓ depends on
Domain Layer
  ↑ implements
Infrastructure Layer
```

**Regla**: Las dependencias siempre apuntan hacia adentro. Domain no depende de nada externo.

## 🎯 Beneficios de esta Arquitectura

1. **Testabilidad**: Domain layer es fácil de testear sin mocks
2. **Mantenibilidad**: Separación clara de responsabilidades
3. **Flexibilidad**: Cambiar infraestructura sin afectar lógica de negocio
4. **Escalabilidad**: Fácil agregar nuevas features
5. **Claridad**: Código auto-documentado por estructura

## 📚 Referencias

- [Clean Architecture - Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design - Eric Evans](https://www.domainlanguage.com/ddd/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)

---

**Última actualización**: 2024

