
# Audio-Video Sync

Audio-Video Sync is a Python desktop application designed to automatically synchronize video motion peaks with audio beats. By leveraging **PyQt6**, **OpenCV**, and **Librosa**, the tool analyzes the rhythmic structure of an audio track and the visual motion vectors of a video, rendering a unified output where visual motion dynamically aligns with the music.

---

## Key Features

* **Audio Peak Detection**: Employs `librosa` for onset envelope computation and `scipy` for dynamic peak detection based on signal standard deviation.
* **Optical Flow Motion Analysis**: Uses OpenCV's Farneback Optical Flow algorithm to compute frame-by-frame motion vectors and isolate key visual events.
* **Adaptive Synchronization**: Automatically aligns video motion peaks with detected audio beats. Includes synthetic peak generation for static video segments to maintain rhythmic continuity.
* **Direct Stream Rendering**: Feeds raw frame buffers directly to an `FFmpeg` subprocess, eliminating the disk overhead of intermediate uncompressed files.
* **Modern Graphical Interface**: Features drag-and-drop file inputs, real-time cross-fade progress animations, and a multi-page asynchronous workflow.
* **Embedded Metadata & Cover Extraction**: Automatically extracts cover art from audio tags (ID3, FLAC, MP4) or captures initial video frames for visual preview thumbnails.
* **Asynchronous Execution**: Offloads heavy processing and analysis tasks to background threads (`QThread`), ensuring the user interface remains responsive.

---

## Architecture and Design

The application follows Separation of Concerns (SoC) and DRY principles, strictly isolating algorithmic processing from the GUI layer.

### Workflow

```text
┌────────────────┐     ┌────────────────┐     ┌──────────────────┐
│   PageConfig   │ ──> │ PageProcessing │ ──> │ PageVisualization│
│ (Media Select) │     │  (Cross-fade)  │     │  (Final Preview) │
└────────────────┘     └────────────────┘     └──────────────────┘
        ▲                                               │
        └────────────── "Sync Another" ─────────────────┘

```

### Core Components

| Component | Responsibility |
| --- | --- |
| `core/audio_analysis` | Computes onset envelopes and isolates audio peaks using `librosa` and `scipy`. |
| `core/video_analysis` | Calculates optical flow vectors and identifies motion peak frames. |
| `core/renderer` | Maps video segments to audio timelines and pipes raw frames to `FFmpeg`. |
| `BaseMediaPlayerWidget` | Abstract base widget managing media player lifecycles, drop zones, and playback controls. |
| `MediaControlsBar` | Reusable widget for playback controls (play/pause, seek slider, timestamp). |
| `DropZone` | File drop handler restricted by format extensions. |
| `config/config.py` | Centralized, strongly-typed configuration (`dataclass`) holding processing constants. |

---

## How It Works

1. **Media Ingestion**: Loads audio into a 1D NumPy array and queries video properties (FPS, total frames, resolution) via OpenCV.
2. **Audio Peak Isolation**: `librosa.onset.onset_strength` calculates the onset envelope. `scipy.signal.find_peaks` identifies prominent peaks using a dynamic threshold based on signal deviation.
3. **Motion Vector Calculation**: Video frames are downscaled and analyzed using Farneback optical flow. Per-frame motion magnitudes are evaluated, and peaks are extracted to match the audio target count.
4. **Timeline Mapping & Rendering**: The output timeline is divided into intervals defined by audio peaks. Video segments are time-stretched or compressed to align with corresponding audio segments, then streamed directly to `FFmpeg`.

---

## Project Structure

```text
audio-video-sync/
├── main.py                         # Application entry point
├── README.md
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── config.py                   # Global parameters and configuration schema
├── core/
│   ├── __init__.py
│   ├── audio_analysis.py           # Onset detection and audio peak analysis
│   ├── video_analysis.py           # Optical flow computation and motion tracking
│   ├── renderer.py                 # Frame mapping and FFmpeg streaming pipe
│   ├── media_info.py               # Container for media metadata
│   └── processing_worker.py        # QThread worker for non-blocking analysis
├── gui/
│   ├── __init__.py
│   ├── main_window.py              # Top-level window and navigation state
│   ├── base_player_widget.py       # Abstract scaffolding for media player UI
│   ├── media_controls.py           # Playback control bar
│   ├── drop_zone.py                # Drag-and-drop input widget
│   ├── page_config.py              # Configuration and file input view
│   ├── page_processing.py          # Processing state and progress view
│   └── page_visualization.py       # Final video preview page
└── utils/
    ├── __init__.py
    └── utils.py                    # Metadata extraction and UI utility functions

```

---

## Installation

### Requirements

* **Python 3.10+**
* **FFmpeg**: Must be installed and present in system `PATH`.

### Setup Instructions

1. Clone the repository:
```bash
git clone [https://github.com/your-username/audio-video-sync.git](https://github.com/your-username/audio-video-sync.git)
cd audio-video-sync

```


2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate        # Linux / macOS
# .venv\Scripts\activate         # Windows

```


3. Install required dependencies:
```bash
pip install -r requirements.txt

```



---

## Usage

1. **Start the application**:
```bash
python main.py

```


2. **Select Media**: Drag and drop the source video and audio files into their respective drop zones on the configuration page. Specify an output directory.
3. **Process**: Click **Start processing**. The application will analyze the files and render the synchronized video in the background.
4. **Preview & Export**: Use the built-in media player on the visualization page to inspect the rendered output. Click **Synchronise another video** to process a new pair of files.

---

## Supported Formats

| Media Type | Supported Extensions |
| --- | --- |
| **Audio** | `.mp3`, `.wav`, `.flac` |
| **Video** | `.mp4`, `.avi`, `.mkv`, `.mov` |

---

## Engineering Considerations

> **Implementation Note**: This project prioritizes UI responsiveness, memory safety, and deterministic state management.

* **Explicit Buffer Allocation**: OpenCV frame extraction utilizes explicit array copying (`.copy()`) prior to `QImage` conversion to prevent garbage collection issues during asynchronous Qt rendering.
* **Signal Isolation**: Sliders use explicit signal blocking (`blockSignals(True)`) during programmatic updates to prevent cyclic feedback loops with `QMediaPlayer`.
* **Strict Encapsulation**: Interface views expose read-only properties rather than exposing internal object states across module boundaries.
* **Non-blocking Execution**: Heavy processing pipelines are isolated within `QThread` instances to maintain full frame rates for UI animations and event loops.
* **Centralized Configuration**: Processing thresholds, scaling factors, and codec settings are isolated in strongly-typed dataclasses, avoiding magic numbers in the business logic.

---

## License

Distributed under the GNU General Public License v3.0 (GPLv3). See [LICENSE](LICENSE) for more information.
