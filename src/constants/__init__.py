# Re-exportar todas las constantes desde index.py
from src.constants.index import (
    PRIVATE_VIDEO_TITLE,
    PRIVATE_VIDEO_DESCRIPTION,
    DELETED_VIDEO_TITLE,
    DELETED_VIDEO_DESCRIPTION,
)

__all__ = [
    "PRIVATE_VIDEO_TITLE",
    "PRIVATE_VIDEO_DESCRIPTION",
    "DELETED_VIDEO_TITLE",
    "DELETED_VIDEO_DESCRIPTION",
]
