import base64
import json
import uuid

from audio_processor import audio_to_wav_bytes


def build_3d_component(audio, sr, latent_points, latent_times, centroids, rms):
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
    background: #0a0a1a;
    border-radius: 8px;
    padding: 16px 20px 20px;
    color: #e0e0e0;
    font-family: -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
    user-select: none;
  }
  #__COMPONENT_ID__-wrap h3 {
    margin: 0;
    color: #fff;
    font-weight: 600;
    font-size: 17px;
    display: inline;
  }
  #__COMPONENT_ID__-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;
  }
  #__COMPONENT_ID__-viewport {
    position: relative;
    border-radius: 6px;
    overflow: hidden;
    height: 520px;
    background: #070714;
  }
  #__COMPONENT_ID__-viewport canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }
  #__COMPONENT_ID__-label-layer {
    position: absolute;
    top: 0; left: 0;
    width: 100%; height: 100%;
    pointer-events: none;
    overflow: hidden;
  }
  #__COMPONENT_ID__-label-layer div {
    pointer-events: none;
  }
  #__COMPONENT_ID__-prof-wrap {
    margin-top: 10px;
    border-radius: 6px;
    overflow: hidden;
    height: 200px;
    background: #070714;
  }
  #__COMPONENT_ID__-prof-wrap canvas {
    display: block;
    width: 100% !important;
    height: 100% !important;
  }
  .__COMPONENT_ID__-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 10px;
    flex-wrap: wrap;
  }
  .__COMPONENT_ID__-controls button {
    background: linear-gradient(135deg,#00d2ff,#3a7bd5);
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
    background: #333;
    border-radius: 2px;
    outline: none;
    cursor: pointer;
    margin: 0;
  }
  .__COMPONENT_ID__-controls input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 12px; height: 12px;
    border-radius: 50%;
    background: #00d2ff;
    cursor: pointer;
  }
  .__COMPONENT_ID__-controls label {
    font-size: 12px;
    color: #999;
    white-space: nowrap;
  }
  .__COMPONENT_ID__-controls .val {
    font-size: 12px;
    color: #888;
    font-family: 'SF Mono',Monaco,monospace;
    min-width: 32px;
  }
  .__COMPONENT_ID__-controls .time {
    font-family: 'SF Mono',Monaco,monospace;
    font-size: 13px;
    color: #888;
    margin-left: auto;
  }
  .__COMPONENT_ID__-seek {
    flex: 1;
    min-width: 80px;
  }
  .nd-label {
    color: #fff;
    font-size: 9px;
    font-family: 'SF Mono',Monaco,monospace;
    background: rgba(0,0,0,0.55);
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
    border: 1px solid rgba(255,255,255,0.1);
    pointer-events: none;
    line-height: 1.3;
  }
</style>

<div id="__COMPONENT_ID__-wrap">
  <div id="__COMPONENT_ID__-header">
    <h3>3D Acoustic Manifold</h3>
    <span class="time" id="__COMPONENT_ID__-time">0:00 / 0:00</span>
  </div>

  <div id="__COMPONENT_ID__-viewport">
    <canvas id="__COMPONENT_ID__-three"></canvas>
    <div id="__COMPONENT_ID__-label-layer"></div>
  </div>

  <div id="__COMPONENT_ID__-prof-wrap">
    <canvas id="__COMPONENT_ID__-prof"></canvas>
  </div>

  <div class="__COMPONENT_ID__-controls">
    <button id="__COMPONENT_ID__-play">&#9654; Play</button>
    <input type="range" class="__COMPONENT_ID__-seek" id="__COMPONENT_ID__-seek" min="0" max="1000" value="0">
    <label>Vol</label>
    <input type="range" id="__COMPONENT_ID__-vol" min="0" max="100" value="75" style="width:64px">
    <span class="val" id="__COMPONENT_ID__-vol-val">75%</span>
    <label>Spd</label>
    <input type="range" id="__COMPONENT_ID__-speed" min="0.25" max="3" step="0.25" value="1" style="width:64px">
    <span class="val" id="__COMPONENT_ID__-speed-val">1x</span>
    <label>Orbit</label>
    <input type="range" id="__COMPONENT_ID__-orbit" min="0" max="5" step="0.1" value="1.8" style="width:64px">
    <span class="val" id="__COMPONENT_ID__-orbit-val">1.8</span>
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
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const DATA = __DATA_JSON__;
const id = '__COMPONENT_ID__';

const viewport = document.getElementById(id+'-viewport');
const threeCanvas = document.getElementById(id+'-three');
const labelLayer = document.getElementById(id+'-label-layer');
const profCanvas = document.getElementById(id+'-prof');
const playBtn = document.getElementById(id+'-play');
const seekBar = document.getElementById(id+'-seek');
const volSlider = document.getElementById(id+'-vol');
const volVal = document.getElementById(id+'-vol-val');
const speedSlider = document.getElementById(id+'-speed');
const speedVal = document.getElementById(id+'-speed-val');
const orbitSlider = document.getElementById(id+'-orbit');
const orbitVal = document.getElementById(id+'-orbit-val');
const timeDisplay = document.getElementById(id+'-time');

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
camera.position.set(3.5, 2.5, 3.5);

const renderer = new THREE.WebGLRenderer({
  canvas: threeCanvas,
  antialias: true,
  alpha: false,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.setSize(viewport.clientWidth, viewport.clientHeight);

const labelRenderer = new CSS2DRenderer({
  element: labelLayer,
});
labelRenderer.setSize(viewport.clientWidth, viewport.clientHeight);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotate = true;
controls.autoRotateSpeed = 1.8;
controls.target.set(0, 0, 0.5);
controls.update();

// ----- lighting -----
const ambLight = new THREE.AmbientLight(0x404060, 0.6);
scene.add(ambLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(1, 2, 1);
scene.add(dirLight);

// ----- create sprite texture -----
function makeSpriteTexture() {
  const c = document.createElement('canvas');
  c.width = 64;
  c.height = 64;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.2, 'rgba(255,255,255,0.8)');
  g.addColorStop(0.6, 'rgba(255,255,255,0.3)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(c);
  tex.needsUpdate = true;
  return tex;
}
const dotTexture = makeSpriteTexture();

// ----- centroid color map: blue (low freq) -> cyan -> magenta -> red (high freq) -----
function centroidColor(t) {
  t = Math.max(0, Math.min(1, t));
  if (t < 0.33) {
    const u = t / 0.33;
    return [0, 0.4 + 0.6*u, 1];              // blue -> cyan
  } else if (t < 0.66) {
    const u = (t - 0.33) / 0.33;
    return [0.6*u, 0.6 + 0.4*u, 1 - u];       // cyan -> magenta
  } else {
    const u = (t - 0.66) / 0.34;
    return [0.6 + 0.4*u, 0.4*(1-u), 0.2*(1-u)]; // magenta -> red
  }
}

const points3d = DATA.points_3d;
const centroids = DATA.centroids;
const centroidMin = DATA.centroid_min;
const centroidRange = DATA.centroid_max - DATA.centroid_min || 1;
const n = points3d.length;

const sprites = [];
const labels = [];
const labelDivs = [];

for (let i = 0; i < n; i++) {
  const p = points3d[i];
  const cf = (centroids[i] - centroidMin) / centroidRange;
  const [r, g, b] = centroidColor(cf);

  const mat = new THREE.SpriteMaterial({
    map: dotTexture,
    color: new THREE.Color(r, g, b),
    transparent: true,
    opacity: 0,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  const sprite = new THREE.Sprite(mat);
  sprite.position.set(p[0], p[1], p[2]);
  sprite.scale.set(0, 0, 1);
  scene.add(sprite);
  sprites.push(sprite);

  // label div (hidden initially)
  const div = document.createElement('div');
  div.className = 'nd-label';
  const freqK = (centroids[i] / 1000).toFixed(1);
  div.textContent = freqK + ' kHz';
  div.style.display = 'none';
  const label = new CSS2DObject(div);
  label.position.set(p[0], p[1] + 0.08, p[2]);
  scene.add(label);
  labels.push(label);
  labelDivs.push(div);
}

// ----- axes -----
function addAxis(from, to, color, labelText) {
  const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0.4 });
  const geo = new THREE.BufferGeometry().setFromPoints([
    new THREE.Vector3(from[0], from[1], from[2]),
    new THREE.Vector3(to[0], to[1], to[2]),
  ]);
  scene.add(new THREE.Line(geo, mat));

  const div = document.createElement('div');
  div.textContent = labelText;
  div.style.color = '#fff';
  div.style.fontSize = '11px';
  div.style.fontWeight = '600';
  div.style.fontFamily = "'SF Mono',Monaco,monospace";
  div.style.textShadow = '0 0 6px rgba(0,0,0,0.8)';
  div.style.background = 'rgba(0,0,0,0.3)';
  div.style.padding = '1px 5px';
  div.style.borderRadius = '3px';
  div.style.pointerEvents = 'none';
  const labelObj = new CSS2DObject(div);
  labelObj.position.set(to[0], to[1], to[2]);
  scene.add(labelObj);
}

const axExt = 1.6;
addAxis([-axExt, 0, 0], [axExt, 0, 0], 0x00d2ff, 'PC1');
addAxis([0, -axExt, 0], [0, axExt, 0], 0x00d2ff, 'PC2');
addAxis([0, 0, -0.1], [0, 0, 1.1], 0x00d2ff, 'Time');

// grid helper
const gridHelper = new THREE.GridHelper(4, 8, 0x444488, 0x222244);
gridHelper.position.y = -axExt;
gridHelper.material.transparent = true;
gridHelper.material.opacity = 0.25;
scene.add(gridHelper);

// ----- centroid color legend (2D canvas overlay) -----
function buildLegend(container) {
  const legW = 120, legH = 10;
  const wrap = document.createElement('div');
  wrap.style.cssText = 'position:absolute;bottom:12px;right:12px;display:flex;flex-direction:column;align-items:flex-end;gap:2px;pointer-events:none;z-index:10';
  const labelLow = document.createElement('span');
  labelLow.textContent = (DATA.centroid_min/1000).toFixed(1)+' kHz';
  labelLow.style.cssText = 'color:#999;font-size:8px;font-family:monospace';
  const labelHigh = document.createElement('span');
  labelHigh.textContent = (DATA.centroid_max/1000).toFixed(1)+' kHz';
  labelHigh.style.cssText = 'color:#999;font-size:8px;font-family:monospace';
  const canvas = document.createElement('canvas');
  canvas.width = legW;
  canvas.height = legH;
  canvas.style.cssText = 'border-radius:3px;border:1px solid rgba(255,255,255,0.1)';
  const ctx = canvas.getContext('2d');
  for (let i = 0; i < legW; i++) {
    const t = i / legW;
    const [r, g, b] = centroidColor(t);
    ctx.fillStyle = `rgb(${(r*255)<<0},${(g*255)<<0},${(b*255)<<0})`;
    ctx.fillRect(i, 0, 1, legH);
  }
  const row = document.createElement('div');
  row.style.cssText = 'display:flex;align-items:center;gap:4px';
  row.appendChild(labelLow);
  row.appendChild(canvas);
  row.appendChild(labelHigh);
  wrap.appendChild(row);
  container.appendChild(wrap);
}
buildLegend(viewport);

// ----- 2D centroid-amplitude profile -----
const profW = profCanvas.parentElement.clientWidth;
const profH = profCanvas.parentElement.clientHeight;
let profWidth = profW;
let profHeight = profH;

function sizeProfCanvas() {
  const rect = profCanvas.parentElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  profWidth = rect.width;
  profHeight = rect.height;
  if (profCanvas.width !== Math.round(profWidth*dpr) || profCanvas.height !== Math.round(profHeight*dpr)) {
    profCanvas.width = Math.round(profWidth*dpr);
    profCanvas.height = Math.round(profHeight*dpr);
    profCanvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
  }
}

function drawProfile(currentTime) {
  const ctx = profCanvas.getContext('2d');
  const w = profWidth, h = profHeight;
  ctx.clearRect(0, 0, w, h);

  const cMin = DATA.centroid_min, cMax = DATA.centroid_max;
  const rMin = DATA.rms_min, rMax = DATA.rms_max;
  const cRange = cMax - cMin || 1;
  const rRange = rMax - rMin || 1;

  const pad = 48;
  const plotW = w - pad * 2;
  const plotH = h - pad * 2;

  function toX(c) { return pad + ((c - cMin) / cRange) * plotW; }
  function toY(r) { return pad + (1 - (r - rMin) / rRange) * plotH; }

  // grid
  ctx.strokeStyle = 'rgba(255,255,255,0.05)';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const gx = pad + (i/4)*plotW;
    ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, pad+plotH); ctx.stroke();
    const gy = pad + (i/4)*plotH;
    ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(pad+plotW, gy); ctx.stroke();
  }

  // axis labels
  ctx.fillStyle = 'rgba(255,255,255,0.3)';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText('Spectral Centroid (Hz)', w/2, h-14);
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  ctx.fillText('Amplitude', pad-8, h/2);

  // data points up to current time
  const progress = Math.min(Math.max(currentTime / DATA.duration, 0), 1);
  const drawIdx = Math.min(Math.floor(progress * n), n);

  for (let i = 0; i < drawIdx; i++) {
    const cx = toX(DATA.centroids[i]);
    const cy = toY(DATA.rms[i]);
    const recency = Math.pow((i + 1) / (drawIdx || 1), 2);
    const r = 1.5 + 2.5 * recency;
    const cf = (DATA.centroids[i] - cMin) / cRange;
    const [cr, cg, cb] = centroidColor(cf);
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI*2);
    ctx.fillStyle = `rgba(${(cr*255)<<0},${(cg*255)<<0},${(cb*255)<<0},${0.3 + 0.5*recency})`;
    ctx.fill();
  }

  // current frame highlight
  if (drawIdx > 0 && drawIdx <= n) {
    const i = drawIdx - 1;
    const hx = toX(DATA.centroids[i]);
    const hy = toY(DATA.rms[i]);
    const grad = ctx.createRadialGradient(hx, hy, 0, hx, hy, 16);
    grad.addColorStop(0, 'rgba(255,215,0,0.6)');
    grad.addColorStop(1, 'rgba(255,215,0,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(hx, hy, 16, 0, Math.PI*2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(hx, hy, 3, 0, Math.PI*2);
    ctx.fillStyle = '#ffd700';
    ctx.fill();
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
  const progress = Math.min(Math.max(t / DATA.duration, 0), 1);
  const drawCount = Math.min(Math.floor(progress * n), n);

  // update sprites
  for (let i = 0; i < n; i++) {
    const sprite = sprites[i];
    if (i < drawCount) {
      const recency = Math.pow((i + 1) / (drawCount || 1), 2);
      const scale = 0.04 + 0.12 * recency;
      sprite.scale.set(scale, scale, 1);
      sprite.material.opacity = 0.25 + 0.6 * recency;
      sprite.visible = true;
    } else {
      sprite.scale.set(0, 0, 1);
      sprite.visible = false;
    }
  }

  // update labels (last 8 nodes)
  const labelStart = Math.max(0, Math.min(drawCount - 8, n - 8));
  const labelEnd = Math.min(drawCount, n);
  for (let i = 0; i < n; i++) {
    if (i >= labelStart && i < labelEnd) {
      labelDivs[i].style.display = 'block';
      labels[i].visible = true;
    } else {
      labelDivs[i].style.display = 'none';
      labels[i].visible = false;
    }
  }

  controls.update();

  // Resize if needed
  const vpW = viewport.clientWidth;
  const vpH = viewport.clientHeight;
  if (renderer.domElement.width !== Math.round(vpW * window.devicePixelRatio) ||
      renderer.domElement.height !== Math.round(vpH * window.devicePixelRatio)) {
    camera.aspect = vpW / vpH;
    camera.updateProjectionMatrix();
    renderer.setSize(vpW, vpH);
    labelRenderer.setSize(vpW, vpH);
  }

  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);

  // profile
  sizeProfCanvas();
  drawProfile(t);

  // UI
  const total = DATA.duration;
  const mins = Math.floor(t/60);
  const secs = Math.floor(t%60);
  const tMins = Math.floor(total/60);
  const tSecs = Math.floor(total%60);
  timeDisplay.textContent = mins + ':' + secs.toString().padStart(2,'0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2,'0');
  seekBar.value = total > 0 ? (t/total)*1000 : 0;

  if (isPlaying && t >= DATA.duration) {
    isPlaying = false;
    pausedAt = DATA.duration;
    playBtn.innerHTML = '&#9654; Play';
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
  orbitVal.textContent = v.toFixed(1);
  controls.autoRotateSpeed = v;
});

// ----- init -----
initAudio();
setTimeout(() => animate(), 100);

window.addEventListener('resize', () => {
  clearTimeout(window._r3dResize);
  window._r3dResize = setTimeout(() => animate(), 100);
});
</script>
"""
