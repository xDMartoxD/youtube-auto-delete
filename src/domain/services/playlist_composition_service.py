"""Domain service with the rules for combining playlists."""

from enum import StrEnum

from src.domain.entities.playlist import Track


class CompositionMode(StrEnum):
    """How source playlists are combined into a new one."""

    UNION = "union"  # every track from every source
    INTERSECTION = "intersection"  # tracks present in all sources
    DIFFERENCE = "difference"  # tracks of the first source missing from the rest


class PlaylistCompositionService:
    """Domain service - pure business logic, tracks are compared by `track_id`."""

    def compose(
        self,
        sources: list[list[Track]],
        mode: CompositionMode = CompositionMode.UNION,
        remove_duplicates: bool = True,
    ) -> list[Track]:
        """
        Combine source playlists, keeping the order in which tracks first appear.

        Business rules:
        - At least one source is required; intersection and difference need two.
        - Intersection and difference are set operations, so they never repeat a track.
        """
        if not sources:
            raise ValueError("At least one source playlist is required")
        if mode != CompositionMode.UNION and len(sources) < 2:
            raise ValueError(f"'{mode}' needs at least two source playlists")

        if mode == CompositionMode.UNION:
            combined = [track for source in sources for track in source]
            return self.unique(combined) if remove_duplicates else combined

        others = [{t.track_id for t in source} for source in sources[1:]]
        if mode == CompositionMode.INTERSECTION:
            kept = [t for t in sources[0] if all(t.track_id in o for o in others)]
        else:
            kept = [t for t in sources[0] if not any(t.track_id in o for o in others)]
        return self.unique(kept)

    def tracks_missing_from(
        self, target: list[Track], incoming: list[Track]
    ) -> list[Track]:
        """Incoming tracks the target playlist does not contain yet (deduplicated)."""
        existing = {t.track_id for t in target}
        return [t for t in self.unique(incoming) if t.track_id not in existing]

    def find_duplicates(self, tracks: list[Track]) -> list[Track]:
        """Every repeated occurrence of a track after its first appearance."""
        seen: set[str] = set()
        duplicates = []
        for track in tracks:
            if track.track_id in seen:
                duplicates.append(track)
            seen.add(track.track_id)
        return duplicates

    def unique(self, tracks: list[Track]) -> list[Track]:
        """First occurrence of each track, in order."""
        seen: set[str] = set()
        result = []
        for track in tracks:
            if track.track_id not in seen:
                seen.add(track.track_id)
                result.append(track)
        return result
