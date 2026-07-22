# main.py
import logging
import sys
from PyQt6.QtWidgets import QApplication
from gui.main_window import MainWindow

logger = logging.getLogger(__name__)

def configure_logging() -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

def main():
    configure_logging()
    app = QApplication(sys.argv)
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()