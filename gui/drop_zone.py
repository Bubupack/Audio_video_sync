from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, pyqtSignal
from utils.utils import validate_input_file
from config.config import VALID_AUDIO_EXTS, VALID_VIDEO_EXTS
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DropZone(QLabel):
    path = pyqtSignal(str)  # Signal emitted when a file is dropped, sending the file path

    def __init__(self, type="video"):
        super().__init__()
        self.curent_path = None
        self.type = type  # "audio" or "video"
        self.init_ui()

        
    def init_ui(self):
        self.setText(f"Drag & drop your {self.type} here\nor use the button below")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 8px;
                background-color: #f0f0f0;
                color: #555;
                font-size: 14px;
            }
        """)

        self.setAcceptDrops(True)


    def dragEnterEvent(self, event):
        """Verify that the dragged item is a file and accept it."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Retrieve the file path when the click is released."""
        urls = event.mimeData().urls()
        if urls:
            file_path = Path(urls[0].toLocalFile())
            if self.type == "audio":
                try:
                    validate_input_file(file_path, VALID_AUDIO_EXTS, "audio")
                except ValueError as e:
                    logger.error(f"Error with audio file : {e}")
                    return
            else:
                try:
                    validate_input_file(file_path, VALID_VIDEO_EXTS, "video")
                except ValueError as e:
                    logger.error(f"Error with video file : {e}")
                    return
            self.load(str(file_path))

    def load(self, file_path: str):
        self.curent_path = file_path
        self.path.emit(file_path)