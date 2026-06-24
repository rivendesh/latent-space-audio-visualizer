import base64
import json
import uuid
from pathlib import Path

from utils.audio_utils import audio_to_wav_bytes


_JS_DIR = Path(__file__).parent / "js-components"

with open(_JS_DIR / "render-2d.js") as f:
    _COMPONENT_JS = f.read()


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

    component_id = f"rtv-{uuid.uuid4().hex[:8]}"
    data_json = json.dumps(data)

    html = _HTML_TEMPLATE.replace("__COMPONENT_ID__", component_id).replace(
        "__DATA_JSON__", data_json
    ).replace(
        "__COMPONENT_JS__", _COMPONENT_JS
    )
    return html


_HTML_TEMPLATE = """
<div id="__COMPONENT_ID__" style="background:#0e1117;border-radius:8px;padding:20px;color:#e0e0e0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;user-select:none">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
    <h3 style="margin:0;color:#fff;font-weight:600;font-size:18px">Real-Time Player</h3>
    <span id="__COMPONENT_ID__-time" style="font-family:'SF Mono',Monaco,monospace;font-size:14px;color:#888">0:00 / 0:00</span>
  </div>

  <div style="margin-bottom:12px;position:relative;border-radius:6px;overflow:hidden">
    <canvas id="__COMPONENT_ID__-latent" style="width:100%;height:380px;display:block;background:#0a0a1a"></canvas>
  </div>

  <div style="margin-bottom:12px;position:relative;border-radius:6px;overflow:hidden">
    <canvas id="__COMPONENT_ID__-wave" style="width:100%;height:120px;display:block;background:#0a0a1a"></canvas>
  </div>

  <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
    <button id="__COMPONENT_ID__-play" style="background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:8px 20px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;letter-spacing:0.3px;min-width:84px">&#9654;</button>
    <button id="__COMPONENT_ID__-loop" style="background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:8px 12px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;opacity:0.4;line-height:1">&#8634;</button>
    <div style="flex:1;position:relative">
      <input type="range" id="__COMPONENT_ID__-seek" min="0" max="1000" value="0" style="width:100%;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer;margin:0">
    </div>
  </div>

  <div style="display:flex;align-items:center;gap:12px">
    <label style="font-size:13px;color:#999;white-space:nowrap">Volume</label>
    <input type="range" id="__COMPONENT_ID__-vol" min="0" max="100" value="75" style="width:100px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer">
    <span id="__COMPONENT_ID__-vol-val" style="font-size:13px;color:#888;min-width:36px;font-family:'SF Mono',monospace">75%</span>
    <label style="font-size:13px;color:#999;white-space:nowrap">Speed</label>
    <input type="range" id="__COMPONENT_ID__-speed" min="0.25" max="3" step="0.25" value="1" style="width:80px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer">
    <span id="__COMPONENT_ID__-speed-val" style="font-size:13px;color:#888;min-width:36px;font-family:'SF Mono',monospace">1x</span>
  </div>

  <div style="display:flex;align-items:center;gap:12px;margin-top:4px">
    <label style="font-size:13px;color:#999;white-space:nowrap">Fade</label>
    <input type="range" id="__COMPONENT_ID__-fade" min="5" max="100" step="5" value="20" style="width:60px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer">
    <span id="__COMPONENT_ID__-fade-val" style="font-size:13px;color:#888;min-width:28px;font-family:'SF Mono',monospace">2.0</span>
    <label style="font-size:13px;color:#999;white-space:nowrap">Trail</label>
    <input type="range" id="__COMPONENT_ID__-trail" min="1" max="50" value="15" style="width:60px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer">
    <span id="__COMPONENT_ID__-trail-val" style="font-size:13px;color:#888;min-width:28px;font-family:'SF Mono',monospace">15</span>
    <label style="font-size:13px;color:#999;white-space:nowrap">Zoom</label>
    <input type="range" id="__COMPONENT_ID__-zoom" min="5" max="40" value="10" style="width:60px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer">
    <span id="__COMPONENT_ID__-zoom-val" style="font-size:13px;color:#888;min-width:28px;font-family:'SF Mono',monospace">1.0</span>
  </div>
</div>

<script>
(function() {
  var DATA = __DATA_JSON__;
  var id = "__COMPONENT_ID__";
  __COMPONENT_JS__
})();
</script>
"""
