import base64
import json
from pathlib import Path

import numpy as np

from utils.audio_utils import audio_to_wav_bytes

_JS_DIR = Path(__file__).parent / "js-components"
_SKETCH_JS = (_JS_DIR / "render-2d.js").read_text()

CANVAS_W = 960
LATENT_H = 325
WAVE_H = 163
CENT_H = 162
TOTAL_H = LATENT_H + WAVE_H + CENT_H
PAD = 0.05


def _normalize(arr):
    lo, hi = arr.min(), arr.max()
    rng = hi - lo if hi > lo else 1.0
    return (arr - lo) / rng


def _lerp(a, b, t):
    return a + (b - a) * t


def _path_color(t):
    c_s = [0, 210, 255]
    c_m = [123, 47, 247]
    c_e = [255, 107, 107]
    if t < 0.5:
        tt = t * 2
        return [_lerp(c_s[i], c_m[i], tt) for i in range(3)]
    tt = (t - 0.5) * 2
    return [_lerp(c_m[i], c_e[i], tt) for i in range(3)]


def build_render_2d(audio, sr, latent_points, latent_times, centroids, rms, waveform_peaks):
    wav_bytes = audio_to_wav_bytes(audio, sr)
    n_frames = len(latent_points)

    # ----- latent screen coords -----
    x_vals = latent_points[:, 0]
    y_vals = latent_points[:, 1]
    x_min, x_max = float(x_vals.min()), float(x_vals.max())
    y_min, y_max = float(y_vals.min()), float(y_vals.max())
    x_rng = (x_max - x_min) or 1.0
    y_rng = (y_max - y_min) or 1.0
    x_scale = CANVAS_W / (x_rng * (1 + 2 * PAD))
    y_scale = LATENT_H / (y_rng * (1 + 2 * PAD))
    scale = min(x_scale, y_scale)
    vw = x_rng * (1 + 2 * PAD) * scale
    vh = y_rng * (1 + 2 * PAD) * scale
    ox = (CANVAS_W - vw) / 2
    oy = (LATENT_H - vh) / 2
    x_mid = (x_min + x_max) / 2
    y_mid = (y_min + y_max) / 2
    x_lo = x_mid - x_rng * (1 + 2 * PAD) / 2
    y_hi = y_mid + y_rng * (1 + 2 * PAD) / 2

    latent_screen = []
    latent_colors = []
    for i in range(n_frames):
        sx = ox + (latent_points[i, 0] - x_lo) * scale
        sy = oy + (y_hi - latent_points[i, 1]) * scale
        latent_screen.append([round(sx, 2), round(sy, 2)])
        t = i / (n_frames - 1) if n_frames > 1 else 0
        base = _path_color(t)
        latent_colors.append([round(c) for c in base])

    # ----- waveform shape (flat [x,y,x,y,...] normalized 0-1) -----
    n_peaks = len(waveform_peaks)
    ws_flat = [0.0, 0.5]
    for i in range(n_peaks):
        ws_flat.extend([(i + 1) / (n_peaks + 1), 0.5 + waveform_peaks[i][0] * 0.42])
    for i in range(n_peaks - 1, -1, -1):
        ws_flat.extend([(i + 1) / (n_peaks + 1), 0.5 + waveform_peaks[i][1] * 0.42])
    ws_flat.extend([0.0, 0.5])

    # ----- centroid scatter screen coords -----
    c_norm = _normalize(centroids)
    r_norm = _normalize(rms)
    cp_pad = 44
    c_plot_w = CANVAS_W - cp_pad * 2
    c_plot_h = CENT_H - cp_pad * 2
    centroid_screen = []
    centroid_colors = []
    for i in range(n_frames):
        cx = cp_pad + c_norm[i] * c_plot_w
        cy = cp_pad + (1.0 - r_norm[i]) * c_plot_h
        centroid_screen.append([round(cx, 2), round(cy, 2)])
        base = _path_color(c_norm[i])
        centroid_colors.append([round(c) for c in base])

    # ----- build payload -----
    payload = {
        "cw": int(CANVAS_W),
        "ch": int(TOTAL_H),
        "lh": int(LATENT_H),
        "wh": int(WAVE_H),
        "dur": round(len(audio) / sr, 3),
        "sr": int(sr),
        "ab": base64.b64encode(wav_bytes).decode("ascii"),
        "li": latent_screen,
        "lc": latent_colors,
        "ws": ws_flat,
        "cp": centroid_screen,
        "cc": centroid_colors,
    }

    payload_js = json.dumps(payload, default=lambda x: float(x) if isinstance(x, (np.floating,)) else str(x))

    return f"""<!DOCTYPE html>
<html>
<head>
<script src="https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.11.3/p5.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#0e1117;font-family:system-ui,sans-serif;color:#e0e0e0;user-select:none}}
#w canvas{{display:block;border-radius:6px}}
#b{{display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap}}
#b button{{background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:6px 18px;border-radius:5px;cursor:pointer;font-weight:700;font-size:14px;min-width:78px}}
#t{{font-family:monospace;font-size:13px;color:#888;white-space:nowrap}}
#s{{flex:1;min-width:60px;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer}}
#s::-webkit-slider-thumb{{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:#00d2ff;cursor:pointer}}
#b label{{font-size:12px;color:#999}}
#v{{height:4px;width:70px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer}}
#v::-webkit-slider-thumb{{-webkit-appearance:none;width:12px;height:12px;border-radius:50%;background:#00d2ff;cursor:pointer}}
#vv{{font-size:12px;color:#888;font-family:monospace;min-width:32px}}
</style>
</head>
<body>
<div id="w"><div id="c"></div><div id="b"><button id="p">&#9654;</button><input type="range" id="s" min="0" max="1000" value="0"><span id="t">0:00 / 0:00</span><label>Vol</label><input type="range" id="v" min="0" max="100" value="75"><span id="vv">75%</span></div></div>
<script>var D={payload_js};
var P=document.getElementById("p"),S=document.getElementById("s"),T=document.getElementById("t"),V=document.getElementById("v"),VV=document.getElementById("vv");
{_SKETCH_JS}</script>
</body>
</html>"""
