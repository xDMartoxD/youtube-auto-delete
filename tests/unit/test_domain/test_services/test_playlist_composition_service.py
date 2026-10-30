"""
Unit tests for PlaylistCompositionService.
"""

import pytest

from src.domain.entities.playlist import Track
from src.domain.services.playlist_composition_service import (
    CompositionMode,
    PlaylistCompositionService,
)


def track(track_id: str, item_id: str | None = None) -> Track:
    return Track(item_id=item_id or f"item-{track_id}", track_id=track_id, title=track_id)


def ids(tracks: list[Track]) -> list[str]:
    return [t.track_id for t in tracks]


class TestPlaylistCompositionService:
    """Tests for PlaylistCompositionService."""

    @pytest.fixture
    def service(self):
        return PlaylistCompositionService()

    def test_union_keeps_first_appearance_order_without_duplicates(self, service):
        sources = [[track("a"), track("b")], [track("b"), track("c"), track("a")]]

        result = service.compose(sources, CompositionMode.UNION)

        assert ids(result) == ["a", "b", "c"]

    def test_union_can_keep_duplicates(self, service):
        sources = [[track("a")], [track("a")]]

        result = service.compose(sources, CompositionMode.UNION, remove_duplicates=False)

        assert ids(result) == ["a", "a"]

    def test_intersection_returns_tracks_in_every_source(self, service):
        sources = [
            [track("a"), track("b"), track("c")],
            [track("c"), track("a")],
            [track("a"), track("c"), track("d")],
        ]

        result = service.compose(sources, CompositionMode.INTERSECTION)

        assert ids(result) == ["a", "c"]

    def test_difference_returns_first_source_minus_the_rest(self, service):
        sources = [[track("a"), track("b"), track("c"), track("b")], [track("b")]]

        result = service.compose(sources, CompositionMode.DIFFERENCE)

        assert ids(result) == ["a", "c"]

    def test_set_modes_never_repeat_tracks(self, service):
        sources = [[track("a"), track("a")], [track("a")]]

        result = service.compose(
            sources, CompositionMode.INTERSECTION, remove_duplicates=False
        )

        assert ids(result) == ["a"]

    def test_requires_a_source(self, service):
        with pytest.raises(ValueError):
            service.compose([], CompositionMode.UNION)

    @pytest.mark.parametrize(
        "mode", [CompositionMode.INTERSECTION, CompositionMode.DIFFERENCE]
    )
    def test_set_modes_require_two_sources(self, service, mode):
        with pytest.raises(ValueError):
            service.compose([[track("a")]], mode)

    def test_tracks_missing_from_skips_existing_tracks(self, service):
        target = [track("a")]
        incoming = [track("a"), track("b"), track("b")]

        result = service.tracks_missing_from(target, incoming)

        assert ids(result) == ["b"]

    def test_find_duplicates_returns_later_occurrences(self, service):
        tracks = [track("a", "1"), track("b", "2"), track("a", "3"), track("a", "4")]

        result = service.find_duplicates(tracks)

        assert [t.item_id for t in result] == ["3", "4"]
