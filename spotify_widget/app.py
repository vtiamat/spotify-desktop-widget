"""Application entry point and lifecycle manager."""

import sys
from typing import List, Optional
from PySide6.QtWidgets import QApplication

from spotify_widget.models import (
    PlaybackState,
    get_placeholder_state,
    get_long_text_placeholder_state,
)
from spotify_widget.ui.card import MusicCardWidget


def create_application(argv: Optional[List[str]] = None) -> QApplication:
    """Create or return existing QApplication with consistent desktop identity."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv or sys.argv)
    app.setApplicationName("Spotify Desktop Widget")
    app.setApplicationDisplayName("Spotify Desktop Widget")
    app.setDesktopFileName("spotify-desktop-widget")
    return app


def run_prototype(argv: Optional[List[str]] = None) -> int:
    """Initialize and run the static UI prototype."""
    args = argv if argv is not None else sys.argv[1:]
    app = create_application(sys.argv[:1] + args)

    state: PlaybackState
    if "--long-text" in args or "--stress-test" in args:
        state = get_long_text_placeholder_state()
    else:
        state = get_placeholder_state()

    widget = MusicCardWidget(state=state)

    if "--missing-art" in args:
        widget.artwork.set_artwork(None)

    widget.show()
    return app.exec()


def main() -> int:
    """Entry point for CLI execution."""
    return run_prototype()


if __name__ == "__main__":
    sys.exit(main())
