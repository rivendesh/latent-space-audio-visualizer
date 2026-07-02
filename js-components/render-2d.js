let audioCtx = null;
let audioBuffer = null;
let source = null;
let gainNode = null;
let isPlaying = false;
let startTime = 0;
let pausedAt = 0;
let currentSpeed = 1.0;
let currentVol = 0.75;
let loopEnabled = false;

let fadeExp = 2.0;
let trailLen = 15;
let zoomLevel = 1.0;

const LATENT_H = 380;
const WAVE_H = 120;
const TOTAL_H = LATENT_H + WAVE_H;

let _bounds;

let playBtn, loopBtn, seekSlider, timeDisplay;
let volSlider, volVal, speedSlider, speedVal;
let fadeSlider, fadeVal, trailSlider, trailVal, zoomSlider, zoomVal;

function base64ToArrayBuffer(b64) {
  var bin = atob(b64);
  var buf = new ArrayBuffer(bin.length);
  var view = new Uint8Array(buf);
  for (var i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
  return buf;
}

function initAudio() {
  if (audioCtx) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  gainNode = audioCtx.createGain();
  gainNode.gain.value = currentVol;
  gainNode.connect(audioCtx.destination);
  var buf = base64ToArrayBuffer(DATA.audio_b64);
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
  var s = audioCtx.createBufferSource();
  s.buffer = audioBuffer;
  s.playbackRate.setValueAtTime(currentSpeed, audioCtx.currentTime);
  s.loop = loopEnabled;
  s.connect(gainNode);
  return s;
}

function setup() {
  var container = document.getElementById(ID + '-p5-container');
  var w = container ? container.clientWidth : windowWidth;
  createCanvas(w, TOTAL_H);
  pixelDensity(1);

  var p = DATA.latent_path;
  var n = p.length;
  var xMin = Infinity, xMax = -Infinity, yMin = Infinity, yMax = -Infinity;
  for (var pi = 0; pi < n; pi++) {
    if (p[pi][0] < xMin) xMin = p[pi][0];
    if (p[pi][0] > xMax) xMax = p[pi][0];
    if (p[pi][1] < yMin) yMin = p[pi][1];
    if (p[pi][1] > yMax) yMax = p[pi][1];
  }
  _bounds = { xMin: xMin, xMax: xMax, yMin: yMin, yMax: yMax };

  playBtn = document.getElementById(ID + '-play');
  loopBtn = document.getElementById(ID + '-loop');
  seekSlider = document.getElementById(ID + '-seek');
  timeDisplay = document.getElementById(ID + '-time');
  volSlider = document.getElementById(ID + '-vol');
  volVal = document.getElementById(ID + '-vol-val');
  speedSlider = document.getElementById(ID + '-speed');
  speedVal = document.getElementById(ID + '-speed-val');
  fadeSlider = document.getElementById(ID + '-fade');
  fadeVal = document.getElementById(ID + '-fade-val');
  trailSlider = document.getElementById(ID + '-trail');
  trailVal = document.getElementById(ID + '-trail-val');
  zoomSlider = document.getElementById(ID + '-zoom');
  zoomVal = document.getElementById(ID + '-zoom-val');

  playBtn.addEventListener('click', togglePlay);
  loopBtn.addEventListener('click', toggleLoop);
  seekSlider.addEventListener('input', onSeek);
  volSlider.addEventListener('input', onVolChange);
  speedSlider.addEventListener('input', onSpeedChange);
  fadeSlider.addEventListener('input', onFadeChange);
  trailSlider.addEventListener('input', onTrailChange);
  zoomSlider.addEventListener('input', onZoomChange);
  document.addEventListener('keydown', onKey);
}

function draw() {
  var t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;

  if (isPlaying && t >= DATA.duration) {
    if (loopEnabled) {
      pausedAt = 0;
      if (source) { source.stop(); source.disconnect(); source = null; }
      loopPlay();
    } else {
      isPlaying = false;
      pausedAt = DATA.duration;
      playBtn.innerHTML = '&#9654;';
      return;
    }
  }

  background(10, 10, 26);

  push();
  clip(0, 0, width, LATENT_H);
  drawLatent(t);
  noClip();
  pop();

  stroke(255, 255, 255, 10);
  strokeWeight(1);
  line(0, LATENT_H, width, LATENT_H);

  push();
  translate(0, LATENT_H);
  clip(0, 0, width, WAVE_H);
  drawWaveform(t);
  noClip();
  pop();

  updateUI(t);
}

function loopPlay() {
  source = createSource();
  source.start(0, 0);
  startTime = audioCtx.currentTime;
  isPlaying = true;
}

function getLatentPos(time) {
  var times = DATA.latent_times;
  var path = DATA.latent_path;
  var n = times.length;
  if (n === 0) return [0, 0];
  if (time <= times[0]) return path[0];
  if (time >= times[n - 1]) return path[n - 1];
  var lo = 0, hi = n - 1;
  while (lo < hi - 1) {
    var mid = (lo + hi) >> 1;
    if (times[mid] <= time) lo = mid;
    else hi = mid;
  }
  var t = (time - times[lo]) / (times[hi] - times[lo] + 1e-10);
  return [
    path[lo][0] + t * (path[hi][0] - path[lo][0]),
    path[lo][1] + t * (path[hi][1] - path[lo][1])
  ];
}

var C_START = [0, 210, 255];
var C_MID = [123, 47, 247];
var C_END = [255, 107, 107];

function pathColor(t) {
  if (t < 0.5) {
    var tt = t * 2;
    return [C_START[0] + (C_MID[0] - C_START[0]) * tt, C_START[1] + (C_MID[1] - C_START[1]) * tt, C_START[2] + (C_MID[2] - C_START[2]) * tt];
  }
  var tt = (t - 0.5) * 2;
  return [C_MID[0] + (C_END[0] - C_MID[0]) * tt, C_MID[1] + (C_END[1] - C_MID[1]) * tt, C_MID[2] + (C_END[2] - C_MID[2]) * tt];
}

function drawLatent(curTime) {
  var w = width;
  var h = LATENT_H;
  var path = DATA.latent_path;
  var n = path.length;
  if (n < 2) return;

  var xMin = _bounds.xMin, xMax = _bounds.xMax;
  var yMin = _bounds.yMin, yMax = _bounds.yMax;
  var pad = 0.04;
  var xRange = (xMax - xMin) || 1;
  var yRange = (yMax - yMin) || 1;
  var xMid = (xMin + xMax) / 2;
  var yMid = (yMin + yMax) / 2;
  var xScale = w / (xRange * (1 + pad * 2));
  var yScale = h / (yRange * (1 + pad * 2));
  var scale = Math.min(xScale, yScale) * zoomLevel;
  var vw = xRange * (1 + pad * 2) * scale;
  var vh = yRange * (1 + pad * 2) * scale;
  var ox = (w - vw) / 2;
  var oy = (h - vh) / 2;

  function toScreen(px, py) {
    return [
      ox + (px - (xMid - xRange * (1 + pad * 2) / 2)) * scale,
      oy + ((yMid + yRange * (1 + pad * 2) / 2) - py) * scale
    ];
  }

  noFill();
  stroke(255, 255, 255, 10);
  strokeWeight(1);
  var steps = 6;
  for (var gi = 1; gi < steps; gi++) {
    var gx = (gi / steps) * w;
    line(gx, 0, gx, h);
    var gy = (gi / steps) * h;
    line(0, gy, w, gy);
  }

  fill(255, 255, 255, 50);
  noStroke();
  textAlign(CENTER, TOP);
  textSize(10);
  text('PC1', w / 2, h - 12);
  textAlign(RIGHT, CENTER);
  text('PC2', w - 6, h / 2);

  var zs = toScreen(0, 0);
  fill(255, 255, 255, 20);
  noStroke();
  circle(zs[0], zs[1], 6);

  fill(255, 255, 255, 38);
  textAlign(RIGHT, TOP);
  textSize(9);
  text('start', w - 8, 8);
  textAlign(RIGHT, BOTTOM);
  text('end', w - 8, h - 8);

  var legX = w - 100, legY = 16, legW = 80, legH = 8;
  noStroke();
  for (var li = 0; li < legW; li++) {
    var lt = li / legW;
    var lc = pathColor(lt);
    fill(lc[0], lc[1], lc[2], 150);
    rect(legX + li, legY, 1, legH);
  }
  noFill();
  stroke(255, 255, 255, 25);
  strokeWeight(1);
  rect(legX, legY, legW, legH);

  var progress = Math.min(Math.max(curTime / DATA.duration, 0), 1);
  var drawCount = Math.min(Math.floor(progress * (n - 1)), n - 1);

  noFill();
  for (var i = 0; i < drawCount; i++) {
    var s1 = toScreen(path[i][0], path[i][1]);
    var s2 = toScreen(path[i + 1][0], path[i + 1][1]);
    var t = i / (n - 1);
    var col = pathColor(t);
    var recency = Math.pow((i + 1) / (drawCount || 1), fadeExp);
    var segW = 1 + 2 * recency;
    var segA = 50 + 153 * recency;
    stroke(col[0], col[1], col[2], segA);
    strokeWeight(segW);
    line(s1[0], s1[1], s2[0], s2[1]);
  }

  var pointCount = Math.min(drawCount + 1, n);
  noStroke();
  for (var i = 0; i < pointCount; i++) {
    var ps = toScreen(path[i][0], path[i][1]);
    var t = i / (n - 1);
    var col = pathColor(t);
    var recency = Math.pow((i + 1) / (pointCount || 1), fadeExp);
    var dotR = 1 + 2.5 * recency;
    fill(col[0], col[1], col[2], 90 + 115 * recency);
    circle(ps[0], ps[1], dotR * 2);
  }

  var cs = toScreen.apply(null, getLatentPos(curTime));

  noStroke();
  for (var glowR = 28; glowR > 0; glowR -= 4) {
    var alpha = map(glowR, 0, 28, 0, 180);
    fill(255, 215, 0, alpha);
    circle(cs[0], cs[1], glowR * 2);
  }
  noFill();
  stroke(255, 215, 0, 90);
  strokeWeight(2);
  circle(cs[0], cs[1], 14);
  noStroke();
  fill(255, 215, 0);
  circle(cs[0], cs[1], 7);

  var curIdx = Math.floor(progress * (n - 1));
  noStroke();
  for (var i = 1; i <= trailLen; i++) {
    var idx = Math.max(0, curIdx - i);
    var tFrac = 1 - i / trailLen;
    var ts = toScreen(path[idx][0], path[idx][1]);
    fill(0, 210, 255, tFrac * 128);
    circle(ts[0], ts[1], 4 * tFrac);
  }
}

function drawWaveform(curTime) {
  var w = width;
  var h = WAVE_H;
  var peaks = DATA.waveform_peaks;
  var n = peaks.length;
  var dur = DATA.duration;

  noFill();
  stroke(255, 255, 255, 10);
  strokeWeight(1);
  for (var y = 0.5; y < h; y += h / 4) {
    line(0, y, w, y);
  }
  stroke(255, 255, 255, 20);
  line(0, h * 0.5, w, h * 0.5);

  fill(255, 255, 255, 38);
  noStroke();
  textAlign(CENTER, TOP);
  textSize(9);
  for (var tm = 0; tm <= dur; tm += Math.max(1, Math.round(dur / 6))) {
    var x = (tm / dur) * w;
    text(tm + 's', x, h - 11);
    stroke(255, 255, 255, 10);
    line(x, 0, x, h);
  }

  noStroke();
  fill(0, 210, 255, 25);
  beginShape();
  vertex(0, h * 0.5);
  for (var i = 0; i < n; i++) {
    vertex((i / n) * w, h * 0.5 + peaks[i][0] * h * 0.42);
  }
  for (var i = n - 1; i >= 0; i--) {
    vertex((i / n) * w, h * 0.5 + peaks[i][1] * h * 0.42);
  }
  endShape(CLOSE);

  var cursorFrac = dur > 0 ? Math.min(curTime / dur, 1) : 0;
  if (cursorFrac > 0.01) {
    fill(0, 210, 255, 64);
    beginShape();
    vertex(0, h * 0.5);
    for (var i = 0; i < n; i++) {
      var cx = (i / n) * w;
      if (cx > cursorFrac * w) break;
      vertex(cx, h * 0.5 + peaks[i][0] * h * 0.42);
    }
    for (var i = n - 1; i >= 0; i--) {
      var cx = (i / n) * w;
      if (cx > cursorFrac * w) break;
      vertex(cx, h * 0.5 + peaks[i][1] * h * 0.42);
    }
    endShape(CLOSE);
  }

  if (cursorFrac > 0 && cursorFrac < 1) {
    var cursorX = cursorFrac * w;
    stroke(255, 255, 255, 200);
    strokeWeight(2);
    line(cursorX, 0, cursorX, h);
  }
}

function updateUI(curTime) {
  var total = DATA.duration;
  var mins = Math.floor(curTime / 60);
  var secs = Math.floor(curTime % 60);
  var tMins = Math.floor(total / 60);
  var tSecs = Math.floor(total % 60);
  timeDisplay.textContent = mins + ':' + secs.toString().padStart(2, '0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2, '0');
  seekSlider.value = total > 0 ? (curTime / total) * 1000 : 0;
}

function togglePlay() {
  initAudio();
  if (!audioBuffer) return;
  if (audioCtx.state === 'suspended') audioCtx.resume();

  if (isPlaying) {
    pausedAt += audioCtx.currentTime - startTime;
    if (source) { source.stop(); source.disconnect(); source = null; }
    isPlaying = false;
    playBtn.innerHTML = '&#9654;';
  } else {
    if (pausedAt >= DATA.duration) pausedAt = 0;
    source = createSource();
    source.start(0, pausedAt);
    startTime = audioCtx.currentTime;
    isPlaying = true;
    playBtn.innerHTML = '&#9208;';
  }
}

function toggleLoop() {
  loopEnabled = !loopEnabled;
  loopBtn.style.opacity = loopEnabled ? '1' : '0.4';
  loopBtn.style.background = loopEnabled ? 'linear-gradient(135deg,#ffd700,#ff8c00)' : 'linear-gradient(135deg,#00d2ff,#3a7bd5)';
}

function onSeek() {
  var time = (parseFloat(this.value) / 1000) * DATA.duration;
  pausedAt = time;
  if (isPlaying) {
    if (source) { source.stop(); source.disconnect(); }
    source = createSource();
    source.start(0, pausedAt);
    startTime = audioCtx.currentTime;
  }
}

function onVolChange() {
  currentVol = parseFloat(this.value) / 100;
  volVal.textContent = Math.round(currentVol * 100) + '%';
  if (gainNode) {
    gainNode.gain.setValueAtTime(currentVol, audioCtx.currentTime);
  }
}

function onSpeedChange() {
  currentSpeed = parseFloat(this.value);
  speedVal.textContent = currentSpeed + 'x';
  if (source) {
    source.playbackRate.setValueAtTime(currentSpeed, audioCtx.currentTime);
  }
}

function onFadeChange() {
  fadeExp = parseFloat(this.value) / 10;
  fadeVal.textContent = fadeExp.toFixed(1);
}

function onTrailChange() {
  trailLen = parseInt(this.value);
  trailVal.textContent = trailLen;
}

function onZoomChange() {
  zoomLevel = parseInt(this.value) / 10;
  zoomVal.textContent = zoomLevel.toFixed(1);
}

function onKey(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') return;
  switch (e.code) {
    case 'Space': e.preventDefault(); togglePlay(); break;
    case 'ArrowLeft': {
      var t = Math.max(0, getCurrentTime() - 5); pausedAt = t;
      if (isPlaying) { if (source) { source.stop(); source.disconnect(); } source = createSource(); source.start(0, t); startTime = audioCtx.currentTime; }
      break;
    }
    case 'ArrowRight': {
      var t = Math.min(DATA.duration, getCurrentTime() + 5); pausedAt = t;
      if (isPlaying) { if (source) { source.stop(); source.disconnect(); } source = createSource(); source.start(0, t); startTime = audioCtx.currentTime; }
      break;
    }
    case 'ArrowUp': volSlider.value = Math.min(100, parseInt(volSlider.value) + 5); volSlider.dispatchEvent(new Event('input')); break;
    case 'ArrowDown': volSlider.value = Math.max(0, parseInt(volSlider.value) - 5); volSlider.dispatchEvent(new Event('input')); break;
  }
}

function windowResized() {
  var container = document.getElementById(ID + '-p5-container');
  var w = container ? container.clientWidth : windowWidth;
  resizeCanvas(w, TOTAL_H);
}
