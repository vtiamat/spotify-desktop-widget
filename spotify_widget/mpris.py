"""Spotify MPRIS client managing D-Bus communication, lifecycle, and state."""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QObject, QThread, Signal
from dbus_next.aio import MessageBus
from dbus_next.signature import Variant

from spotify_widget.models import PlaybackState, get_offline_state

logger = logging.getLogger(__name__)

SPOTIFY_BUS_NAME = "org.mpris.MediaPlayer2.spotify"
MPRIS_OBJECT_PATH = "/org/mpris/MediaPlayer2"
PLAYER_INTERFACE = "org.mpris.MediaPlayer2.Player"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
DBUS_SERVICE_NAME = "org.freedesktop.DBus"
DBUS_OBJECT_PATH = "/org/freedesktop/DBus"
DBUS_INTERFACE = "org.freedesktop.DBus"


def extract_variant(val: Any) -> Any:
    """Extract raw Python value from a dbus-next Variant or return as-is."""
    if isinstance(val, Variant):
        return val.value
    return val


def parse_metadata(raw_metadata: Any) -> Dict[str, Any]:
    """Parse raw D-Bus metadata dictionary into standard Python types."""
    parsed: Dict[str, Any] = {}
    if not isinstance(raw_metadata, dict):
        return parsed
    for k, v in raw_metadata.items():
        parsed[k] = extract_variant(v)
    return parsed


def parse_player_properties(props: Dict[str, Any]) -> PlaybackState:
    """Convert raw MPRIS properties dictionary into a PlaybackState instance."""
    unpacked: Dict[str, Any] = {}
    for k, v in props.items():
        unpacked[k] = extract_variant(v)

    raw_meta = unpacked.get("Metadata", {})
    meta = parse_metadata(raw_meta)

    # 1. Track title
    title = meta.get("xesam:title")
    title_str = str(title).strip() if title else "Unknown Title"

    # 2. Artist
    raw_artist = meta.get("xesam:artist")
    if isinstance(raw_artist, list):
        artist_str = ", ".join(str(a) for a in raw_artist if a) or "Unknown Artist"
    elif raw_artist:
        artist_str = str(raw_artist)
    else:
        artist_str = "Unknown Artist"

    # 3. Album
    album_val = meta.get("xesam:album")
    album_str = str(album_val).strip() if album_val else ""

    # 4. Duration (mpris:length is in microseconds)
    raw_length = meta.get("mpris:length", 0)
    try:
        length_us = int(raw_length)
        duration_seconds = max(0, length_us // 1_000_000)
    except (ValueError, TypeError):
        duration_seconds = 0

    # 5. Position (in microseconds if present)
    raw_pos = unpacked.get("Position", 0)
    try:
        pos_us = int(raw_pos)
        position_seconds = max(0, pos_us // 1_000_000)
    except (ValueError, TypeError):
        position_seconds = 0

    # 6. Playback status and capabilities
    playback_status = str(unpacked.get("PlaybackStatus", "Paused"))
    is_playing = (playback_status.lower() == "playing")

    can_go_next = bool(unpacked.get("CanGoNext", True))
    can_go_previous = bool(unpacked.get("CanGoPrevious", True))
    can_play = bool(unpacked.get("CanPlay", True))
    can_pause = bool(unpacked.get("CanPause", True))
    can_seek = bool(unpacked.get("CanSeek", True))

    # 7. Artwork and track id
    art_url = meta.get("mpris:artUrl")
    art_url_str = str(art_url) if art_url else None

    track_id = meta.get("mpris:trackid")
    track_id_str = str(track_id) if track_id else None

    return PlaybackState(
        title=title_str,
        artist=artist_str,
        album=album_str,
        duration_seconds=duration_seconds,
        position_seconds=position_seconds,
        is_playing=is_playing,
        can_go_previous=can_go_previous,
        can_go_next=can_go_next,
        can_seek=can_seek,
        can_play=can_play,
        can_pause=can_pause,
        is_online=True,
        art_url=art_url_str,
        track_id=track_id_str,
        art_data=None,
    )


class MprisWorkerThread(QThread):
    """Background worker thread running asyncio event loop for D-Bus communication."""

    def __init__(self, client: "SpotifyMprisClient"):
        super().__init__()
        self._client = client
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event: Optional[asyncio.Event] = None

    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._stop_event = asyncio.Event()
        try:
            self._loop.run_until_complete(
                self._client._async_loop(self._loop, self._stop_event)
            )
        except Exception as e:
            logger.error(f"Error in MPRIS worker loop: {e}")
        finally:
            try:
                # Cancel remaining tasks
                pending = asyncio.all_tasks(self._loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
            except Exception:
                pass
            self._loop.close()

    def stop(self):
        """Signal the asyncio loop to stop and wait for thread termination."""
        if self._loop and self._loop.is_running() and not self._loop.is_closed():
            if self._stop_event:
                self._loop.call_soon_threadsafe(self._stop_event.set)
        self.wait(2000)


class SpotifyMprisClient(QObject):
    """Client for Spotify MPRIS interface providing signals, polling, and playback actions."""

    state_changed = Signal(PlaybackState)
    connection_changed = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_state = get_offline_state()
        self._cached_props: Dict[str, Any] = {}
        self._worker: Optional[MprisWorkerThread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # D-Bus proxy references
        self._bus: Optional[MessageBus] = None
        self._spotify_obj = None
        self._player_iface = None
        self._props_iface = None
        self._dbus_iface = None

        # Background position polling task and overlap guard
        self._polling_task: Optional[asyncio.Task] = None
        self._position_lock: Optional[asyncio.Lock] = None

    def start(self):
        """Start the background D-Bus listener worker thread."""
        if self._worker is None:
            self._worker = MprisWorkerThread(self)
            self._worker.start()

    def stop(self):
        """Stop the background worker thread and disconnect from D-Bus."""
        if self._worker is not None:
            self._worker.stop()
            self._worker = None

    def current_state(self) -> PlaybackState:
        """Return the current cached PlaybackState."""
        return self._current_state

    # --- Thread-Safe Action Methods (Invoked from Qt UI) ---
    def play_pause(self):
        """Toggle play/pause if permitted by current capabilities."""
        if not self._current_state.is_online or self._player_iface is None:
            return

        # Check capability
        if self._current_state.is_playing:
            if not self._current_state.can_pause:
                logger.debug("Cannot pause: CanPause is False")
                return
        else:
            if not self._current_state.can_play:
                logger.debug("Cannot play: CanPlay is False")
                return

        if self._loop and self._loop.is_running() and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._call_play_pause(), self._loop)

    def next(self):
        """Skip to next track if permitted by CanGoNext."""
        if not self._current_state.is_online or self._player_iface is None:
            return
        if not self._current_state.can_go_next:
            logger.debug("Cannot skip next: CanGoNext is False")
            return
        if self._loop and self._loop.is_running() and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._call_next(), self._loop)

    def previous(self):
        """Skip to previous track if permitted by CanGoPrevious."""
        if not self._current_state.is_online or self._player_iface is None:
            return
        if not self._current_state.can_go_previous:
            logger.debug("Cannot skip previous: CanGoPrevious is False")
            return
        if self._loop and self._loop.is_running() and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(self._call_previous(), self._loop)

    def seek(self, position_seconds: int):
        """Seek to specified position in seconds using MPRIS SetPosition."""
        if not self._current_state.is_online or self._player_iface is None:
            return
        if not self._current_state.can_seek:
            logger.debug("Cannot seek: CanSeek is False")
            return

        track_id = self._current_state.track_id
        if not track_id or not str(track_id).startswith("/"):
            logger.debug(f"Cannot seek: invalid or missing track_id '{track_id}'")
            return

        # Clamp position between 0 and duration
        if self._current_state.duration_seconds > 0:
            target_sec = max(0, min(position_seconds, self._current_state.duration_seconds))
        else:
            target_sec = max(0, position_seconds)

        position_us = int(target_sec * 1_000_000)

        # Optimistically update current state so UI reflects the seek position immediately
        self._current_state.position_seconds = target_sec
        self.state_changed.emit(self._current_state)

        if self._loop and self._loop.is_running() and not self._loop.is_closed():
            asyncio.run_coroutine_threadsafe(
                self._call_set_position(track_id, position_us), self._loop
            )

    # --- Async D-Bus Event Loop ---
    async def _async_loop(self, loop: asyncio.AbstractEventLoop, stop_event: asyncio.Event):
        self._loop = loop
        self._position_lock = asyncio.Lock()
        try:
            self._bus = await MessageBus().connect()

            # 1. Listen for NameOwnerChanged to handle Spotify lifecycle
            dbus_intro = await self._bus.introspect(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH)
            dbus_obj = self._bus.get_proxy_object(DBUS_SERVICE_NAME, DBUS_OBJECT_PATH, dbus_intro)
            self._dbus_iface = dbus_obj.get_interface(DBUS_INTERFACE)

            def on_name_owner_changed(name: str, old_owner: str, new_owner: str):
                self._handle_name_owner_changed(name, old_owner, new_owner)

            self._dbus_iface.on_name_owner_changed(on_name_owner_changed)

            # 2. Check if Spotify is already running
            has_owner = await self._dbus_iface.call_name_has_owner(SPOTIFY_BUS_NAME)
            if has_owner:
                await self._attach_spotify()
            else:
                self._detach_spotify()

            # 3. Wait until stopped
            await stop_event.wait()
        except Exception as e:
            logger.error(f"D-Bus connection error: {e}")
            self._detach_spotify()
        finally:
            self._stop_polling()
            if self._bus:
                try:
                    self._bus.disconnect()
                except Exception:
                    pass
                self._bus = None

    def _handle_name_owner_changed(self, name: str, old_owner: str, new_owner: str):
        """Handle service lifecycle events on the session bus."""
        if name != SPOTIFY_BUS_NAME:
            return

        if new_owner:
            # Spotify started or restarted
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(self._attach_spotify(), self._loop)
        else:
            # Spotify stopped
            self._detach_spotify()

    async def _attach_spotify(self):
        """Introspect Spotify, subscribe to PropertiesChanged, and fetch current state."""
        if self._bus is None:
            return
        try:
            intro = await self._bus.introspect(SPOTIFY_BUS_NAME, MPRIS_OBJECT_PATH)
            self._spotify_obj = self._bus.get_proxy_object(SPOTIFY_BUS_NAME, MPRIS_OBJECT_PATH, intro)
            self._player_iface = self._spotify_obj.get_interface(PLAYER_INTERFACE)
            self._props_iface = self._spotify_obj.get_interface(PROPERTIES_INTERFACE)

            def on_properties_changed(interface_name: str, changed_properties: Dict[str, Any], invalidated_properties: List[str]):
                if interface_name == PLAYER_INTERFACE:
                    self._handle_properties_changed(changed_properties)

            self._props_iface.on_properties_changed(on_properties_changed)

            # Subscribe to Seeked signal
            def on_seeked(position_us: int):
                self._handle_seeked(position_us)

            self._player_iface.on_seeked(on_seeked)

            # Retrieve all current player properties
            raw_props = await self._props_iface.call_get_all(PLAYER_INTERFACE)
            self._cached_props.clear()
            for k, v in raw_props.items():
                self._cached_props[k] = extract_variant(v)

            # Query initial live position
            try:
                pos_us = await self._player_iface.get_position()
                self._cached_props["Position"] = pos_us
            except Exception:
                pass

            state = parse_player_properties(self._cached_props)
            self._current_state = state
            self.state_changed.emit(state)
            self.connection_changed.emit(True)

            if state.is_playing:
                self._start_polling()
            else:
                self._stop_polling()
        except Exception as e:
            logger.error(f"Failed to attach to Spotify: {e}")
            self._detach_spotify()

    def _detach_spotify(self):
        """Clean up Spotify references, stop polling, and emit offline state."""
        self._stop_polling()
        self._spotify_obj = None
        self._player_iface = None
        self._props_iface = None
        self._cached_props.clear()
        state = get_offline_state()
        self._current_state = state
        self.state_changed.emit(state)
        self.connection_changed.emit(False)

    def _handle_properties_changed(self, changed_properties: Dict[str, Any]):
        """Merge changed properties, detect track changes, manage polling, and emit updated state."""
        old_track_id = self._current_state.track_id
        old_title = self._current_state.title

        # Check if Metadata was updated
        if "Metadata" in changed_properties:
            meta = parse_metadata(extract_variant(changed_properties["Metadata"]))
            new_track_id = meta.get("mpris:trackid")
            new_title = meta.get("xesam:title")

            # If track changed, reset position to 0 immediately to prevent stale timestamps
            if new_track_id != old_track_id or (new_title and new_title != old_title):
                self._cached_props["Position"] = 0
                self._current_state.position_seconds = 0
                if self._loop and self._loop.is_running() and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self._fetch_current_position(), self._loop)

        for k, v in changed_properties.items():
            self._cached_props[k] = extract_variant(v)

        state = parse_player_properties(self._cached_props)
        self._current_state = state

        # Manage periodic polling based on playback state
        if state.is_playing:
            self._start_polling()
        else:
            self._stop_polling()
            # On pause/stop, query position once to record exact pause timestamp
            if self._loop and self._loop.is_running() and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._fetch_current_position(), self._loop)

        self.state_changed.emit(state)

    def _handle_seeked(self, position_us: int):
        """Handle Seeked signal from Spotify."""
        pos_sec = max(0, int(position_us // 1_000_000))
        if self._current_state.duration_seconds > 0:
            pos_sec = min(pos_sec, self._current_state.duration_seconds)

        self._cached_props["Position"] = position_us
        self._current_state.position_seconds = pos_sec
        self.state_changed.emit(self._current_state)

    # --- Position Polling Mechanism ---
    def _start_polling(self):
        """Start periodic position query loop if not already running."""
        if self._polling_task is None or self._polling_task.done():
            if self._loop and self._loop.is_running() and not self._loop.is_closed():
                self._polling_task = self._loop.create_task(self._poll_position_loop())

    def _stop_polling(self):
        """Stop periodic position query loop."""
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
        self._polling_task = None

    async def _poll_position_loop(self):
        """Periodically query position while playback is active (500ms interval)."""
        while self._current_state.is_online and self._current_state.is_playing:
            try:
                await asyncio.sleep(0.5)
                if not self._current_state.is_online or not self._current_state.is_playing:
                    break
                if self._player_iface:
                    # Prevent overlapping requests with seeking or manual fetch
                    if self._position_lock is not None:
                        if self._position_lock.locked():
                            continue
                        async with self._position_lock:
                            pos_us = await self._player_iface.get_position()
                    else:
                        pos_us = await self._player_iface.get_position()

                    pos_sec = max(0, int(pos_us // 1_000_000))
                    if self._current_state.duration_seconds > 0:
                        pos_sec = min(pos_sec, self._current_state.duration_seconds)

                    if pos_sec != self._current_state.position_seconds:
                        self._cached_props["Position"] = pos_us
                        self._current_state.position_seconds = pos_sec
                        self.state_changed.emit(self._current_state)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Position query loop encountered error: {e}")
                try:
                    await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    break

    async def _fetch_current_position(self):
        """Fetch current position once and update state without overlapping."""
        try:
            if self._player_iface:
                if self._position_lock is not None:
                    async with self._position_lock:
                        pos_us = await self._player_iface.get_position()
                else:
                    pos_us = await self._player_iface.get_position()

                pos_sec = max(0, int(pos_us // 1_000_000))
                if self._current_state.duration_seconds > 0:
                    pos_sec = min(pos_sec, self._current_state.duration_seconds)
                self._cached_props["Position"] = pos_us
                self._current_state.position_seconds = pos_sec
                self.state_changed.emit(self._current_state)
        except Exception as e:
            logger.debug(f"Single position fetch error: {e}")

    # --- D-Bus Coroutine Invocations ---
    async def _call_play_pause(self):
        try:
            if self._player_iface:
                await self._player_iface.call_play_pause()
        except Exception as e:
            logger.error(f"Error calling PlayPause: {e}")

    async def _call_next(self):
        try:
            if self._player_iface:
                await self._player_iface.call_next()
        except Exception as e:
            logger.error(f"Error calling Next: {e}")

    async def _call_previous(self):
        try:
            if self._player_iface:
                await self._player_iface.call_previous()
        except Exception as e:
            logger.error(f"Error calling Previous: {e}")

    async def _call_set_position(self, track_id: str, position_us: int):
        try:
            if self._player_iface:
                if self._position_lock is not None:
                    async with self._position_lock:
                        await self._player_iface.call_set_position(track_id, position_us)
                        # Confirm position with Spotify after seeking
                        pos_us = await self._player_iface.get_position()
                else:
                    await self._player_iface.call_set_position(track_id, position_us)
                    pos_us = await self._player_iface.get_position()

                pos_sec = max(0, int(pos_us // 1_000_000))
                if self._current_state.duration_seconds > 0:
                    pos_sec = min(pos_sec, self._current_state.duration_seconds)
                self._cached_props["Position"] = pos_us
                self._current_state.position_seconds = pos_sec
                self.state_changed.emit(self._current_state)
        except Exception as e:
            logger.error(f"Error calling SetPosition: {e}")
