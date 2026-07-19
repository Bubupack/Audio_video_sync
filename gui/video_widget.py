# gui/video_widget.py
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QStyle
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from gui.drop_zone import DropZone
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QStyle, QSlider
class VideoWidget(QWidget):
    video_loaded = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.current_video_path = None

        # 1. Configuration du moteur multimédia de Qt6
        self.media_player = QMediaPlayer()
        self.video_widget = QVideoWidget()
        self.media_player.setVideoOutput(self.video_widget)
        
        self.drop_zone = DropZone(type="video")
        self.drop_zone.path.connect(self.load_video)
        
        # On connecte les signaux de position et de durée du lecteur
        self.media_player.positionChanged.connect(self.update_slider_position)
        self.media_player.durationChanged.connect(self.update_slider_duration)
        # 2. Création de l'interface visuelle
        self.init_ui()
        
    def init_ui(self):
        # Boutons de contrôle
        self.btn_open = QPushButton("Ouvrir un fichier")
        self.btn_open.clicked.connect(self.open_file_dialog)
        
        self.btn_play = QPushButton()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_play.setEnabled(False)

        # Bouton Revenir au début
        self.btn_restart = QPushButton()
        self.btn_restart.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.btn_restart.clicked.connect(self.restart_media)
        self.btn_restart.setEnabled(False)

        # La barre de lecture (Slider Horizontal)
        self.slider_playback = QSlider(Qt.Orientation.Horizontal)
        self.slider_playback.setRange(0, 0) # 0 au début, la durée max sera définie au chargement
        self.slider_playback.setEnabled(False)
        
        # /!\ Attention : On utilise sliderMoved et pas valueChanged pour éviter que 
        # le lecteur et le slider ne se battent entre eux pendant la lecture.
        self.slider_playback.valueChanged.connect(self.set_media_position)

        #Layout de controles video
        layout_controls_video = QHBoxLayout()
        layout_controls_video.addWidget(self.btn_restart)
        layout_controls_video.addWidget(self.btn_play)

        # Layout des contrôles
        layout_controls = QVBoxLayout()
        layout_controls.addWidget(self.slider_playback)
        layout_controls.addLayout(layout_controls_video)
        layout_controls.addWidget(self.btn_open)

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.drop_zone) # Plus besoin de stretch fixe ici
        self.main_layout.addLayout(layout_controls)
        
        self.setLayout(self.main_layout)

    # =====================================================================
    # RÈGLE DE RATIO UNIQUEMENT SUR LA ZONE MÉDIA
    # =====================================================================
    def resizeEvent(self, event):
        """Ajuste l'écran au format 16:9 en fonction de la largeur disponible"""
        super().resizeEvent(event)
        largeur_utile = self.width()
        hauteur_16_9 = int(largeur_utile * 9 / 16)
        
        # On force la hauteur 16:9 STRICTEMENT sur les zones d'affichage
        self.drop_zone.setFixedHeight(hauteur_16_9)
        self.video_widget.setFixedHeight(hauteur_16_9)

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner une vidéo", "", "Fichiers Vidéo (*.mp4 *.mkv *.avi *.mov)"
        )
        if file_name:
            self.load_video(file_name)

    def load_video(self, file_path):
        self.current_video_path = file_path
        self.video_loaded.emit(file_path)

        if self.main_layout.indexOf(self.drop_zone) != -1:
            self.main_layout.replaceWidget(self.drop_zone, self.video_widget)
            self.drop_zone.hide()
            self.video_widget.show()
            self.btn_play.setEnabled(True)
            self.btn_restart.setEnabled(True)
            self.slider_playback.setEnabled(True)

        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))

    def toggle_play(self):
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        else:
            self.media_player.play()
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
    
    def restart_media(self):
        """Remet la lecture à zéro (position 0 milliseconde)"""
        self.media_player.setPosition(0)

    def update_slider_position(self, position):
        """Met à jour le slider selon l'avancement du morceau"""
        # On met à jour la barre normalement
        self.slider_playback.blockSignals(True)
        self.slider_playback.setValue(position)
        self.slider_playback.blockSignals(False)

    def update_slider_duration(self, duration):
        """Ajuste la valeur maximale du slider à la durée totale du fichier (en millisecondes)"""
        self.slider_playback.setRange(0, duration)

    def set_media_position(self, position):
        """Déplace le curseur de lecture (gère le clic fixe ET le glissé)"""
        # On ne change le temps du lecteur QUE si c'est l'utilisateur 
        # who is in the process of clicking or dragging the slider
        #if self.slider_playback.isSliderDown():
        self.media_player.setPosition(position) # (ou media_player pour la vidéo)