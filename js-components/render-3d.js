import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const DATA = window.DATA;
const id = window.__ID__;

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
let panMode = 'midpoint';
let fadeExp = 3.0;
let loopEnabled = false;
const loopBtn = document.getElementById(id+'-loop');

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
controls.target.set(0, 0, 0);
controls.update();

const dataGroup = new THREE.Group();
scene.add(dataGroup);
dataGroup.scale.z = 3.5;

const ambLight = new THREE.AmbientLight(0x404060, 0.6);
scene.add(ambLight);
const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
dirLight.position.set(1, 2, 1);
scene.add(dirLight);

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

var C_START = [0, 210, 255];
var C_MID = [123, 47, 247];
var C_END = [255, 107, 107];

function lerpColor(a, b, t) {
  return [a[0] + (b[0]-a[0])*t, a[1] + (b[1]-a[1])*t, a[2] + (b[2]-a[2])*t];
}
function pathColor(t) {
  if (t < 0.5) return lerpColor(C_START, C_MID, t * 2);
  return lerpColor(C_MID, C_END, (t - 0.5) * 2);
}

const points3d = DATA.points_3d;
const centroids = DATA.centroids;
const n = points3d.length;
var n1 = Math.max(1, n - 1);

const prefX = new Array(n);
const prefY = new Array(n);
const prefZ = new Array(n);
let sx = 0, sy = 0, sz = 0;
for (let i = 0; i < n; i++) {
  sx += points3d[i][0];
  sy += points3d[i][1];
  sz += points3d[i][2];
  prefX[i] = sx;
  prefY[i] = sy;
  prefZ[i] = sz;
}

const posArr = new Float32Array(n * 3);
const colArr = new Float32Array(n * 3);
const sizeArr = new Float32Array(n);
const alphaArr = new Float32Array(n);
const cMin = DATA.centroid_min, cMax = DATA.centroid_max, cRange = cMax - cMin || 1;
const nCent = DATA.centroids.length;
for (let i = 0; i < n; i++) {
  const p = points3d[i];
  const ci = Math.min(i, nCent - 1);
  const cent = (DATA.centroids[ci] - cMin) / cRange;
  const [r, g, b] = pathColor(cent);
  posArr[i*3] = p[0];
  posArr[i*3+1] = p[1];
  posArr[i*3+2] = p[2];
  colArr[i*3] = r / 255;
  colArr[i*3+1] = g / 255;
  colArr[i*3+2] = b / 255;
}

const pointGeo = new THREE.BufferGeometry();
pointGeo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
pointGeo.setAttribute('customColor', new THREE.BufferAttribute(colArr, 3));
pointGeo.setAttribute('pointSize', new THREE.BufferAttribute(sizeArr, 1));
pointGeo.setAttribute('pointAlpha', new THREE.BufferAttribute(alphaArr, 1));
pointGeo.setDrawRange(0, 0);

const pointMat = new THREE.ShaderMaterial({
  uniforms: {
    pointTexture: { value: dotTexture },
  },
  vertexShader: [
    'attribute float pointSize;',
    'attribute float pointAlpha;',
    'attribute vec3 customColor;',
    'varying vec3 vColor;',
    'varying float vAlpha;',
    'void main() {',
    '  vColor = customColor;',
    '  vAlpha = pointAlpha;',
    '  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);',
    '  gl_PointSize = pointSize * (300.0 / -mvPosition.z);',
    '  gl_Position = projectionMatrix * mvPosition;',
    '}',
  ].join('\n'),
  fragmentShader: [
    'uniform sampler2D pointTexture;',
    'varying vec3 vColor;',
    'varying float vAlpha;',
    'void main() {',
    '  vec4 tex = texture2D(pointTexture, gl_PointCoord);',
    '  gl_FragColor = vec4(vColor, tex.a * vAlpha);',
    '}',
  ].join('\n'),
  transparent: true,
  depthWrite: false,
  blending: THREE.AdditiveBlending,
});
const points = new THREE.Points(pointGeo, pointMat);
dataGroup.add(points);

const linePos = new Float32Array(n * 3);
for (let i = 0; i < n; i++) {
  linePos[i*3] = points3d[i][0];
  linePos[i*3+1] = points3d[i][1];
  linePos[i*3+2] = points3d[i][2];
}
const lineGeo = new THREE.BufferGeometry();
lineGeo.setAttribute('position', new THREE.BufferAttribute(linePos, 3));
lineGeo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(colArr), 3));
lineGeo.setDrawRange(0, 0);
const lineMat = new THREE.LineBasicMaterial({
  vertexColors: true,
  transparent: true,
  opacity: 0.4,
});
const line = new THREE.Line(lineGeo, lineMat);
dataGroup.add(line);

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

const gridHelper = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridHelper.position.y = -axExt;
gridHelper.material.transparent = true;
gridHelper.material.opacity = 0.55;
scene.add(gridHelper);

const gridSide = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridSide.position.x = -axExt;
gridSide.rotation.z = Math.PI / 2;
gridSide.material.transparent = true;
gridSide.material.opacity = 0.3;
scene.add(gridSide);

const gridBack = new THREE.GridHelper(8, 16, 0x6666aa, 0x444477);
gridBack.position.z = 0;
gridBack.rotation.x = Math.PI / 2;
gridBack.material.transparent = true;
gridBack.material.opacity = 0.3;
scene.add(gridBack);

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

function buildLegend() {
  const ctx = legendBar.getContext('2d');
  for (var i = 0; i < legendBar.width; i++) {
    var t = i / legendBar.width;
    var [r, g, b] = pathColor(t);
    ctx.fillStyle = 'rgb(' + ((r)<<0) + ',' + ((g)<<0) + ',' + ((b)<<0) + ')';
    ctx.fillRect(i, 0, 1, legendBar.height);
  }
  legendLow.textContent = (DATA.centroid_min / 1000).toFixed(1) + ' kHz';
  legendHigh.textContent = (DATA.centroid_max / 1000).toFixed(1) + ' kHz';
}
buildLegend();

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

  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  for (var y = 0.5; y < h; y += h/4) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }

  ctx.font = '9px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (var tm = 0; tm <= dur; tm += Math.max(1, Math.round(dur/6))) {
    var x = (tm / dur) * w;
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    ctx.fillText(tm + 's', x, h - 11);
  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }

  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath(); ctx.moveTo(0, h*0.5); ctx.lineTo(w, h*0.5); ctx.stroke();

  ctx.beginPath();
  ctx.moveTo(0, h*0.5);
  for (var i=0; i<n; i++) {
    ctx.lineTo((i/n)*w, h*0.5 + peaks[i][0] * h*0.42);
  }
  for (var i=n-1; i>=0; i--) {
    ctx.lineTo((i/n)*w, h*0.5 + peaks[i][1] * h*0.42);
  }
  ctx.closePath();
  ctx.fillStyle = 'rgba(0,210,255,0.1)';
  ctx.fill();

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
    ctx.fillStyle = 'rgba(0,210,255,0.25)';
    ctx.fill();
    ctx.restore();

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

  var gridCol = 'rgba(255,255,255,0.05)';
  var textCol = 'rgba(255,255,255,0.3)';

  ctx.strokeStyle = gridCol;
  ctx.lineWidth = 1;
  for (var i = 0; i <= 4; i++) {
    var gx = pad + (i/4)*plotW;
    ctx.beginPath(); ctx.moveTo(gx, pad); ctx.lineTo(gx, pad+plotH); ctx.stroke();
    var gy = pad + (i/4)*plotH;
    ctx.beginPath(); ctx.moveTo(pad, gy); ctx.lineTo(pad+plotW, gy); ctx.stroke();
  }

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

  var cMin = DATA.centroid_min, cMax = DATA.centroid_max, cRange = cMax - cMin || 1;
  for (var i = 0; i < n; i++) {
    var cx = toX(DATA.centroids[i]);
    var cy = toY(DATA.rms[i]);
    var col = pathColor((DATA.centroids[i] - cMin) / cRange);
    ctx.beginPath();
    ctx.arc(cx, cy, 2, 0, Math.PI*2);
    ctx.fillStyle = 'rgba(' + (col[0]<<0) + ',' + (col[1]<<0) + ',' + (col[2]<<0) + ',0.5)';
    ctx.fill();
  }

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
      playBtn.innerHTML = '&#9654;';
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
  playBtn.innerHTML = '&#9208;';
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
  playBtn.innerHTML = '&#9654;';
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

function animate() {
  const t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;

  const progress = Math.min(Math.max(t / DATA.duration, 0), 1);
  const drawCount = Math.min(Math.floor(progress * n), n);

  pointGeo.setDrawRange(0, drawCount);

  for (var i = 0; i < drawCount; i++) {
    var recency = Math.pow((i + 1) / (drawCount || 1), fadeExp);
    sizeArr[i] = 0.06 + 0.4 * recency;
    alphaArr[i] = 0.3 + 0.7 * recency;
  }
  for (var i = drawCount; i < n; i++) {
    sizeArr[i] = 0;
    alphaArr[i] = 0;
  }
  pointGeo.attributes.pointSize.needsUpdate = true;
  pointGeo.attributes.pointAlpha.needsUpdate = true;

  lineGeo.setDrawRange(0, Math.max(0, drawCount - 1));

  if (drawCount > 0 && panMode === 'midpoint') {
    var tx = prefX[drawCount - 1] / drawCount;
    var ty = prefY[drawCount - 1] / drawCount;
    var tz = prefZ[drawCount - 1] / drawCount;
    tz *= dataGroup.scale.z;
    controls.target.x += (tx - controls.target.x) * 0.12;
    controls.target.y += (ty - controls.target.y) * 0.12;
    controls.target.z += (tz - controls.target.z) * 0.12;
  }
  controls.update();

  renderer.render(scene, camera);

  drawWaveform(t);
  drawProfile(t);

  const total = DATA.duration;
  const mins = Math.floor(t/60);
  const secs = Math.floor(t%60);
  const tMins = Math.floor(total/60);
  const tSecs = Math.floor(total%60);
  timeDisplay.textContent = mins + ':' + secs.toString().padStart(2,'0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2,'0');
  seekBar.value = total > 0 ? (t/total)*1000 : 0;

  if (t >= DATA.duration) {
    if (loopEnabled) {
      pausedAt = 0;
      if (isPlaying) {
        if (source) { source.stop(); source.disconnect(); source = null; }
        source = createSource();
        source.start(0, 0);
        startTime = audioCtx.currentTime;
      }
    } else {
      if (isPlaying) {
        isPlaying = false;
        playBtn.innerHTML = '&#9654;';
      }
      pausedAt = DATA.duration;
    }
  }
  animId = requestAnimationFrame(animate);
}

playBtn.addEventListener('click', togglePlay);

loopBtn.addEventListener('click', function() {
  loopEnabled = !loopEnabled;
  loopBtn.style.opacity = loopEnabled ? '1' : '0.4';
  loopBtn.style.background = loopEnabled ? 'linear-gradient(135deg,#ffd700,#ff8c00)' : 'linear-gradient(135deg,#00d2ff,#3a7bd5)';
});

document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  switch (e.code) {
    case 'Space': e.preventDefault(); togglePlay(); break;
    case 'ArrowLeft': seek(Math.max(0, pausedAt - 5)); break;
    case 'ArrowRight': seek(Math.min(DATA.duration, pausedAt + 5)); break;
    case 'ArrowUp': volSlider.value = Math.min(100, parseInt(volSlider.value) + 5); volSlider.dispatchEvent(new Event('input')); break;
    case 'ArrowDown': volSlider.value = Math.max(0, parseInt(volSlider.value) - 5); volSlider.dispatchEvent(new Event('input')); break;
  }
});

seekBar.addEventListener('input', function() {
  const time = (parseFloat(this.value) / 1000) * DATA.duration;
  pausedAt = time;
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

const panSelect = document.getElementById(id+'-pan-mode');
panSelect.addEventListener('change', function() {
  panMode = this.value;
});

const fadeSlider = document.getElementById(id+'-fade');
const fadeVal = document.getElementById(id+'-fade-val');
fadeSlider.addEventListener('input', function() {
  const v = parseFloat(this.value);
  fadeExp = v / 10;
  fadeVal.textContent = fadeExp.toFixed(1);
});

const fsBtn = document.getElementById(id+'-fs-btn');
fsBtn.addEventListener('click', function() {
  if (!document.fullscreenElement) {
    viewport.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
});
function onFsChange() {
  const isFs = !!document.fullscreenElement;
  fsBtn.textContent = isFs ? '✕' : '⛶';
  if (!isFs && viewport) {
    requestAnimationFrame(function() {
      var w = viewport.clientWidth, h = viewport.clientHeight;
      if (w > 0 && h > 0) {
        renderer.setSize(w, h);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }
    });
  }
}
document.addEventListener('fullscreenchange', onFsChange);
document.addEventListener('webkitfullscreenchange', onFsChange);
document.addEventListener('mozfullscreenchange', onFsChange);

initAudio();
animate();

function resizeRenderer() {
  var w = viewport.clientWidth, h = viewport.clientHeight;
  if (w > 0 && h > 0) {
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  }
}
const ro = new ResizeObserver(resizeRenderer);
ro.observe(viewport);
