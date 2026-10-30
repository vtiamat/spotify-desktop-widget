"""Pytest fixtures shared across test modules."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    """Session-scoped QApplication instance."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
