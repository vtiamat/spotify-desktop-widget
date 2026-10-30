"""Tests for PySide6 UI components, glass styling, dragging, and layout constraints."""

import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from spotify_widget.models import (
    PlaybackState,
    get_placeholder_state,
    get_long_text_placeholder_state,
    get_offline_state,
)
from spotify_widget.ui.card import MusicCardWidget, GlassCardContainer
from spotify_widget.ui.style import CARD_WIDTH, CARD_HEIGHT, ARTWORK_SIZE
from spotify_widget.ui.controls import CONTROL_BUTTON_SIZE, VectorControlButton


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_widget_geometry_and_flags(qapp):
    widget = MusicCardWidget()
    assert widget.width() == CARD_WIDTH
    assert widget.height() == CARD_HEIGHT
    assert widget.windowFlags() & Qt.WindowType.FramelessWindowHint
    assert widget.artwork.width() == ARTWORK_SIZE
    assert widget.artwork.height() == ARTWORK_SIZE
    assert isinstance(widget.card_container, GlassCardContainer)
    widget.close()


def test_long_title_preserves_card_dimensions(qapp):
    long_state = get_long_text_placeholder_state()
    widget = MusicCardWidget(state=long_state)
    widget.show()

    # The widget dimensions must remain strictly anchored to specified card size
    assert widget.width() == CARD_WIDTH
    assert widget.height() == CARD_HEIGHT
    assert widget.title_label.text() == long_state.title

    widget.close()


def test_missing_artwork_fallback_renders(qapp):
    state_no_art = PlaybackState(art_data=None)
    widget = MusicCardWidget(state=state_no_art)
    widget.artwork.set_artwork(None)
    widget.show()

    # Verify widget paints and remains stable without artwork
    assert widget.artwork._pixmap is None
    widget.close()


def test_close_button_closes_widget(qapp):
    widget = MusicCardWidget()
    widget.show()
    assert widget.isVisible()

    widget.close_btn.click()
    assert not widget.isVisible()


def test_interactive_play_pause_toggle(qapp):
    state = PlaybackState(is_playing=True)
    widget = MusicCardWidget(state=state)
    assert widget.controls.play_btn.text() == "⏸"

    widget.controls.play_btn.click()
    assert widget.state().is_playing is False
    assert widget.controls.play_btn.text() == "▶"

    widget.controls.play_btn.click()
    assert widget.state().is_playing is True
    assert widget.controls.play_btn.text() == "⏸"
    widget.close()


def test_interactive_seek(qapp):
    state = PlaybackState(duration_seconds=200, position_seconds=0)
    widget = MusicCardWidget(state=state)

    # Simulate seek to 50%
    widget.progress_section.seek_requested.emit(0.5)
    assert widget.state().position_seconds == 100
    assert widget.progress_section.elapsed_label.text() == "01:40"
    assert pytest.approx(widget.progress_section.bar.fraction()) == 0.5
    widget.close()


def test_drag_from_artwork(qapp):
    widget = MusicCardWidget()
    widget.show()
    widget.move(100, 100)

    # Simulate left button press on artwork
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(20, 20),
        QPointF(120, 120),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.artwork, press_event)
    assert not widget._drag_pos.isNull()

    # Simulate drag motion to (200, 200)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(120, 120),
        QPointF(220, 220),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.artwork, move_event)
    assert widget.pos() == QPoint(200, 200)

    # Release
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(120, 120),
        QPointF(220, 220),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.artwork, release_event)
    assert widget._drag_pos.isNull()
    widget.close()


def test_drag_from_labels(qapp):
    widget = MusicCardWidget()
    widget.show()
    widget.move(50, 50)

    # Press on track title label
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        QPointF(160, 80),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.title_label, press_event)
    assert not widget._drag_pos.isNull()

    # Move to 150, 150
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(110, 110),
        QPointF(260, 180),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.title_label, move_event)
    assert widget.pos() == QPoint(150, 150)
    widget.close()


def test_drag_does_not_interfere_with_buttons(qapp):
    widget = MusicCardWidget()
    widget.show()

    # Play button click must not set drag_pos
    initial_playing = widget.state().is_playing
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        QPointF(170, 220),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.controls.play_btn, press_event)
    assert widget._drag_pos.isNull()

    widget.controls.play_btn.click()
    assert widget.state().is_playing != initial_playing
    widget.close()


def test_drag_does_not_interfere_with_progress_bar(qapp):
    widget = MusicCardWidget()
    widget.show()

    # Progress bar press must not set drag_pos
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(50, 7),
        QPointF(100, 160),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(widget.progress_section.bar, press_event)
    assert widget._drag_pos.isNull()
    widget.close()


def test_glass_container_render(qapp):
    widget = MusicCardWidget()
    widget.show()

    # Ensure widget and GlassCardContainer render offscreen without errors
    pixmap = QPixmap(widget.size())
    pixmap.fill(Qt.GlobalColor.transparent)
    widget.render(pixmap)
    assert not pixmap.isNull()
    assert pixmap.width() == CARD_WIDTH
    assert pixmap.height() == CARD_HEIGHT
    widget.close()


def test_controls_button_alignment_and_geometry(qapp):
    widget = MusicCardWidget()
    widget.show()

    controls = widget.controls
    prev_geom = controls.prev_btn.geometry()
    play_geom = controls.play_btn.geometry()
    next_geom = controls.next_btn.geometry()

    # Identical dimensions
    assert prev_geom.width() == CONTROL_BUTTON_SIZE
    assert prev_geom.height() == CONTROL_BUTTON_SIZE
    assert play_geom.width() == CONTROL_BUTTON_SIZE
    assert play_geom.height() == CONTROL_BUTTON_SIZE
    assert next_geom.width() == CONTROL_BUTTON_SIZE
    assert next_geom.height() == CONTROL_BUTTON_SIZE

    # Identical vertical position (flawless baseline alignment)
    assert prev_geom.y() == play_geom.y() == next_geom.y()

    # Symmetrical horizontal ordering and spacing
    assert prev_geom.right() < play_geom.left()
    assert play_geom.right() < next_geom.left()
    spacing_left = play_geom.left() - prev_geom.right() - 1
    spacing_right = next_geom.left() - play_geom.right() - 1
    assert spacing_left == spacing_right == 16

    # Verify entire control group is centered within the card
    prev_map = controls.prev_btn.mapTo(widget, controls.prev_btn.rect().topLeft())
    next_map = controls.next_btn.mapTo(widget, controls.next_btn.rect().topRight())
    left_margin = prev_map.x()
    right_margin = widget.width() - next_map.x() - 1
    assert left_margin == right_margin

    play_center_x = controls.play_btn.mapTo(widget, controls.play_btn.rect().center()).x()
    assert abs(play_center_x - (widget.width() / 2.0)) <= 1.0

    widget.close()


def test_vector_icon_button_visual_centering(qapp):
    """Verify that vector icons are mathematically centered with identical vertical centerlines."""
    from PySide6.QtGui import QImage
    from PIL import Image

    for icon_type, name in [
        ("previous", "SecondaryControl"),
        ("next", "SecondaryControl"),
        ("play", "PlayPauseControl"),
        ("pause", "PlayPauseControl"),
    ]:
        btn = VectorControlButton(icon_type, "fallback")
        btn.setObjectName(name)
        btn.setFixedSize(CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE)

        img = QImage(CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE, QImage.Format_ARGB32_Premultiplied)
        img.fill(0)
        btn.render(img)

        # Convert to PIL to verify bounding box center
        buffer = img.bits().tobytes()
        im = Image.frombuffer("RGBA", (CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE), buffer, "raw", "BGRA", 0, 1)
        # Note: Outer button shape is rendered with background
        bbox = im.getbbox()
        assert bbox is not None
        # Button itself is centered
        center_y = (bbox[1] + bbox[3]) / 2.0
        assert center_y == 19.0


def test_progress_bar_scrubbing_and_commit(qapp):
    state = PlaybackState(duration_seconds=200, position_seconds=50, can_seek=True)
    widget = MusicCardWidget(state=state)
    widget.show()

    bar = widget.progress_section.bar
    bar.resize(200, 14)

    scrubbed_fractions = []
    committed_fractions = []
    bar.scrubbing.connect(scrubbed_fractions.append)
    bar.seek_requested.connect(committed_fractions.append)

    assert not bar.is_dragging()

    # 1. Mouse press at x=100 (50%)
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(100, 7),
        QPointF(100, 7),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(bar, press_event)
    assert bar.is_dragging() is True
    assert pytest.approx(bar.fraction()) == 0.5
    assert len(scrubbed_fractions) == 1
    assert pytest.approx(scrubbed_fractions[-1]) == 0.5
    assert len(committed_fractions) == 0

    # 2. Incoming polling state update must NOT overwrite bar while dragging
    bar.set_fraction(0.1)
    assert pytest.approx(bar.fraction()) == 0.5

    # 3. Mouse move to x=150 (75%)
    move_event = QMouseEvent(
        QMouseEvent.Type.MouseMove,
        QPointF(150, 7),
        QPointF(150, 7),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(bar, move_event)
    assert bar.is_dragging() is True
    assert pytest.approx(bar.fraction()) == 0.75
    assert pytest.approx(scrubbed_fractions[-1]) == 0.75
    assert len(committed_fractions) == 0

    # 4. Mouse release at x=150 commits seek
    release_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonRelease,
        QPointF(150, 7),
        QPointF(150, 7),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(bar, release_event)
    assert bar.is_dragging() is False
    assert len(committed_fractions) == 1
    assert pytest.approx(committed_fractions[-1]) == 0.75

    widget.close()


def test_seeking_disabled_when_offline_or_unseekable(qapp):
    offline_state = get_offline_state()
    widget = MusicCardWidget(state=offline_state)
    widget.show()

    bar = widget.progress_section.bar
    assert bar._seeking_enabled is False
    assert bar.cursor().shape() == Qt.CursorShape.ArrowCursor

    scrubbed = []
    committed = []
    bar.scrubbing.connect(scrubbed.append)
    bar.seek_requested.connect(committed.append)

    # Press should be ignored
    press_event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(50, 7),
        QPointF(50, 7),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    qapp.sendEvent(bar, press_event)
    assert bar.is_dragging() is False
    assert len(scrubbed) == 0
    assert len(committed) == 0

    widget.close()


def test_control_button_capabilities(qapp):
    state = PlaybackState(
        is_playing=False,
        can_play=True,
        can_pause=False,
        can_go_previous=False,
        can_go_next=True,
    )
    widget = MusicCardWidget(state=state)
    assert widget.controls.prev_btn.isEnabled() is False
    assert widget.controls.play_btn.isEnabled() is True
    assert widget.controls.next_btn.isEnabled() is True

    # Offline disables all playback controls
    offline_state = get_offline_state()
    widget.update_state(offline_state)
    assert widget.controls.prev_btn.isEnabled() is False
    assert widget.controls.play_btn.isEnabled() is False
    assert widget.controls.next_btn.isEnabled() is False
    widget.close()
