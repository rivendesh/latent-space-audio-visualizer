import base64
import json
import uuid
from pathlib import Path

from utils.audio_utils import audio_to_wav_bytes


_JS_DIR = Path(__file__).parent / "js-components"

with open(_JS_DIR / "render-3d.js") as f:
    _COMPONENT_JS = f.read()


def build_render_3d(audio, sr, latent_points, latent_times, centroids, rms, waveform_peaks):
    wav_bytes = audio_to_wav_bytes(audio, sr)
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

    centroid_min = float(centroids.min())
    centroid_max = float(centroids.max())
    rms_min = float(rms.min())
    rms_max = float(rms.max())

    time_max = float(latent_times.max()) if len(latent_times) > 0 else 1.0
    time_norm = (latent_times / time_max).tolist()

    points_3d = []
    for i in range(len(latent_points)):
        points_3d.append([
            float(latent_points[i, 0]),
            float(latent_points[i, 1]),
            time_norm[i],
        ])

    data = {
        "points_3d": points_3d,
        "centroids": centroids.tolist(),
        "rms": rms.tolist(),
        "times": latent_times.tolist(),
        "centroid_min": centroid_min,
        "centroid_max": centroid_max,
        "rms_min": rms_min,
        "rms_max": rms_max,
        "duration": float(len(audio) / sr),
        "audio_b64": audio_b64,
        "sr": sr,
        "waveform_peaks": waveform_peaks,
    }

    component_id = f"r3d-{uuid.uuid4().hex[:8]}"
    data_json = json.dumps(data)

    html = _TEMPLATE.replace("__COMPONENT_ID__", component_id).replace(
        "__DATA_JSON__", data_json
    ).replace(
        "__COMPONENT_JS__", _COMPONENT_JS
    )
    return html


_TEMPLATE = r"""
<style>
  #__COMPONENT_ID__-wrap {
    --bg: #0a0a1a;
    --bg2: #070714;
    --text: #e0e0e0;
    --text-strong: #fff;
    --text-muted: #888;
    --text-label: #999;
    --range-bg: #333;
    --accent: #00d2ff;
    font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    user-select: none;
    display: flex;
    flex-direction: column;
    height: 100%;
    box-sizing: border-box;
    color: var(--text);
  }
  #__COMPONENT_ID__-inner {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  #__COMPONENT_ID__-viewport:fullscreen {
    width: 100vw;
    height: 100vh;
    background: var(--bg2);
  }
  #__COMPONENT_ID__-viewport:fullscreen canvas {
    width: 100vw !important;
    height: 100vh !important;
  }
  #__COMPONENT_ID__-viewport {
    position: relative;
    border-radius: 6px;
    overflow: hidden;
    flex: 1;
    min-height: 300px;
    background: var(--bg2);
  }
  #__COMPONENT_ID__-viewport canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }
  #__COMPONENT_ID__-fs-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 20;
    background: rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.6);
    border-radius: 4px;
    padding: 4px 8px;
    cursor: pointer;
    font-size: 14px;
    line-height: 1;
    font-family: sans-serif;
    transition: opacity 0.2s;
  }
  #__COMPONENT_ID__-fs-btn:hover {
    background: rgba(0,0,0,0.55);
    color: #fff;
  }
  .__COMPONENT_ID__-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .__COMPONENT_ID__-controls button {
    background: linear-gradient(135deg,var(--accent),#3a7bd5);
    border: none;
    color: #000;
    padding: 8px 20px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 700;
    font-size: 15px;
    min-width: 84px;
  }
  .__COMPONENT_ID__-controls input[type=range] {
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: var(--range-bg);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    margin: 0;
  }
  .__COMPONENT_ID__-controls input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
  }
  .__COMPONENT_ID__-controls label {
    font-size: 12px;
    color: var(--text-label);
    white-space: nowrap;
  }
  .__COMPONENT_ID__-controls .val {
    font-size: 12px;
    color: var(--text-muted);
    font-family: 'SF Mono',Monaco,monospace;
    min-width: 32px;
  }
  .__COMPONENT_ID__-controls .time {
    font-family: 'SF Mono',Monaco,monospace;
    font-size: 13px;
    color: var(--text-muted);
    margin-left: auto;
  }
  .__COMPONENT_ID__-seek {
    flex: 1;
    min-width: 80px;
  }
  .__COMPONENT_ID__-slider-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    flex-wrap: wrap;
  }
  .__COMPONENT_ID__-slider-row input[type=range] {
    height: 4px;
    -webkit-appearance: none;
    appearance: none;
    background: var(--range-bg);
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    margin: 0;
  }
  .__COMPONENT_ID__-slider-row input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: var(--accent);
    cursor: pointer;
  }
  .__COMPONENT_ID__-slider-row label {
    font-size: 11px;
    color: var(--text-label);
    white-space: nowrap;
  }
  .__COMPONENT_ID__-slider-row .val {
    font-size: 11px;
    color: var(--text-muted);
    font-family: 'SF Mono',Monaco,monospace;
    min-width: 28px;
  }
  #__COMPONENT_ID__-bottom {
    display: flex;
    gap: 10px;
    margin-top: 8px;
    flex-shrink: 0;
    height: 280px;
  }
  .__COMPONENT_ID__-bottom-item {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-width: 0;
  }
  .__COMPONENT_ID__-bottom-label {
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 4px;
    flex-shrink: 0;
  }
  .__COMPONENT_ID__-bottom-canvas {
    flex: 1;
    position: relative;
    border-radius: 4px;
    overflow: hidden;
    background: var(--bg2);
    min-height: 0;
  }
  .__COMPONENT_ID__-bottom-canvas canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }
  .__COMPONENT_ID__-legend {
    display: flex;
    align-items: center;
    gap: 4px;
    margin-bottom: 2px;
    flex-shrink: 0;
  }
  .__COMPONENT_ID__-legend-label {
    font-size: 9px;
    color: var(--text-muted);
    font-family: 'SF Mono', Monaco, monospace;
    white-space: nowrap;
  }
  #__COMPONENT_ID__-legend-bar {
    border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.08);
    flex-shrink: 0;
  }
</style>

<div id="__COMPONENT_ID__-wrap">
  <div id="__COMPONENT_ID__-inner">
  <div id="__COMPONENT_ID__-viewport">
    <canvas id="__COMPONENT_ID__-three"></canvas>
    <button id="__COMPONENT_ID__-fs-btn">⛶</button>
  </div>

  <div id="__COMPONENT_ID__-bottom">
    <div class="__COMPONENT_ID__-bottom-item">
      <div class="__COMPONENT_ID__-bottom-label">Waveform</div>
      <div class="__COMPONENT_ID__-bottom-canvas">
        <canvas id="__COMPONENT_ID__-wave"></canvas>
      </div>
    </div>
    <div class="__COMPONENT_ID__-bottom-item">
      <div class="__COMPONENT_ID__-bottom-label">Spectral Centroid</div>
      <div class="__COMPONENT_ID__-legend">
        <span class="__COMPONENT_ID__-legend-label" id="__COMPONENT_ID__-legend-low">0 kHz</span>
        <canvas id="__COMPONENT_ID__-legend-bar" width="100" height="8"></canvas>
        <span class="__COMPONENT_ID__-legend-label" id="__COMPONENT_ID__-legend-high">10 kHz</span>
      </div>
      <div class="__COMPONENT_ID__-bottom-canvas">
        <canvas id="__COMPONENT_ID__-prof"></canvas>
      </div>
    </div>
  </div>

  <div class="__COMPONENT_ID__-controls">
    <button id="__COMPONENT_ID__-play">&#9654;</button>
    <button id="__COMPONENT_ID__-loop" style="background:linear-gradient(135deg,var(--accent),#3a7bd5);border:none;color:#000;padding:8px 12px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;opacity:0.4;line-height:1;min-width:0">&#8634;</button>
    <input type="range" class="__COMPONENT_ID__-seek" id="__COMPONENT_ID__-seek" min="0" max="1000" value="0">
    <span class="time" id="__COMPONENT_ID__-time">0:00 / 0:00</span>
  </div>
  <div class="__COMPONENT_ID__-slider-row">
    <label>Vol</label>
    <input type="range" id="__COMPONENT_ID__-vol" min="0" max="100" value="75" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-vol-val">75%</span>
    <label>Spd</label>
    <input type="range" id="__COMPONENT_ID__-speed" min="0.25" max="3" step="0.25" value="1" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-speed-val">1x</span>
    <label>Orbit</label>
    <input type="range" id="__COMPONENT_ID__-orbit" min="-0.4" max="0.4" step="0.05" value="0.1" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-orbit-val">0.10</span>
    <label>Stretch</label>
    <input type="range" id="__COMPONENT_ID__-stretch" min="0.5" max="6" step="0.1" value="3.5" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-stretch-val">3.5</span>
    <label>Slc</label>
    <input type="range" id="__COMPONENT_ID__-slices" min="0" max="10" value="5" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-slices-val">5</span>
    <label>Op</label>
    <input type="range" id="__COMPONENT_ID__-slice-op" min="0" max="100" value="5" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-slice-op-val">5</span>
    <label>Zoom</label>
    <input type="range" id="__COMPONENT_ID__-zoom" min="5" max="50" value="15" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-zoom-val">1.5</span>
    <label>Fade</label>
    <input type="range" id="__COMPONENT_ID__-fade" min="5" max="100" step="5" value="30" style="width:56px">
    <span class="val" id="__COMPONENT_ID__-fade-val">3.0</span>
    <label>Pan</label>
    <select id="__COMPONENT_ID__-pan-mode" style="background:var(--bg2);color:var(--text);border:1px solid var(--text-muted);border-radius:4px;font-size:11px;padding:2px 4px;width:66px;">
      <option value="midpoint">Midpoint</option>
      <option value="none">None</option>
    </select>
  </div>
  </div>
</div>

<script>
  window.DATA = __DATA_JSON__;
  window.__ID__ = "__COMPONENT_ID__";
</script>
<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>
<script type="module">
__COMPONENT_JS__
</script>
"""
