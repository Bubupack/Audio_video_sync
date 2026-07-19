# gui/audio_widget.py
import os
import base64
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QStyle, QSizePolicy # <-- Ajout de QSizePolicy
from PyQt6.QtCore import QUrl, Qt, pyqtSignal
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog, QStyle, QSlider

from mutagen import File
from mutagen.flac import Picture
from gui.drop_zone import DropZone

class AudioWidget(QWidget):
    audio_loaded = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.current_audio_path = None
        self.cover_pixmap = None

        # 1. Configuration du moteur audio de Qt6
        self.audio_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.audio_player.setAudioOutput(self.audio_output)
        
        # Le QLabel pour l'image de couverture
        self.cover_label = QLabel()
        self.cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # On connecte les signaux de position et de durée du lecteur
        self.audio_player.positionChanged.connect(self.update_slider_position)
        self.audio_player.durationChanged.connect(self.update_slider_duration)
        # =====================================================================
        # LE FIX ULTRA-CRUCIAL POUR LE RATIO 50/50
        # =====================================================================
        # On force le label à ignorer la taille brute de l'image chargée.
        # Il va maintenant obéir sagement au layout imposé par la MainWindow.
        self.cover_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        # =====================================================================
        
        self.drop_zone = DropZone(type="audio")
        self.drop_zone.path.connect(self.load_audio)

        # 2. Création de l'interface visuelle
        self.init_ui()
        
    def init_ui(self):
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

        # Bouton Mute
        self.btn_mute = QPushButton()
        self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
        self.btn_mute.clicked.connect(self.toggle_mute)
        self.btn_mute.setEnabled(False)

        # La barre de volume (Slider Horizontal)
        self.slider_volume = QSlider(Qt.Orientation.Horizontal)
        self.slider_volume.setRange(0, 100)
        self.slider_volume.setValue(70) # Volume par défaut à 70%
        self.slider_volume.valueChanged.connect(self.change_volume)
        self.slider_volume.setEnabled(False)

        # La barre de lecture (Slider Horizontal)
        self.slider_playback = QSlider(Qt.Orientation.Horizontal)
        self.slider_playback.setRange(0, 0) # 0 au début, la durée max sera définie au chargement
        self.slider_playback.setEnabled(False)
        
        # /!\ Attention : On utilise sliderMoved et pas valueChanged pour éviter que 
        # le lecteur et le slider ne se battent entre eux pendant la lecture.
        self.slider_playback.valueChanged.connect(self.set_media_position)

        # Layout des contrôles audio
        layout_controls_audio = QHBoxLayout()
        layout_controls_audio.addWidget(self.btn_restart, stretch=1)
        layout_controls_audio.addWidget(self.btn_play, stretch=1)
        layout_controls_audio.addWidget(self.btn_mute, stretch=1)
        layout_controls_audio.addWidget(self.slider_volume, stretch=2)

        layout_controls = QVBoxLayout()
        layout_controls.addWidget(self.slider_playback)
        layout_controls.addLayout(layout_controls_audio)
        layout_controls.addWidget(self.btn_open)
        

        # Layout principal
        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.drop_zone)
        self.main_layout.addLayout(layout_controls)
        
        self.setLayout(self.main_layout)

    def resizeEvent(self, event):
        """Force la zone de drop et la miniature à s'aligner sur le format 16:9 de la vidéo"""
        super().resizeEvent(event)
        largeur_utile = self.width()
        hauteur_16_9 = int(largeur_utile * 9 / 16)
        
        self.drop_zone.setFixedHeight(hauteur_16_9)
        self.cover_label.setFixedHeight(hauteur_16_9)
        
        self.update_cover()

    def open_file_dialog(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier audio", "", "Fichiers Audio (*.mp3 *.wav *.flac *.aac)"
        )
        if file_name:
            self.load_audio(file_name)

    def load_audio(self, file_path):
        self.current_audio_path = file_path
        self.audio_loaded.emit(file_path)

        if self.main_layout.indexOf(self.drop_zone) != -1:
            self.main_layout.replaceWidget(self.drop_zone, self.cover_label)
            self.drop_zone.hide()
            self.cover_label.show()
            self.btn_play.setEnabled(True)
            self.btn_restart.setEnabled(True)
            self.btn_mute.setEnabled(True)
            self.slider_volume.setEnabled(True)

            # On applique le volume initial choisi sur le slider (70% -> 0.7)
            self.audio_output.setVolume(self.slider_volume.value() / 100.0)

            self.slider_playback.setEnabled(True)

        self.cover_label.setText("Chargement de la miniature...")
        self.extract_cover(file_path)

        self.audio_player.setSource(QUrl.fromLocalFile(file_path))
        self.audio_player.play()
        self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))

    def extract_cover(self, file_path):
        try:
            audio = File(file_path)
            if audio is None:
                self.cover_label.setText("Impossible de lire le fichier")
                return

            image_data = None
            if hasattr(audio, 'pictures') and audio.pictures:
                for pic in audio.pictures:
                    if pic.type == 3:
                        image_data = pic.data
                        break
                if not image_data:
                    image_data = audio.pictures[0].data
            elif audio.tags and hasattr(audio.tags, 'keys'):
                for key in audio.tags.keys():
                    if key.startswith("APIC"):
                        image_data = audio.tags[key].data
                        break
            tags = audio.tags if (hasattr(audio, 'tags') and audio.tags) else audio
            if tags and 'covr' in tags:
                image_data = bytes(tags['covr'][0])
            elif 'metadata_block_picture' in audio:
                b64_data = audio['metadata_block_picture'][0]
                raw_data = base64.b64decode(b64_data)
                picture = Picture(raw_data)
                image_data = picture.data

            if image_data:
                pixmap = QPixmap()
                pixmap.loadFromData(image_data)
                self.cover_pixmap = pixmap
                self.cover_label.setText("")
                self.update_cover()
            else:
                self.cover_pixmap = None
                self.cover_label.setText("Aucune miniature intégrée dans ce fichier")

        except Exception as e:
            self.cover_pixmap = None
            print(f"[MUTAGEN ERROR] : {e}")
            self.cover_label.setText("Erreur lors de la lecture de la miniature")

    def update_cover(self):
        if self.cover_pixmap and not self.cover_pixmap.isNull():
            # .size() renvoie maintenant la taille exacte calculée en 16:9 par le layout !
            scaled_pixmap = self.cover_pixmap.scaled(
                self.cover_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.cover_label.setPixmap(scaled_pixmap)

    def toggle_play(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.audio_player.pause()
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        else:
            self.audio_player.play()
            self.btn_play.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
    
    def restart_media(self):
        """Remet la lecture à zéro (position 0 milliseconde)"""
        self.audio_player.setPosition(0)

    def toggle_mute(self):
        """Alterne entre le mode muet et normal"""
        is_muted = self.audio_output.isMuted()
        self.audio_output.setMuted(not is_muted)
        
        # Change l'icône en fonction de l'état
        if not is_muted:
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolumeMuted))
        else:
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))
    
    def change_volume(self, value):
        """Convertit la valeur entière (0-100) du slider en float (0.0-1.0) pour Qt6"""
        float_volume = value / 100.0
        self.audio_output.setVolume(float_volume)
        
        # Optionnel : Si l'utilisateur remet du son au curseur alors qu'il était en Mute, 
        # on peut réactiver l'icône normale
        if float_volume > 0 and self.audio_output.isMuted():
            self.audio_output.setMuted(False)
            self.btn_mute.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaVolume))

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
        self.audio_player.setPosition(position) # (ou media_player pour la vidéo)

