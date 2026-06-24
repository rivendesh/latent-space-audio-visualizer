import io
import librosa
import numpy as np


def load_audio(file_or_path, sr=22050):
    if isinstance(file_or_path, bytes):
        file_or_path = io.BytesIO(file_or_path)
    audio, _ = librosa.load(file_or_path, sr=sr, mono=True)
    return audio, sr


def compute_waveform_peaks(audio, n_peaks=2000):
    chunk_size = max(1, len(audio) // n_peaks)
    peaks = []
    for i in range(n_peaks):
        start = i * chunk_size
        end = start + chunk_size if i < n_peaks - 1 else len(audio)
        chunk = audio[start:end]
        peaks.append([float(np.min(chunk)), float(np.max(chunk))])
    return peaks


def audio_to_wav_bytes(audio, sr):
    import soundfile as sf
    buffer = io.BytesIO()
    sf.write(buffer, audio, sr, format="WAV")
    return buffer.getvalue()
