"""Album artwork display component with rounded corners and missing art fallback."""

from typing import Optional
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter,
    QPainterPath,
    QPixmap,
    QColor,
    QBrush,
    QPen,
    QFont,
    QLinearGradient,
)
from PySide6.QtWidgets import QWidget

from spotify_widget.ui.style import ARTWORK_SIZE, ART_CORNER_RADIUS


class ArtworkWidget(QWidget):
    """Square album artwork widget with rounded corners and elegant fallback rendering."""

    def __init__(self, size: int = ARTWORK_SIZE, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap: Optional[QPixmap] = None
        self.setFixedSize(self._size, self._size)

    def set_artwork(self, pixmap: Optional[QPixmap]):
        """Set or clear the displayed artwork pixmap."""
        self._pixmap = pixmap
        self.update()

    def set_artwork_from_data(self, data: Optional[bytes]):
        """Load artwork from raw bytes, or set fallback if None/invalid."""
        if not data:
            self.set_artwork(None)
            return

        pm = QPixmap()
        if pm.loadFromData(data):
            self.set_artwork(pm)
        else:
            self.set_artwork(None)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        rect = QRectF(0, 0, self._size, self._size)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(rect, ART_CORNER_RADIUS, ART_CORNER_RADIUS)
        painter.setClipPath(clip_path)

        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self._size,
                self._size,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center crop if aspect ratio is not 1:1
            sx = (scaled.width() - self._size) // 2
            sy = (scaled.height() - self._size) // 2
            painter.drawPixmap(0, 0, scaled, sx, sy, self._size, self._size)
        else:
            self._draw_fallback(painter, rect)

        # Draw subtle glass border around artwork
        painter.setClipping(False)
        painter.setPen(QPen(QColor(255, 255, 255, 32), 1.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.5, 0.5, -0.5, -0.5), ART_CORNER_RADIUS, ART_CORNER_RADIUS)

    def _draw_fallback(self, painter: QPainter, rect: QRectF):
        """Draw an elegant minimalist placeholder when album art is unavailable."""
        # Gradient background matching dark glass palette
        gradient = QLinearGradient(0, 0, self._size, self._size)
        gradient.setColorAt(0.0, QColor(36, 38, 48, 200))
        gradient.setColorAt(1.0, QColor(20, 21, 26, 220))
        painter.fillRect(rect, QBrush(gradient))

        # Stylized concentric vinyl rings
        center = rect.center()
        painter.setPen(QPen(QColor(255, 255, 255, 18), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self._size * 0.38, self._size * 0.38)
        painter.drawEllipse(center, self._size * 0.26, self._size * 0.26)

        # Center disc label
        painter.setBrush(QBrush(QColor(42, 44, 54, 230)))
        painter.setPen(QPen(QColor(255, 255, 255, 35), 1.0))
        painter.drawEllipse(center, self._size * 0.14, self._size * 0.14)

        # Center spindle hole
        painter.setBrush(QBrush(QColor(16, 17, 20, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, self._size * 0.05, self._size * 0.05)


def create_fictional_cover_pixmap(size: int = ARTWORK_SIZE) -> QPixmap:
    """Generate a rich, colorful fictional album art pixmap for prototype display."""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Cosmic gradient
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0.0, QColor("#1E3C72"))
    gradient.setColorAt(0.5, QColor("#2A5298"))
    gradient.setColorAt(1.0, QColor("#0D1B2A"))
    painter.fillRect(0, 0, size, size, QBrush(gradient))

    # Abstract celestial circles
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(QColor(29, 185, 84, 90)))  # Spotify green glow
    painter.drawEllipse(QRectF(size * 0.45, size * 0.1, size * 0.65, size * 0.65))

    painter.setBrush(QBrush(QColor(114, 9, 183, 110)))  # Violet ambient
    painter.drawEllipse(QRectF(size * -0.1, size * 0.35, size * 0.7, size * 0.7))

    # Minimalist typography / monogram
    font = QFont("sans-serif", int(size * 0.14), QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(255, 255, 255, 200))
    painter.drawText(
        QRectF(size * 0.1, size * 0.68, size * 0.8, size * 0.25),
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom,
        "HORIZON",
    )

    painter.end()
    return pixmap
