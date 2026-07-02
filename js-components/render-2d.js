var audioCtx = null;
var gain = null;
var audioBuf = null;
var source = null;
var playing = false;
var startTime = 0;
var pausedAt = 0;
var btn, seek, timeDisp, volSlider, volVal;

function setup() {
  var cw = Math.max(windowWidth, 400);
  var canvas = createCanvas(cw, D.ch);
  var container = document.getElementById("c");
  if (container) canvas.parent(container);
  btn = document.getElementById("p");
  seek = document.getElementById("s");
  timeDisp = document.getElementById("t");
  volSlider = document.getElementById("v");
  volVal = document.getElementById("vv");
  btn.onclick = togglePlay;
  seek.oninput = onSeek;
  volSlider.oninput = function () {
    volVal.textContent = this.value + "%";
    if (gain) gain.gain.value = this.value / 100;
  };
  document.onkeydown = function (e) {
    if (e.target.tagName === "INPUT") return;
    if (e.code === "Space") { e.preventDefault(); togglePlay(); }
  };
}

function draw() {
  var t = playing ? Math.min(currentAudioTime() - startTime + pausedAt, D.dur) : pausedAt;
  if (playing && t >= D.dur) {
    playing = false; pausedAt = D.dur; btn.innerHTML = "&#9654;";
  }
  background(30, 30, 50);
  drawLatent(t);
  stroke(255, 255, 255, 12); strokeWeight(1); line(0, D.lh, width, D.lh);
  push(); translate(0, D.lh); drawCentroid(t); pop();
  stroke(255, 255, 255, 12); strokeWeight(1); line(0, D.lh + D.ct_h, width, D.lh + D.ct_h);
  push(); translate(0, D.lh + D.ct_h); drawWaveform(t); pop();
  var m = Math.floor(t / 60);
  var s = Math.floor(t % 60);
  var dm = Math.floor(D.dur / 60);
  var ds = Math.floor(D.dur % 60);
  timeDisp.textContent = m + ":" + (s < 10 ? "0" : "") + s + " / " + dm + ":" + (ds < 10 ? "0" : "") + ds;
  seek.value = D.dur > 0 ? (t / D.dur) * 1000 : 0;
}

function currentAudioTime() {
  if (!audioCtx) return 0;
  if (audioCtx.state === "suspended") audioCtx.resume();
  return audioCtx.currentTime;
}

function initAudio() {
  if (audioCtx) return;
  audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  gain = audioCtx.createGain();
  gain.gain.value = volSlider.value / 100;
  gain.connect(audioCtx.destination);
  var bin = atob(D.ab);
  var buf = new ArrayBuffer(bin.length);
  var view = new Uint8Array(buf);
  for (var i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
  audioCtx.decodeAudioData(buf, function (b) { audioBuf = b; });
}

function togglePlay() {
  initAudio();
  if (!audioBuf) return;
  if (playing) {
    pausedAt += audioCtx.currentTime - startTime;
    if (source) { source.stop(); source.disconnect(); source = null; }
    playing = false; btn.innerHTML = "&#9654;";
  } else {
    if (pausedAt >= D.dur) pausedAt = 0;
    source = audioCtx.createBufferSource();
    source.buffer = audioBuf; source.connect(gain);
    source.start(0, pausedAt);
    startTime = audioCtx.currentTime;
    playing = true; btn.innerHTML = "&#9208;";
  }
}

function onSeek() {
  var t = (this.value / 1000) * D.dur;
  pausedAt = t;
  if (playing) {
    if (source) { source.stop(); source.disconnect(); }
    source = audioCtx.createBufferSource();
    source.buffer = audioBuf; source.connect(gain);
    source.start(0, t);
    startTime = audioCtx.currentTime;
  }
}

function drawGrid(w, h, xDivs, yDivs) {
  stroke(255, 255, 255, 20);
  strokeWeight(1);
  for (var i = 1; i < xDivs; i++) {
    var x = (w / xDivs) * i;
    line(x, 0, x, h);
  }
  for (var i = 1; i < yDivs; i++) {
    var y = (h / yDivs) * i;
    line(0, y, w, y);
  }
}

function drawLatent(t) {
  var pts = D.li, n = pts.length;
  if (n < 2) return;
  drawGrid(width, D.lh, 6, 5);
  var sx = width / D.cw;
  var prog = D.dur > 0 ? Math.min(t / D.dur, 1) : 0;
  var drawN = Math.max(Math.floor(prog * (n - 1)), 0);
  noFill();
  for (var i = 0; i < drawN && i < n - 1; i++) {
    var c = D.lc[i];
    stroke(c[0], c[1], c[2], 80);
    strokeWeight(1.5);
    line(pts[i][0] * sx, pts[i][1], pts[i + 1][0] * sx, pts[i + 1][1]);
  }
  noStroke();
  for (var i = 0; i <= drawN && i < n; i++) {
    var c = D.lc[i];
    fill(c[0], c[1], c[2], 180);
    circle(pts[i][0] * sx, pts[i][1], 3.5);
  }
  var idx = Math.min(drawN, n - 1);
  var cx = pts[idx][0] * sx, cy = pts[idx][1];
  noStroke();
  for (var r = 24; r > 0; r -= 4) { fill(255, 215, 0, 200 - r * 8); circle(cx, cy, r); }
  fill(255, 215, 0); circle(cx, cy, 5);

  // axes labels
  fill(255, 255, 255, 50); noStroke(); textAlign(CENTER, BOTTOM); textSize(10); textFont("sans-serif");
  text("PC 1", width / 2, D.lh - 4);
  textAlign(CENTER, CENTER);
  push(); translate(10, D.lh / 2); rotate(-HALF_PI); text("PC 2", 0, 0); pop();
}

function drawCentroid(t) {
  var pts = D.cp, n = pts.length;
  if (n < 2) return;
  drawGrid(width, D.ct_h, 6, 5);
  var sx = width / D.cw;
  var h = D.ct_h;
  noStroke();
  for (var i = 0; i < n; i++) {
    var c = D.cc[i];
    fill(c[0], c[1], c[2], 130);
    circle(pts[i][0] * sx, pts[i][1], 2.5);
  }
  var prog = D.dur > 0 ? Math.min(t / D.dur, 1) : 0;
  var idx = Math.min(Math.floor(prog * n), n - 1);
  if (idx >= 0 && idx < n) {
    var cx = pts[idx][0] * sx, cy = pts[idx][1];
    noStroke();
    for (var r = 16; r > 0; r -= 3) { fill(255, 215, 0, 140 - r * 8); circle(cx, cy, r); }
    fill(255, 215, 0); circle(cx, cy, 5);
  }
  // axes labels
  fill(255, 255, 255, 50); noStroke(); textAlign(CENTER, BOTTOM); textSize(10); textFont("sans-serif");
  text("Spectral Centroid (Hz)", width / 2, h - 4);
  textAlign(CENTER, CENTER);
  push(); translate(10, h / 2); rotate(-HALF_PI); text("RMS Energy", 0, 0); pop();
}

function drawWaveform(t) {
  var ws = D.ws, h = D.wh;
  var prog = D.dur > 0 ? Math.min(t / D.dur, 1) : 0;
  var lPad = 30, bPad = 16;
  var dw = width - lPad, dh = h - bPad;
  noStroke();
  fill(0, 210, 255, 15);
  beginShape();
  for (var i = 0; i + 1 < ws.length; i += 2) vertex(lPad + ws[i] * dw, ws[i + 1] * dh);
  endShape(CLOSE);
  if (prog > 0.02) {
    noStroke();
    fill(0, 210, 255, 55);
    rect(lPad, 0, prog * dw, dh);
  }
  if (prog > 0.02 && prog < 0.98) {
    stroke(255, 255, 255, 200); strokeWeight(2);
    line(lPad + prog * dw, 0, lPad + prog * dw, dh);
  }
  // axes labels
  fill(255, 255, 255, 50); noStroke(); textAlign(CENTER, BOTTOM); textSize(10); textFont("sans-serif");
  text("Time (s)", width / 2, h - 2);
  textAlign(CENTER, CENTER);
  push(); translate(10, h / 2); rotate(-HALF_PI); text("Amplitude", 0, 0); pop();
}

function windowResized() {
  resizeCanvas(Math.max(windowWidth, 400), D.ch);
}
