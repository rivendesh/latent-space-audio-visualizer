# Audio Latent Space Visualizer

A Streamlit-based interactive tool that extracts spectral features from audio files, projects them into a 2D/3D latent space via PCA, and visualizes the trajectory in real time with synchronized playback.

## Features

- **Static Analysis** — Full-duration waveform, frequency spectrum, and 2D latent-space scatter plot with download support (PNG / HTML).
- **Real-Time Player** — 2D latent canvas + waveform canvas with synchronized audio playback, speed and volume controls, and progressive trajectory rendering.
- **3D Acoustic Manifold** — Interactive 3D scatter plot (Three.js) where each audio frame is a point positioned by its PCA coordinates and time, colored by spectral centroid. Auto-rotating camera, orbit speed control, centroid–amplitude profile graph.
- **Light / Dark Theme** — Toggle in the sidebar applies across the entire app.
- **File input** — Upload via browser, CLI `--file`/`-f` flag, or `AUDIO_FILE` environment variable.

## Project Structure

```
.
├── app.py                  # Streamlit entry point, sidebar, tabs, plotting helpers
├── audio_processor.py      # Audio loading and waveform peak computation
├── latent_encoder.py       # Mel-spectrogram → PCA encoder with spectral features
├── realtime_component.py   # 2D real-time player HTML/JS component
├── realtime_3d.py          # 3D manifold HTML/JS component (Three.js)
├── requirements.txt        # Python dependencies
├── assets/
│   ├── reference-dashboard.png  # Design reference
│   └── data/                    # Sample audio files
│       ├── test_sweep.wav
│       └── test_intricate.wav
└── README.md
```

## How It Works

1. **Audio is loaded** and converted to a mono waveform at 22 050 Hz.
2. **A mel-spectrogram** is computed (configurable bands and hop length).
3. **PCA** reduces each spectral frame to 2 (or 3 with Time as Z) dimensions, forming a trajectory through latent space.
4. **Spectral centroid and RMS amplitude** are computed per frame for the real-time profile graph and point coloring.
5. **The browser component** (pure JS + Three.js) progressively renders the trajectory in sync with Web Audio API playback.

## Usage

### With a file picker (default)

```bash
streamlit run app.py
```

Then upload a `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, or `.aiff` file via the sidebar.

### With a CLI argument

```bash
streamlit run app.py -- -f path/to/song.wav
```

### With an environment variable

```bash
AUDIO_FILE=path/to/song.wav streamlit run app.py
```

### Sample files

```bash
# 10s sine sweep
streamlit run app.py -- -f assets/data/test_sweep.wav

# 30s chord progression with arpeggios and clicks
streamlit run app.py -- -f assets/data/test_intricate.wav
```

## Configuration

| Sidebar Control     | Default | Description |
|---------------------|---------|-------------|
| Mel bands           | 128     | Frequency bins fed into PCA (32–256) |
| Hop length          | 512     | Frames stride in samples (128–2048) |
| Max playback (s)    | 120     | Truncates long audio for the real-time player |

## Dependencies

- Python 3.10+
- streamlit, librosa, numpy, scikit-learn, soundfile, plotly

Install with:

```bash
pip install -r requirements.txt
```

## Notes

- The 2D latent space uses PCA with 2 components; the explained variance ratio is shown in the metrics bar.
- The 3D view uses PC1 / PC2 as X/Y and normalized time as Z.
- Point color in the 3D view maps to spectral centroid (blue = low frequency, red = high frequency).
- Long audio files are truncated to the "Max playback" setting (default 120 s) to stay under the 200 MB Streamlit component message limit. The Static Analysis tab always uses the full file.
