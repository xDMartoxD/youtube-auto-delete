import logging
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Body, Query, status
from fastapi.responses import RedirectResponse

from src.api.deps import (
    current_session_dependency,
    playlist_management_service_dependency,
    provider_connection_service_dependency,
)
from src.core.config import config
from src.core.exceptions import PlaylistMasterApiError
from src.domain.providers import ProviderType
from src.schemas.providers import (
    ConnectResponse,
    CreatePlaylistFromSourcesRequest,
    MergePlaylistsRequest,
    PlaylistListResponse,
    PlaylistOperationResponse,
    PlaylistResponse,
    ProviderInfo,
    ProviderListResponse,
    RemoveTracksRequest,
    RemoveTracksResponse,
    TrackListResponse,
    TrackResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", status_code=status.HTTP_200_OK)
async def list_providers(
    service: playlist_management_service_dependency,
) -> ProviderListResponse:
    """List supported providers and whether each one serves demo data."""
    return ProviderListResponse(
        providers=[ProviderInfo.from_provider(p) for p in service.list_providers()]
    )


@router.get("/{provider}/playlists", status_code=status.HTTP_200_OK)
async def list_playlists(
    provider: ProviderType,
    service: playlist_management_service_dependency,
) -> PlaylistListResponse:
    """Get every playlist of the user on a provider."""
    playlists = await service.list_playlists(provider)
    return PlaylistListResponse(
        provider=provider,
        playlists=[PlaylistResponse.from_entity(p) for p in playlists],
    )


@router.get("/{provider}/playlists/{playlist_id}/tracks", status_code=status.HTTP_200_OK)
async def get_playlist_tracks(
    provider: ProviderType,
    playlist_id: str,
    service: playlist_management_service_dependency,
) -> TrackListResponse:
    """Get all tracks of a playlist, flagging repeated entries."""
    tracks, duplicate_item_ids = await service.get_tracks(provider, playlist_id)
    return TrackListResponse(
        playlist_id=playlist_id,
        tracks=[TrackResponse.from_entity(t) for t in tracks],
        duplicate_item_ids=duplicate_item_ids,
    )


@router.post(
    "/{provider}/playlists/{playlist_id}/tracks/remove",
    status_code=status.HTTP_200_OK,
)
async def remove_playlist_tracks(
    provider: ProviderType,
    playlist_id: str,
    request: Annotated[RemoveTracksRequest, Body(media_type="application/json")],
    service: playlist_management_service_dependency,
) -> RemoveTracksResponse:
    """Remove several entries from a playlist at once."""
    removed = await service.remove_tracks(provider, playlist_id, request.item_ids)
    return RemoveTracksResponse(
        removed_count=removed, requested_count=len(set(request.item_ids))
    )


@router.post("/{provider}/playlists/merge", status_code=status.HTTP_200_OK)
async def merge_playlists(
    provider: ProviderType,
    request: Annotated[MergePlaylistsRequest, Body(media_type="application/json")],
    service: playlist_management_service_dependency,
) -> PlaylistOperationResponse:
    """Copy the tracks of several playlists into an existing or a new playlist."""
    playlist, added = await service.merge_playlists(
        provider,
        request.source_playlist_ids,
        target_playlist_id=request.target_playlist_id,
        new_playlist_name=request.new_playlist_name,
        remove_duplicates=request.remove_duplicates,
    )
    return PlaylistOperationResponse(
        playlist=PlaylistResponse.from_entity(playlist), added_count=added
    )


@router.post("/{provider}/playlists", status_code=status.HTTP_201_CREATED)
async def create_playlist_from_sources(
    provider: ProviderType,
    request: Annotated[
        CreatePlaylistFromSourcesRequest, Body(media_type="application/json")
    ],
    service: playlist_management_service_dependency,
) -> PlaylistOperationResponse:
    """Create a new playlist by combining other playlists (union, intersection, difference)."""
    playlist, added = await service.create_from_playlists(
        provider,
        request.name,
        request.source_playlist_ids,
        mode=request.mode,
        remove_duplicates=request.remove_duplicates,
        description=request.description,
    )
    return PlaylistOperationResponse(
        playlist=PlaylistResponse.from_entity(playlist), added_count=added
    )


@router.post("/{provider}/connect", status_code=status.HTTP_200_OK)
async def connect_provider(
    provider: ProviderType,
    session: current_session_dependency,
    service: provider_connection_service_dependency,
) -> ConnectResponse:
    """Start linking the user's account: returns the provider's consent URL."""
    return ConnectResponse(
        authorize_url=service.authorize_url(session["user_sub"], provider)
    )


@router.get("/{provider}/callback", include_in_schema=False)
async def provider_callback(
    provider: ProviderType,
    service: provider_connection_service_dependency,
    code: Annotated[str | None, Query()] = None,
    state: Annotated[str | None, Query()] = None,
    error: Annotated[str | None, Query()] = None,
) -> RedirectResponse:
    """
    Where the provider sends the browser after consent. Authenticated by the
    signed `state`, then redirects back to the frontend with the outcome.
    """
    if error or not code or not state:
        message = "Access was not granted" if error == "access_denied" else (
            error or "Missing authorization code"
        )
        return _back_to_frontend(connect_error=message)
    try:
        await service.complete(provider, code, state)
    except PlaylistMasterApiError as e:
        logger.warning(f"Connecting {provider} failed: {e.message}")
        return _back_to_frontend(connect_error=e.user_message)
    return _back_to_frontend(connected=provider)


@router.delete("/{provider}/connection", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_provider(
    provider: ProviderType,
    session: current_session_dependency,
    service: provider_connection_service_dependency,
) -> None:
    """Unlink the user's account; the provider falls back to demo data."""
    await service.disconnect(session["user_sub"], provider)


def _back_to_frontend(**params: str) -> RedirectResponse:
    return RedirectResponse(
        f"{config.frontend_url}/?{urlencode(params)}",
        status_code=status.HTTP_303_SEE_OTHER,
    )
