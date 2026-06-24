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
├── app.py                      # Streamlit entry point — sidebar, tabs, CSS, orchestration
├── static_analysis.py          # Tab 1: Plotly figure builders + download helpers
├── render_2d.py                # Tab 2: 2D Player HTML template builder
├── render_3d.py                # Tab 3: 3D Manifold HTML template builder (Three.js + Web Audio)
├── utils/
│   ├── __init__.py
│   ├── audio_utils.py          # Audio loading, resampling, waveform peaks, WAV byte encoding
│   └── latent_utils.py         # Mel-spectrogram → PCA encoder, spectral centroid + RMS
├── js-components/
│   ├── render-2d.js            # Tab 2: 2D latent + waveform canvas rendering + playback
│   └── render-3d.js            # Tab 3: Three.js 3D scene, orbit controls, profile charts
├── requirements.txt            # Python dependencies
├── assets/
│   ├── reference-dashboard.png # Design reference
│   └── data/                   # Sample audio files
│       ├── test_sweep.wav      # 10s sine sweep
│       └── test_intricate.wav  # 30s chord progression + arpeggio + clicks
├── LICENSE
└── README.md
```

### File summaries

| File | Role |
|------|------|
| `app.py` | Entry point. Parses CLI args, renders sidebar (file upload + settings sliders), loads audio, runs the encoder, creates 3 tabs. Passes data to each tab's render function. |
| `static_analysis.py` | Tab 1 — builds Plotly figures (latent scatter, waveform, FFT spectrum) with dark theme styling and high-res download buttons. |
| `render_2d.py` | Tab 2 — reads `js-components/render-2d.js`, serialises audio + latent data as JSON, produces an HTML string via template substitution for `st.components.v1.html`. |
| `render_3d.py` | Tab 3 — reads `js-components/render-3d.js`, serialises 3D point cloud + centroid/RMS data, produces the HTML string with an importmap for Three.js CDN. |
| `utils/audio_utils.py` | Shared: `load_audio()` (librosa → mono 22 kHz), `compute_waveform_peaks()` (downsampled min/max pairs for canvas), `audio_to_wav_bytes()` (float array → WAV bytes via soundfile). |
| `utils/latent_utils.py` | Shared: `LatentEncoder` class — computes mel-spectrogram → PCA (2 components) → z-scored latent points, plus per-frame spectral centroid and RMS. |
| `js-components/render-2d.js` | 2D player JS — AudioContext playback, 2D latent scatter + waveform canvas drawing, seek/volume/speed/fade/trail/zoom controls. |
| `js-components/render-3d.js` | 3D viewer ES module — Three.js scene with `ShaderMaterial` point cloud, OrbitControls, time-slice planes, waveform + spectral centroid canvases. |

### App flow

```
Upload / CLI audio file
         │
         ▼
  app.py: load_audio() ──► audio_utils.py (librosa → 22 kHz mono)
         │
         ▼
  app.py: LatentEncoder.encode() ──► latent_utils.py (mel-spec → PCA → centroids + RMS)
         │
         ├──► tab1: static_analysis.py ──► Plotly figures (latent, waveform, FFT)
         │
         │              truncate to max_playback seconds
         │                         │
         │        ┌────────────────┼────────────────┐
         │        ▼                ▼                 ▼
         │   tab2: render_2d.py              tab3: render_3d.py
         │        │                            │
         │        │  read render-2d.js          │  read render-3d.js
         │        │  inline as __COMPONENT_JS__  │  inline as __COMPONENT_JS__
         │        │                            │
         │        ▼                            ▼
         │   st.components.v1.html         st.components.v1.html
         │   (canvas + AudioContext)       (Three.js scene + Web Audio)
         ▼
  Browser renders 60 fps animation loop synchronized with playback
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
