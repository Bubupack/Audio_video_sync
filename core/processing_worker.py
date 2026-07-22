# workers/processing_worker.py
import time
from PyQt6.QtCore import QObject, pyqtSignal


class ProcessingWorker(QObject):
    """Effectue les calculs lourds en arrière-plan."""

    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, video_path: str, audio_path: str, output_dir: str) -> None:
        super().__init__()
        self.video_path = video_path
        self.audio_path = audio_path
        self.output_dir = output_dir

    def run(self) -> None:
        """Méthode exécutée dans le thread secondaire."""
        try:
            self.status.emit("Analyse des flux audio et vidéo...")
            self.progress.emit(10)
            time.sleep(1)  # Simulation de calcul

            self.status.emit("Calcul de la resynchronisation par optical flow...")
            self.progress.emit(50)
            time.sleep(1.5)  # Simulation de calcul

            self.status.emit("Rendu du fichier final via FFmpeg...")
            self.progress.emit(85)
            time.sleep(1)  # Simulation de rendu

            self.progress.emit(100)
            self.status.emit("Terminé !")
            self.finished.emit()

        except Exception as exc:
            self.error.emit(str(exc))