"""Application entry point for the Audio-Video Sync tool."""
from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from gui.main_window import MainWindow


def configure_logging() -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def main() -> None:
    """Launch the Audio-Video Sync application."""
    configure_logging()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()