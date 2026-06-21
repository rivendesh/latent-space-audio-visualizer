# latent-space-audio-visualizer

Visualize audio in latent space with real-time animations, in a Streamlit webapp.

## Quick start

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Project structure

| File | Role |
|---|---|
| `app.py` | Streamlit dashboard — two tabs: static Plotly analysis & real-time canvas player |
| `audio_processor.py` | Audio loading (librosa) + waveform-peak downsampling |
| `latent_encoder.py` | Mel-spectrogram PCA encoder — projects audio frames into a 2D latent trajectory |
| `realtime_component.py` | Custom HTML/JS component with Canvas rendering + Web Audio API playback |

## How the latent space works

Each audio frame is converted to a mel-spectrogram vector (128 bands). PCA reduces those vectors to 2D, producing a trajectory through "latent space" that reveals the spectral evolution of the sound.

## Usage

1. Upload a WAV/MP3/FLAC/OGG file in the sidebar
2. **Static Analysis** tab — explore with a time slider; Plotly charts show waveform + latent space
3. **Real-Time Player** tab — press Play; the waveform cursor and latent-space dot move in sync with audio
4. Adjust **Mel bands** and **Hop length** in the sidebar to change the latent-space resolution

## References

- [Bird Call Audio Representation](https://www.youtube.com/watch?v=7lEiYqCV25s)