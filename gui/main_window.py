# gui/main_window.py
from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from gui.video_widget import VideoWidget
from gui.audio_widget import AudioWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio-Vidéo Sync")
        self.resize(960, 540)

        # 1. On instancie les lecteurs
        self.Videoplayer = VideoWidget()
        self.Audioplayer = AudioWidget()

        # 2. Connexion des signaux
        self.Audioplayer.audio_loaded.connect(self.on_audio_received)
        self.Videoplayer.video_loaded.connect(self.on_video_received)

        # Largeur identique (50% / 50%)
        layout_cote_a_cote = QHBoxLayout()
        layout_cote_a_cote.addWidget(self.Videoplayer, stretch=1)
        layout_cote_a_cote.addWidget(self.Audioplayer, stretch=1)

        # Layout principal avec le stretch tout en bas
        # C'est lui qui colle l'ensemble vers le haut sans écraser les boutons
        layout_principal = QVBoxLayout()
        layout_principal.addLayout(layout_cote_a_cote)
        layout_principal.addStretch() 

        container = QWidget()
        container.setLayout(layout_principal)
        self.setCentralWidget(container)
    
    def on_audio_received(self, path):
        print(path)

    def on_video_received(self, path):
        print(path)