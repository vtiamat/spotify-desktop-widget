"""Tests for Spotify MPRIS client, metadata parsing, position tracking, seeking, and lifecycle."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from dbus_next.signature import Variant

from spotify_widget.models import PlaybackState, get_offline_state
from spotify_widget.mpris import (
    SpotifyMprisClient,
    parse_player_properties,
    parse_metadata,
    extract_variant,
    SPOTIFY_BUS_NAME,
)


def test_extract_variant():
    assert extract_variant("simple_string") == "simple_string"
    assert extract_variant(Variant("s", "unpacked")) == "unpacked"
    assert extract_variant(Variant("b", True)) is True
    assert extract_variant(Variant("t", 12345)) == 12345


def test_parse_player_properties_full():
    raw_props = {
        "PlaybackStatus": Variant("s", "Playing"),
        "CanGoNext": Variant("b", True),
        "CanGoPrevious": Variant("b", False),
        "CanPlay": Variant("b", True),
        "CanPause": Variant("b", True),
        "CanSeek": Variant("b", True),
        "Position": Variant("x", 45000000),  # 45s
        "Metadata": Variant("a{sv}", {
            "xesam:title": Variant("s", "Billie Jean"),
            "xesam:artist": Variant("as", ["Michael Jackson"]),
            "xesam:album": Variant("s", "Thriller"),
            "mpris:length": Variant("t", 294000000),  # 294s = 04:54
            "mpris:artUrl": Variant("s", "https://i.scdn.co/image/art123"),
            "mpris:trackid": Variant("s", "/com/spotify/track/123"),
        }),
    }

    state = parse_player_properties(raw_props)

    assert state.title == "Billie Jean"
    assert state.artist == "Michael Jackson"
    assert state.album == "Thriller"
    assert state.duration_seconds == 294
    assert state.position_seconds == 45
    assert state.formatted_duration == "04:54"
    assert state.formatted_position == "00:45"
    assert state.is_playing is True
    assert state.can_go_next is True
    assert state.can_go_previous is False
    assert state.can_play is True
    assert state.can_pause is True
    assert state.can_seek is True
    assert state.is_online is True
    assert state.art_url == "https://i.scdn.co/image/art123"
    assert state.track_id == "/com/spotify/track/123"


def test_parse_player_properties_multiple_artists():
    raw_props = {
        "PlaybackStatus": "Paused",
        "Metadata": {
            "xesam:title": "Collaborative Hit",
            "xesam:artist": ["Artist Alpha", "Artist Beta", "Artist Gamma"],
            "xesam:album": "Collab Album",
            "mpris:length": 180000000,
        },
    }

    state = parse_player_properties(raw_props)
    assert state.artist == "Artist Alpha, Artist Beta, Artist Gamma"
    assert state.duration_seconds == 180
    assert state.is_playing is False


def test_parse_player_properties_missing_or_corrupt_metadata():
    # Empty properties
    state_empty = parse_player_properties({})
    assert state_empty.title == "Unknown Title"
    assert state_empty.artist == "Unknown Artist"
    assert state_empty.album == ""
    assert state_empty.duration_seconds == 0
    assert state_empty.position_seconds == 0
    assert state_empty.is_playing is False

    # Corrupt string values for integers
    corrupt_props = {
        "Position": "not_an_int",
        "Metadata": {
            "mpris:length": "invalid_length",
            "xesam:title": "",
            "xesam:artist": [],
        },
    }
    state_corrupt = parse_player_properties(corrupt_props)
    assert state_corrupt.duration_seconds == 0
    assert state_corrupt.position_seconds == 0
    assert state_corrupt.title == "Unknown Title"
    assert state_corrupt.artist == "Unknown Artist"


def test_playback_status_handling():
    props_playing = {"PlaybackStatus": "Playing"}
    props_paused = {"PlaybackStatus": "Paused"}
    props_stopped = {"PlaybackStatus": "Stopped"}

    assert parse_player_properties(props_playing).is_playing is True
    assert parse_player_properties(props_paused).is_playing is False
    assert parse_player_properties(props_stopped).is_playing is False


def test_mpris_client_capability_enforcement(qapp):
    client = SpotifyMprisClient()
    mock_player_iface = MagicMock()
    mock_player_iface.call_play_pause = AsyncMock()
    mock_player_iface.call_next = AsyncMock()
    mock_player_iface.call_previous = AsyncMock()

    client._player_iface = mock_player_iface
    client._loop = MagicMock()
    client._loop.is_running.return_value = True
    client._loop.is_closed.return_value = False

    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        mock_run_coro.side_effect = lambda coro, loop: coro.close()

        # 1. PlayPause when playing and can_pause is False
        client._current_state = PlaybackState(
            is_playing=True, can_pause=False, can_play=True, is_online=True
        )
        client.play_pause()
        mock_run_coro.assert_not_called()

        # 2. PlayPause when playing and can_pause is True
        client._current_state = PlaybackState(
            is_playing=True, can_pause=True, can_play=True, is_online=True
        )
        client.play_pause()
        assert mock_run_coro.call_count == 1

        # 3. Next when can_go_next is False
        mock_run_coro.reset_mock()
        client._current_state = PlaybackState(can_go_next=False, is_online=True)
        client.next()
        mock_run_coro.assert_not_called()

        # 4. Next when can_go_next is True
        client._current_state = PlaybackState(can_go_next=True, is_online=True)
        client.next()
        assert mock_run_coro.call_count == 1

        # 5. Previous when can_go_previous is False
        mock_run_coro.reset_mock()
        client._current_state = PlaybackState(can_go_previous=False, is_online=True)
        client.previous()
        mock_run_coro.assert_not_called()

        # 6. Previous when can_go_previous is True
        client._current_state = PlaybackState(can_go_previous=True, is_online=True)
        client.previous()
        assert mock_run_coro.call_count == 1


def test_mpris_client_seeking_arguments_and_clamping(qapp):
    client = SpotifyMprisClient()
    mock_player_iface = MagicMock()
    mock_player_iface.call_set_position = AsyncMock()
    mock_player_iface.get_position = AsyncMock(return_value=30000000)

    client._player_iface = mock_player_iface
    client._loop = MagicMock()
    client._loop.is_running.return_value = True
    client._loop.is_closed.return_value = False

    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        mock_run_coro.side_effect = lambda coro, loop: coro.close()

        # Track with duration 200s
        client._current_state = PlaybackState(
            title="Song",
            duration_seconds=200,
            can_seek=True,
            track_id="/com/spotify/track/abc1234",
            is_online=True,
        )

        # 1. Standard seek to 30s -> 30,000,000 us
        client.seek(30)
        assert mock_run_coro.call_count == 1
        assert client._current_state.position_seconds == 30

        # 2. Clamped seek beyond duration -> clamped to 200s (200,000,000 us)
        mock_run_coro.reset_mock()
        client.seek(350)
        assert mock_run_coro.call_count == 1
        assert client._current_state.position_seconds == 200

        # 3. Negative seek -> clamped to 0s
        mock_run_coro.reset_mock()
        client.seek(-20)
        assert mock_run_coro.call_count == 1
        assert client._current_state.position_seconds == 0

        # 4. Seeking when can_seek is False
        mock_run_coro.reset_mock()
        client._current_state.can_seek = False
        client.seek(50)
        mock_run_coro.assert_not_called()

        # 5. Seeking when track_id is invalid (does not start with '/')
        mock_run_coro.reset_mock()
        client._current_state.can_seek = True
        client._current_state.track_id = "invalid_id"
        client.seek(50)
        mock_run_coro.assert_not_called()

        # 6. Seeking when offline
        mock_run_coro.reset_mock()
        client._current_state.track_id = "/com/spotify/track/abc"
        client._current_state.is_online = False
        client.seek(50)
        mock_run_coro.assert_not_called()


def test_mpris_client_offline_behavior(qapp):
    client = SpotifyMprisClient()
    client._loop = MagicMock()
    client._loop.is_running.return_value = True
    client._loop.is_closed.return_value = False

    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        # Offline state should reject all actions
        client._current_state = get_offline_state()
        client.play_pause()
        client.next()
        client.previous()
        client.seek(10)
        mock_run_coro.assert_not_called()


def test_mpris_client_properties_changed_merging(qapp):
    client = SpotifyMprisClient()
    client._loop = MagicMock()
    client._loop.is_running.return_value = True
    received_states = []
    client.state_changed.connect(received_states.append)

    # Initial properties
    client._cached_props = {
        "PlaybackStatus": Variant("s", "Playing"),
        "CanGoNext": Variant("b", True),
        "Metadata": Variant("a{sv}", {
            "xesam:title": Variant("s", "Initial Song"),
            "xesam:artist": Variant("as", ["Initial Artist"]),
            "mpris:trackid": Variant("s", "/com/spotify/track/track1"),
            "mpris:length": Variant("t", 200000000),
        }),
    }
    client._current_state = parse_player_properties(client._cached_props)

    # Simulate PropertiesChanged event containing only PlaybackStatus
    changed = {"PlaybackStatus": Variant("s", "Paused")}
    client._handle_properties_changed(changed)

    assert len(received_states) == 1
    updated = received_states[0]
    assert updated.is_playing is False
    # Ensure title and artist were preserved
    assert updated.title == "Initial Song"
    assert updated.artist == "Initial Artist"
    assert updated.duration_seconds == 200


def test_mpris_client_track_change_resets_position(qapp):
    client = SpotifyMprisClient()
    client._loop = MagicMock()
    client._loop.is_running.return_value = True
    received_states = []
    client.state_changed.connect(received_states.append)

    # Initial track with progress at 120s
    client._current_state = PlaybackState(
        title="Old Track",
        track_id="/com/spotify/track/old",
        duration_seconds=240,
        position_seconds=120,
        is_playing=True,
    )
    client._cached_props = {
        "PlaybackStatus": "Playing",
        "Position": 120000000,
        "Metadata": {
            "mpris:trackid": "/com/spotify/track/old",
            "xesam:title": "Old Track",
            "mpris:length": 240000000,
        },
    }

    # Simulate track change to a new song
    new_metadata = {
        "mpris:trackid": Variant("s", "/com/spotify/track/new"),
        "xesam:title": Variant("s", "New Track"),
        "xesam:artist": Variant("as", ["New Artist"]),
        "mpris:length": Variant("t", 180000000),
    }

    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        mock_run_coro.side_effect = lambda coro, loop: coro.close()
        client._handle_properties_changed({"Metadata": Variant("a{sv}", new_metadata)})

    assert len(received_states) == 1
    new_state = received_states[0]
    assert new_state.title == "New Track"
    assert new_state.track_id == "/com/spotify/track/new"
    # Position must be reset to 0 to prevent displaying stale progress
    assert new_state.position_seconds == 0
    assert new_state.duration_seconds == 180


def test_mpris_client_handle_seeked_signal(qapp):
    client = SpotifyMprisClient()
    client._current_state = PlaybackState(
        duration_seconds=300, position_seconds=10, is_playing=True
    )

    states = []
    client.state_changed.connect(states.append)

    # Simulate Spotify emitting Seeked signal to 125,000,000 us (125s)
    client._handle_seeked(125000000)

    assert len(states) == 1
    assert states[0].position_seconds == 125
    assert states[0].formatted_position == "02:05"


def test_mpris_client_polling_lifecycle(qapp):
    client = SpotifyMprisClient()
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = True
    mock_loop.is_closed.return_value = False
    mock_task = MagicMock()
    mock_task.done.return_value = False

    def _create_task_mock(coro):
        coro.close()
        return mock_task

    mock_loop.create_task.side_effect = _create_task_mock

    client._loop = mock_loop

    # 1. Starting polling when not running creates task
    client._start_polling()
    assert mock_loop.create_task.call_count == 1
    assert client._polling_task == mock_task

    # 2. Starting polling again while task is active does not recreate
    client._start_polling()
    assert mock_loop.create_task.call_count == 1

    # 3. Stopping polling cancels task
    client._stop_polling()
    mock_task.cancel.assert_called_once()
    assert client._polling_task is None


def test_mpris_client_disconnect_and_reconnect(qapp):
    client = SpotifyMprisClient()
    client._loop = MagicMock()
    client._loop.is_running.return_value = True

    states = []
    connections = []
    client.state_changed.connect(states.append)
    client.connection_changed.connect(connections.append)

    # Simulate disconnect: Spotify shuts down
    client._handle_name_owner_changed(SPOTIFY_BUS_NAME, ":1.123", "")

    assert len(connections) == 1
    assert connections[-1] is False
    assert states[-1].is_online is False
    assert states[-1].title == "Spotify is not running"

    # Simulate reconnect: Spotify starts up
    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        mock_run_coro.side_effect = lambda coro, loop: coro.close()
        client._handle_name_owner_changed(SPOTIFY_BUS_NAME, "", ":1.456")
        assert mock_run_coro.call_count == 1


def test_mpris_client_polling_loop_recovers_from_transient_error():
    async def _run():
        client = SpotifyMprisClient()
        client._current_state = PlaybackState(
            is_online=True,
            is_playing=True,
            duration_seconds=200,
            position_seconds=10,
        )
        client._position_lock = asyncio.Lock()

        mock_player = AsyncMock()
        # First call raises an exception (transient error), second call returns 15s
        mock_player.get_position.side_effect = [RuntimeError("Transient D-Bus failure"), 15000000]
        client._player_iface = mock_player

        states = []
        client.state_changed.connect(states.append)

        # Run loop for a short duration with mocked sleep
        with patch("asyncio.sleep", AsyncMock(return_value=None)) as mock_sleep:
            async def stop_after_two(*args):
                if mock_player.get_position.call_count >= 2:
                    client._current_state.is_playing = False

            mock_sleep.side_effect = stop_after_two
            await client._poll_position_loop()

        assert mock_player.get_position.call_count == 2
        assert len(states) == 1
        assert states[0].position_seconds == 15

    asyncio.run(_run())


def test_mpris_client_polling_prevents_overlap_with_lock():
    async def _run():
        client = SpotifyMprisClient()
        client._current_state = PlaybackState(
            is_online=True,
            is_playing=True,
            duration_seconds=200,
            position_seconds=10,
        )
        client._position_lock = asyncio.Lock()
        mock_player = AsyncMock()
        client._player_iface = mock_player

        # Acquire lock externally as if seek or manual fetch is currently running
        await client._position_lock.acquire()
        assert client._position_lock.locked()

        with patch("asyncio.sleep", AsyncMock(return_value=None)) as mock_sleep:
            async def stop_loop(*args):
                client._current_state.is_playing = False

            mock_sleep.side_effect = stop_loop
            await client._poll_position_loop()

        # get_position should have been skipped because lock was held
        assert mock_player.get_position.call_count == 0
        client._position_lock.release()

    asyncio.run(_run())


def test_mpris_client_actions_never_block_gui_thread(qapp):
    client = SpotifyMprisClient()
    client._current_state = PlaybackState(
        is_online=True,
        is_playing=True,
        can_play=True,
        can_pause=True,
        can_go_next=True,
        can_go_previous=True,
        can_seek=True,
        duration_seconds=200,
        track_id="/com/spotify/track/abc",
    )
    client._player_iface = MagicMock()
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = True
    mock_loop.is_closed.return_value = False
    client._loop = mock_loop

    with patch("asyncio.run_coroutine_threadsafe") as mock_run_coro:
        mock_run_coro.side_effect = lambda coro, loop: coro.close()

        # Invoking from Qt main thread
        client.play_pause()
        assert mock_run_coro.call_count == 1

        client.next()
        assert mock_run_coro.call_count == 2

        client.previous()
        assert mock_run_coro.call_count == 3

        client.seek(50)
        assert mock_run_coro.call_count == 4
