# Propuesta de Arquitectura Multi-Proveedor

> **Estado:** implementado en una versión simplificada. Ver `src/domain/providers/`
> (puerto `PlaylistProvider`), `src/infrastructure/providers/` (adaptador de YouTube y
> proveedores mock para Spotify, Apple Music y Amazon Music) y
> `src/application/services/playlist_management_service.py`. Endpoints en `/v1/providers`.

## 🎯 Objetivo

Reestructurar la arquitectura actual para soportar múltiples proveedores de música/video (YouTube, Spotify, etc.) de manera escalable, manteniendo los principios de Clean Architecture y DDD.

## 📐 Principios de Diseño

1. **Open/Closed Principle**: Abierto para extensión (nuevos proveedores), cerrado para modificación
2. **Dependency Inversion**: Depender de abstracciones, no de implementaciones concretas
3. **Strategy Pattern**: Diferentes estrategias por proveedor
4. **Factory Pattern**: Crear servicios según el proveedor
5. **Separation of Concerns**: Separar lógica de dominio de detalles de infraestructura

## 🏗️ Estructura Propuesta

```
src/
├── domain/
│   ├── providers/                    # 🆕 Abstracciones de proveedores
│   │   ├── __init__.py
│   │   ├── provider_interface.py    # Protocolo base para proveedores
│   │   ├── provider_type.py         # Enum de tipos de proveedor
│   │   └── media_types.py           # Value objects genéricos
│   │
│   ├── entities/
│   │   ├── playlist.py              # 🆕 Entidad genérica de playlist
│   │   ├── media_item.py            # 🆕 Entidad genérica de item (video/track)
│   │   ├── session.py
│   │   └── suggestion.py
│   │
│   └── services/
│       ├── media_filter_service.py  # 🔄 Renombrar de video_filter_service
│       └── ...
│
├── application/
│   ├── providers/                    # 🆕 Servicios de aplicación por proveedor
│   │   ├── __init__.py
│   │   ├── base_provider_service.py # Clase base abstracta
│   │   ├── youtube/
│   │   │   ├── __init__.py
│   │   │   └── youtube_service.py   # 🔄 Mover desde services/
│   │   └── spotify/
│   │       ├── __init__.py
│   │       └── spotify_service.py  # 🆕 Nuevo servicio
│   │
│   └── services/
│       ├── auth_service.py
│       └── suggestions_service.py
│
├── infrastructure/
│   ├── providers/                    # 🆕 Clientes de APIs por proveedor
│   │   ├── __init__.py
│   │   ├── base_provider_client.py  # Clase base para clientes
│   │   ├── youtube/
│   │   │   ├── __init__.py
│   │   │   ├── youtube_client.py    # 🔄 Mover desde external_services/
│   │   │   └── youtube_mapper.py    # 🆕 Mapper YouTube → Domain
│   │   └── spotify/
│   │       ├── __init__.py
│   │       ├── spotify_client.py    # 🆕 Cliente Spotify API
│   │       └── spotify_mapper.py    # 🆕 Mapper Spotify → Domain
│   │
│   └── factories/
│       ├── __init__.py
│       └── provider_factory.py      # 🆕 Factory para crear servicios
│
├── api/
│   └── v1/
│       ├── providers/                # 🆕 Endpoints por proveedor
│       │   ├── __init__.py
│       │   ├── youtube.py           # 🔄 Mover desde v1/
│       │   └── spotify.py            # 🆕 Nuevos endpoints
│       │
│       └── auth.py
│
└── schemas/
    ├── providers/                    # 🆕 Schemas genéricos y específicos
    │   ├── __init__.py
    │   ├── common.py                # Schemas comunes (Pagination, etc.)
    │   ├── youtube.py               # 🔄 Mover desde schemas/
    │   └── spotify.py               # 🆕 Nuevos schemas
    └── ...
```

## 🔌 Interfaces y Abstracciones

### 1. Provider Interface (Domain)

```python
# domain/providers/provider_interface.py
from typing import Protocol, List
from abc import ABC, abstractmethod
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.schemas.providers.common import PaginationParams, DateRangeParams

class IProviderClient(Protocol):
    """Interface para clientes de APIs de proveedores."""
    
    async def get_user_playlists(
        self, 
        pagination: PaginationParams
    ) -> List[Playlist]:
        """Obtener playlists del usuario."""
        ...
    
    async def get_playlist_items(
        self,
        playlist_id: str,
        pagination: PaginationParams
    ) -> List[MediaItem]:
        """Obtener items de una playlist."""
        ...
    
    async def delete_playlist_items(
        self,
        playlist_id: str,
        item_ids: List[str]
    ) -> None:
        """Eliminar items de una playlist."""
        ...

class IProviderService(Protocol):
    """Interface para servicios de aplicación de proveedores."""
    
    async def get_user_playlists(
        self,
        pagination: PaginationParams
    ) -> List[Playlist]:
        """Obtener playlists con caché y lógica de aplicación."""
        ...
    
    async def get_playlist_items(
        self,
        playlist_id: str,
        pagination: PaginationParams,
        date_range: DateRangeParams | None = None
    ) -> List[MediaItem]:
        """Obtener items con filtrado y caché."""
        ...
    
    async def delete_playlist_items(
        self,
        playlist_id: str,
        item_ids: List[str],
        include_private: bool = False,
        include_deleted: bool = False
    ) -> None:
        """Eliminar items con validaciones."""
        ...
```

### 2. Provider Type Enum

```python
# domain/providers/provider_type.py
from enum import Enum

class ProviderType(str, Enum):
    """Tipos de proveedores soportados."""
    YOUTUBE = "youtube"
    SPOTIFY = "spotify"
    # Futuros: APPLE_MUSIC, SOUNDCLOUD, etc.
```

### 3. Entidades de Dominio Genéricas

```python
# domain/entities/playlist.py
from dataclasses import dataclass
from datetime import datetime
from src.domain.providers.provider_type import ProviderType

@dataclass(frozen=True)
class Playlist:
    """Entidad de dominio genérica para playlists."""
    id: str
    provider: ProviderType
    title: str
    description: str | None
    item_count: int
    created_at: datetime
    updated_at: datetime | None
    owner_id: str
    
    def is_empty(self) -> bool:
        """Verificar si la playlist está vacía."""
        return self.item_count == 0

# domain/entities/media_item.py
from dataclasses import dataclass
from datetime import datetime
from src.domain.providers.provider_type import ProviderType

@dataclass(frozen=True)
class MediaItem:
    """Entidad de dominio genérica para items (videos/tracks)."""
    id: str
    provider: ProviderType
    playlist_id: str
    title: str
    description: str | None
    duration_seconds: int | None
    added_at: datetime
    is_private: bool
    is_deleted: bool
    thumbnail_url: str | None
    
    def can_be_deleted(self) -> bool:
        """Verificar si el item puede ser eliminado."""
        return not self.is_deleted
```

## 🏭 Factory Pattern

```python
# infrastructure/factories/provider_factory.py
from typing import Protocol
from src.domain.providers.provider_type import ProviderType
from src.domain.providers.provider_interface import IProviderService
from src.application.providers.youtube.youtube_service import YoutubeService
from src.application.providers.spotify.spotify_service import SpotifyService
from src.schemas.auth import SessionValidation

class ProviderServiceFactory:
    """Factory para crear servicios de proveedores."""
    
    @staticmethod
    def create(
        provider_type: ProviderType,
        session: SessionValidation
    ) -> IProviderService:
        """Crear servicio según el tipo de proveedor."""
        match provider_type:
            case ProviderType.YOUTUBE:
                return YoutubeService(session)
            case ProviderType.SPOTIFY:
                return SpotifyService(session)
            case _:
                raise ValueError(f"Unsupported provider: {provider_type}")
```

## 🔄 Servicio Base Abstracto

```python
# application/providers/base_provider_service.py
from abc import ABC, abstractmethod
from typing import List
from src.domain.providers.provider_interface import IProviderClient, IProviderService
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.domain.services.media_filter_service import MediaFilterService
from src.infrastructure.services.cache_service import CacheService
from src.schemas.providers.common import PaginationParams, DateRangeParams

class BaseProviderService(ABC, IProviderService):
    """Clase base abstracta para servicios de proveedores."""
    
    def __init__(
        self,
        client: IProviderClient,
        filter_service: MediaFilterService | None = None,
        cache_service: CacheService | None = None,
    ):
        self.client = client
        self.filter_service = filter_service or MediaFilterService()
        self.cache_service = cache_service or CacheService()
    
    async def get_user_playlists(
        self,
        pagination: PaginationParams
    ) -> List[Playlist]:
        """Implementación base con caché."""
        cache_key = self._get_playlists_cache_key(pagination)
        
        # Intentar obtener de caché
        cached = await self.cache_service.get_json_cache(cache_key)
        if cached:
            return [Playlist(**item) for item in cached]
        
        # Obtener de API
        playlists = await self.client.get_user_playlists(pagination)
        
        # Guardar en caché
        await self.cache_service.set_json_cache(
            cache_key,
            [p.__dict__ for p in playlists],
            expire=self._get_cache_ttl()
        )
        
        return playlists
    
    @abstractmethod
    def _get_playlists_cache_key(self, pagination: PaginationParams) -> str:
        """Generar clave de caché para playlists."""
        ...
    
    @abstractmethod
    def _get_cache_ttl(self) -> int:
        """Obtener TTL de caché."""
        ...
```

## 📝 Ejemplo: Implementación Spotify

```python
# application/providers/spotify/spotify_service.py
from src.application.providers.base_provider_service import BaseProviderService
from src.infrastructure.providers.spotify.spotify_client import SpotifyClient
from src.schemas.providers.common import PaginationParams
from src.core.config import config

class SpotifyService(BaseProviderService):
    """Servicio de aplicación para Spotify."""
    
    def __init__(self, session: SessionValidation):
        client = SpotifyClient(session)
        super().__init__(client)
        self._user_id = session.get("user_sub")
    
    def _get_playlists_cache_key(self, pagination: PaginationParams) -> str:
        return f"spotify:playlists:{self._user_id}:{pagination.max_results}"
    
    def _get_cache_ttl(self) -> int:
        return config.cache_ttl_user_playlists

# infrastructure/providers/spotify/spotify_client.py
from src.domain.providers.provider_interface import IProviderClient
from src.domain.entities.playlist import Playlist
from src.infrastructure.providers.spotify.spotify_mapper import SpotifyMapper

class SpotifyClient(IProviderClient):
    """Cliente para Spotify Web API."""
    
    def __init__(self, session: SessionValidation):
        self.access_token = session["access_token"]
        # Inicializar cliente de Spotify
    
    async def get_user_playlists(
        self,
        pagination: PaginationParams
    ) -> List[Playlist]:
        # Llamar a Spotify API
        # Mapear respuesta a entidades de dominio
        return SpotifyMapper.to_playlists(api_response)
```

## 🛣️ Endpoints Unificados

```python
# api/v1/providers/youtube.py
from fastapi import APIRouter, Depends, Path
from src.api.deps import current_session_dependency
from src.domain.providers.provider_type import ProviderType
from src.infrastructure.factories.provider_factory import ProviderServiceFactory

router = APIRouter(prefix="/youtube", tags=["YouTube"])

@router.get("/playlists")
async def get_user_playlists(
    session: current_session_dependency,
    pagination: PaginationParams = Depends(),
):
    """Obtener playlists de YouTube."""
    service = ProviderServiceFactory.create(ProviderType.YOUTUBE, session)
    return await service.get_user_playlists(pagination)

# api/v1/providers/spotify.py
router = APIRouter(prefix="/spotify", tags=["Spotify"])

@router.get("/playlists")
async def get_user_playlists(
    session: current_session_dependency,
    pagination: PaginationParams = Depends(),
):
    """Obtener playlists de Spotify."""
    service = ProviderServiceFactory.create(ProviderType.SPOTIFY, session)
    return await service.get_user_playlists(pagination)
```

## 🔄 Plan de Migración

### Fase 1: Preparación (Sin romper código existente)
1. ✅ Crear interfaces y abstracciones en `domain/providers/`
2. ✅ Crear entidades genéricas `Playlist` y `MediaItem`
3. ✅ Crear `BaseProviderService` abstracto
4. ✅ Crear `ProviderServiceFactory`

### Fase 2: Refactorización YouTube
1. Mover `YoutubeService` → `application/providers/youtube/`
2. Mover `GoogleClient` → `infrastructure/providers/youtube/`
3. Hacer que `YoutubeService` extienda `BaseProviderService`
4. Crear `YoutubeMapper` para convertir API → Domain
5. Actualizar endpoints para usar factory

### Fase 3: Implementación Spotify
1. Crear `SpotifyClient` en `infrastructure/providers/spotify/`
2. Crear `SpotifyService` en `application/providers/spotify/`
3. Crear `SpotifyMapper`
4. Crear endpoints en `api/v1/providers/spotify.py`
5. Agregar configuración de Spotify en `config.py`

### Fase 4: Limpieza
1. Eliminar código duplicado
2. Actualizar tests
3. Actualizar documentación

## ✅ Ventajas de esta Arquitectura

1. **Escalabilidad**: Agregar nuevos proveedores es solo crear nuevas implementaciones
2. **Mantenibilidad**: Código común en clases base, específico en implementaciones
3. **Testabilidad**: Fácil mockear interfaces para tests
4. **Consistencia**: Misma estructura para todos los proveedores
5. **Flexibilidad**: Cada proveedor puede tener lógica específica sin afectar otros

## 🎯 Próximos Pasos

1. Revisar y aprobar esta propuesta
2. Crear las interfaces y abstracciones base
3. Refactorizar YouTube gradualmente
4. Implementar Spotify siguiendo el mismo patrón

