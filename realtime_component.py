import base64
import json
import uuid

from audio_processor import audio_to_wav_bytes


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
    <h3 style="margin:0;color:#fff;font-weight:600;font-size:18px">&#127916; Real-Time Player</h3>
    <span id="__COMPONENT_ID__-time" style="font-family:'SF Mono',Monaco,monospace;font-size:14px;color:#888">0:00 / 0:00</span>
  </div>

  <div style="margin-bottom:12px;position:relative;border-radius:6px;overflow:hidden">
    <canvas id="__COMPONENT_ID__-wave" style="width:100%;height:120px;display:block;background:#0a0a1a"></canvas>
  </div>

  <div style="margin-bottom:16px;position:relative;border-radius:6px;overflow:hidden">
    <canvas id="__COMPONENT_ID__-latent" style="width:100%;height:380px;display:block;background:#0a0a1a"></canvas>
  </div>

  <div style="display:flex;align-items:center;gap:12px">
    <button id="__COMPONENT_ID__-play" style="background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:8px 24px;border-radius:6px;cursor:pointer;font-weight:700;font-size:15px;letter-spacing:0.3px;transition:transform 0.1s;min-width:90px">&#9654; Play</button>
    <div style="flex:1;position:relative">
      <input type="range" id="__COMPONENT_ID__-seek" min="0" max="1000" value="0" style="width:100%;height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer;margin:0">
    </div>
  </div>
</div>

<script>
(function() {
  const DATA = __DATA_JSON__;
  const id = "__COMPONENT_ID__";

  const waveCanvas = document.getElementById(id+'-wave');
  const latentCanvas = document.getElementById(id+'-latent');
  const playBtn = document.getElementById(id+'-play');
  const seekBar = document.getElementById(id+'-seek');
  const timeDisplay = document.getElementById(id+'-time');

  let audioCtx = null;
  let audioBuffer = null;
  let source = null;
  let isPlaying = false;
  let startTime = 0;
  let pausedAt = 0;
  let animId = null;

  function sizeCanvas(canvas) {
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    const w = rect.width;
    const h = rect.height;
    if (canvas.width !== Math.round(w*dpr) || canvas.height !== Math.round(h*dpr)) {
      canvas.width = Math.round(w*dpr);
      canvas.height = Math.round(h*dpr);
      canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    return {w, h};
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
    const buf = base64ToArrayBuffer(DATA.audio_b64);
    audioCtx.decodeAudioData(buf, function(buf) {
      audioBuffer = buf;
    }, function(err) {
      console.error('Audio decode error:', err);
    });
  }

  function getCurrentTime() {
    if (!isPlaying || !audioCtx) return pausedAt;
    return audioCtx.currentTime - startTime + pausedAt;
  }

  function play() {
    initAudio();
    if (!audioBuffer) return;
    if (audioCtx.state === 'suspended') audioCtx.resume();

    if (pausedAt >= DATA.duration) {
      pausedAt = 0;
    }

    source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);
    source.start(0, pausedAt);

    startTime = audioCtx.currentTime;
    isPlaying = true;
    playBtn.innerHTML = '&#9646;&#9646; Pause';

    source.onended = function() {
      if (isPlaying) {
        isPlaying = false;
        pausedAt = DATA.duration;
        playBtn.innerHTML = '&#9654; Play';
      }
    };

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
      if (source) {
        source.stop();
        source.disconnect();
      }
      source = audioCtx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(audioCtx.destination);
      source.start(0, pausedAt);
      startTime = audioCtx.currentTime;
    }
  }

  function getLatentPos(time) {
    const times = DATA.latent_times;
    const path = DATA.latent_path;
    const n = times.length;
    if (n === 0) return [0,0];
    if (time <= times[0]) return path[0];
    if (time >= times[n-1]) return path[n-1];

    let lo = 0, hi = n-1;
    while (lo < hi-1) {
      const mid = (lo+hi)>>1;
      if (times[mid] <= time) lo = mid;
      else hi = mid;
    }
    const t = (time - times[lo]) / (times[hi] - times[lo] + 1e-10);
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

  const C_START = [0, 210, 255];
  const C_MID   = [123, 47, 247];
  const C_END   = [255, 107, 107];

  function pathColor(t) {
    if (t < 0.5) return lerpColor(C_START, C_MID, t*2);
    return lerpColor(C_MID, C_END, (t-0.5)*2);
  }

  function drawWaveform(ctx, w, h, currentTime) {
    ctx.clearRect(0,0,w,h);

    const peaks = DATA.waveform_peaks;
    const n = peaks.length;
    const dur = DATA.duration;

    // unplayed portion
    ctx.beginPath();
    ctx.moveTo(0, h*0.5);
    for (let i=0; i<n; i++) {
      const x = (i/n)*w;
      ctx.lineTo(x, h*0.5 + peaks[i][0] * h*0.45);
    }
    for (let i=n-1; i>=0; i--) {
      const x = (i/n)*w;
      ctx.lineTo(x, h*0.5 + peaks[i][1] * h*0.45);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0,210,255,0.12)';
    ctx.fill();

    // played portion overlay
    const cursorFrac = dur > 0 ? currentTime/dur : 0;
    const cursorX = cursorFrac * w;

    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, cursorX, h);
    ctx.clip();

    ctx.beginPath();
    ctx.moveTo(0, h*0.5);
    for (let i=0; i<n; i++) {
      const x = (i/n)*w;
      ctx.lineTo(x, h*0.5 + peaks[i][0] * h*0.45);
    }
    for (let i=n-1; i>=0; i--) {
      const x = (i/n)*w;
      ctx.lineTo(x, h*0.5 + peaks[i][1] * h*0.45);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0,210,255,0.3)';
    ctx.fill();
    ctx.restore();

    // cursor line
    if (cursorFrac > 0 && cursorFrac < 1) {
      ctx.beginPath();
      ctx.moveTo(cursorX, 0);
      ctx.lineTo(cursorX, h);
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.shadowColor = 'rgba(255,255,255,0.5)';
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }

  function drawLatent(ctx, w, h, currentTime) {
    ctx.clearRect(0,0,w,h);

    const path = DATA.latent_path;
    const n = path.length;
    if (n < 2) return;

    // compute bounds with padding
    let xMin=Infinity, xMax=-Infinity, yMin=Infinity, yMax=-Infinity;
    for (const p of path) {
      if (p[0] < xMin) xMin = p[0];
      if (p[0] > xMax) xMax = p[0];
      if (p[1] < yMin) yMin = p[1];
      if (p[1] > yMax) yMax = p[1];
    }
    const pad = 0.15;
    const xRange = (xMax - xMin) || 1;
    const yRange = (yMax - yMin) || 1;
    const xMid = (xMin + xMax) / 2;
    const yMid = (yMin + yMax) / 2;
    const xScale = w / (xRange * (1+pad*2));
    const yScale = h / (yRange * (1+pad*2));
    const scale = Math.min(xScale, yScale);
    const vw = xRange * (1+pad*2) * scale;
    const vh = yRange * (1+pad*2) * scale;
    const ox = (w - vw) / 2;
    const oy = (h - vh) / 2;

    function toScreen(px, py) {
      return [
        ox + (px - (xMid - xRange*(1+pad*2)/2)) * scale,
        oy + ((yMid + yRange*(1+pad*2)/2) - py) * scale
      ];
    }

    // trajectory as gradient segments
    for (let i=0; i<n-1; i++) {
      const [x1,y1] = toScreen(path[i][0], path[i][1]);
      const [x2,y2] = toScreen(path[i+1][0], path[i+1][1]);
      const t = i / (n-1);
      const col = pathColor(t);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = rgba(col, 0.5);
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // faint white trajectory overlay
    for (let i=0; i<n-1; i++) {
      const [x1,y1] = toScreen(path[i][0], path[i][1]);
      const [x2,y2] = toScreen(path[i+1][0], path[i+1][1]);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = 'rgba(255,255,255,0.08)';
      ctx.lineWidth = 1;
      ctx.stroke();
    }

    // current position
    const [cx, cy] = toScreen(...getLatentPos(currentTime));

    // glow
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, 30);
    grad.addColorStop(0, 'rgba(255,215,0,0.8)');
    grad.addColorStop(0.3, 'rgba(255,215,0,0.3)');
    grad.addColorStop(1, 'rgba(255,215,0,0)');
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, 30, 0, Math.PI*2);
    ctx.fill();

    // outer ring
    ctx.beginPath();
    ctx.arc(cx, cy, 8, 0, Math.PI*2);
    ctx.strokeStyle = 'rgba(255,215,0,0.4)';
    ctx.lineWidth = 2;
    ctx.stroke();

    // inner dot
    ctx.beginPath();
    ctx.arc(cx, cy, 4, 0, Math.PI*2);
    ctx.fillStyle = '#ffd700';
    ctx.fill();

    // trail (last 30 frames)
    const curIdx = Math.floor(currentTime / DATA.duration * (n-1));
    const trailLen = 30;
    for (let i=1; i<=trailLen; i++) {
      const idx = Math.max(0, curIdx - i);
      const tFrac = 1 - i/trailLen;
      const [tx, ty] = toScreen(path[idx][0], path[idx][1]);
      ctx.beginPath();
      ctx.arc(tx, ty, 2 * tFrac, 0, Math.PI*2);
      ctx.fillStyle = 'rgba(0,210,255,' + (tFrac*0.6) + ')';
      ctx.fill();
    }
  }

  function updateUI(currentTime) {
    const total = DATA.duration;
    const mins = Math.floor(currentTime/60);
    const secs = Math.floor(currentTime%60);
    const tMins = Math.floor(total/60);
    const tSecs = Math.floor(total%60);
    timeDisplay.textContent = mins + ':' + secs.toString().padStart(2,'0') + ' / ' + tMins + ':' + tSecs.toString().padStart(2,'0');
    seekBar.value = total > 0 ? (currentTime/total)*1000 : 0;
  }

  function tick() {
    const t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;

    const {w:ww, h:wh} = sizeCanvas(waveCanvas);
    const wctx = waveCanvas.getContext('2d');
    drawWaveform(wctx, ww, wh, t);

    const {w:lw, h:lh} = sizeCanvas(latentCanvas);
    const lctx = latentCanvas.getContext('2d');
    drawLatent(lctx, lw, lh, t);

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
    const val = parseFloat(this.value) / 1000;
    const time = val * DATA.duration;
    pausedAt = time;
    if (!isPlaying && audioBuffer) {
      const {w:ww, h:wh} = sizeCanvas(waveCanvas);
      drawWaveform(waveCanvas.getContext('2d'), ww, wh, time);
      const {w:lw, h:lh} = sizeCanvas(latentCanvas);
      drawLatent(latentCanvas.getContext('2d'), lw, lh, time);
      updateUI(time);
    }
    if (isPlaying) seek(time);
  });

  // init
  initAudio();

  setTimeout(function() {
    const {w:ww, h:wh} = sizeCanvas(waveCanvas);
    drawWaveform(waveCanvas.getContext('2d'), ww, wh, 0);
    const {w:lw, h:lh} = sizeCanvas(latentCanvas);
    drawLatent(latentCanvas.getContext('2d'), lw, lh, 0);
    updateUI(0);
  }, 50);

  // resize handler
  let resizeTimer;
  window.addEventListener('resize', function() {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function() {
      const t = isPlaying ? Math.min(getCurrentTime(), DATA.duration) : pausedAt;
      const {w:ww, h:wh} = sizeCanvas(waveCanvas);
      drawWaveform(waveCanvas.getContext('2d'), ww, wh, t);
      const {w:lw, h:lh} = sizeCanvas(latentCanvas);
      drawLatent(latentCanvas.getContext('2d'), lw, lh, t);
    }, 100);
  });
})();
</script>
"""
