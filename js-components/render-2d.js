var latentCanvas = document.getElementById(id+'-latent');
var waveCanvas = document.getElementById(id+'-wave');
var playBtn = document.getElementById(id+'-play');
var seekBar = document.getElementById(id+'-seek');
var volSlider = document.getElementById(id+'-vol');
var volVal = document.getElementById(id+'-vol-val');
var speedSlider = document.getElementById(id+'-speed');
var speedVal = document.getElementById(id+'-speed-val');
var timeDisplay = document.getElementById(id+'-time');

var audioCtx = null;
var audioBuffer = null;
var source = null;
var gainNode = null;
var isPlaying = false;
var startTime = 0;
var pausedAt = 0;
var animId = null;
var currentSpeed = 1.0;
var currentVol = 0.75;
var sourceGen = 0;
var fadeExp = 2.0;
var trailLen = 15;
var zoomLevel = 1.0;
var loopEnabled = false;
var loopBtn = document.getElementById(id+'-loop');

function sizeCanvas(canvas) {
  var rect = canvas.getBoundingClientRect();
  var dpr = window.devicePixelRatio || 1;
  var w = rect.width;
  var h = rect.height;
  if (canvas.width !== Math.round(w*dpr) || canvas.height !== Math.round(h*dpr)) {
    canvas.width = Math.round(w*dpr);
    canvas.height = Math.round(h*dpr);
    canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
  }
  return {w: w, h: h};
}

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
  sourceGen++;
  var s = audioCtx.createBufferSource();
  s.buffer = audioBuffer;
  s.playbackRate.setValueAtTime(currentSpeed, audioCtx.currentTime);
  s.connect(gainNode);
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

  if (!animId) tick();
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

function getLatentPos(time) {
  var times = DATA.latent_times;
  var path = DATA.latent_path;
  var n = times.length;
  if (n === 0) return [0,0];
  if (time <= times[0]) return path[0];
  if (time >= times[n-1]) return path[n-1];
  var lo = 0, hi = n-1;
  while (lo < hi-1) {
    var mid = (lo+hi)>>1;
    if (times[mid] <= time) lo = mid;
    else hi = mid;
  }
  var t = (time - times[lo]) / (times[hi] - times[lo] + 1e-10);
  return [
    path[lo][0] + t * (path[hi][0] - path[lo][0]),
    path[lo][1] + t * (path[hi][1] - path[lo][1])
  ];
}

function lerpColor(a, b, t) {
  return [
    a[0] + (b[0]-a[0])*t,
    a[1] + (b[1]-a[1])*t,
    a[2] + (b[2]-a[2])*t
  ];
}

function rgba(c, a) {
  return 'rgba(' + (c[0]<<0) + ',' + (c[1]<<0) + ',' + (c[2]<<0) + ',' + a + ')';
}

var C_START = [0, 210, 255];
var C_MID   = [123, 47, 247];
var C_END   = [255, 107, 107];

function pathColor(t) {
  if (t < 0.5) return lerpColor(C_START, C_MID, t*2);
  return lerpColor(C_MID, C_END, (t-0.5)*2);
}

function drawWaveform(ctx, w, h, currentTime) {
  ctx.clearRect(0,0,w,h);

  var peaks = DATA.waveform_peaks;
  var n = peaks.length;
  var dur = DATA.duration;

  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  ctx.font = '9px sans-serif';
  ctx.fillStyle = 'rgba(255,255,255,0.15)';
  for (var y = 0.5; y < h; y += h/4) {
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath(); ctx.moveTo(0, h*0.5); ctx.lineTo(w, h*0.5); ctx.stroke();

  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  for (var t = 0; t <= dur; t += Math.max(1, Math.round(dur/6))) {
    var x = (t / dur) * w;
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    ctx.fillText(t + 's', x, h - 11);
  }

  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  for (var t = 0; t <= dur; t += Math.max(1, Math.round(dur/6))) {
    var x = (t / dur) * w;
    ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
  }

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

  var cursorFrac = dur > 0 ? currentTime/dur : 0;
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

function drawLatent(ctx, w, h, currentTime) {
  ctx.clearRect(0,0,w,h);

  var path = DATA.latent_path;
  var n = path.length;
  if (n < 2) return;

  var xMin=_bounds.xMin, xMax=_bounds.xMax, yMin=_bounds.yMin, yMax=_bounds.yMax;
  var pad = 0.04;
  var xRange = (xMax - xMin) || 1;
  var yRange = (yMax - yMin) || 1;
  var xMid = (xMin + xMax) / 2;
  var yMid = (yMin + yMax) / 2;
  var xScale = w / (xRange * (1+pad*2));
  var yScale = h / (yRange * (1+pad*2));
  var scale = Math.min(xScale, yScale) * zoomLevel;
  var vw = xRange * (1+pad*2) * scale;
  var vh = yRange * (1+pad*2) * scale;
  var ox = (w - vw) / 2;
  var oy = (h - vh) / 2;

  function toScreen(px, py) {
    return [
      ox + (px - (xMid - xRange*(1+pad*2)/2)) * scale,
      oy + ((yMid + yRange*(1+pad*2)/2) - py) * scale
    ];
  }

  ctx.strokeStyle = 'rgba(255,255,255,0.04)';
  ctx.lineWidth = 1;
  var steps = 6;
  for (var gi=1; gi<steps; gi++) {
    var gx = (gi / steps) * w;
    ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke();
  }
  for (var gi=1; gi<steps; gi++) {
    var gy = (gi / steps) * h;
    ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
  }

  ctx.fillStyle = 'rgba(255,255,255,0.2)';
  ctx.font = '10px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  ctx.fillText('PC1', w/2, h-12);
  ctx.textAlign = 'right';
  ctx.textBaseline = 'middle';
  ctx.fillText('PC2', w-6, h/2);
  var [zx, zy] = toScreen(0, 0);
  ctx.fillStyle = 'rgba(255,255,255,0.08)';
  ctx.beginPath();
  ctx.arc(zx, zy, 3, 0, Math.PI*2);
  ctx.fill();

  ctx.fillStyle = 'rgba(255,255,255,0.15)';
  ctx.font = '9px sans-serif';
  ctx.textAlign = 'right';
  ctx.textBaseline = 'top';
  ctx.fillText('start', w-8, 8);
  ctx.textBaseline = 'bottom';
  ctx.fillText('end', w-8, h-8);

  var legX = w - 100, legY = 16, legW = 80, legH = 8;
  for (var li=0; li<legW; li++) {
    var lt = li / legW;
    var lc = pathColor(lt);
    ctx.fillStyle = rgba(lc, 0.6);
    ctx.fillRect(legX+li, legY, 1, legH);
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.strokeRect(legX, legY, legW, legH);

  var progress = Math.min(Math.max(currentTime / DATA.duration, 0), 1);
  var drawCount = Math.min(Math.floor(progress * (n - 1)), n - 1);

  for (var i=0; i<drawCount; i++) {
    var [x1,y1] = toScreen(path[i][0], path[i][1]);
    var [x2,y2] = toScreen(path[i+1][0], path[i+1][1]);
    var t = i / (n-1);
    var col = pathColor(t);
    var recency = Math.pow((i + 1) / (drawCount || 1), fadeExp);
    var segW = 1 + 2 * recency;
    var segA = 0.2 + 0.6 * recency;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = rgba(col, segA);
    ctx.lineWidth = segW;
    ctx.stroke();
  }

  var pointCount = Math.min(drawCount + 1, n);
  for (var i=0; i<pointCount; i++) {
    var [px, py] = toScreen(path[i][0], path[i][1]);
    var t = i / (n-1);
    var col = pathColor(t);
    var recency = Math.pow((i + 1) / (pointCount || 1), fadeExp);
    var dotR = 1 + 2.5 * recency;
    ctx.beginPath();
    ctx.arc(px, py, dotR, 0, Math.PI*2);
    ctx.fillStyle = rgba(col, 0.35 + 0.45 * recency);
    ctx.fill();
  }

  var [cx, cy] = toScreen.apply(null, getLatentPos(currentTime));

  var grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 28);
  grad.addColorStop(0, 'rgba(255,215,0,0.7)');
  grad.addColorStop(0.3, 'rgba(255,215,0,0.25)');
  grad.addColorStop(1, 'rgba(255,215,0,0)');
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(cx, cy, 28, 0, Math.PI*2);
  ctx.fill();

  ctx.beginPath();
  ctx.arc(cx, cy, 7, 0, Math.PI*2);
  ctx.strokeStyle = 'rgba(255,215,0,0.35)';
  ctx.lineWidth = 2;
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx, cy, 3.5, 0, Math.PI*2);
  ctx.fillStyle = '#ffd700';
  ctx.fill();

  var curIdx = Math.floor(progress * (n-1));
  for (var i=1; i<=trailLen; i++) {
    var idx = Math.max(0, curIdx - i);
    var tFrac = 1 - i/trailLen;
    var [tx, ty] = toScreen(path[idx][0], path[idx][1]);
    ctx.beginPath();
    ctx.arc(tx, ty, 2 * tFrac, 0, Math.PI*2);
    ctx.fillStyle = 'rgba(0,210,255,' + (tFrac*0.5) + ')';
    ctx.fill();
  }
}

function updateUI(currentTime) {
  var total = DATA.duration;
  var mins = Math.floor(currentTime/60);
  var secs = Math.floor(currentTime%60);
  var tMins = Math.floor(total/60);
  var tSecs = Math.floor(total%60);
  timeDisplay.textContent = mins + ':' + secs.toString().padStart(2,'0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2,'0');
  seekBar.value = total > 0 ? (currentTime/total)*1000 : 0;
}

function tick() {
  var t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;

  var lsz = sizeCanvas(latentCanvas);
  drawLatent(latentCanvas.getContext('2d'), lsz.w, lsz.h, t);

  var wsz = sizeCanvas(waveCanvas);
  drawWaveform(waveCanvas.getContext('2d'), wsz.w, wsz.h, t);

  updateUI(t);

  if (t >= DATA.duration) {
    if (loopEnabled) {
      pausedAt = 0;
      source = null;
      play();
    } else {
      isPlaying = false;
      pausedAt = DATA.duration;
      playBtn.innerHTML = '&#9654;';
      animId = null;
      return;
    }
  }
  animId = requestAnimationFrame(tick);
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
  var time = (parseFloat(this.value) / 1000) * DATA.duration;
  pausedAt = time;
  if (!isPlaying && audioBuffer) {
    var lsz = sizeCanvas(latentCanvas);
    drawLatent(latentCanvas.getContext('2d'), lsz.w, lsz.h, time);
    var wsz = sizeCanvas(waveCanvas);
    drawWaveform(waveCanvas.getContext('2d'), wsz.w, wsz.h, time);
    updateUI(time);
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

var fadeSlider = document.getElementById(id+'-fade');
var fadeVal = document.getElementById(id+'-fade-val');
fadeSlider.addEventListener('input', function() {
  var v = parseFloat(this.value);
  fadeExp = v / 10;
  fadeVal.textContent = fadeExp.toFixed(1);
});

var trailSlider = document.getElementById(id+'-trail');
var trailVal = document.getElementById(id+'-trail-val');
trailSlider.addEventListener('input', function() {
  trailLen = parseInt(this.value);
  trailVal.textContent = trailLen;
});

var zoomSlider = document.getElementById(id+'-zoom');
var zoomVal = document.getElementById(id+'-zoom-val');
zoomSlider.addEventListener('input', function() {
  var v = parseInt(this.value);
  zoomLevel = v / 10;
  zoomVal.textContent = zoomLevel.toFixed(1);
});

var _bounds = (function() {
  var p = DATA.latent_path, n = p.length, xMin=Infinity, xMax=-Infinity, yMin=Infinity, yMax=-Infinity;
  for (var pi=0; pi<n; pi++) {
    if (p[pi][0] < xMin) xMin = p[pi][0];
    if (p[pi][0] > xMax) xMax = p[pi][0];
    if (p[pi][1] < yMin) yMin = p[pi][1];
    if (p[pi][1] > yMax) yMax = p[pi][1];
  }
  return {xMin:xMin, xMax:xMax, yMin:yMin, yMax:yMax};
})();

initAudio();

setTimeout(function() {
  var lsz = sizeCanvas(latentCanvas);
  drawLatent(latentCanvas.getContext('2d'), lsz.w, lsz.h, 0);
  var wsz = sizeCanvas(waveCanvas);
  drawWaveform(waveCanvas.getContext('2d'), wsz.w, wsz.h, 0);
  updateUI(0);
}, 50);

window.addEventListener('resize', function() {
  clearTimeout(window._rtvResize);
  window._rtvResize = setTimeout(function() {
    var t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;
    var lsz = sizeCanvas(latentCanvas);
    drawLatent(latentCanvas.getContext('2d'), lsz.w, lsz.h, t);
    var wsz = sizeCanvas(waveCanvas);
    drawWaveform(waveCanvas.getContext('2d'), wsz.w, wsz.h, t);
  }, 100);
});
