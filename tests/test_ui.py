"""Tests for PySide6 UI components, glass styling, dragging, and layout constraints."""

import pytest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import QApplication

from spotify_widget.models import (
    PlaybackState,
    get_placeholder_state,
    get_long_text_placeholder_state,
)
from spotify_widget.ui.card import MusicCardWidget, GlassCardContainer
from spotify_widget.ui.style import CARD_WIDTH, CARD_HEIGHT, ARTWORK_SIZE


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
