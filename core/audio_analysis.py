"""Audio onset-peak detection using librosa."""
from typing import List

import librosa
import numpy as np
from scipy.signal import find_peaks

from config.config import AudioConfig


def get_audio_peaks(samples: np.ndarray, sample_rate: int, config: AudioConfig) -> List[int]:
    """Detect onset-strength peaks in the audio signal.

    Args:
        samples: 1-D float array of audio samples.
        sample_rate: Sample rate in Hz.
        config: Audio-detection parameters.

    Returns:
        List of peak timestamps in milliseconds.
    """
    onset_env = librosa.onset.onset_strength(y=samples, sr=sample_rate)
    times = librosa.times_like(onset_env, sr=sample_rate)

    # Guard against degenerate inputs (T17).
    if len(times) == 0 or times[-1] <= 0:
        return []

    global_std = float(np.std(onset_env))
    dynamic_prominence = global_std * config.prominence_factor

    audio_fps = len(times) / times[-1]
    min_distance_frames = max(1, int((config.min_distance_ms / 1000) * audio_fps))

    peaks_indices, _ = find_peaks(
        onset_env, distance=min_distance_frames, prominence=dynamic_prominence
    )
    return [int(round(times[idx] * 1000)) for idx in peaks_indices]