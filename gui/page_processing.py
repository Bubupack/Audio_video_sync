# gui/page_processing.py
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPaintEvent, QPainter, QPixmap
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


class PageProcessing(QWidget):
    """Page de chargement avec :

    - Image audio en fond d'écran.
    - Image vidéo superposée qui apparaît en fondu selon le pourcentage.
    - Barre de progression avec pourcentage affiché à droite.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._video_pixmap: Optional[QPixmap] = None
        self._audio_pixmap: Optional[QPixmap] = None

        self._build_ui()

    def _build_ui(self) -> None:
        # 1. Label de statut
        self.label_status = QLabel("Initialisation du traitement...", self)
        self.label_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_status.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 15px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 0.65);
                padding: 8px 18px;
                border-radius: 8px;
            }
        """)

        # 2. Barre de progression (sans texte à l'intérieur)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(22)
        self.progress_bar.setTextVisible(False)  # Masque le texte interne
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid rgba(255, 255, 255, 0.7);
                border-radius: 11px;
                background-color: rgba(0, 0, 0, 0.55);
            }
            QProgressBar::chunk {
                background-color: #007ACC;
                border-radius: 9px;
            }
        """)

        # 3. Label de pourcentage affiché à droite
        self.lbl_percentage = QLabel("0%", self)
        self.lbl_percentage.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 14px;
                font-weight: bold;
                background-color: rgba(0, 0, 0, 0.65);
                padding: 3px 10px;
                border-radius: 6px;
            }
        """)

        # Layout horizontal pour aligner la barre et le pourcentage
        progress_row = QHBoxLayout()
        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.lbl_percentage)

        # Layout principal centré
        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.label_status, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addSpacing(15)
        layout.addLayout(progress_row)
        layout.addStretch()

        # Marges latérales
        layout.setContentsMargins(60, 0, 60, 0)

    # ------------------------------------------------------------------
    # API Publique
    # ------------------------------------------------------------------
    def set_media_info(
        self, video_cover: Optional[QPixmap], audio_cover: Optional[QPixmap]
    ) -> None:
        """Injecte les visuels vidéo et audio et déclenche le réaffichage."""
        self._video_pixmap = video_cover if (video_cover and not video_cover.isNull()) else None
        self._audio_pixmap = audio_cover if (audio_cover and not audio_cover.isNull()) else None
        self.update()

    def set_progress(self, value: int) -> None:
        """Met à jour le pourcentage et redessine le fondu vidéo en arrière-plan."""
        self.progress_bar.setValue(value)
        self.lbl_percentage.setText(f"{value}%")
        self.update()  # Indispensable pour forcer le paintEvent avec la nouvelle opacité !

    def set_status(self, text: str) -> None:
        self.label_status.setText(text)
        
    def reset_ui(self) -> None:
        self.progress_bar.setValue(0)
        self.lbl_percentage.setText("0%")
        self.label_status.setText("Initialisation...")
        self._video_pixmap = None
        self._audio_pixmap = None
        self.update()

    # ------------------------------------------------------------------
    # Rendu graphique d'arrière-plan (paintEvent)
    # ------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        w, h = self.width(), self.height()

        # A. FOND : Image Audio (Plein écran)
        if self._audio_pixmap:
            scaled_audio = self._audio_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            ax = (w - scaled_audio.width()) // 2
            ay = (h - scaled_audio.height()) // 2
            painter.drawPixmap(ax, ay, scaled_audio)
        else:
            painter.fillRect(0, 0, w, h, QColor(25, 25, 25))

        # B. SUPERPOSITION : Image Vidéo en fondu (Opacité calculée en fonction du %)
        if self._video_pixmap:
            opacity = self.progress_bar.value() / 100.0  # Varie de 0.0 à 1.0
            painter.setOpacity(opacity)

            scaled_video = self._video_pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            vx = (w - scaled_video.width()) // 2
            vy = (h - scaled_video.height()) // 2
            painter.drawPixmap(vx, vy, scaled_video)

        # Réinitialisation de l'opacité par précaution pour le reste des opérations
        painter.setOpacity(1.0)