# gui/PageConfig.py
"""Configuration page widget hosting video player, audio player, and output selection."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from gui.audio_widget import AudioWidget
from gui.video_widget import VideoWidget
from gui.outputDir_widget import OutputDirWidget
from config.config import DEFAULT_OUTPUT_DIR
from utils.utils import extract_video_thumbnail
logger = logging.getLogger(__name__)


class PageConfig(QWidget):
    video_path = pyqtSignal(str)
    audio_path = pyqtSignal(str)
    output_directory = pyqtSignal(str)
    start_requested = pyqtSignal()  # Signal émis au clic sur Démarrer

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # 1. Stockage interne des chemins
        self._video_path: Optional[str] = None
        self._audio_path: Optional[str] = None
        self._output_dir: Optional[str] = DEFAULT_OUTPUT_DIR

        # 2. Instanciation des sous-widgets
        self.video_player = VideoWidget(self)
        self.audio_player = AudioWidget(self)
        self.output_dir_widget = OutputDirWidget()

        # 3. Création des boutons Start et Reset
        self.btn_start = QPushButton("Démarrer le traitement", self)
        self.btn_start.setEnabled(False)  # Grisé par défaut
        self.btn_start.clicked.connect(self.start_requested.emit)

        self.btn_reset = QPushButton("Réinitialiser les médias", self)
        self.btn_reset.clicked.connect(self.reset)

        # 4. Connexion des signaux
        self.video_player.video_loaded.connect(self._on_video_loaded)
        self.audio_player.audio_loaded.connect(self._on_audio_loaded)
        self.output_dir_widget.output_directory.connect(self._on_output_dir_changed)

        # 5. Disposition de l'interface (Layouts)
        side_by_side = QHBoxLayout()
        side_by_side.addWidget(self.video_player, stretch=1)
        side_by_side.addWidget(self.audio_player, stretch=1)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.btn_reset)
        actions_layout.addWidget(self.btn_start)

        main_layout = QVBoxLayout(self)
        main_layout.addLayout(side_by_side)
        main_layout.addWidget(self.output_dir_widget)
        main_layout.addLayout(actions_layout)
        main_layout.addStretch()

        # 6. Vérification initiale de l'état du bouton Start
        self._update_start_button_state()

    # ------------------------------------------------------------------
    # Gestion des états et validation
    # ------------------------------------------------------------------
    def _update_start_button_state(self) -> None:
        """Active le bouton Start seulement si vidéo, audio et dossier de sortie sont valides."""
        has_valid_video = bool(self._video_path and Path(self._video_path).is_file())
        has_valid_audio = bool(self._audio_path and Path(self._audio_path).is_file())
        has_valid_output = bool(self._output_dir and Path(self._output_dir).is_dir())

        # Le bouton est dégrisé UNIQUEMENT si les 3 conditions sont réunies
        self.btn_start.setEnabled(has_valid_video and has_valid_audio and has_valid_output)

    def _on_video_loaded(self, path: str) -> None:
        self._video_path = path
        self.video_path.emit(path)
        self._update_start_button_state()

    def _on_audio_loaded(self, path: str) -> None:
        self._audio_path = path
        self.audio_path.emit(path)
        self._update_start_button_state()

    def _on_output_dir_changed(self, path: str) -> None:
        self._output_dir = path
        self.output_directory.emit(path)
        self._update_start_button_state()

    # ------------------------------------------------------------------
    # Action de réinitialisation
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """Réinitialise les lecteurs audio/vidéo et leurs chemins (conserve le dossier de sortie)."""
        # 1. Réinitialise les widgets graphiques et les DropZones
        self.video_player.reset()
        self.audio_player.reset()

        # 2. Efface les chemins mémoire vidéo et audio (PAS le dossier de sortie)
        self._video_path = None
        self._audio_path = None

        # 3. Notifie la MainWindow que les médias sont vides
        self.video_path.emit("")
        self.audio_path.emit("")

        # 4. Met à jour le bouton Start (qui redevient grisé automatiquement)
        self._update_start_button_state()

    def get_audio_cover(self) -> Optional[QPixmap]:
        """Récupère la pochette audio extraite par AudioWidget."""
        return self.audio_player.get_cover_pixmap()

    def get_video_cover(self) -> Optional[QPixmap]:
        """Génère et retourne la miniature vidéo."""
        if self._video_path:
            return extract_video_thumbnail(self._video_path)
        return None