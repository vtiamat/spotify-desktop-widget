"""Main MusicCardWidget integrating artwork, track info, progress, and controls."""

from typing import Optional
from PySide6.QtCore import Qt, QPoint, QRectF, QEvent, QObject
from PySide6.QtGui import (
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QColor,
    QLinearGradient,
    QPen,
    QBrush,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
)

from spotify_widget.models import PlaybackState, get_placeholder_state
from spotify_widget.ui.artwork import ArtworkWidget, create_fictional_cover_pixmap
from spotify_widget.ui.controls import SpotifyBadge, PlaybackControls
from spotify_widget.ui.elided_label import ElidedLabel
from spotify_widget.ui.progress import ProgressSection, ClickableProgressBar
from spotify_widget.ui.style import (
    CARD_WIDTH,
    CARD_HEIGHT,
    ARTWORK_SIZE,
    CORNER_RADIUS,
    GLASS_BG_TOP,
    GLASS_BG_BOTTOM,
    GLASS_SHEEN_START,
    GLASS_SHEEN_END,
    GLASS_BORDER_TOP_LEFT,
    GLASS_BORDER_MID,
    GLASS_BORDER_BOTTOM_RIGHT,
    CARD_STYLESHEET,
)


class GlassCardContainer(QWidget):
    """Semi-transparent dark glass container with antialiased specular highlights and gradient border."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MusicCardRoot")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        radius = float(CORNER_RADIUS)

        # Inset slightly for 1.0px stroke alignment
        rect = QRectF(0.5, 0.5, w - 1.0, h - 1.0)
        card_path = QPainterPath()
        card_path.addRoundedRect(rect, radius, radius)

        # 1. Dark Translucent Glass Gradient Base
        bg_gradient = QLinearGradient(0, 0, 0, h)
        bg_gradient.setColorAt(0.0, QColor(*GLASS_BG_TOP))
        bg_gradient.setColorAt(1.0, QColor(*GLASS_BG_BOTTOM))
        painter.fillPath(card_path, QBrush(bg_gradient))

        # 2. Specular Top Sheen (Subtle light reflection across top 35%)
        sheen_h = min(85.0, h * 0.35)
        sheen_path = QPainterPath()
        sheen_path.addRoundedRect(QRectF(1.0, 1.0, w - 2.0, sheen_h), radius, radius)
        sheen_clipped = card_path.intersected(sheen_path)

        sheen_gradient = QLinearGradient(0, 0, 0, sheen_h)
        sheen_gradient.setColorAt(0.0, QColor(*GLASS_SHEEN_START))
        sheen_gradient.setColorAt(1.0, QColor(*GLASS_SHEEN_END))
        painter.fillPath(sheen_clipped, QBrush(sheen_gradient))

        # 3. Translucent Gradient Specular Border
        border_gradient = QLinearGradient(0, 0, w, h)
        border_gradient.setColorAt(0.0, QColor(*GLASS_BORDER_TOP_LEFT))
        border_gradient.setColorAt(0.4, QColor(*GLASS_BORDER_MID))
        border_gradient.setColorAt(1.0, QColor(*GLASS_BORDER_BOTTOM_RIGHT))
        painter.setPen(QPen(QBrush(border_gradient), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(card_path)


class MusicCardWidget(QWidget):
    """Frameless, translucent glass desktop music card widget for Spotify."""

    def __init__(self, state: Optional[PlaybackState] = None, parent=None):
        super().__init__(parent)
        self._state = state or get_placeholder_state()
        self._drag_pos = QPoint()

        # Window configuration for frameless presentation on desktop
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedSize(CARD_WIDTH, CARD_HEIGHT)
        self.setWindowTitle("Spotify Desktop Widget")

        # Root layout holding the glass container
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        self.card_container = GlassCardContainer(self)
        self.card_container.setStyleSheet(CARD_STYLESHEET)
        root_layout.addWidget(self.card_container)

        # Internal card layout
        container_layout = QVBoxLayout(self.card_container)
        container_layout.setContentsMargins(16, 12, 16, 14)
        container_layout.setSpacing(10)

        # 1. Header Row (Spotify Badge + Close Button)
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)

        self.badge = SpotifyBadge(self.card_container)
        self.close_btn = QPushButton("✕", self.card_container)
        self.close_btn.setObjectName("CloseButton")
        self.close_btn.setFixedSize(22, 22)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Close Widget (Esc)")
        self.close_btn.clicked.connect(self.close)

        header_row.addWidget(self.badge)
        header_row.addStretch()
        header_row.addWidget(self.close_btn)
        container_layout.addLayout(header_row)

        # 2. Main Details Row (Album Art on Left, Metadata on Right)
        details_row = QHBoxLayout()
        details_row.setContentsMargins(0, 0, 0, 0)
        details_row.setSpacing(14)

        # Artwork
        self.artwork = ArtworkWidget(size=ARTWORK_SIZE, parent=self.card_container)
        details_row.addWidget(self.artwork)

        # Text Metadata Column
        meta_col = QVBoxLayout()
        meta_col.setContentsMargins(0, 2, 0, 2)
        meta_col.setSpacing(4)
        meta_col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = ElidedLabel(self._state.title, self.card_container)
        self.title_label.setObjectName("TrackTitle")

        self.artist_label = ElidedLabel(self._state.artist, self.card_container)
        self.artist_label.setObjectName("TrackArtist")

        self.album_label = ElidedLabel(self._state.album, self.card_container)
        self.album_label.setObjectName("TrackAlbum")

        meta_col.addWidget(self.title_label)
        meta_col.addWidget(self.artist_label)
        meta_col.addWidget(self.album_label)
        details_row.addLayout(meta_col, stretch=1)

        container_layout.addLayout(details_row)

        # 3. Progress Section (Progress Bar + Timestamps)
        self.progress_section = ProgressSection(self.card_container)
        self.progress_section.seek_requested.connect(self._on_seek_requested)
        container_layout.addWidget(self.progress_section)

        # 4. Controls Section (Prev, Play/Pause, Next)
        self.controls = PlaybackControls(self.card_container)
        self.controls.play_pause_clicked.connect(self._on_play_pause_toggled)
        self.controls.previous_clicked.connect(self._on_previous_clicked)
        self.controls.next_clicked.connect(self._on_next_clicked)
        container_layout.addWidget(self.controls)

        # Render initial state
        self._apply_state(self._state)

        # Default placeholder artwork if none provided
        if not self._state.art_data:
            self.artwork.set_artwork(create_fictional_cover_pixmap(ARTWORK_SIZE))

        # Setup drag filters across card areas and artwork
        self._setup_drag_filters()

    def update_state(self, state: PlaybackState):
        """Update widget with new playback state."""
        self._state = state
        self._apply_state(state)

    def state(self) -> PlaybackState:
        return self._state

    def _apply_state(self, state: PlaybackState):
        self.title_label.setText(state.title)
        self.artist_label.setText(state.artist)
        self.album_label.setText(state.album)

        self.progress_section.update_progress(
            position_text=state.formatted_position,
            duration_text=state.formatted_duration,
            fraction=state.progress_fraction,
        )

        self.controls.set_playing(state.is_playing)
        self.controls.set_capabilities(state.can_go_previous, state.can_go_next)

        if state.art_data:
            self.artwork.set_artwork_from_data(state.art_data)

    # Prototype interactive handlers
    def _on_play_pause_toggled(self):
        self._state.is_playing = not self._state.is_playing
        self.controls.set_playing(self._state.is_playing)

    def _on_seek_requested(self, fraction: float):
        if self._state.duration_seconds > 0:
            self._state.position_seconds = int(fraction * self._state.duration_seconds)
            self.progress_section.update_progress(
                self._state.formatted_position,
                self._state.formatted_duration,
                self._state.progress_fraction,
            )

    def _on_previous_clicked(self):
        self._state.position_seconds = 0
        self.progress_section.update_progress(
            self._state.formatted_position,
            self._state.formatted_duration,
            0.0,
        )

    def _on_next_clicked(self):
        if self._state.duration_seconds > 0:
            self._state.position_seconds = min(
                self._state.duration_seconds,
                self._state.position_seconds + 30,
            )
            self.progress_section.update_progress(
                self._state.formatted_position,
                self._state.formatted_duration,
                self._state.progress_fraction,
            )

    # --- Mouse Dragging Implementation ---
    def _is_interactive_widget(self, obj: Optional[QObject]) -> bool:
        """Return True if obj is an interactive control that consumes clicks."""
        w = obj
        while w and w is not self:
            if isinstance(w, (QPushButton, ClickableProgressBar)):
                return True
            w = w.parent() if hasattr(w, "parent") else None
        return False

    def _setup_drag_filters(self):
        """Install event filters on non-interactive regions so clicks initiate window dragging."""
        self.installEventFilter(self)
        self.card_container.installEventFilter(self)
        for child in self.card_container.findChildren(QWidget):
            if not self._is_interactive_widget(child):
                child.installEventFilter(self)

    def _start_drag(self, event: QMouseEvent):
        """Initiate window movement via Wayland compositor startSystemMove or fallback manual drag."""
        wh = self.windowHandle()
        if wh is not None:
            if wh.startSystemMove():
                self._drag_pos = QPoint()
                return

        # Fallback for X11, test runners, or compositors without startSystemMove
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                if not self._is_interactive_widget(watched):
                    self._start_drag(event)
                    return True
        elif event.type() == QEvent.Type.MouseMove:
            if isinstance(event, QMouseEvent):
                if not self._drag_pos.isNull() and (event.buttons() & Qt.MouseButton.LeftButton):
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = QPoint()
        return super().eventFilter(watched, event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._start_drag(event)
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._drag_pos.isNull() and (event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = QPoint()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_Q):
            self.close()
        else:
            super().keyPressEvent(event)
