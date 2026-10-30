"""Playback progress bar and timestamp display components."""

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from spotify_widget.models import format_seconds
from spotify_widget.ui.style import (
    PROGRESS_BG_COLOR,
    COLOR_PROGRESS_FILL,
    COLOR_TEXT_TIMESTAMPS,
)


class ClickableProgressBar(QWidget):
    """Custom compact progress bar supporting scrubbing and seek-on-release."""

    seek_requested = Signal(float)  # Emitted when seek is committed on mouse release (0.0 - 1.0)
    scrubbing = Signal(float)       # Emitted while dragging for live timestamp preview (0.0 - 1.0)

    def __init__(self, height: int = 5, parent=None):
        super().__init__(parent)
        self._fraction: float = 0.0
        self._bar_height = height
        self._is_dragging = False
        self._seeking_enabled = True
        self.setFixedHeight(14)  # Generous hit target for clicking while bar itself is slim
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def is_dragging(self) -> bool:
        """Return True if user is currently dragging the progress slider."""
        return self._is_dragging

    def set_seeking_enabled(self, enabled: bool):
        """Enable or disable seeking interaction and cursor."""
        self._seeking_enabled = enabled
        self.setCursor(
            Qt.CursorShape.PointingHandCursor if enabled else Qt.CursorShape.ArrowCursor
        )

    def set_fraction(self, fraction: float):
        """Update fraction from playback progress if not actively dragged."""
        if not self._is_dragging:
            self._fraction = max(0.0, min(1.0, fraction))
            self.update()

    def set_drag_fraction(self, fraction: float):
        """Update fraction during active dragging."""
        self._fraction = max(0.0, min(1.0, fraction))
        self.update()

    def fraction(self) -> float:
        return self._fraction

    def _fraction_from_pos(self, x: float) -> float:
        w = max(1.0, float(self.width()))
        return max(0.0, min(1.0, x / w))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._seeking_enabled:
            self._is_dragging = True
            fraction = self._fraction_from_pos(event.position().x())
            self.set_drag_fraction(fraction)
            self.scrubbing.emit(fraction)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._seeking_enabled:
            fraction = self._fraction_from_pos(event.position().x())
            self.set_drag_fraction(fraction)
            self.scrubbing.emit(fraction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            fraction = self._fraction_from_pos(event.position().x())
            self.set_drag_fraction(fraction)
            self.seek_requested.emit(fraction)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        y = (self.height() - self._bar_height) / 2.0
        w = float(self.width())
        radius = self._bar_height / 2.0

        # Background track (translucent glass groove)
        bg_rect = QRectF(0, y, w, self._bar_height)
        bg_path = QPainterPath()
        bg_path.addRoundedRect(bg_rect, radius, radius)
        painter.fillPath(bg_path, QBrush(QColor(*PROGRESS_BG_COLOR)))

        # Filled track
        fill_width = w * self._fraction
        if fill_width > 0:
            fill_rect = QRectF(0, y, fill_width, self._bar_height)
            fill_path = QPainterPath()
            fill_path.addRoundedRect(fill_rect, radius, radius)
            painter.fillPath(fill_path, QBrush(QColor(COLOR_PROGRESS_FILL)))


class ProgressSection(QWidget):
    """Container holding progress bar and timestamp labels."""

    seek_requested = Signal(float)  # Emitted when seek is committed (fraction 0.0 - 1.0)
    scrubbing = Signal(float)       # Emitted while scrubbing

    def __init__(self, parent=None):
        super().__init__(parent)
        self._duration_seconds = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.bar = ClickableProgressBar(height=5)
        self.bar.seek_requested.connect(self.seek_requested.emit)
        self.bar.scrubbing.connect(self._on_bar_scrubbing)

        time_row = QHBoxLayout()
        time_row.setContentsMargins(0, 0, 0, 0)

        self.elapsed_label = QLabel("00:00")
        self.elapsed_label.setObjectName("TimeLabel")
        self.elapsed_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.duration_label = QLabel("00:00")
        self.duration_label.setObjectName("TimeLabel")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        time_row.addWidget(self.elapsed_label)
        time_row.addStretch()
        time_row.addWidget(self.duration_label)

        layout.addWidget(self.bar)
        layout.addLayout(time_row)

    def _on_bar_scrubbing(self, fraction: float):
        """Update elapsed timestamp preview during mouse scrubbing."""
        if self._duration_seconds > 0:
            pos = int(fraction * self._duration_seconds)
            self.elapsed_label.setText(format_seconds(pos))
        self.scrubbing.emit(fraction)

    def set_seeking_enabled(self, enabled: bool):
        """Enable or disable seeking on the progress bar."""
        self.bar.set_seeking_enabled(enabled)

    def update_progress(
        self,
        position_text: str,
        duration_text: str,
        fraction: float,
        duration_seconds: int = 0,
    ):
        """Update timestamps and progress bar position unless being scrubbed."""
        self._duration_seconds = duration_seconds
        self.duration_label.setText(duration_text)

        if not self.bar.is_dragging():
            self.elapsed_label.setText(position_text)
            self.bar.set_fraction(fraction)
