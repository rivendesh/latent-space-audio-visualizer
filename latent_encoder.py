import librosa
import numpy as np
from sklearn.decomposition import PCA


class LatentEncoder:
    def __init__(self, n_mels=128, hop_length=512, n_components=2):
        self.n_mels = n_mels
        self.hop_length = hop_length
        self.n_components = n_components
        self.pca = None
        self.latent_mean = None
        self.latent_std = None

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

        return latent_points, times

    @property
    def explained_variance_ratio(self):
        if self.pca is not None:
            return self.pca.explained_variance_ratio_.tolist()
        return None
