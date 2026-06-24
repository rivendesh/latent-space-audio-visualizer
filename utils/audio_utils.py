import io
import librosa
import numpy as np


def load_audio(file_or_path, sr=22050):
    if isinstance(file_or_path, bytes):
        file_or_path = io.BytesIO(file_or_path)
    audio, _ = librosa.load(file_or_path, sr=sr, mono=True)
    return audio, sr


def compute_waveform_peaks(audio, n_peaks=2000):
    n = len(audio)
    if n == 0:
        return [[0.0, 0.0]] * n_peaks
    chunk_size = max(1, n // n_peaks)
    actual = n // chunk_size
    trimmed = audio[:actual * chunk_size]
    chunks = trimmed.reshape(actual, chunk_size)
    mins = chunks.min(axis=1)
    maxs = chunks.max(axis=1)
    peaks = [[float(mins[i]), float(maxs[i])] for i in range(actual)]
    if actual < n_peaks:
        peaks.extend([[0.0, 0.0]] * (n_peaks - actual))
    return peaks[:n_peaks]


def audio_to_wav_bytes(audio, sr):
    import soundfile as sf
    buffer = io.BytesIO()
    sf.write(buffer, audio, sr, format="WAV")
    return buffer.getvalue()
