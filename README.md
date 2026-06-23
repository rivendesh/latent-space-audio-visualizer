# Audio Latent Space Visualizer

A Streamlit-based interactive tool that extracts spectral features from audio files, projects them into a 2D/3D latent space via PCA, and visualizes the trajectory in real time with synchronized playback.

## Features

- **Static Analysis** — Full-duration waveform, frequency spectrum, and 2D latent-space scatter plot with download support (PNG / HTML). Points colored by time position (cyan → purple → red-orange).
- **Real-Time 2D Player** — 2D latent canvas + waveform canvas with Web Audio API playback, speed/volume controls, seek bar, and progressive trajectory rendering with per-point recency scaling (newer points larger and brighter).
- **3D Acoustic Manifold** — Interactive Three.js scene where each audio frame is a 3D point positioned by PC1 (x), PC2 (y), and normalized time (z). Colored by time position to match the Static Analysis color scheme. Includes:
  - OrbitControls with auto-rotation (speed slider)
  - Z-axis stretch slider (0.5–6x)
  - Time-slice planes with count and opacity controls
  - Zoom slider, dynamic orbit-center tracking (Midpoint / None)
  - Centroid profile chart + waveform canvas drawn in sync with playback
  - Fullscreen mode (viewport + controls)
  - Per-vertex recency scaling via `ShaderMaterial` (size + alpha falloff)
  - Fade-rate slider controlling recency falloff exponent
- **File input** — Upload via browser, CLI `--file`/`-f` flag, or `AUDIO_FILE` environment variable.
- **Persistent dark theme** — No theme toggle; always dark.

## Project Structure

```
.
├── app.py                  # Streamlit entry point, sidebar, tabs, plotting helpers, CSS
├── audio_processor.py      # Audio loading, resampling, waveform peaks, WAV byte encoding
├── latent_encoder.py       # Mel-spectrogram → PCA encoder, spectral centroid + RMS
├── realtime_component.py   # 2D real-time player HTML/JS template
├── realtime_3d.py          # 3D manifold HTML/JS template (Three.js + Web Audio)
├── requirements.txt        # Python dependencies
├── assets/
│   ├── reference-dashboard.png  # Design reference
│   └── data/                    # Sample audio files
│       ├── test_sweep.wav       # 10s sine sweep
│       └── test_intricate.wav   # 30s chord progression + arpeggio + clicks
├── LICENSE
└── README.md
```

## How It Works

1. **Audio is loaded** via `librosa.load` and resampled to 22 050 Hz mono.
2. **A mel-spectrogram** is computed with configurable `n_mels` (32–256) and `hop_length` (128–2048), then log-scaled.
3. **PCA** is fit on the flattened spectral frames using 2 components. The 3D view additionally uses normalized time as the Z axis. Explained-variance ratio is reported.
4. **Per-frame features** — spectral centroid, RMS energy — are computed alongside for the profile chart.
5. **Data is serialized** (points, centroids, peak waveform, durations) into JSON and embedded as base64 WAV audio inside the respective HTML component.
6. **The browser component** (pure JS + Three.js + Web Audio API) progressively renders the latent trajectory at 60 fps, synchronized with audio playback. The animation loop runs indefinitely to support post-playback OrbitControls interaction.

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

## Sidebar Controls

| Control           | Default | Description |
|-------------------|---------|-------------|
| Mel bands         | 128     | Frequency bins fed into PCA (32–256). More bands → finer frequency detail but noisier latent space. |
| Hop length        | 512     | Frame stride in samples (128–2048). Smaller → higher temporal resolution, more points. |
| Max playback (s)  | 120     | Truncates audio for real-time players to stay under the 200 MB component message limit. Static Analysis always uses the full file. |

## 3D Tab Controls

| Control            | Default | Description |
|--------------------|---------|-------------|
| Speed              | 1x      | Playback speed multiplier (0.25–3x). |
| Volume             | 75%     | Output gain. |
| Orbit              | 0.10    | OrbitControls auto-rotation speed (−0.4 to +0.4). |
| Stretch            | 3.5     | Z-axis scale multiplier (0.5–6). |
| Slices             | 5       | Number of time-slice planes (0–10). |
| Slice Opacity      | 5%      | Opacity of time-slice planes and edges. |
| Zoom               | 1.5     | Camera zoom (0.5–5). |
| Fade               | 3.0     | Recency-falloff exponent (0.5–10). Higher = older nodes fade faster. |
| Pan                | Midpoint| Orbit-center tracking mode: Midpoint (lerp toward running midpoint) or None (fixed). |

# Development Issues

### 200 MB Streamlit message size limit
Streamlit caps `st.components.v1.html` data at 200 MB. Base64-encoded WAV audio for long files easily exceeds this. Fix: truncate audio to a configurable max playback duration (default 120 s) before embedding. The Static Analysis tab continues to use the full file.

### Pause/Resume audio desync
Creating a new `AudioBufferSourceNode` on resume produces a stale `onended` callback that stops playback prematurely. Fix: per-source generation counter (`sourceGen`) — each buffered source gets a unique generation ID; `onended` only fires if the generation still matches.

### End-of-track animation stall
Stopping the animation loop when audio finishes prevents OrbitControls interaction after playback. Fix: the `requestAnimationFrame` loop runs indefinitely; it never sets `animId = null` on completion.

### Recency scaling with ShaderMaterial
`THREE.PointsMaterial` does not support per-vertex size or alpha. Fix: replace with a custom `ShaderMaterial` that reads `pointSize` and `pointAlpha` attributes from the geometry, enabling quadratic-falloff size and transparency for trailing points.

### Fullscreen resize artifacts
The Streamlit component does not fire a ResizeObserver entry when exiting fullscreen, leaving the canvas at the fullscreen resolution. Fix: in the fullscreenchange handler, schedule a `requestAnimationFrame` callback that re-reads `viewport.clientWidth/clientHeight` and updates the renderer.

### Orbit center tracking
Three OrbitControls require smooth target changes for natural interaction. Three approaches were implemented:
- **Midpoint**: lerp the orbit target toward the running midpoint (prefix-sum averaged) of all drawn points.
- **None**: fixed orbit at the scene origin.
A lerp factor of 0.12 keeps camera movement smooth without lag.

## Dependencies

- Python 3.10+
- streamlit, librosa, numpy, scikit-learn, soundfile, plotly

Install with:

```bash
pip install -r requirements.txt
```

## Notes

- The 2D latent space uses PCA with 2 components; the explained variance ratio is shown in the sidebar.
- The 3D view uses PC1/PC2 as X/Y and normalized time as Z.
- Point color in all views maps to time position using a cyan → purple → red-orange gradient, matching between Static Analysis, 2D Player, and 3D Manifold.
- Three.js (v0.160.0) is loaded from CDN via importmap; only OrbitControls is used (no addon dependencies).
