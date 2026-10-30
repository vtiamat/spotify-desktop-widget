"""Label widget that automatically elides overflowing text with an ellipsis."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QPainter, QFontMetrics
from PySide6.QtWidgets import QLabel, QSizePolicy


class ElidedLabel(QLabel):
    """A QLabel that elides single-line text with an ellipsis if it exceeds available width."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self._full_text = text
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setToolTip(text)

    def setText(self, text: str):
        self._full_text = text or ""
        self.setToolTip(self._full_text)
        super().setText(self._full_text)
        self.update()

    def text(self) -> str:
        return self._full_text

    def sizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(100, fm.height())

    def minimumSizeHint(self) -> QSize:
        fm = QFontMetrics(self.font())
        return QSize(20, fm.height())

    def paintEvent(self, event):
        painter = QPainter(self)
        fm = QFontMetrics(self.font())
        available_width = self.width()

        # Compute elided version
        elided = fm.elidedText(self._full_text, Qt.TextElideMode.ElideRight, available_width)

        # Draw text aligned vertically center and horizontally left
        painter.setFont(self.font())
        painter.setPen(self.palette().color(self.foregroundRole()))
        painter.drawText(0, 0, available_width, self.height(), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided)
