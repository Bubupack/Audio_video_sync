# gui/main_window.py
"""Main application window hosting the video and audio players side by side."""
from __future__ import annotations

import logging

from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from PyQt6.QtCore import QThread
from core.processing_worker import ProcessingWorker
from gui.PageConfig import PageConfig
from gui.audio_widget import AudioWidget
from gui.video_widget import VideoWidget
from gui.outputDir_widget import OutputDirWidget
from config.config import DEFAULT_OUTPUT_DIR
from gui.page_processing import PageProcessing
from gui.page_visualisation import PageVisualisation
logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Audio-Video Sync")
        self.resize(960, 540)

        self.pages = QStackedWidget(self)
        self.setCentralWidget(self.pages)

        self.page_config = PageConfig()
        self.page_processing = PageProcessing()
        self.page_visu = PageVisualisation()

        self.pages.addWidget(self.page_config)
        self.pages.addWidget(self.page_processing)
        self.pages.addWidget(self.page_visu)

        self.page_config.start_requested.connect(self._start_processing)
        self.page_visu.sync_another_requested.connect(self._restart_app)
        # Variables pour le thread
        self._thread: QThread | None = None
        self._worker: ProcessingWorker | None = None

    def _start_processing(self) -> None:
        # Récupération des chemins validés
        video_path = self.page_config._video_path
        audio_path = self.page_config._audio_path
        output_dir = self.page_config._output_dir

        video_cover = self.page_config.get_video_cover()
        audio_cover = self.page_config.get_audio_cover()

        # 1. Préparation de l'UI : réinitialiser et afficher la page de progression
        self.page_config.reset()
        self.page_processing.reset_ui()
        self.page_processing.set_media_info(video_cover, audio_cover)
        self.pages.setCurrentWidget(self.page_processing)

        # 2. Instanciation du Worker et du QThread
        self._thread = QThread()
        self._worker = ProcessingWorker(video_path, audio_path, output_dir)
        self._worker.moveToThread(self._thread)

        # 3. Connexion des signaux
        # Quand le thread démarre, exécuter worker.run
        self._thread.started.connect(self._worker.run)

        # Transmission directe des informations du Worker à la page de chargement
        self._worker.progress.connect(self.page_processing.set_progress)
        self._worker.status.connect(self.page_processing.set_status)

        # Fin ou Erreur du traitement
        self._worker.finished.connect(self._on_processing_finished)
        self._worker.error.connect(self._on_processing_error)

        # Nettoyage de la mémoire quand c'est fini
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        # 4. Lancement du thread
        self._thread.start()

    def _on_processing_finished(self, generated_video_path:str) -> None:
        logger.info("Traitement terminé !")
        self.page_visu.set_video(generated_video_path)
        self.pages.setCurrentWidget(self.page_visu)

    def _on_processing_error(self, err_msg: str) -> None:
        logger.error("Erreur durant le traitement : %s", err_msg)
        QMessageBox.critical(
            self, "Erreur", f"Une erreur s'est produite lors du traitement :\n{err_msg}"
        )
        if self._thread and self._thread.isRunning():
            self._thread.quit()
        self.pages.setCurrentWidget(self.page_config)

    def _restart_app(self) -> None:
        self.page_visu.reset_ui()
        self.page_config.reset()
        self.pages.setCurrentWidget(self.page_config)