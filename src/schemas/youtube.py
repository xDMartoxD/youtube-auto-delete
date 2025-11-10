from typing import Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone


class PaginationParams(BaseModel):
    """Parámetros de paginación para YouTube API."""

    max_results: int = Field(
        25, ge=1, le=50, description="Número máximo de resultados por página"
    )
    page_token: str | None = Field(None, description="Token de página para paginación")

    model_config = {"extra": "forbid"}


class DateRangeParams(BaseModel):
    """Parámetros para filtrar por rango de fechas."""

    date_from: datetime = Field(
        description="Fecha de inicio (ISO 8601). Filtra videos agregados a la playlist desde esta fecha.",
        alias="date_from",
    )
    date_to: datetime = Field(
        description="Fecha de fin (ISO 8601). Filtra videos agregados a la playlist hasta esta fecha.",
        alias="date_to",
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        """Valida que date_to sea mayor o igual que date_from."""
        if self.date_to < self.date_from:
            raise ValueError("date_to debe ser mayor o igual que date_from")
        if self.date_from < datetime(2005, 4, 20, tzinfo=timezone.utc):
            raise ValueError("date_from debe ser mayor o igual a 2005-04-20")
        if self.date_to > datetime.now(timezone.utc):
            raise ValueError("date_to debe ser menor o igual a la fecha actual")
        return self

    model_config = {"extra": "forbid"}


class PlaylistVideoQueryParams(BaseModel):
    """Parámetros combinados de paginación y filtro de fechas para videos de playlist."""

    max_results: int = Field(
        default=25,
        ge=1,
        le=50,
        description="Número máximo de resultados por página",
    )
    page_token: str | None = Field(
        default=None, description="Token de página para paginación"
    )
    date_from: datetime | None = Field(
        default=None,
        description="Fecha de inicio (ISO 8601). Filtra videos agregados a la playlist desde esta fecha.",
        alias="date_from",
    )
    date_to: datetime | None = Field(
        default=None,
        description="Fecha de fin (ISO 8601). Filtra videos agregados a la playlist hasta esta fecha.",
        alias="date_to",
    )

    @model_validator(mode="after")
    def validate_date_range(self):
        """Valida que si se proporcionan fechas, ambas estén presentes y sean válidas."""
        has_date_from = self.date_from is not None
        has_date_to = self.date_to is not None

        # Si se proporciona alguna fecha, ambas deben estar presentes
        if has_date_from and not has_date_to:
            raise ValueError(
                "date_to es requerido cuando se usa filtro de fechas. Proporcione ambas fechas: date_from y date_to."
            )
        if has_date_to and not has_date_from:
            raise ValueError(
                "date_from es requerido cuando se usa filtro de fechas. Proporcione ambas fechas: date_from y date_to."
            )

        # Si ambas fechas están presentes, validar el rango
        if has_date_from and has_date_to:
            # Type narrowing: sabemos que ambos son datetime, no None
            date_from = self.date_from
            date_to = self.date_to
            assert date_from is not None and date_to is not None  # Para type checker

            if date_to < date_from:
                raise ValueError("date_to debe ser mayor o igual que date_from")
            if date_from < datetime(2005, 4, 20, tzinfo=timezone.utc):
                raise ValueError("date_from debe ser mayor o igual a 2005-04-20")
            if date_to > datetime.now(timezone.utc):
                raise ValueError("date_to debe ser menor o igual a la fecha actual")

        return self

    @property
    def pagination(self) -> PaginationParams:
        """Retorna los parámetros de paginación."""
        return PaginationParams(
            max_results=self.max_results, page_token=self.page_token
        )

    @property
    def date_range(self) -> DateRangeParams | None:
        """Retorna los parámetros de rango de fechas si están presentes."""
        if self.date_from is None or self.date_to is None:
            return None
        return DateRangeParams(date_from=self.date_from, date_to=self.date_to)

    model_config = {"extra": "forbid"}


class PageInfo(BaseModel):
    totalResults: int
    resultsPerPage: int


class PlaylistSnippet(BaseModel):
    title: str
    description: str | None = None
    publishedAt: str | None = None
    channelId: str | None = None
    channelTitle: str | None = None
    thumbnails: dict[str, Any] | None = None


class PlaylistItem(BaseModel):
    kind: str
    etag: str
    id: str
    snippet: PlaylistSnippet | None = None


class YoutubePlaylistListResponse(BaseModel):
    kind: str = Field("youtube#playlistListResponse", description="Tipo de respuesta")
    etag: str = Field(description="Etag de la respuesta")
    nextPageToken: str | None = Field(None, description="Token de la siguiente página")
    pageInfo: PageInfo = Field(description="Información de la página")
    items: list[PlaylistItem] = Field(description="Lista de items de la playlist")


# Schemas para PlaylistItemVideo (items de videos en una playlist)
class Thumbnail(BaseModel):
    """Thumbnail individual con tamaño específico."""

    url: str
    width: int
    height: int


class Thumbnails(BaseModel):
    """Todos los thumbnails disponibles para un video."""

    default: Thumbnail | None = None
    medium: Thumbnail | None = None
    high: Thumbnail | None = None
    standard: Thumbnail | None = None
    maxres: Thumbnail | None = None


class ResourceId(BaseModel):
    """Resource ID que identifica el video."""

    kind: str = Field(description="Tipo de recurso, generalmente 'youtube#video'")
    videoId: str = Field(description="ID del video de YouTube")


class PlaylistItemSnippet(BaseModel):
    """Snippet completo de un item en una playlist."""

    publishedAt: str = Field(description="Fecha de publicación del item en la playlist")
    channelId: str = Field(description="ID del canal que agregó el video a la playlist")
    title: str = Field(description="Título del video")
    description: str = Field(default="", description="Descripción del video")
    thumbnails: Thumbnails | None = None
    channelTitle: str = Field(description="Nombre del canal que agregó el video")
    playlistId: str = Field(description="ID de la playlist")
    position: int = Field(description="Posición del video en la playlist")
    resourceId: ResourceId = Field(description="ID del recurso (video)")
    videoOwnerChannelTitle: str | None = Field(
        None, description="Título del canal que subió el video"
    )
    videoOwnerChannelId: str | None = Field(
        None, description="ID del canal que subió el video"
    )


class ContentDetails(BaseModel):
    """Detalles del contenido del video."""

    videoId: str = Field(description="ID del video")
    videoPublishedAt: str | None = Field(
        None, description="Fecha de publicación del video original"
    )


class PlaylistItemVideo(BaseModel):
    """Item completo de un video en una playlist."""

    kind: str = Field(default="youtube#playlistItem", description="Tipo de recurso")
    etag: str = Field(description="ETag del recurso")
    id: str = Field(description="ID único del item en la playlist")
    snippet: PlaylistItemSnippet = Field(
        description="Información del snippet del video"
    )
    contentDetails: ContentDetails = Field(description="Detalles del contenido")


class PlaylistVideoResponse(BaseModel):
    """Respuesta paginada de videos de playlist con schemas completos."""

    items: list[PlaylistItemVideo] = Field(description="Lista de items de la playlist")
    total_results: int = Field(description="Total de resultados")
    next_page_token: str | None = Field(
        None, description="Token de la siguiente página"
    )
    prev_page_token: str | None = Field(None, description="Token de la página anterior")
    page_info: PageInfo = Field(description="Información de la página")


class DeletePlaylistVideosRequest(BaseModel):
    playlist_id: str = Field(description="ID de la playlist")
    include_private_videos: bool = Field(description="Incluir videos privados")
    video_ids: list[str] | None = Field(
        None, description="IDs de los videos a eliminar"
    )
