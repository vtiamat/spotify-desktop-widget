"""Playback control buttons and header badge components."""

from PySide6.QtCore import Qt, Signal, QSize, QRectF
from PySide6.QtGui import QPainter, QPainterPath, QColor
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
)

from spotify_widget.ui.style import (
    COLOR_SPOTIFY_GREEN,
    COLOR_BUTTON_FG,
    COLOR_BUTTON_HOVER,
    COLOR_BUTTON_DISABLED,
    COLOR_TEXT_MUTED,
)


class SpotifyBadge(QWidget):
    """Subtle Spotify branding indicator with green dot and text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Green pulse dot
        self.dot = QLabel("●")
        self.dot.setStyleSheet(f"color: {COLOR_SPOTIFY_GREEN}; font-size: 8px;")
        self.dot.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Label
        self.label = QLabel("SPOTIFY")
        self.label.setObjectName("SpotifyBrand")
        self.label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout.addWidget(self.dot)
        layout.addWidget(self.label)
        layout.addStretch()


CONTROL_BUTTON_SIZE = 38


class VectorControlButton(QPushButton):
    """Playback control button rendering crisp, mathematically aligned vector icons."""

    def __init__(self, icon_type: str, fallback_text: str = "", parent=None):
        super().__init__(fallback_text, parent)
        self._icon_type = icon_type  # 'previous', 'next', 'play', 'pause'

    def icon_type(self) -> str:
        return self._icon_type

    def set_icon_type(self, icon_type: str):
        if self._icon_type != icon_type:
            self._icon_type = icon_type
            self.update()

    def enterEvent(self, event):
        super().enterEvent(event)
        self.update()

    def leaveEvent(self, event):
        super().leaveEvent(event)
        self.update()

    def paintEvent(self, event):
        # Let stylesheet render circular background, border-radius, and hover/press backgrounds
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        is_secondary = (self.objectName() == "SecondaryControl")
        if is_secondary:
            if not self.isEnabled():
                color = QColor(COLOR_BUTTON_DISABLED)
            elif self.isDown():
                color = QColor(COLOR_TEXT_MUTED)
            elif self.underMouse():
                color = QColor(COLOR_BUTTON_HOVER)
            else:
                color = QColor(COLOR_BUTTON_FG)
        else:
            # PlayPauseControl
            if not self.isEnabled():
                color = QColor(18, 18, 18, 90)
            else:
                color = QColor("#121212")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        cx = self.width() / 2.0
        cy = self.height() / 2.0

        if self._icon_type == "previous":
            # Vertical bar on left: width 2.0, height 12.0
            painter.drawRoundedRect(QRectF(cx - 5.5, cy - 6.0, 2.0, 12.0), 1.0, 1.0)
            # Left-pointing triangle
            path = QPainterPath()
            path.moveTo(cx - 2.5, cy)
            path.lineTo(cx + 5.5, cy - 5.8)
            path.lineTo(cx + 5.5, cy + 5.8)
            path.closeSubpath()
            painter.drawPath(path)

        elif self._icon_type == "next":
            # Right-pointing triangle
            path = QPainterPath()
            path.moveTo(cx - 5.5, cy - 5.8)
            path.lineTo(cx + 2.5, cy)
            path.lineTo(cx - 5.5, cy + 5.8)
            path.closeSubpath()
            painter.drawPath(path)
            # Vertical bar on right: width 2.0, height 12.0
            painter.drawRoundedRect(QRectF(cx + 3.5, cy - 6.0, 2.0, 12.0), 1.0, 1.0)

        elif self._icon_type == "play":
            # Right-pointing triangle with optical centering
            path = QPainterPath()
            path.moveTo(cx - 4.0, cy - 6.5)
            path.lineTo(cx + 6.5, cy)
            path.lineTo(cx - 4.0, cy + 6.5)
            path.closeSubpath()
            painter.drawPath(path)

        elif self._icon_type == "pause":
            # Two vertical rounded bars
            painter.drawRoundedRect(QRectF(cx - 5.5, cy - 6.5, 3.5, 13.0), 1.0, 1.0)
            painter.drawRoundedRect(QRectF(cx + 2.0, cy - 6.5, 3.5, 13.0), 1.0, 1.0)


class PlaybackControls(QWidget):
    """Control row featuring Previous, Play/Pause, and Next buttons."""

    previous_clicked = Signal()
    play_pause_clicked = Signal()
    next_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Previous button
        self.prev_btn = VectorControlButton("previous", "⏮", self)
        self.prev_btn.setObjectName("SecondaryControl")
        self.prev_btn.setFixedSize(CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self.previous_clicked.emit)

        # Play / Pause button
        self.play_btn = VectorControlButton("play", "▶", self)
        self.play_btn.setObjectName("PlayPauseControl")
        self.play_btn.setFixedSize(CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.play_pause_clicked.emit)

        # Next button
        self.next_btn = VectorControlButton("next", "⏭", self)
        self.next_btn.setObjectName("SecondaryControl")
        self.next_btn.setFixedSize(CONTROL_BUTTON_SIZE, CONTROL_BUTTON_SIZE)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self.next_clicked.emit)

        layout.addStretch()
        layout.addWidget(self.prev_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.play_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.next_btn, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()

    def set_playing(self, is_playing: bool):
        """Update play/pause icon based on playback state."""
        self.play_btn.set_icon_type("pause" if is_playing else "play")
        self.play_btn.setText("⏸" if is_playing else "▶")

    def set_capabilities(self, can_prev: bool, can_next: bool, can_play_pause: bool = True):
        """Enable or disable previous, next, and play/pause buttons."""
        self.prev_btn.setEnabled(can_prev)
        self.next_btn.setEnabled(can_next)
        self.play_btn.setEnabled(can_play_pause)
