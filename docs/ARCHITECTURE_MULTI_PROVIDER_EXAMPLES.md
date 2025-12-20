# Ejemplos de Código - Arquitectura Multi-Proveedor

## 1. Interfaces de Dominio

```python
# domain/providers/provider_interface.py
from typing import Protocol, List
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.schemas.providers.common import PaginationParams

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

## 2. Entidades de Dominio

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

## 3. Servicio Base

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

## 4. Implementación YouTube (Refactorizada)

```python
# application/providers/youtube/youtube_service.py
from src.application.providers.base_provider_service import BaseProviderService
from src.infrastructure.providers.youtube.youtube_client import YoutubeClient
from src.domain.services.media_filter_service import MediaFilterService
from src.infrastructure.services.cache_service import CacheService
from src.schemas.auth import SessionValidation
from src.schemas.providers.common import PaginationParams, DateRangeParams
from src.core.config import config

class YoutubeService(BaseProviderService):
    """Servicio de aplicación para YouTube."""
    
    def __init__(
        self,
        session: SessionValidation,
        filter_service: MediaFilterService | None = None,
        cache_service: CacheService | None = None,
    ):
        client = YoutubeClient(session)
        super().__init__(client, filter_service, cache_service)
        self._user_id = session.get("user_sub")
        self._youtube_client = None  # Inicializado en initialize()
    
    async def initialize(self) -> None:
        """Inicializar cliente de YouTube."""
        if self._youtube_client is None:
            credentials = Credentials(self._session["access_token"])
            self._youtube_client = await asyncio.to_thread(
                build, "youtube", "v3", credentials=credentials
            )
            # Actualizar cliente con instancia inicializada
            self.client.set_client(self._youtube_client)
    
    def _get_playlists_cache_key(self, pagination: PaginationParams) -> str:
        return f"youtube:playlists:{self._user_id}:{pagination.max_results}:{pagination.page_token or ''}"
    
    def _get_cache_ttl(self) -> int:
        return config.cache_ttl_user_playlists
```

## 5. Implementación Spotify (Nueva)

```python
# application/providers/spotify/spotify_service.py
from src.application.providers.base_provider_service import BaseProviderService
from src.infrastructure.providers.spotify.spotify_client import SpotifyClient
from src.domain.services.media_filter_service import MediaFilterService
from src.infrastructure.services.cache_service import CacheService
from src.schemas.auth import SessionValidation
from src.schemas.providers.common import PaginationParams, DateRangeParams
from src.core.config import config

class SpotifyService(BaseProviderService):
    """Servicio de aplicación para Spotify."""
    
    def __init__(
        self,
        session: SessionValidation,
        filter_service: MediaFilterService | None = None,
        cache_service: CacheService | None = None,
    ):
        client = SpotifyClient(session)
        super().__init__(client, filter_service, cache_service)
        self._user_id = session.get("user_sub")
    
    def _get_playlists_cache_key(self, pagination: PaginationParams) -> str:
        return f"spotify:playlists:{self._user_id}:{pagination.max_results}:{pagination.page_token or ''}"
    
    def _get_cache_ttl(self) -> int:
        return config.cache_ttl_user_playlists

# infrastructure/providers/spotify/spotify_client.py
import httpx
from typing import List
from src.domain.providers.provider_interface import IProviderClient
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.infrastructure.providers.spotify.spotify_mapper import SpotifyMapper
from src.schemas.auth import SessionValidation
from src.schemas.providers.common import PaginationParams

class SpotifyClient(IProviderClient):
    """Cliente para Spotify Web API."""
    
    def __init__(self, session: SessionValidation):
        self.access_token = session["access_token"]
        self._client = httpx.AsyncClient(
            base_url="https://api.spotify.com/v1",
            headers={"Authorization": f"Bearer {self.access_token}"}
        )
    
    async def get_user_playlists(
        self,
        pagination: PaginationParams
    ) -> List[Playlist]:
        """Obtener playlists del usuario desde Spotify API."""
        params = {
            "limit": pagination.max_results,
            "offset": self._calculate_offset(pagination)
        }
        
        response = await self._client.get("/me/playlists", params=params)
        response.raise_for_status()
        data = response.json()
        
        return SpotifyMapper.to_playlists(data["items"])
    
    async def get_playlist_items(
        self,
        playlist_id: str,
        pagination: PaginationParams
    ) -> List[MediaItem]:
        """Obtener tracks de una playlist."""
        params = {
            "limit": pagination.max_results,
            "offset": self._calculate_offset(pagination)
        }
        
        response = await self._client.get(
            f"/playlists/{playlist_id}/tracks",
            params=params
        )
        response.raise_for_status()
        data = response.json()
        
        return SpotifyMapper.to_media_items(data["items"], playlist_id)
    
    async def delete_playlist_items(
        self,
        playlist_id: str,
        item_ids: List[str]
    ) -> None:
        """Eliminar tracks de una playlist."""
        # Spotify API requiere enviar URIs
        uris = [f"spotify:track:{track_id}" for track_id in item_ids]
        
        await self._client.delete(
            f"/playlists/{playlist_id}/tracks",
            json={"tracks": [{"uri": uri} for uri in uris]}
        )
    
    def _calculate_offset(self, pagination: PaginationParams) -> int:
        """Calcular offset desde page_token (Spotify usa offset, no tokens)."""
        # Implementar lógica de conversión si es necesario
        return 0
```

## 6. Factory Pattern

```python
# infrastructure/factories/provider_factory.py
from src.domain.providers.provider_type import ProviderType
from src.domain.providers.provider_interface import IProviderService
from src.application.providers.youtube.youtube_service import YoutubeService
from src.application.providers.spotify.spotify_service import SpotifyService
from src.schemas.auth import SessionValidation

class ProviderServiceFactory:
    """Factory para crear servicios de proveedores."""
    
    @staticmethod
    async def create(
        provider_type: ProviderType,
        session: SessionValidation
    ) -> IProviderService:
        """Crear servicio según el tipo de proveedor."""
        match provider_type:
            case ProviderType.YOUTUBE:
                service = YoutubeService(session)
                await service.initialize()  # YouTube necesita inicialización
                return service
            case ProviderType.SPOTIFY:
                return SpotifyService(session)
            case _:
                raise ValueError(f"Unsupported provider: {provider_type}")
```

## 7. Endpoints

```python
# api/v1/providers/youtube.py
from fastapi import APIRouter, Depends, Path
from src.api.deps import current_session_dependency
from src.domain.providers.provider_type import ProviderType
from src.infrastructure.factories.provider_factory import ProviderServiceFactory
from src.schemas.providers.common import PaginationParams, DateRangeParams

router = APIRouter(prefix="/youtube", tags=["YouTube"])

@router.get("/playlists")
async def get_user_playlists(
    session: current_session_dependency,
    pagination: PaginationParams = Depends(),
):
    """Obtener playlists de YouTube."""
    service = await ProviderServiceFactory.create(ProviderType.YOUTUBE, session)
    playlists = await service.get_user_playlists(pagination)
    return playlists

@router.get("/playlists/{playlist_id}/items")
async def get_playlist_items(
    playlist_id: str = Path(...),
    session: current_session_dependency,
    pagination: PaginationParams = Depends(),
    date_range: DateRangeParams | None = Depends(),
):
    """Obtener items de una playlist de YouTube."""
    service = await ProviderServiceFactory.create(ProviderType.YOUTUBE, session)
    items = await service.get_playlist_items(
        playlist_id,
        pagination,
        date_range
    )
    return items

# api/v1/providers/spotify.py
router = APIRouter(prefix="/spotify", tags=["Spotify"])

@router.get("/playlists")
async def get_user_playlists(
    session: current_session_dependency,
    pagination: PaginationParams = Depends(),
):
    """Obtener playlists de Spotify."""
    service = await ProviderServiceFactory.create(ProviderType.SPOTIFY, session)
    playlists = await service.get_user_playlists(pagination)
    return playlists
```

## 8. Mappers

```python
# infrastructure/providers/youtube/youtube_mapper.py
from typing import List
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.domain.providers.provider_type import ProviderType

class YoutubeMapper:
    """Mapper para convertir respuestas de YouTube API a entidades de dominio."""
    
    @staticmethod
    def to_playlists(api_response: dict) -> List[Playlist]:
        """Convertir respuesta de YouTube API a lista de Playlist."""
        playlists = []
        for item in api_response.get("items", []):
            playlist = Playlist(
                id=item["id"],
                provider=ProviderType.YOUTUBE,
                title=item["snippet"]["title"],
                description=item["snippet"].get("description"),
                item_count=int(item["contentDetails"]["itemCount"]),
                created_at=datetime.fromisoformat(
                    item["snippet"]["publishedAt"].replace("Z", "+00:00")
                ),
                updated_at=datetime.fromisoformat(
                    item["snippet"]["publishedAt"].replace("Z", "+00:00")
                ) if item["snippet"].get("publishedAt") else None,
                owner_id=item["snippet"]["channelId"]
            )
            playlists.append(playlist)
        return playlists
    
    @staticmethod
    def to_media_items(api_response: dict, playlist_id: str) -> List[MediaItem]:
        """Convertir respuesta de YouTube API a lista de MediaItem."""
        items = []
        for item in api_response.get("items", []):
            snippet = item.get("snippet", {})
            media_item = MediaItem(
                id=item["contentDetails"]["videoId"],
                provider=ProviderType.YOUTUBE,
                playlist_id=playlist_id,
                title=snippet.get("title", "Private video"),
                description=snippet.get("description"),
                duration_seconds=None,  # Requiere llamada adicional
                added_at=datetime.fromisoformat(
                    snippet["publishedAt"].replace("Z", "+00:00")
                ),
                is_private=snippet.get("title") == "Private video",
                is_deleted=snippet.get("title") == "Deleted video",
                thumbnail_url=snippet.get("thumbnails", {}).get("default", {}).get("url")
            )
            items.append(media_item)
        return items

# infrastructure/providers/spotify/spotify_mapper.py
from typing import List
from src.domain.entities.playlist import Playlist
from src.domain.entities.media_item import MediaItem
from src.domain.providers.provider_type import ProviderType

class SpotifyMapper:
    """Mapper para convertir respuestas de Spotify API a entidades de dominio."""
    
    @staticmethod
    def to_playlists(api_items: List[dict]) -> List[Playlist]:
        """Convertir respuesta de Spotify API a lista de Playlist."""
        playlists = []
        for item in api_items:
            playlist = Playlist(
                id=item["id"],
                provider=ProviderType.SPOTIFY,
                title=item["name"],
                description=item.get("description"),
                item_count=item["tracks"]["total"],
                created_at=None,  # Spotify no expone fecha de creación
                updated_at=None,
                owner_id=item["owner"]["id"]
            )
            playlists.append(playlist)
        return playlists
    
    @staticmethod
    def to_media_items(api_items: List[dict], playlist_id: str) -> List[MediaItem]:
        """Convertir respuesta de Spotify API a lista de MediaItem."""
        items = []
        for item in api_items:
            track = item.get("track")
            if not track:
                continue
            
            media_item = MediaItem(
                id=track["id"],
                provider=ProviderType.SPOTIFY,
                playlist_id=playlist_id,
                title=track["name"],
                description=None,
                duration_seconds=track.get("duration_ms", 0) // 1000,
                added_at=datetime.fromisoformat(
                    item["added_at"].replace("Z", "+00:00")
                ) if item.get("added_at") else datetime.now(timezone.utc),
                is_private=track.get("is_local", False),
                is_deleted=track is None,
                thumbnail_url=track.get("album", {}).get("images", [{}])[0].get("url")
            )
            items.append(media_item)
        return items
```

## 9. Configuración

```python
# core/config.py (agregar)
class Config(BaseSettings):
    # ... configuración existente ...
    
    # Spotify OAuth
    spotify_client_id: str | None = None
    spotify_client_secret: str | None = None
    spotify_redirect_uri: str | None = None
    
    # Cache TTLs (pueden ser compartidos o específicos)
    cache_ttl_user_playlists: int = 300  # 5 minutos
    cache_ttl_playlist_items: int = 600  # 10 minutos
```

## 10. Dependency Injection

```python
# api/deps.py (actualizar)
from src.domain.providers.provider_type import ProviderType
from src.infrastructure.factories.provider_factory import ProviderServiceFactory

async def get_youtube_service(
    session: current_session_dependency,
) -> AsyncGenerator[IProviderService, None]:
    """Crear servicio de YouTube."""
    service = await ProviderServiceFactory.create(ProviderType.YOUTUBE, session)
    try:
        yield service
    finally:
        pass

async def get_spotify_service(
    session: current_session_dependency,
) -> AsyncGenerator[IProviderService, None]:
    """Crear servicio de Spotify."""
    service = await ProviderServiceFactory.create(ProviderType.SPOTIFY, session)
    try:
        yield service
    finally:
        pass
```

