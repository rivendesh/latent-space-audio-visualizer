import librosa
import numpy as np
from sklearn.decomposition import PCA


# Encodes audio into a 2D latent trajectory via mel-spectrogram → PCA pipeline.
# Also extracts spectral centroid and RMS per frame for downstream visualisation.
class LatentEncoder:
    def __init__(self, n_mels=128, hop_length=512, n_components=2):
        self.n_mels = n_mels
        self.hop_length = hop_length
        self.n_components = n_components
        self.pca = None
        self.latent_mean = None
        self.latent_std = None

    # Compute mel spectrogram → PCA projection → z-score normalised latent points.
    # Also returns per-frame timestamps, spectral centroid, and RMS energy.
    def encode(self, audio, sr):
        mel_spec = librosa.feature.melspectrogram(
            y=audio, sr=sr, n_mels=self.n_mels,
            hop_length=self.hop_length,
        )
        mel_spec_db = librosa.power_to_db(mel_spec, ref=np.max)

        features = mel_spec_db.T

        if self.pca is None:
            self.pca = PCA(n_components=self.n_components)
            latent_points = self.pca.fit_transform(features)
            self.latent_mean = latent_points.mean(axis=0)
            self.latent_std = latent_points.std(axis=0)
        else:
            latent_points = self.pca.transform(features)

        latent_points = (latent_points - self.latent_mean) / (self.latent_std + 1e-8)

        n_frames = features.shape[0]
        times = np.arange(n_frames) * self.hop_length / sr

        S = np.abs(librosa.stft(audio, hop_length=self.hop_length))
        centroids = librosa.feature.spectral_centroid(S=S, sr=sr)[0]
        rms = librosa.feature.rms(S=S)[0]

        n_feats = min(len(centroids), n_frames)
        centroids = centroids[:n_feats]
        rms = rms[:n_feats]

        return latent_points, times, centroids, rms

    @property
    # Fraction of total variance captured by each PCA component.
    # Returns None until fit() is called (first call to encode).
    def explained_variance_ratio(self):
        if self.pca is not None:
            return self.pca.explained_variance_ratio_.tolist()
        return None
