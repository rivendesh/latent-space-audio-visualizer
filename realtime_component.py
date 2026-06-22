import base64
import json
import uuid

from audio_processor import audio_to_wav_bytes


# Build a self-contained HTML/JS string with embedded audio and latent data
# for the 2D real-time player tab. Returns raw HTML for st.components.v1.html.
def build_realtime_component(audio, sr, latent_points, latent_times, waveform_peaks):
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
    <button id="__COMPONENT_ID__-play" style="background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:8px 20px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;letter-spacing:0.3px;min-width:84px">&#9654; Play</button>
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
</div>

<script>
(function() {
  var DATA = __DATA_JSON__;
  var id = "__COMPONENT_ID__";

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
    var myGen = sourceGen;
    var s = audioCtx.createBufferSource();
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

  // ---------- waveform ----------
  function drawWaveform(ctx, w, h, currentTime) {
    ctx.clearRect(0,0,w,h);

    var peaks = DATA.waveform_peaks;
    var n = peaks.length;
    var dur = DATA.duration;

    // grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    ctx.font = '9px sans-serif';
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    for (var y = 0.5; y < h; y += h/4) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke();
    }
    // baseline
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.beginPath(); ctx.moveTo(0, h*0.5); ctx.lineTo(w, h*0.5); ctx.stroke();

    // time marks
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

    // unplayed fill
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

    // played overlay
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

    // cursor
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

  // ---------- latent space ----------
  function drawLatent(ctx, w, h, currentTime) {
    ctx.clearRect(0,0,w,h);

    var path = DATA.latent_path;
    var n = path.length;
    if (n < 2) return;

    var xMin=Infinity, xMax=-Infinity, yMin=Infinity, yMax=-Infinity;
    for (var pi=0; pi<n; pi++) {
      if (path[pi][0] < xMin) xMin = path[pi][0];
      if (path[pi][0] > xMax) xMax = path[pi][0];
      if (path[pi][1] < yMin) yMin = path[pi][1];
      if (path[pi][1] > yMax) yMax = path[pi][1];
    }
    var pad = 0.04;
    var xRange = (xMax - xMin) || 1;
    var yRange = (yMax - yMin) || 1;
    var xMid = (xMin + xMax) / 2;
    var yMid = (yMin + yMax) / 2;
    var xScale = w / (xRange * (1+pad*2));
    var yScale = h / (yRange * (1+pad*2));
    var scale = Math.min(xScale, yScale);
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

    // grid
    ctx.strokeStyle = 'rgba(255,255,255,0.04)';
    ctx.lineWidth = 1;
    // vertical
    var steps = 6;
    for (var gi=1; gi<steps; gi++) {
      var gx = (gi / steps) * w;
      ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, h); ctx.stroke();
    }
    // horizontal
    for (var gi=1; gi<steps; gi++) {
      var gy = (gi / steps) * h;
      ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(w, gy); ctx.stroke();
    }

    // axis arrows and labels
    ctx.fillStyle = 'rgba(255,255,255,0.2)';
    ctx.font = '10px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    // x-axis label
    ctx.fillText('PC1', w/2, h-12);
    // y-axis label
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText('PC2', w-6, h/2);
    // origin marker
    var [zx, zy] = toScreen(0, 0);
    ctx.fillStyle = 'rgba(255,255,255,0.08)';
    ctx.beginPath();
    ctx.arc(zx, zy, 3, 0, Math.PI*2);
    ctx.fill();

    // corner label — progress legend
    ctx.fillStyle = 'rgba(255,255,255,0.15)';
    ctx.font = '9px sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'top';
    ctx.fillText('start', w-8, 8);
    ctx.textBaseline = 'bottom';
    ctx.fillText('end', w-8, h-8);

    // gradient mini-legend (top-right)
    var legX = w - 100, legY = 16, legW = 80, legH = 8;
    for (var li=0; li<legW; li++) {
      var lt = li / legW;
      var lc = pathColor(lt);
      ctx.fillStyle = rgba(lc, 0.6);
      ctx.fillRect(legX+li, legY, 1, legH);
    }
    ctx.strokeStyle = 'rgba(255,255,255,0.1)';
    ctx.strokeRect(legX, legY, legW, legH);

    // trajectory — progressive with node scaling
    var progress = Math.min(Math.max(currentTime / DATA.duration, 0), 1);
    var drawCount = Math.min(Math.floor(progress * (n - 1)), n - 1);

    for (var i=0; i<drawCount; i++) {
      var [x1,y1] = toScreen(path[i][0], path[i][1]);
      var [x2,y2] = toScreen(path[i+1][0], path[i+1][1]);
      var t = i / (n-1);
      var col = pathColor(t);
      var recency = Math.pow((i + 1) / (drawCount || 1), 2);
      var segW = 1 + 2 * recency;
      var segA = 0.2 + 0.6 * recency;
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = rgba(col, segA);
      ctx.lineWidth = segW;
      ctx.stroke();
    }

    // plot every frame as a discrete point, scaled by recency
    var pointCount = Math.min(drawCount + 1, n);
    for (var i=0; i<pointCount; i++) {
      var [px, py] = toScreen(path[i][0], path[i][1]);
      var t = i / (n-1);
      var col = pathColor(t);
      var recency = Math.pow((i + 1) / (pointCount || 1), 2);
      var dotR = 1 + 2.5 * recency;
      ctx.beginPath();
      ctx.arc(px, py, dotR, 0, Math.PI*2);
      ctx.fillStyle = rgba(col, 0.35 + 0.45 * recency);
      ctx.fill();
    }

    // current position
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

    // trail
    var curIdx = Math.floor(progress * (n-1));
    var trailLen = 15;
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

    if (isPlaying && t >= DATA.duration) {
      isPlaying = false;
      pausedAt = DATA.duration;
      playBtn.innerHTML = '&#9654; Play';
      animId = null;
      return;
    }
    animId = requestAnimationFrame(tick);
  }

  // events
  playBtn.addEventListener('click', togglePlay);

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

  // init
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
})();
</script>
"""
