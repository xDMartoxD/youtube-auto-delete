"""
Regression test: YouTube rejects concurrent changes to one playlist with 409.
"""

import threading
import time

import pytest
from unittest.mock import AsyncMock, MagicMock

from googleapiclient.errors import HttpError

from src.application.services.youtube_service import YoutubeService


class FakePlaylistItems:
    """Mimics playlistItems().delete(): fails with 409 if another delete is in flight."""

    def __init__(self):
        self._lock = threading.Lock()
        self._in_flight = 0
        self.deleted: list[str] = []

    def delete(self, id: str):
        request = MagicMock()
        request.execute.side_effect = lambda: self._execute(id)
        return request

    def _execute(self, item_id: str):
        with self._lock:
            self._in_flight += 1
            overlapping = self._in_flight > 1
        try:
            time.sleep(0.02)
            if overlapping:
                raise HttpError(MagicMock(status=409), b"conflict")
            self.deleted.append(item_id)
        finally:
            with self._lock:
                self._in_flight -= 1


@pytest.fixture
def service():
    session = {"user_sub": "user-1", "access_token": "token"}
    svc = YoutubeService(session, cache_service=AsyncMock())
    items = FakePlaylistItems()
    svc._youtube_client = MagicMock()
    svc._youtube_client.playlistItems.return_value = items
    return svc, items


@pytest.mark.asyncio
async def test_deletes_every_item_without_conflicts(service):
    svc, items = service

    deleted = await svc.delete_playlist_videos(
        "PL1",
        include_private_videos=False,
        include_delete_videos=False,
        item_ids=["a", "b", "c", "d"],
    )

    assert deleted == 4
    assert items.deleted == ["a", "b", "c", "d"]
