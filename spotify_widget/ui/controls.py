"""Playback control buttons and header badge components."""

from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QSizePolicy,
)

from spotify_widget.ui.style import COLOR_SPOTIFY_GREEN


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
        self.prev_btn = QPushButton("⏮")
        self.prev_btn.setObjectName("SecondaryControl")
        self.prev_btn.setFixedSize(36, 36)
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_btn.clicked.connect(self.previous_clicked.emit)

        # Play / Pause button
        self.play_btn = QPushButton("▶")
        self.play_btn.setObjectName("PlayPauseControl")
        self.play_btn.setFixedSize(40, 40)
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.clicked.connect(self.play_pause_clicked.emit)

        # Next button
        self.next_btn = QPushButton("⏭")
        self.next_btn.setObjectName("SecondaryControl")
        self.next_btn.setFixedSize(36, 36)
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_btn.clicked.connect(self.next_clicked.emit)

        layout.addStretch()
        layout.addWidget(self.prev_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.next_btn)
        layout.addStretch()

    def set_playing(self, is_playing: bool):
        """Update play/pause icon based on playback state."""
        self.play_btn.setText("⏸" if is_playing else "▶")

    def set_capabilities(self, can_prev: bool, can_next: bool):
        """Enable or disable previous/next buttons."""
        self.prev_btn.setEnabled(can_prev)
        self.next_btn.setEnabled(can_next)
