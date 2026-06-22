import io
import librosa
import numpy as np


# Load audio from a file path, bytes, or BytesIO object.
# Returns a mono float array resampled to `sr` (Hz) and the sample rate.
def load_audio(file_or_path, sr=22050):
    if isinstance(file_or_path, bytes):
        file_or_path = io.BytesIO(file_or_path)

    audio, _ = librosa.load(file_or_path, sr=sr, mono=True)
    return audio, sr


# Downsample the waveform to `n_peaks` min/max pairs for efficient canvas rendering
# without aliasing. Each pair covers an equal-sized chunk of the audio.
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
