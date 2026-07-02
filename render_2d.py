import base64
import json
import uuid
from pathlib import Path

from utils.audio_utils import audio_to_wav_bytes


_JS_DIR = Path(__file__).parent / "js-components"

with open(_JS_DIR / "render-2d.js") as f:
    _SKETCH_JS = f.read()


def build_render_2d(audio, sr, latent_points, latent_times, waveform_peaks):
    wav_bytes = audio_to_wav_bytes(audio, sr)
    audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

    data = {
        "waveform_peaks": waveform_peaks,
        "latent_path": latent_points.tolist(),
        "latent_times": latent_times.tolist(),
        "duration": float(len(audio) / sr),
        "audio_b64": audio_b64,
        "sr": sr,
    }

    component_id = f"p5d-{uuid.uuid4().hex[:8]}"
    data_json = json.dumps(data)

    html = _TEMPLATE.replace("__ID__", component_id).replace(
        "__DATA_JSON__", data_json
    ).replace(
        "__SKETCH_JS__", _SKETCH_JS
    )
    return html


_TEMPLATE = r"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.11.3/p5.min.js"></script>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #0e1117; font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; color: #e0e0e0; user-select: none; }
  #__ID__-wrap { padding: 20px; }
  #__ID__-p5-container canvas { display: block; border-radius: 6px; }
  #__ID__-controls { display: flex; align-items: center; gap: 10px; margin-top: 12px; flex-wrap: wrap; }
  #__ID__-controls button {
    background: linear-gradient(135deg,#00d2ff,#3a7bd5); border: none; color: #000;
    padding: 8px 20px; border-radius: 6px; cursor: pointer; font-weight: 700; font-size: 15px; letter-spacing: 0.3px; min-width: 84px;
  }
  #__ID__-loop { padding: 8px 12px; min-width: 0; }
  #__ID__-time { font-family: 'SF Mono',Monaco,monospace; font-size: 14px; color: #888; margin-left: auto; }
  #__ID__-seek { flex: 1; min-width: 80px; height: 4px; -webkit-appearance: none; appearance: none; background: #333; border-radius: 2px; outline: none; cursor: pointer; }
  #__ID__-seek::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%; background: #00d2ff; cursor: pointer; }
  .__ID__-row { display: flex; align-items: center; gap: 12px; margin-top: 6px; flex-wrap: wrap; }
  .__ID__-row label { font-size: 13px; color: #999; white-space: nowrap; }
  .__ID__-row input[type=range] { height: 4px; -webkit-appearance: none; appearance: none; background: #333; border-radius: 2px; outline: none; cursor: pointer; }
  .__ID__-row input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 12px; height: 12px; border-radius: 50%; background: #00d2ff; cursor: pointer; }
  .__ID__-row .val { font-size: 13px; color: #888; font-family: 'SF Mono',Monaco,monospace; min-width: 36px; }
</style>
</head>
<body>
<div id="__ID__-wrap">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="margin:0;color:#fff;font-weight:600;font-size:18px">Real-Time Player</h3>
    <span id="__ID__-time" style="font-family:'SF Mono',Monaco,monospace;font-size:14px;color:#888">0:00 / 0:00</span>
  </div>
  <div id="__ID__-p5-container"></div>
  <div id="__ID__-controls">
    <button id="__ID__-play">&#9654;</button>
    <button id="__ID__-loop" style="background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:8px 12px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;opacity:0.4;min-width:0">&#8634;</button>
    <input type="range" id="__ID__-seek" min="0" max="1000" value="0">
  </div>
  <div class="__ID__-row">
    <label>Volume</label>
    <input type="range" id="__ID__-vol" min="0" max="100" value="75" style="width:80px">
    <span class="val" id="__ID__-vol-val">75%</span>
    <label>Speed</label>
    <input type="range" id="__ID__-speed" min="0.25" max="3" step="0.25" value="1" style="width:80px">
    <span class="val" id="__ID__-speed-val">1x</span>
    <label>Fade</label>
    <input type="range" id="__ID__-fade" min="5" max="100" step="5" value="20" style="width:60px">
    <span class="val" id="__ID__-fade-val">2.0</span>
    <label>Trail</label>
    <input type="range" id="__ID__-trail" min="1" max="50" value="15" style="width:60px">
    <span class="val" id="__ID__-trail-val">15</span>
    <label>Zoom</label>
    <input type="range" id="__ID__-zoom" min="5" max="40" value="10" style="width:60px">
    <span class="val" id="__ID__-zoom-val">1.0</span>
  </div>
</div>
<script>
var DATA = __DATA_JSON__;
var ID = '__ID__';
</script>
<script>
__SKETCH_JS__
</script>
</body>
</html>"""
