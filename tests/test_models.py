"""Tests for PlaybackState data model and formatting utilities."""

import pytest
from spotify_widget.models import (
    PlaybackState,
    format_seconds,
    get_placeholder_state,
    get_long_text_placeholder_state,
)


def test_format_seconds_standard():
    assert format_seconds(0) == "00:00"
    assert format_seconds(9) == "00:09"
    assert format_seconds(78) == "01:18"
    assert format_seconds(234) == "03:54"


def test_format_seconds_hours():
    assert format_seconds(3600) == "1:00:00"
    assert format_seconds(3665) == "1:01:05"
    assert format_seconds(7325) == "2:02:05"


def test_format_seconds_negative():
    assert format_seconds(-15) == "00:00"


def test_playback_state_progress_fraction():
    # Halfway
    state = PlaybackState(duration_seconds=200, position_seconds=100)
    assert pytest.approx(state.progress_fraction) == 0.5

    # Zero duration
    state_zero = PlaybackState(duration_seconds=0, position_seconds=10)
    assert state_zero.progress_fraction == 0.0

    # Overshoot clamped
    state_over = PlaybackState(duration_seconds=100, position_seconds=150)
    assert state_over.progress_fraction == 1.0

    # Undershoot clamped
    state_under = PlaybackState(duration_seconds=100, position_seconds=-20)
    assert state_under.progress_fraction == 0.0


def test_playback_state_formatted_properties():
    state = PlaybackState(duration_seconds=244, position_seconds=87)
    assert state.formatted_position == "01:27"
    assert state.formatted_duration == "04:04"


def test_placeholder_state_defaults():
    state = get_placeholder_state()
    assert state.title == "Starry Night Horizon"
    assert state.artist == "Cosmic Waves"
    assert state.album == "Signals Across the Void"
    assert state.duration_seconds > 0
    assert state.is_playing is True


def test_long_text_placeholder():
    state = get_long_text_placeholder_state()
    assert len(state.title) > 50
    assert len(state.artist) > 30
    assert state.duration_seconds > 3600
    assert "1:" in state.formatted_duration
