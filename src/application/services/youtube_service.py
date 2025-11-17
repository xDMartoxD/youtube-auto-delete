"""Application service for YouTube - orchestrates domain and infrastructure."""

from typing import Any
from datetime import datetime
import asyncio
import logging

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError

from src.schemas.auth import SessionValidation
from src.schemas.youtube import (
    PaginationParams,
    DateRangeParams,
    PlaylistVideoResponse,
    YoutubePlaylistListResponse,
    PageInfo,
    PlaylistItemVideo,
)
from src.domain.services.video_filter_service import VideoFilterService
from src.infrastructure.services.cache_service import CacheService
from src.core.config import config
from src.constants import (
    PRIVATE_VIDEO_TITLE,
    PRIVATE_VIDEO_DESCRIPTION,
    DELETED_VIDEO_TITLE,
    DELETED_VIDEO_DESCRIPTION,
)

logger = logging.getLogger(__name__)

# YouTube API constants
MAX_RESULTS_PER_PAGE = 50  # Maximum allowed by YouTube API
API_PART_SNIPPET_CONTENT = "snippet,contentDetails"


class YoutubeService:
    """
    Application service - orchestrates domain and infrastructure.
    Does not contain business logic, only orchestrates.
    """

    def __init__(
        self,
        session: SessionValidation,
        video_filter_service: VideoFilterService | None = None,
        cache_service: CacheService | None = None,
    ):
        self._session = session
        self._youtube_client: Any = None
        self.video_filter_service = video_filter_service or VideoFilterService()
        self.cache_service = cache_service or CacheService()
        self._user_id = session.get("user_sub")

    def _ensure_initialized(self) -> None:
        """Ensure the YouTube client has been initialized."""
        if self._youtube_client is None:
            raise RuntimeError(
                "YoutubeService must be initialized before use. "
                "Call initialize() first or use the dependency injection."
            )

    async def _execute_youtube_request(
        self, request_func: Any, max_retries: int = 3
    ) -> dict[str, Any]:
        """
        Execute a YouTube API request in a thread with retry logic and exponential backoff.

        Args:
            request_func: Callable that returns a YouTube API request object with .execute() method
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            Response dictionary from YouTube API

        Raises:
            HttpError: If all retry attempts fail
        """
        last_exception = None

        for attempt in range(max_retries):
            try:

                def _execute():
                    return request_func().execute()

                return await asyncio.to_thread(_execute)
            except HttpError as e:
                last_exception = e
                status_code = e.resp.status if hasattr(e, "resp") else None

                # Don't retry on client errors (4xx) except 429 (rate limit)
                if status_code and 400 <= status_code < 500 and status_code != 429:
                    logger.warning(
                        f"YouTube API client error (not retrying): {status_code} - {e}"
                    )
                    raise

                # Don't retry on last attempt
                if attempt == max_retries - 1:
                    break

                # Calculate exponential backoff: 2^attempt seconds
                wait_time = 2**attempt
                logger.warning(
                    f"YouTube API request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            except Exception as e:
                # For non-HTTP errors, don't retry
                logger.error(f"Unexpected error in YouTube API request: {e}")
                raise

        # All retries exhausted
        if last_exception:
            logger.error(
                f"YouTube API request failed after {max_retries} attempts: {last_exception}"
            )
            raise last_exception
        else:
            raise RuntimeError(
                f"YouTube API request failed after {max_retries} attempts with unknown error"
            )

    async def _fetch_with_cache(
        self,
        cache_key_prefix: str,
        fetch_func: Any,
        expire: int,
        response_model: type,
        *cache_args: Any,
        **cache_kwargs: Any,
    ) -> Any:
        """
        Fetch data with cache-aside pattern.

        Args:
            cache_key_prefix: Prefix for cache key
            fetch_func: Async function to fetch data if not in cache
            expire: Cache expiration time in seconds
            response_model: Pydantic model class to deserialize cached/fetched data
            *cache_args: Positional arguments for cache key
            **cache_kwargs: Keyword arguments for cache key

        Returns:
            Instance of response_model with fetched or cached data
        """
        # INFRASTRUCTURE: Get from cache or fetch
        cached_result = await self.cache_service.get(
            cache_key_prefix, *cache_args, **cache_kwargs
        )

        if cached_result:
            return response_model(**cached_result)

        # Cache miss - fetch and cache
        result = await fetch_func()
        await self.cache_service.set(
            cache_key_prefix,
            result.model_dump(),
            expire,
            *cache_args,
            **cache_kwargs,
        )

        return result

    async def initialize(self) -> None:
        """
        Initialize the YouTube client in a thread to avoid blocking the event loop.
        This should be called during dependency injection before using the service.
        """
        if self._youtube_client is None:
            # INFRASTRUCTURE: Build client in a thread to avoid blocking the event loop
            credentials = Credentials(self._session["access_token"])
            self._youtube_client = await asyncio.to_thread(
                build, "youtube", "v3", credentials=credentials
            )

    async def get_user_playlists(
        self, pagination: PaginationParams
    ) -> YoutubePlaylistListResponse:
        """Get user's playlists with pagination."""
        self._ensure_initialized()

        async def _fetch_playlists() -> YoutubePlaylistListResponse:
            """Fetch playlists from YouTube API."""
            # INFRASTRUCTURE: Build API parameters
            request_params = {
                "part": API_PART_SNIPPET_CONTENT,
                "mine": True,
                "maxResults": pagination.max_results,
            }

            # Add pageToken if exists
            if pagination.page_token:
                request_params["pageToken"] = pagination.page_token

            # INFRASTRUCTURE: Execute request in a thread to avoid blocking the event loop
            response_dict = await self._execute_youtube_request(
                lambda: self._youtube_client.playlists().list(**request_params)
            )

            # Convert dict to Pydantic model
            return YoutubePlaylistListResponse(**response_dict)

        return await self._fetch_with_cache(
            cache_key_prefix="user_playlists",
            fetch_func=_fetch_playlists,
            expire=config.cache_ttl_user_playlists,
            response_model=YoutubePlaylistListResponse,
            user_id=self._user_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

    async def get_playlist_videos(
        self, playlist_id: str, pagination: PaginationParams
    ) -> PlaylistVideoResponse:
        """Get videos from a playlist with pagination."""
        self._ensure_initialized()

        async def _fetch_videos() -> PlaylistVideoResponse:
            """Fetch videos from YouTube API."""
            # INFRASTRUCTURE: Build API parameters
            request_params = {
                "part": API_PART_SNIPPET_CONTENT,
                "playlistId": playlist_id,
                "maxResults": pagination.max_results,
            }

            # Add pageToken if exists
            if pagination.page_token:
                request_params["pageToken"] = pagination.page_token

            # INFRASTRUCTURE: Execute request in a thread to avoid blocking the event loop
            response = await self._execute_youtube_request(
                lambda: self._youtube_client.playlistItems().list(**request_params)
            )

            # Build paginated response using schemas
            items = [PlaylistItemVideo(**item) for item in response.get("items", [])]
            page_info_dict = response.get("pageInfo", {})
            page_info = (
                PageInfo(**page_info_dict)
                if page_info_dict
                else PageInfo(totalResults=0, resultsPerPage=0)
            )

            return PlaylistVideoResponse(
                items=items,
                total_results=page_info.totalResults,
                next_page_token=response.get("nextPageToken"),
                prev_page_token=response.get("prevPageToken"),
                page_info=page_info,
            )

        return await self._fetch_with_cache(
            cache_key_prefix="playlist_videos",
            fetch_func=_fetch_videos,
            expire=config.cache_ttl_playlist_videos,
            response_model=PlaylistVideoResponse,
            playlist_id=playlist_id,
            max_results=pagination.max_results,
            page_token=pagination.page_token or "",
        )

    async def _fetch_and_filter_playlist_by_date(
        self,
        playlist_id: str,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> tuple[list[PlaylistItemVideo], PageInfo]:
        """
        Fetch all playlist pages and filter by date range.

        Args:
            playlist_id: ID of the playlist
            date_from: Start date for filtering
            date_to: End date for filtering

        Returns:
            Tuple of (filtered items as PlaylistItemVideo, page info from last response)
        """
        all_items: list[PlaylistItemVideo] = []
        next_page_token = None
        last_page_info: PageInfo | None = None

        # Iterate over all pages to get all videos
        while True:
            # INFRASTRUCTURE: Build API parameters
            request_params = {
                "part": API_PART_SNIPPET_CONTENT,
                "playlistId": playlist_id,
                "maxResults": MAX_RESULTS_PER_PAGE,
            }

            # Add pageToken if exists
            if next_page_token:
                request_params["pageToken"] = next_page_token

            # INFRASTRUCTURE: Execute request in a thread to avoid blocking the event loop
            response = await self._execute_youtube_request(
                lambda: self._youtube_client.playlistItems().list(**request_params)
            )

            # Get items from this page and convert to schemas
            page_items_dict = response.get("items", [])
            page_items = [PlaylistItemVideo(**item) for item in page_items_dict]

            # DOMAIN: Filter items by date range using domain service
            # Convert PlaylistItemVideo to dict for domain service (it expects dict)
            filtered_items_dict = self.video_filter_service.filter_by_date_range(
                [item.model_dump() for item in page_items], date_from, date_to
            )
            # Convert back to PlaylistItemVideo
            filtered_items = [PlaylistItemVideo(**item) for item in filtered_items_dict]
            all_items.extend(filtered_items)

            # Get next page token
            next_page_token = response.get("nextPageToken")

            # Store page info from last response
            page_info_dict = response.get("pageInfo", {})
            if page_info_dict:
                last_page_info = PageInfo(**page_info_dict)

            # If no more pages, exit loop
            if not next_page_token:
                break

        # Return default PageInfo if none was set
        if last_page_info is None:
            last_page_info = PageInfo(
                totalResults=len(all_items), resultsPerPage=MAX_RESULTS_PER_PAGE
            )

        return all_items, last_page_info

    async def get_playlist_videos_by_date_ranges(
        self,
        playlist_id: str,
        date_range: DateRangeParams,
    ) -> PlaylistVideoResponse:
        """
        Gets ALL videos from a playlist within a date range.
        Iterates over all pages to get all results that match the filter.
        Uses caching to optimize repeated requests with the same parameters.
        """
        self._ensure_initialized()

        # Build cache key with date range parameters
        date_from_str = (
            date_range.date_from.isoformat() if date_range.date_from else None
        )
        date_to_str = date_range.date_to.isoformat() if date_range.date_to else None

        # INFRASTRUCTURE: Check cache first
        cached_result = await self.cache_service.get(
            "playlist_videos_by_date",
            playlist_id=playlist_id,
            date_from=date_from_str or "",
            date_to=date_to_str or "",
        )

        if cached_result:
            return PlaylistVideoResponse(**cached_result)

        # Cache miss - fetch all pages and filter
        all_items, page_info = await self._fetch_and_filter_playlist_by_date(
            playlist_id, date_range.date_from, date_range.date_to
        )

        # Build response with all filtered items (already PlaylistItemVideo objects)
        result = PlaylistVideoResponse(
            items=all_items,
            total_results=len(all_items),
            next_page_token=None,  # We already got all results
            prev_page_token=None,
            page_info=page_info,
        )

        # INFRASTRUCTURE: Cache the result
        await self.cache_service.set(
            "playlist_videos_by_date",
            result.model_dump(),
            expire=config.cache_ttl_playlist_videos_by_date,
            playlist_id=playlist_id,
            date_from=date_from_str or "",
            date_to=date_to_str or "",
        )

        return result

    async def _fetch_all_playlist_pages(
        self, playlist_id: str
    ) -> list[PlaylistItemVideo]:
        """
        Fetch all pages of playlist items.

        Args:
            playlist_id: ID of the playlist

        Returns:
            List of all playlist items from all pages as PlaylistItemVideo objects
        """
        all_items: list[PlaylistItemVideo] = []
        next_page_token = None

        while True:
            request_params = {
                "part": API_PART_SNIPPET_CONTENT,
                "playlistId": playlist_id,
                "maxResults": MAX_RESULTS_PER_PAGE,
            }

            if next_page_token:
                request_params["pageToken"] = next_page_token

            response = await self._execute_youtube_request(
                lambda: self._youtube_client.playlistItems().list(**request_params)
            )

            # Convert dict items to PlaylistItemVideo schemas
            page_items_dict = response.get("items", [])
            page_items = [PlaylistItemVideo(**item) for item in page_items_dict]
            all_items.extend(page_items)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return all_items

    def _is_deleted_video(self, item: PlaylistItemVideo) -> bool:
        """
        Check if a video is deleted based on snippet title/description and contentDetails.

        Args:
            item: PlaylistItemVideo object from YouTube API

        Returns:
            True if the video is deleted, False otherwise
        """
        snippet = item.snippet
        return (
            snippet.title == DELETED_VIDEO_TITLE
            or (snippet.description or "") == DELETED_VIDEO_DESCRIPTION
            or item.contentDetails.videoPublishedAt is None
        )

    def _is_private_video(self, item: PlaylistItemVideo) -> bool:
        """
        Check if a video is private based on snippet title/description.

        Args:
            item: PlaylistItemVideo object from YouTube API

        Returns:
            True if the video is private, False otherwise
        """
        snippet = item.snippet
        return (
            snippet.title == PRIVATE_VIDEO_TITLE
            or (snippet.description or "") == PRIVATE_VIDEO_DESCRIPTION
        )

    def _should_delete_item(
        self,
        item: PlaylistItemVideo,
        include_private_videos: bool,
        include_delete_videos: bool,
    ) -> bool:
        """
        Determine if a playlist item should be deleted based on filters.

        Args:
            item: Playlist item to evaluate
            include_private_videos: If True, include private videos
            include_delete_videos: If True, include deleted videos

        Returns:
            True if item should be deleted, False otherwise
        """
        is_deleted = self._is_deleted_video(item)
        is_private = self._is_private_video(item)

        return (is_deleted and include_delete_videos) or (
            is_private and include_private_videos
        )

    def _filter_items_for_deletion(
        self,
        all_items: list[PlaylistItemVideo],
        include_private_videos: bool,
        include_delete_videos: bool,
    ) -> list[str]:
        """
        Filter playlist items to determine which should be deleted.

        Args:
            all_items: List of all playlist items as PlaylistItemVideo objects
            include_private_videos: If True, include private videos in deletion
            include_delete_videos: If True, include deleted videos in deletion

        Returns:
            List of playlist item IDs to delete
        """
        return [
            item.id
            for item in all_items
            if self._should_delete_item(
                item, include_private_videos, include_delete_videos
            )
        ]

    async def _delete_playlist_item(self, playlist_id: str, item_id: str) -> bool:
        """
        Delete a single playlist item.

        Args:
            playlist_id: ID of the playlist
            item_id: Playlist item ID to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            await self._execute_youtube_request(
                lambda: self._youtube_client.playlistItems().delete(id=item_id)
            )
            logger.info(f"Deleted playlist item {item_id} from playlist {playlist_id}")
            return True
        except Exception as e:
            logger.warning(
                f"Failed to delete playlist item {item_id} from playlist {playlist_id}: {e}"
            )
            return False

    async def _delete_items_batch(self, playlist_id: str, item_ids: list[str]) -> int:
        """
        Delete playlist items in batch (concurrently).

        Args:
            playlist_id: ID of the playlist
            item_ids: List of playlist item IDs to delete

        Returns:
            Number of successfully deleted items
        """
        if not item_ids:
            return 0

        # Delete items concurrently
        tasks = [
            self._delete_playlist_item(playlist_id, item_id) for item_id in item_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count successful deletions (True values, ignoring exceptions)
        return sum(1 for result in results if result is True)

    async def delete_playlist_videos(
        self,
        playlist_id: str,
        include_private_videos: bool,
        include_delete_videos: bool,
        item_ids: list[str] | None = None,
    ) -> None:
        """
        Delete videos from a playlist.
        Invalidates relevant cache entries after deletion.

        Args:
            playlist_id: ID of the playlist
            include_private_videos: If True, include private videos in deletion
            include_delete_videos: If True, include deleted videos in deletion
            item_ids: Optional list of playlist item IDs to delete. If provided,
                     these items will be deleted in addition to any filtered items
        """
        self._ensure_initialized()

        # Determine which items to delete
        items_to_delete: list[str] = []

        if item_ids:
            # If specific item IDs provided, use them directly
            items_to_delete.extend(item_ids)

        if include_private_videos or include_delete_videos:
            # Filter by private/deleted status
            all_items = await self._fetch_all_playlist_pages(playlist_id)
            filtered_items = self._filter_items_for_deletion(
                all_items, include_private_videos, include_delete_videos
            )
            items_to_delete.extend(filtered_items)

        # Delete items if any
        if items_to_delete:
            deleted_count = await self._delete_items_batch(playlist_id, items_to_delete)
            logger.info(
                f"Deleted {deleted_count} out of {len(items_to_delete)} items from playlist {playlist_id}"
            )

        # INFRASTRUCTURE: Invalidate cache for this playlist
        # Since cache keys are sorted alphabetically, playlist_id may appear in different positions
        # Use filter-based invalidation to find all keys containing this playlist_id
        playlist_id_pattern = f":playlist_id:{playlist_id}"
        await self.cache_service.invalidate_by_filter(
            key_prefixes=["playlist_videos:*", "playlist_videos_by_date:*"],
            filter_func=lambda key: playlist_id_pattern in key,
        )
