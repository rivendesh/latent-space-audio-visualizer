Here's the proposed layout project structure I want built and loosely followed. Keep the components as separate as possible and open to experiementation and improvement. Keep the js files \
separate and not inline to the python code.

---

**Streamlit as the app shell + a custom Streamlit component for p5.js rendering + Python for all audio analysis and metrics.**

## Recommended architecture

```text
User uploads audio
   ↓
Streamlit (Python app)
   ├─ audio loading / preprocessing
   ├─ metric extraction
   ├─ embedding / manifold computation
   ├─ state + controls + caching
   ↓
Custom Streamlit component
   ├─ p5.js canvas
   ├─ animation / interaction
   ├─ hover / click / playback sync
   ↓
Back to Streamlit
   └─ selected frame / region / event
```

## Tech stack I would use

### Python side

* **streamlit** — UI shell, sidebar controls, layout, app state
* **librosa** or **torchaudio** — audio loading and feature extraction
* **numpy / pandas / scipy** — signal processing and tabular data
* **scikit-learn** — normalization, PCA, clustering
* **umap-learn** — latent space projection
* **plotly** or **altair** — standard charts and metrics panels
* **st.cache_data / st.cache_resource** — avoid recomputing features every rerun

### JavaScript side

* **p5.js** — custom animation / visual layer
* **Streamlit custom component** infrastructure — the bridge between Python and JS
* Optional: **React + Vite** if you want a cleaner component build process

## The optimal way to do it

### Best option: a real Streamlit custom component

This is the right approach if p5.js is doing anything interactive or stateful.

Why it is best:

* Python can send structured data to the canvas
* the canvas can send back selections, clicks, hover points, playback position
* it stays stable across reruns
* it is much better than injecting raw HTML/JS into `components.html`

### Avoid relying only on `st.components.html`

That works for quick prototypes, but it is fragile for a real dashboard:

* hard to sync state
* harder to return events to Python
* reruns can reset the canvas
* long-term maintenance gets messy

## Suggested project structure

```text
audio-latent-dashboard/
├── app.py
├── requirements.txt
├── data/
├── src/
│   ├── audio/
│   │   ├── load.py
│   │   ├── features.py
│   │   └── embeddings.py
│   ├── viz/
│   │   ├── metrics.py
│   │   └── plots.py
│   └── utils/
│       └── cache.py
└── components/
    └── p5_canvas/
        ├── frontend/
        │   ├── main.js
        │   ├── sketch.js
        │   └── package.json
        └── __init__.py
```

## How the data should flow

### 1) Python computes everything

From the uploaded WAV:

* waveform
* spectrogram
* spectral centroid
* spectral spread
* RMS
* MFCCs
* latent coordinates

Then Python packages the results into JSON-like data:

```python
payload = {
    "waveform": [...],
    "sr": 44100,
    "frames": [...],
    "centroid": [...],
    "embedding": [[x1, y1], [x2, y2], ...],
    "timestamps": [...],
    "colors": [...],
}
```

### 2) Streamlit passes that payload into the p5 component

The component receives the arrays and renders:

* latent-space particles
* animated trajectories
* color mapped by centroid
* overlays or trails
* pointer interactions

### 3) p5.js returns user actions

For example:

* clicked frame index
* brushed region
* hovered embedding point
* current animation time

Streamlit can then update the side panels and charts.

## What the dashboard would look like

A strong layout is:

* **Left sidebar:** upload, feature settings, model settings
* **Top row:** summary cards

  * duration
  * sample rate
  * average centroid
  * centroid spread
* **Center:** p5.js latent-space canvas
* **Right panel:** detailed metrics for selected frame
* **Bottom:** spectrogram, centroid trace, waveform

## What to build first

### MVP

1. Upload WAV
2. Compute waveform + centroid + spectrogram
3. Compute 2D embedding
4. Render:

   * p5 latent-space scatter/trajectory
   * Plotly spectrogram
   * centroid over time
5. Click a point in p5 and update the stats panel

### Then add

* playback sync
* multiscale windows
* clustering
* comparison between multiple files
* animated brushing / filtering
* saved sessions

## My recommendation for the actual implementation

If you want this to be maintainable, do this:

* **Streamlit** for the app
* **Python audio pipeline** for analysis
* **Custom Streamlit component** for p5.js
* **Plotly** for non-custom charts
* **JSON data contract** between Python and JS

That gives you the speed of Streamlit without sacrificing the visual quality of p5.js.

## One practical note

If the p5 visualization becomes very complex, keep it as a separate frontend package inside the Streamlit component rather than embedding p5 directly in `app.py`. That makes it much easier to version, test, and extend.

I can sketch the exact folder layout plus a minimal working `app.py` and p5 component scaffold next.
