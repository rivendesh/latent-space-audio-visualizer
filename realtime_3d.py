import base64
import json
import uuid

from audio_processor import audio_to_wav_bytes


# Serialise audio + latent data into a self-contained HTML string with Three.js.
# Returns an <iframe>-ready component embedding a 3D latent-space viewer.
def build_3d_component(audio, sr, latent_points, latent_times, centroids, rms, waveform_peaks, is_dark=True):
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
        "is_dark": is_dark,
        "waveform_peaks": waveform_peaks,
    }

    component_id = f"r3d-{uuid.uuid4().hex[:8]}"
    data_json = json.dumps(data)

    html = _TEMPLATE.replace("__COMPONENT_ID__", component_id).replace(
        "__DATA_JSON__", data_json
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
  #__COMPONENT_ID__-wrap.light {
    --bg: #f0f2f5;
    --bg2: #ffffff;
    --text: #333;
    --text-strong: #111;
    --text-muted: #777;
    --text-label: #666;
    --range-bg: #ccc;
    --accent: #0066cc;
  }
  #__COMPONENT_ID__-inner {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
  }
  #__COMPONENT_ID__-inner:fullscreen {
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: var(--bg);
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
  .__COMPONENT_ID__-controls .theme-btn {
    background: none;
    border: 1px solid var(--text-muted);
    color: var(--text-muted);
    min-width: auto;
    padding: 6px 10px;
    font-size: 16px;
    line-height: 1;
    border-radius: 6px;
    cursor: pointer;
  }
  .__COMPONENT_ID__-controls .theme-btn:hover {
    border-color: var(--text-strong);
    color: var(--text-strong);
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
    <button id="__COMPONENT_ID__-play">&#9654; Play</button>
    <input type="range" class="__COMPONENT_ID__-seek" id="__COMPONENT_ID__-seek" min="0" max="1000" value="0">
    <span class="time" id="__COMPONENT_ID__-time">0:00 / 0:00</span>
    <button class="theme-btn" id="__COMPONENT_ID__-theme">&#127769;</button>
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
  </div>
  </div>
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js",
    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = __DATA_JSON__;
const id = '__COMPONENT_ID__';

const viewport = document.getElementById(id+'-viewport');
const threeCanvas = document.getElementById(id+'-three');
const playBtn = document.getElementById(id+'-play');
const seekBar = document.getElementById(id+'-seek');
const volSlider = document.getElementById(id+'-vol');
const volVal = document.getElementById(id+'-vol-val');
const speedSlider = document.getElementById(id+'-speed');
const speedVal = document.getElementById(id+'-speed-val');
const orbitSlider = document.getElementById(id+'-orbit');
const orbitVal = document.getElementById(id+'-orbit-val');
const stretchSlider = document.getElementById(id+'-stretch');
const stretchVal = document.getElementById(id+'-stretch-val');
const slicesSlider = document.getElementById(id+'-slices');
const slicesVal = document.getElementById(id+'-slices-val');
const sliceOpSlider = document.getElementById(id+'-slice-op');
const sliceOpVal = document.getElementById(id+'-slice-op-val');
const zoomSlider = document.getElementById(id+'-zoom');
const zoomVal = document.getElementById(id+'-zoom-val');
const timeDisplay = document.getElementById(id+'-time');
const waveCanvas = document.getElementById(id+'-wave');
const profCanvas = document.getElementById(id+'-prof');
const legendBar = document.getElementById(id+'-legend-bar');
const legendLow = document.getElementById(id+'-legend-low');
const legendHigh = document.getElementById(id+'-legend-high');

// ----- audio state -----
let audioCtx = null;
let audioBuffer = null;
let source = null;
let gainNode = null;
let isPlaying = false;
let startTime = 0;
let pausedAt = 0;
let animId = null;
let currentSpeed = 1.0;
let currentVol = 0.75;
let sourceGen = 0;

// ----- Three.js -----
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x070714);

const camera = new THREE.PerspectiveCamera(45, viewport.clientWidth / viewport.clientHeight, 0.1, 100);
camera.position.set(5, 3.5, 5);
camera.zoom = 1.5;

const renderer = new THREE.WebGLRenderer({
  canvas: threeCanvas,
  antialias: true,
  alpha: false,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(viewport.clientWidth, viewport.clientHeight);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.1;
controls.target.set(0, 0, 0.5);
controls.update();

// Data group for time-axis stretching
const dataGroup = new THREE.Group();
scene.add(dataGroup);
dataGroup.scale.z = 3.5;

// ----- theme -----
const wrapEl = document.getElementById(id+'-wrap');
const innerEl = document.getElementById(id+'-inner');
const themeBtn = document.getElementById(id+'-theme');
let isDark = DATA.is_dark !== undefined ? DATA.is_dark : true;

function applyTheme(dark) {
  isDark = dark;
  wrapEl.classList.toggle('light', !dark);
  const bg = dark ? 0x070714 : 0xf0f0f0;
  scene.background = new THREE.Color(bg);
  const gridCol = dark ? 0x6666aa : 0xaaaaaa;
  const gridCol2 = dark ? 0x444477 : 0x888888;
  [gridHelper, gridSide, gridBack].forEach(function(g) {
    g.material.color.set(dark ? 0x6666aa : 0xaaaaaa);
    g.material.opacity = dark ? 0.55 : 0.5;
  });
  timePlaneMat.color.set(dark ? 0x6666aa : 0x888888);
  timePlaneEdgeMat.color.set(dark ? 0x8888cc : 0x999999);
  themeBtn.innerHTML = dark ? '&#127769;' : '&#9728;';
}

themeBtn.addEventListener('click', function() {
  applyTheme(!isDark);
});

// ----- lighting -----
const ambLight = new THREE.AmbientLight(0x404060, 0.6);
scene.add(ambLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(1, 2, 1);
scene.add(dirLight);

// ----- sharp dot texture for points -----
function makeDotTexture() {
  const c = document.createElement('canvas');
  c.width = 16;
  c.height = 16;
  const ctx = c.getContext('2d');
  ctx.beginPath();
  ctx.arc(8, 8, 6, 0, Math.PI * 2);
  ctx.fillStyle = '#fff';
  ctx.fill();
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}
const dotTexture = makeDotTexture();

// ----- centroid color map: deep blue (low freq) -> cyan -> yellow -> hot red (high freq) -----
function centroidColor(t) {
  t = Math.max(0, Math.min(1, t));
  if (t < 0.25) {
    const u = t / 0.25;
    return [0.05, 0.05 + 0.35*u, 0.5 + 0.5*u];
  } else if (t < 0.5) {
    const u = (t - 0.25) / 0.25;
    return [0, 0.4 + 0.6*u, 1.0 - 0.3*u];
  } else if (t < 0.75) {
    const u = (t - 0.5) / 0.25;
    return [0.8*u, 1.0 - 0.5*u, 0.7 - 0.7*u];
  } else {
    const u = (t - 0.75) / 0.25;
    return [0.8 + 0.2*u, 0.5 - 0.4*u, 0];
  }
}

const points3d = DATA.points_3d;
const centroids = DATA.centroids;
const centroidMin = DATA.centroid_min;
const centroidRange = DATA.centroid_max - DATA.centroid_min || 1;
const n = points3d.length;

// Pre-fill geometry arrays
const posArr = new Float32Array(n * 3);
const colArr = new Float32Array(n * 3);
for (let i = 0; i < n; i++) {
  const p = points3d[i];
  const cf = (centroids[i] - centroidMin) / centroidRange;
  const [r, g, b] = centroidColor(cf);
  posArr[i*3] = p[0];
  posArr[i*3+1] = p[1];
  posArr[i*3+2] = p[2];
  colArr[i*3] = r;
  colArr[i*3+1] = g;
  colArr[i*3+2] = b;
}

// Points (sharp dots)
const pointGeo = new THREE.BufferGeometry();
pointGeo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
pointGeo.setAttribute('color', new THREE.BufferAttribute(colArr, 3));
pointGeo.setDrawRange(0, 0);
const pointMat = new THREE.PointsMaterial({
  size: 0.12,
  map: dotTexture,
  vertexColors: true,
  sizeAttenuation: true,
  transparent: true,
  opacity: 1,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});
const points = new THREE.Points(pointGeo, pointMat);
dataGroup.add(points);

// Trajectory line
const linePos = new Float32Array(n * 3);
for (let i = 0; i < n; i++) {
  linePos[i*3] = points3d[i][0];
  linePos[i*3+1] = points3d[i][1];
  linePos[i*3+2] = points3d[i][2];
}
const lineGeo = new THREE.BufferGeometry();
lineGeo.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
lineGeo.setDrawRange(0, 0);
const lineMat = new THREE.LineBasicMaterial({
  color: 0x00d2ff,
  transparent: true,
  opacity: 0.3,
});
const line = new THREE.Line(lineGeo, lineMat);
dataGroup.add(line);

// ----- axes -----
function makeLabelSprite(text) {
  const c = document.createElement('canvas');
  c.width = 128;
  c.height = 48;
  const ctx = c.getContext('2d');
  ctx.fillStyle = 'rgba(0,0,0,0.3)';
  ctx.fillRect(0, 12, c.width, 28);
  ctx.font = 'bold 22px "SF Mono",Monaco,monospace';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillStyle = '#fff';
  ctx.fillText(text, 64, 28);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, opacity: 0.6, depthWrite: false });
  const sprite = new THREE.Sprite(mat);
  sprite.scale.set(0.5, 0.2, 1);
  return sprite;
}

function addAxis(from, to, color, labelText) {
  const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.2 });
  const geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(from[0], from[1], from[2]),
    new THREE.Vector3(to[0], to[1], to[2]),
  ]);
  scene.add(new THREE.Line(geo, mat));
  const lbl = makeLabelSprite(labelText);
  lbl.material.opacity = 0.3;
  lbl.position.set(to[0], to[1], to[2]);
  scene.add(lbl);
}

const axExt = 3.0;
addAxis([-axExt, 0, 0], [axExt, 0, 0], 0x00d2ff, 'PC1');
addAxis([0, -axExt, 0], [0, axExt, 0], 0x00d2ff, 'PC2');
addAxis([0, 0, -0.1], [0, 0, 1.1], 0x00d2ff, 'Time');

// grid helper
const gridHelper = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridHelper.position.y = -axExt;
gridHelper.material.transparent = true;
gridHelper.material.opacity = 0.55;
scene.add(gridHelper);

// Side grid (PC2-Time plane at x=-axExt)
const gridSide = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridSide.position.x = -axExt;
gridSide.rotation.z = Math.PI / 2;
gridSide.material.transparent = true;
gridSide.material.opacity = 0.3;
scene.add(gridSide);

// Back grid (PC1-PC2 plane at z=0)
const gridBack = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridBack.position.z = 0;
gridBack.rotation.x = Math.PI / 2;
gridBack.material.transparent = true;
gridBack.material.opacity = 0.3;
scene.add(gridBack);

// Time slice planes — vertical XY planes at regular z intervals
const timePlaneGroup = new THREE.Group();
dataGroup.add(timePlaneGroup);
const timePlaneMat = new THREE.MeshBasicMaterial({
  color: 0x6666aa,
  transparent: true,
  opacity: 0.05,
  side: THREE.DoubleSide,
  depthWrite: false,
});
const timePlaneEdgeMat = new THREE.LineBasicMaterial({
  color: 0x8888cc,
  transparent: true,
  opacity: 0.12,
});
applyTheme(isDark);

// ----- build time slice planes -----
function buildTimePlanes(n) {
  while (timePlaneGroup.children.length) {
    const c = timePlaneGroup.children[0];
    c.geometry.dispose();
    timePlaneGroup.remove(c);
  }
  if (n <= 0) return;
  const step = 1 / n;
  for (let z = 0; z <= 1.001; z += step) {
    const geo = new THREE.PlaneGeometry(axExt * 2, axExt * 2);
    const mesh = new THREE.Mesh(geo, timePlaneMat);
    mesh.position.set(0, 0, z);
    timePlaneGroup.add(mesh);
    const edges = new THREE.EdgesGeometry(geo);
    const line = new THREE.LineSegments(edges, timePlaneEdgeMat);
    line.position.set(0, 0, z);
    timePlaneGroup.add(line);
  }
}
buildTimePlanes(5);

// ----- centroid color legend (draw to profile legend bar) -----
function buildLegend() {
  const ctx = legendBar.getContext('2d');
  for (var i = 0; i < legendBar.width; i++) {
    var t = i / legendBar.width;
    var [r, g, b] = centroidColor(t);
    ctx.fillStyle = 'rgb(' + ((r*255)<<0) + ',' + ((g*255)<<0) + ',' + ((b*255)<<0) + ')';
    ctx.fillRect(i, 0, 1, legendBar.height);
  }
  legendLow.textContent = (DATA.centroid_min / 1000).toFixed(1) + ' kHz';
  legendHigh.textContent = (DATA.centroid_max / 1000).toFixed(1) + ' kHz';
}
buildLegend();

// ----- waveform drawing -----
function drawWaveform(t) {
  var ctx = waveCanvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var rect = waveCanvas.parentElement.getBoundingClientRect();
  var w = rect.width, h = rect.height;
  if (w === 0 || h === 0) return;
  waveCanvas.width = Math.round(w * dpr);
  waveCanvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  var peaks = DATA.waveform_peaks;
  var n = peaks.length;
  var dur = DATA.duration;

  // grid
  ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)';
  ctx.lineWidth = 1;
  for (var y = 0.5; y < h; y += h/4) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  // time marks
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (var tm = 0; tm <= dur; tm += Math.max(1, Math.round(dur/6))) {
    var x = (tm / dur) * w;
    ctx.fillStyle = isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.15)';
    ctx.fillText(tm + 's', x, h - 11);
    ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)';
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }

  // baseline
  ctx.strokeStyle = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)';
  ctx.beginPath(); ctx.moveTo(0, h*0.5); ctx.lineTo(w, h*0.5); ctx.stroke();

  // unplayed fill (full waveform)
  ctx.beginPath();
  ctx.moveTo(0, h*0.5);
  for (var i=0; i<n; i++) {
    ctx.lineTo((i/n)*w, h*0.5 + peaks[i][0] * h*0.42);
  }
  for (var i=n-1; i>=0; i--) {
    ctx.lineTo((i/n)*w, h*0.5 + peaks[i][1] * h*0.42);
  }
  ctx.closePath();
  ctx.fillStyle = isDark ? 'rgba(0,210,255,0.1)' : 'rgba(0,102,204,0.08)';
  ctx.fill();

  // played overlay (clipped to cursor)
  if (t >= 0) {
    var cursorFrac = Math.min(Math.max(t / dur, 0), 1);
    var cursorX = cursorFrac * w;

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, cursorX, h);
    ctx.clip();

    ctx.beginPath();
    ctx.moveTo(0, h*0.5);
    for (var i=0; i<n; i++) {
      ctx.lineTo((i/n)*w, h*0.5 + peaks[i][0] * h*0.42);
    }
    for (var i=n-1; i>=0; i--) {
      ctx.lineTo((i/n)*w, h*0.5 + peaks[i][1] * h*0.42);
    }
    ctx.closePath();
    ctx.fillStyle = isDark ? 'rgba(0,210,255,0.25)' : 'rgba(0,102,204,0.2)';
    ctx.fill();
    ctx.restore();

    // cursor line
    if (cursorFrac > 0 && cursorFrac < 1) {
      ctx.beginPath();
      ctx.moveTo(cursorX, 0);
      ctx.lineTo(cursorX, h);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.shadowColor = 'rgba(255,255,255,0.4)';
      ctx.shadowBlur = 6;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }
}

// ----- spectral centroid profile drawing -----
function drawProfile(t) {
  var ctx = profCanvas.getContext('2d');
  var dpr = window.devicePixelRatio || 1;
  var rect = profCanvas.parentElement.getBoundingClientRect();
  var w = rect.width, h = rect.height;
  if (w === 0 || h === 0) return;
  profCanvas.width = Math.round(w * dpr);
  profCanvas.height = Math.round(h * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  var cMin = DATA.centroid_min, cMax = DATA.centroid_max;
  var rMin = DATA.rms_min, rMax = DATA.rms_max;
  var cRange = cMax - cMin || 1;
  var rRange = rMax - rMin || 1;

  var pad = 44;
  var plotW = w - pad * 2;
  var plotH = h - pad * 2;

  function toX(c) { return pad + ((c - cMin) / cRange) * plotW; }
  function toY(r) { return pad + (1 - (r - rMin) / rRange) * plotH; }

  var gridCol = isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)';
  var textCol = isDark ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.35)';

  // grid lines
  ctx.strokeStyle = gridCol;
  ctx.lineWidth = 1;
  for (var i = 0; i <= 4; i++) {
    var gx = pad + (i/4)*plotW;
    ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, pad+plotH); ctx.stroke();
    var gy = pad + (i/4)*plotH;
    ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(pad+plotW, gy); ctx.stroke();
  }

  // axis labels
  ctx.fillStyle = textCol;
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText('Centroid (Hz)', w/2, h-12);
  ctx.save();
  ctx.translate(10, h/2);
  ctx.rotate(-Math.PI/2);
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText('RMS Amplitude', 0, 0);
  ctx.restore();

  var n = DATA.centroids.length;

  // all data points, coloured by centroid
  for (var i = 0; i < n; i++) {
    var cx = toX(DATA.centroids[i]);
    var cy = toY(DATA.rms[i]);
    var cf = (DATA.centroids[i] - cMin) / cRange;
    var col = centroidColor(cf);
    ctx.beginPath();
    ctx.arc(cx, cy, 2, 0, Math.PI*2);
    ctx.fillStyle = 'rgba(' + ((col[0]*255)<<0) + ',' + ((col[1]*255)<<0) + ',' + ((col[2]*255)<<0) + ',0.5)';
    ctx.fill();
  }

  // highlight current playback frame
  if (t >= 0) {
    var progress = Math.min(Math.max(t / DATA.duration, 0), 1);
    var drawIdx = Math.min(Math.floor(progress * n), n);
    if (drawIdx > 0 && drawIdx <= n) {
      var idx = drawIdx - 1;
      var hx = toX(DATA.centroids[idx]);
      var hy = toY(DATA.rms[idx]);
      var grad = ctx.createRadialGradient(hx, hy, 0, hx, hy, 14);
      grad.addColorStop(0, 'rgba(255,215,0,0.5)');
      grad.addColorStop(1, 'rgba(255,215,0,0)');
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(hx, hy, 14, 0, Math.PI*2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(hx, hy, 2.5, 0, Math.PI*2);
      ctx.fillStyle = '#ffd700';
      ctx.fill();
    }
  }
}

// ----- audio -----
function base64ToArrayBuffer(b64) {
  const bin = atob(b64);
  const buf = new ArrayBuffer(bin.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
  return buf;
}

function initAudio() {
  if (audioCtx) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  gainNode = audioCtx.createGain();
  gainNode.gain.value = currentVol;
  gainNode.connect(audioCtx.destination);
  const buf = base64ToArrayBuffer(DATA.audio_b64);
  audioCtx.decodeAudioData(buf, function(b) {
    audioBuffer = b;
  }, function(err) {
    console.error('Audio decode error:', err);
  });
}

function getCurrentTime() {
  if (!isPlaying || !audioCtx) return pausedAt;
  return audioCtx.currentTime - startTime + pausedAt;
}

function createSource() {
  sourceGen++;
  const myGen = sourceGen;
  const s = audioCtx.createBufferSource();
  s.buffer = audioBuffer;
  s.playbackRate.setValueAtTime(currentSpeed, audioCtx.currentTime);
  s.connect(gainNode);
  s.onended = function() {
    if (isPlaying && myGen === sourceGen) {
      isPlaying = false;
      pausedAt = DATA.duration;
      playBtn.innerHTML = '&#9654; Play';
    }
  };
  return s;
}

function play() {
  initAudio();
  if (!audioBuffer) return;
  if (audioCtx.state === 'suspended') audioCtx.resume();
  if (pausedAt >= DATA.duration) pausedAt = 0;
  source = createSource();
  source.start(0, pausedAt);
  startTime = audioCtx.currentTime;
  isPlaying = true;
  playBtn.innerHTML = '&#9646;&#9646; Pause';
  if (!animId) animate();
}

function pause() {
  if (source) {
    pausedAt += audioCtx.currentTime - startTime;
    source.stop();
    source.disconnect();
    source = null;
  }
  isPlaying = false;
  playBtn.innerHTML = '&#9654; Play';
}

function togglePlay() {
  if (isPlaying) pause();
  else play();
}

function seek(time) {
  if (time < 0) time = 0;
  if (time > DATA.duration) time = DATA.duration;
  pausedAt = time;
  if (isPlaying) {
    if (source) { source.stop(); source.disconnect(); }
    source = createSource();
    source.start(0, pausedAt);
    startTime = audioCtx.currentTime;
  }
}

// ----- animation -----
function animate() {
  const t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;

  // Stop the loop when track ends
  if (t >= DATA.duration && !isPlaying && pausedAt >= DATA.duration) {
    animId = null;
    return;
  }

  const progress = Math.min(Math.max(t / DATA.duration, 0), 1);
  const drawCount = Math.min(Math.floor(progress * n), n);

  // Update point draw range — recency is handled by PointsMaterial blending
  pointGeo.setDrawRange(0, drawCount);
  pointMat.size = 0.06 + 0.1 * Math.min(progress * 1.5, 1);

  // Update trajectory line
  lineGeo.setDrawRange(0, Math.max(0, drawCount - 1));

  controls.update();

  // Resize if needed
  const vpW = viewport.clientWidth;
  const vpH = viewport.clientHeight;
  if (renderer.domElement.width !== Math.round(vpW * window.devicePixelRatio) ||
      renderer.domElement.height !== Math.round(vpH * window.devicePixelRatio)) {
    camera.aspect = vpW / vpH;
    camera.updateProjectionMatrix();
    renderer.setSize(vpW, vpH);
  }

  renderer.render(scene, camera);

  // Draw waveform and profile
  drawWaveform(t);
  drawProfile(t);

  // UI
  const total = DATA.duration;
  const mins = Math.floor(t/60);
  const secs = Math.floor(t%60);
  const tMins = Math.floor(total/60);
  const tSecs = Math.floor(total%60);
  timeDisplay.textContent = mins + ':' + secs.toString().padStart(2,'0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2,'0');
  seekBar.value = total > 0 ? (t/total)*1000 : 0;

  if (t >= DATA.duration) {
    if (isPlaying) {
      isPlaying = false;
      playBtn.innerHTML = '&#9654; Play';
    }
    pausedAt = DATA.duration;
    animId = null;
    return;
  }
  animId = requestAnimationFrame(animate);
}

// ----- events -----
playBtn.addEventListener('click', togglePlay);

seekBar.addEventListener('input', function() {
  const time = (parseFloat(this.value) / 1000) * DATA.duration;
  pausedAt = time;
  if (!isPlaying && audioBuffer) {
    animate();
  }
  if (isPlaying) seek(time);
});

volSlider.addEventListener('input', function() {
  currentVol = parseFloat(this.value) / 100;
  volVal.textContent = Math.round(currentVol * 100) + '%';
  if (gainNode) {
    gainNode.gain.setValueAtTime(currentVol, audioCtx.currentTime);
  }
});

speedSlider.addEventListener('input', function() {
  currentSpeed = parseFloat(this.value);
  speedVal.textContent = currentSpeed + 'x';
  if (source) {
    source.playbackRate.setValueAtTime(currentSpeed, audioCtx.currentTime);
  }
});

orbitSlider.addEventListener('input', function() {
  const v = parseFloat(this.value);
  orbitVal.textContent = v.toFixed(2);
  controls.autoRotateSpeed = v;
});

stretchSlider.addEventListener('input', function() {
  const v = parseFloat(this.value);
  stretchVal.textContent = v.toFixed(1);
  dataGroup.scale.z = v;
});

slicesSlider.addEventListener('input', function() {
  const v = parseInt(this.value);
  slicesVal.textContent = v;
  buildTimePlanes(v);
});

sliceOpSlider.addEventListener('input', function() {
  const v = parseInt(this.value);
  sliceOpVal.textContent = v;
  const op = v / 100;
  timePlaneMat.opacity = op;
  timePlaneEdgeMat.opacity = op * 2;
});

zoomSlider.addEventListener('input', function() {
  const v = parseInt(this.value);
  zoomVal.textContent = (v / 10).toFixed(1);
  camera.zoom = v / 10;
  camera.updateProjectionMatrix();
});

// ----- fullscreen toggle (targets inner wrapper to include controls) -----
const fsBtn = document.getElementById(id+'-fs-btn');
fsBtn.addEventListener('click', function() {
  if (!document.fullscreenElement) {
    innerEl.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
});
function onFsChange() {
  const isFs = !!document.fullscreenElement;
  fsBtn.textContent = isFs ? '✕' : '⛶';
  if (!isFs && viewport) {
    // Force correct sizing after exiting fullscreen
    requestAnimationFrame(function() {
      var w = viewport.clientWidth, h = viewport.clientHeight;
      if (w > 0 && h > 0) {
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }
      animate();
    });
  }
}
document.addEventListener('fullscreenchange', onFsChange);
document.addEventListener('webkitfullscreenchange', onFsChange);
document.addEventListener('mozfullscreenchange', onFsChange);

// ----- init -----
initAudio();
setTimeout(() => animate(), 100);

// ResizeObserver for sidebar and container size changes
const ro = new ResizeObserver(() => {
  clearTimeout(window._r3dResize);
  window._r3dResize = setTimeout(() => animate(), 80);
});
ro.observe(viewport);
</script>
"""


