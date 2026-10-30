from typing import Annotated
from fastapi import APIRouter, Body, status

from src.api.deps import playlist_management_service_dependency
from src.domain.providers import ProviderType
from src.schemas.providers import (
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
