"""Script para limpiar todo el cache de Redis."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.infrastructure.services.cache_service import CacheService
from src.core.cache.client import close_redis_client


async def clear_all_cache():
    """Borra todo el cache de Redis."""
    cache_service = CacheService()
    
    try:
        deleted = await cache_service.flush_all()
        print(f"✅ Borradas {deleted} claves del cache.")
    except Exception as e:
        print(f"❌ Error al borrar el cache: {e}")
        raise
    finally:
        await close_redis_client()


async def clear_cache_by_prefix(prefix: str):
    """Borra todas las claves que empiecen con un prefijo específico."""
    from src.core.cache.invalidation import PatternInvalidationStrategy
    
    try:
        pattern = f"{prefix}*"
        strategy = PatternInvalidationStrategy()
        deleted = await strategy.invalidate(pattern)
        print(f"✅ Borradas {deleted} claves con prefijo '{prefix}'.")
    except Exception as e:
        print(f"❌ Error al borrar el cache: {e}")
        raise
    finally:
        await close_redis_client()


async def main():
    """Función principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Limpiar cache de Redis")
    parser.add_argument(
        "--prefix",
        type=str,
        help="Borrar solo claves con este prefijo (ej: playlist_videos)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Borrar todo el cache (por defecto)",
    )
    
    args = parser.parse_args()
    
    if args.prefix:
        await clear_cache_by_prefix(args.prefix)
    else:
        await clear_all_cache()


if __name__ == "__main__":
    asyncio.run(main())

