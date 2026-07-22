# gui/page_processing.py
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class PageProcessing(QWidget):
    """Page affichant la progression ainsi que les miniatures des médias en cours."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        # Miniatures
        self.lbl_video_cover = QLabel("Vidéo", self)
        self.lbl_video_cover.setFixedSize(200, 150)
        self.lbl_video_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_video_cover.setStyleSheet("border: 1px solid #ccc; background-color: #f8f8f8;")

        self.lbl_audio_cover = QLabel("Audio", self)
        self.lbl_audio_cover.setFixedSize(150, 150)
        self.lbl_audio_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_audio_cover.setStyleSheet("border: 1px solid #ccc; background-color: #f8f8f8;")

        covers_layout = QHBoxLayout()
        covers_layout.addStretch()
        covers_layout.addWidget(self.lbl_video_cover)
        covers_layout.addSpacing(20)
        covers_layout.addWidget(self.lbl_audio_cover)
        covers_layout.addStretch()

        # Progression & Statut
        self.label_status = QLabel("Initialisation du traitement...", self)
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Layout principal
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addLayout(covers_layout)
        layout.addSpacing(20)
        layout.addWidget(self.label_status)
        layout.addWidget(self.progress_bar)
        layout.addStretch()

    def set_media_info(self, video_cover: Optional[QPixmap], audio_cover: Optional[QPixmap]) -> None:
        """Injecte les visuels de la vidéo et de l'audio dans la page."""
        if video_cover and not video_cover.isNull():
            scaled = video_cover.scaled(
                self.lbl_video_cover.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_video_cover.setPixmap(scaled)
        else:
            self.lbl_video_cover.setText("Pas de miniature vidéo")

        if audio_cover and not audio_cover.isNull():
            scaled = audio_cover.scaled(
                self.lbl_audio_cover.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_audio_cover.setPixmap(scaled)
        else:
            self.lbl_audio_cover.setText("Pas de pochette audio")

    def set_progress(self, value: int) -> None:
        self.progress_bar.setValue(value)

    def set_status(self, text: str) -> None:
        self.label_status.setText(text)

    def reset_ui(self) -> None:
        self.progress_bar.setValue(0)
        self.label_status.setText("Initialisation...")
        self.lbl_video_cover.clear()
        self.lbl_audio_cover.clear()