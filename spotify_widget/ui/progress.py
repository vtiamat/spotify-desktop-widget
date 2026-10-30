"""Playback progress bar and timestamp display components."""

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QPainterPath, QColor, QBrush, QPen
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

from spotify_widget.ui.style import (
    PROGRESS_BG_COLOR,
    COLOR_PROGRESS_FILL,
    COLOR_TEXT_TIMESTAMPS,
)


class ClickableProgressBar(QWidget):
    """Custom compact progress bar supporting clicks and drag-seeking."""

    seek_requested = Signal(float)  # Emits fraction 0.0 - 1.0

    def __init__(self, height: int = 5, parent=None):
        super().__init__(parent)
        self._fraction: float = 0.0
        self._bar_height = height
        self._is_dragging = False
        self.setFixedHeight(14)  # Generous hit target for clicking while bar itself is slim
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_fraction(self, fraction: float):
        self._fraction = max(0.0, min(1.0, fraction))
        self.update()

    def fraction(self) -> float:
        return self._fraction

    def _fraction_from_pos(self, x: float) -> float:
        w = max(1.0, float(self.width()))
        return max(0.0, min(1.0, x / w))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            fraction = self._fraction_from_pos(event.position().x())
            self.set_fraction(fraction)
            self.seek_requested.emit(fraction)

    def mouseMoveEvent(self, event):
        if self._is_dragging:
            fraction = self._fraction_from_pos(event.position().x())
            self.set_fraction(fraction)
            self.seek_requested.emit(fraction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

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

    seek_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.bar = ClickableProgressBar(height=5)
        self.bar.seek_requested.connect(self.seek_requested.emit)

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

    def update_progress(self, position_text: str, duration_text: str, fraction: float):
        self.elapsed_label.setText(position_text)
        self.duration_label.setText(duration_text)
        self.bar.set_fraction(fraction)
