"""Data models and formatting helpers for music playback state."""

from dataclasses import dataclass
from typing import Optional


def format_seconds(seconds: int) -> str:
    """Format duration in seconds to standard M:SS or H:MM:SS string."""
    if seconds < 0:
        seconds = 0
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


@dataclass
class PlaybackState:
    """Represents current playback information and UI display state."""

    title: str = "Starry Night Horizon"
    artist: str = "Cosmic Waves"
    album: str = "Signals Across the Void"
    duration_seconds: int = 234  # 03:54
    position_seconds: int = 78   # 01:18
    is_playing: bool = True
    can_go_previous: bool = True
    can_go_next: bool = True
    can_seek: bool = True
    can_play: bool = True
    can_pause: bool = True
    is_online: bool = True
    art_url: Optional[str] = None
    track_id: Optional[str] = None
    art_data: Optional[bytes] = None

    @property
    def progress_fraction(self) -> float:
        """Fraction of track completed between 0.0 and 1.0."""
        if self.duration_seconds <= 0:
            return 0.0
        fraction = self.position_seconds / self.duration_seconds
        return max(0.0, min(1.0, fraction))

    @property
    def formatted_position(self) -> str:
        """Elapsed time as MM:SS string."""
        return format_seconds(self.position_seconds)

    @property
    def formatted_duration(self) -> str:
        """Total duration as MM:SS string."""
        return format_seconds(self.duration_seconds)


def get_placeholder_state() -> PlaybackState:
    """Return default realistic placeholder track information for the prototype."""
    return PlaybackState(
        title="Starry Night Horizon",
        artist="Cosmic Waves",
        album="Signals Across the Void",
        duration_seconds=234,
        position_seconds=78,
        is_playing=True,
        can_go_previous=True,
        can_go_next=True,
        can_seek=True,
        can_play=True,
        can_pause=True,
        is_online=True,
        art_data=None,
    )


def get_offline_state() -> PlaybackState:
    """Return state representing Spotify when offline or disconnected."""
    return PlaybackState(
        title="Spotify is not running",
        artist="Waiting for Spotify...",
        album="",
        duration_seconds=0,
        position_seconds=0,
        is_playing=False,
        can_go_previous=False,
        can_go_next=False,
        can_seek=False,
        can_play=False,
        can_pause=False,
        is_online=False,
        art_url=None,
        track_id=None,
        art_data=None,
    )


def get_long_text_placeholder_state() -> PlaybackState:
    """Return placeholder state with excessively long strings to stress test layout."""
    return PlaybackState(
        title="The Extremely Lengthy Track Title That Definitely Exceeds Any Standard Screen Boundary (feat. Extended Orchestra & Synthesizers) - 2026 Anniversary Remaster",
        artist="The Incredibly Prolific Collaboration Ensemble feat. Guest Vocalist With A Very Long Name",
        album="Anthology of Infinite Resonances and Comprehensive Spatial Acoustics Across Modern Horizons Volume IV",
        duration_seconds=3665,  # 1:01:05
        position_seconds=1245,  # 20:45
        is_playing=False,
        can_go_previous=True,
        can_go_next=True,
        can_seek=True,
        can_play=True,
        can_pause=True,
        is_online=True,
        art_data=None,
    )
