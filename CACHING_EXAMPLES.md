# Redis Caching - Ejemplos de Uso

Este documento muestra cómo usar el sistema de caché con Redis en la aplicación.

## 1. Usando el Decorador `@cached` (Recomendado)

El decorador `@cached` es la forma más simple de agregar caché a una función.

### Ejemplo Básico

```python
from src.core.cache import cached

@cached("user_playlists", expire=1800)  # Cache por 30 minutos
async def get_user_playlists(self, pagination: PaginationParams):
    # Tu lógica aquí
    response = await self._youtube_client.playlists().list(...).execute()
    return response
```

### Ejemplo con Parámetros

```python
@cached("playlist_videos", expire=3600)  # Cache por 1 hora
async def get_playlist_videos(self, playlist_id: str, pagination: PaginationParams):
    # El cache key incluirá automáticamente playlist_id y los parámetros de paginación
    response = await self._youtube_client.playlistItems().list(...).execute()
    return response
```

**Cache Key generado**: `playlist_videos:PL123:max_results:25:page_token:abc123`

## 2. Uso Manual del Cache

Para más control, puedes usar las funciones de cache manualmente.

### Ejemplo: Cache Manual con JSON

```python
from src.core.cache import get_json_cache, set_json_cache, cache_key

async def get_playlist_videos(self, playlist_id: str):
    # Generar key del cache
    cache_key_str = cache_key("playlist_videos", playlist_id)
    
    # Intentar obtener del cache
    cached = await get_json_cache(cache_key_str)
    if cached:
        logger.info(f"Cache hit for playlist {playlist_id}")
        return cached
    
    # Cache miss - obtener datos
    logger.info(f"Cache miss for playlist {playlist_id}")
    videos = await self._fetch_from_youtube_api(playlist_id)
    
    # Guardar en cache (expira en 1 hora = 3600 segundos)
    await set_json_cache(cache_key_str, videos, expire=3600)
    
    return videos
```

### Ejemplo: Invalidar Cache Manualmente

```python
from src.core.cache import delete_cache, cache_key

async def delete_playlist_videos(self, playlist_id: str):
    # Eliminar videos
    await self._delete_from_youtube(playlist_id)
    
    # Invalidar cache relacionado
    cache_key_str = cache_key("playlist_videos", playlist_id)
    await delete_cache(cache_key_str)
    
    # También podrías invalidar todos los caches de esta playlist
    # usando un patrón (requiere implementación adicional)
```

## 3. Cache con Condiciones

A veces quieres cachear solo bajo ciertas condiciones:

```python
from src.core.cache import get_json_cache, set_json_cache, cache_key

async def get_playlist_videos(self, playlist_id: str, use_cache: bool = True):
    if use_cache:
        cache_key_str = cache_key("playlist_videos", playlist_id)
        cached = await get_json_cache(cache_key_str)
        if cached:
            return cached
    
    videos = await self._fetch_from_youtube_api(playlist_id)
    
    if use_cache:
        await set_json_cache(cache_key_str, videos, expire=3600)
    
    return videos
```

## 4. Cache con TTL Diferentes

Diferentes tipos de datos pueden tener diferentes tiempos de expiración:

```python
# Datos que cambian frecuentemente - cache corto
@cached("user_status", expire=300)  # 5 minutos
async def get_user_status(self, user_id: str):
    ...

# Datos estables - cache largo
@cached("playlist_metadata", expire=86400)  # 24 horas
async def get_playlist_metadata(self, playlist_id: str):
    ...
```

## 5. Cache con Serialización Personalizada

Si necesitas cachear objetos que no son JSON estándar:

```python
from src.core.cache import get_cache, set_cache, cache_key
import json

async def get_custom_data(self, key: str):
    cache_key_str = cache_key("custom", key)
    
    # Obtener como string
    cached_str = await get_cache(cache_key_str)
    if cached_str:
        # Deserializar manualmente
        return json.loads(cached_str)
    
    # Obtener y cachear
    data = await self._fetch_data(key)
    await set_cache(cache_key_str, json.dumps(data), expire=3600)
    
    return data
```

## 6. Invalidar Cache por Patrón

Para invalidar múltiples keys que coincidan con un patrón:

```python
from src.core.cache import get_redis_client

async def invalidate_playlist_cache(self, playlist_id: str):
    """Invalidar todos los caches relacionados con una playlist."""
    client = await get_redis_client()
    
    # Buscar todas las keys que empiecen con "playlist_videos:{playlist_id}"
    pattern = f"playlist_videos:{playlist_id}*"
    
    # Nota: SCAN es mejor que KEYS para producción
    async for key in client.scan_iter(match=pattern):
        await client.delete(key)
        logger.info(f"Deleted cache key: {key}")
```

## 7. Cache con Tags/Metadatos

Para invalidar grupos de cache relacionados:

```python
from src.core.cache import set_json_cache, get_redis_client, cache_key

async def cache_with_tag(self, data: dict, tag: str):
    """Cachear datos con un tag para invalidación grupal."""
    key = cache_key("data", tag)
    await set_json_cache(key, data, expire=3600)
    
    # Guardar el tag en un set para tracking
    client = await get_redis_client()
    await client.sadd(f"cache_tags:{tag}", key)

async def invalidate_by_tag(self, tag: str):
    """Invalidar todos los caches con un tag específico."""
    client = await get_redis_client()
    
    # Obtener todas las keys con este tag
    keys = await client.smembers(f"cache_tags:{tag}")
    
    if keys:
        await client.delete(*keys)
        await client.delete(f"cache_tags:{tag}")
        logger.info(f"Invalidated {len(keys)} cache entries for tag: {tag}")
```

## Mejores Prácticas

1. **TTL Apropiado**: Usa TTL cortos para datos que cambian frecuentemente, largos para datos estables
2. **Keys Descriptivos**: Usa prefijos claros para organizar tus keys
3. **Invalidación**: Invalida el cache cuando los datos cambian
4. **Manejo de Errores**: El cache es opcional - tu app debe funcionar sin él
5. **Logging**: Usa logging para monitorear cache hits/misses en desarrollo

## Ejemplo Real: YouTube Service con Cache

```python
from src.core.cache import cached, delete_cache, cache_key

class YoutubeService:
    @cached("user_playlists", expire=1800)  # 30 minutos
    async def get_user_playlists(self, pagination: PaginationParams):
        # Si está en cache, retorna inmediatamente
        # Si no, ejecuta la función y guarda el resultado
        ...
    
    async def delete_playlist_videos(self, playlist_id: str, ...):
        # Eliminar videos
        await self._delete_videos(...)
        
        # Invalidar cache de esta playlist
        cache_key_str = cache_key("playlist_videos", playlist_id)
        await delete_cache(cache_key_str)
```

