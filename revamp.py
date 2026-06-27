import argparse
import base64
import json
import os
import uuid
from pathlib import Path

import streamlit as st
import numpy as np

from utils.audio_utils import load_audio, compute_waveform_peaks, audio_to_wav_bytes
from utils.latent_utils import LatentEncoder


def _parse_cli_args():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--file", "-f", type=str, default=None)
    try:
        args, _ = parser.parse_known_args()
    except SystemExit:
        args = argparse.Namespace(file=None)
    return args

CLI_ARGS = _parse_cli_args()

_AUTO_PATH = None
if CLI_ARGS.file:
    _AUTO_PATH = Path(CLI_ARGS.file)
elif os.environ.get("AUDIO_FILE"):
    _AUTO_PATH = Path(os.environ["AUDIO_FILE"])

if _AUTO_PATH is not None and _AUTO_PATH.exists():
    st.session_state.setdefault("auto_file", _AUTO_PATH.read_bytes())
    st.session_state.setdefault("auto_file_name", _AUTO_PATH.name)

st.set_page_config(page_title="Latent Space", layout="wide")
HAS_AUTO = "auto_file" in st.session_state

st.title("Latent Space")

with st.sidebar:
    st.header("Controls")
    if HAS_AUTO:
        st.success(f"Loaded: {st.session_state['auto_file_name']}")
        uploaded_file = st.file_uploader("Replace audio file", type=["wav","mp3","flac","ogg","m4a","aiff"], key="sidebar_uploader")
    else:
        uploaded_file = None
    st.divider()
    st.markdown("### Settings")
    n_mels = st.slider("Mel bands", 32, 256, 128, 32)
    hop_length = st.slider("Hop length", 128, 2048, 512, 128)
    max_playback = st.slider("Max playback (s)", 10, 600, 120, 10)

if not HAS_AUTO:
    main_uf = st.file_uploader("Choose an audio file", type=["wav","mp3","flac","ogg","m4a","aiff"], key="main_uploader")
    if main_uf is not None:
        uploaded_file = main_uf

auto_file = st.session_state.get("auto_file")

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
elif auto_file is not None:
    file_bytes = auto_file
else:
    st.info("Upload an audio file to get started.")
    st.stop()

@st.cache_data
def _process_audio(file_bytes, n_mels, hop_length):
    a, sr = load_audio(file_bytes)
    enc = LatentEncoder(n_mels=n_mels, hop_length=hop_length)
    pts, times, cents, rms = enc.encode(a, sr)
    peaks = compute_waveform_peaks(a)
    ev = sum(enc.explained_variance_ratio) if enc.explained_variance_ratio is not None else None
    return a, sr, pts, times, cents, rms, peaks, ev

with st.spinner("Processing audio …"):
    audio, sr, points, times, centroids, rms, peaks, ev = _process_audio(file_bytes, n_mels, hop_length)

duration = len(audio) / sr
max_samp = int(max_playback * sr)

if len(audio) > max_samp:
    pb_audio = audio[:max_samp]
    pb_n = np.searchsorted(times, max_playback) + 1
    points = points[:pb_n]
    times = times[:pb_n]
    peaks = compute_waveform_peaks(pb_audio)
    centroids = centroids[:pb_n]
    rms = rms[:pb_n]
    audio = pb_audio
    st.caption(f"Rendering first {max_playback}s ({pb_n} frames) of {duration:.0f}s total.")

# ---------- build self-contained HTML ----------
cid = f"lv-{uuid.uuid4().hex[:8]}"

wav_b64 = base64.b64encode(audio_to_wav_bytes(audio, sr)).decode("ascii")
t_max = float(times.max()) if len(times) > 0 else 1.0
t_norm = (times / t_max).tolist()
pts_3d = [[float(points[i,0]), float(points[i,1]), t_norm[i]] for i in range(len(points))]

data = {
    "p3d": pts_3d,
    "cents": centroids.tolist(),
    "cmin": float(centroids.min()),
    "cmax": float(centroids.max()),
    "dur": float(len(audio) / sr),
    "b64": wav_b64,
    "sr": sr,
}
data_json = json.dumps(data)

HTML = f"""<!DOCTYPE html>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:#070714;color:#ccc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;overflow:hidden;user-select:none}}
#v{{position:relative;width:100%;height:340px;background:#070714;border-radius:6px;overflow:hidden;cursor:grab}}
#v:active{{cursor:grabbing}}
#v canvas{{display:block;width:100%!important;height:100%!important}}
#fs{{position:absolute;top:6px;right:6px;z-index:20;background:rgba(0,0,0,.35);border:1px solid rgba(255,255,255,.15);color:rgba(255,255,255,.6);border-radius:4px;padding:3px 7px;cursor:pointer;font:14px sans-serif}}
#fs:hover{{background:rgba(0,0,0,.55);color:#fff}}
.rw{{display:flex;align-items:center;gap:8px;margin-top:8px;flex-wrap:wrap}}
.rw button{{background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:7px 18px;border-radius:5px;cursor:pointer;font-weight:700;font-size:14px;min-width:76px}}
.rw input[type=range]{{height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer;margin:0}}
.rw input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:11px;height:11px;border-radius:50%;background:#00d2ff;cursor:pointer}}
.rw label{{font-size:11px;color:#999;white-space:nowrap}}
.rw .v{{font-size:11px;color:#888;font-family:'SF Mono',Monaco,monospace;min-width:26px}}
.rw .tm{{font-family:'SF Mono',Monaco,monospace;font-size:12px;color:#888;margin-left:auto}}
.sr{{display:flex;align-items:center;gap:5px;margin-top:5px;flex-wrap:wrap}}
.sr input[type=range]{{height:4px;-webkit-appearance:none;appearance:none;background:#333;border-radius:2px;outline:none;cursor:pointer;margin:0}}
.sr input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:11px;height:11px;border-radius:50%;background:#00d2ff;cursor:pointer}}
.sr label{{font-size:10px;color:#999;white-space:nowrap}}
.sr .v{{font-size:10px;color:#888;font-family:'SF Mono',Monaco,monospace;min-width:24px}}
.sr select{{background:#070714;color:#ccc;border:1px solid #888;border-radius:3px;font-size:10px;padding:2px 3px;width:60px}}
</style>
<div id="v"><button id="fs">⛶</button></div>
<div class="rw">
<button id="pb">▶</button>
<button id="lp" style="opacity:.4;background:linear-gradient(135deg,#00d2ff,#3a7bd5);border:none;color:#000;padding:7px 10px;border-radius:5px;cursor:pointer;font-weight:700;font-size:14px;line-height:1;min-width:0">↺</button>
<input type="range" id="sk" min="0" max="1000" value="0" style="flex:1;min-width:60px">
<span class="tm" id="tm">0:00 / 0:00</span>
</div>
<div class="sr">
<label>Vol</label><input type="range" id="vl" min="0" max="100" value="75" style="width:50px"><span class="v" id="vlv">75%</span>
<label>Spd</label><input type="range" id="sd" min="0.25" max="3" step="0.25" value="1" style="width:50px"><span class="v" id="sdv">1x</span>
<label>Orb</label><input type="range" id="ob" min="-0.4" max="0.4" step="0.05" value="0.1" style="width:50px"><span class="v" id="obv">0.10</span>
<label>Str</label><input type="range" id="st" min="0.5" max="6" step="0.1" value="3.5" style="width:50px"><span class="v" id="stv">3.5</span>
<label>Slc</label><input type="range" id="sl" min="0" max="10" value="5" style="width:50px"><span class="v" id="slv">5</span>
<label>Op</label><input type="range" id="op" min="0" max="100" value="5" style="width:50px"><span class="v" id="opv">5</span>
<label>Z</label><input type="range" id="zm" min="5" max="50" value="15" style="width:50px"><span class="v" id="zmv">15</span>
<label>Fd</label><input type="range" id="fd" min="5" max="100" step="5" value="30" style="width:50px"><span class="v" id="fdv">3.0</span>
<label>Pan</label><select id="pn"><option value="mid">Mid</option><option value="none">Off</option></select>
</div>

<script>
(function(){{
const D={data_json};

let aCtx=null,aBuf=null,src=null,gain=null;
let play=false,pauseAt=0,startT=0,spd=1,vol=.75;
let fade=3,orbit=0.1,stretch=3.5,slices=5,slOp=5,zoom=15,pan='mid',loop=false;
let theta=0.6,phi=-0.35,running=true;
let mx=0,my=0,md=false;

const pts=D.p3d,cts=D.cents,n=pts.length;
const cMin=D.cmin,cMax=D.cmax,cRng=cMax-cMin||1,dur=D.dur;

const prefX=[],prefY=[],prefZ=[];
let sx=0,sy=0,sz=0;
for(let i=0;i<n;i++){{sx+=pts[i][0];sy+=pts[i][1];sz+=pts[i][2];prefX[i]=sx;prefY[i]=sy;prefZ[i]=sz;}}

const C0=[0,210,255],C1=[123,47,247],C2=[255,107,107];
function lc(a,b,t){{return[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t,a[2]+(b[2]-a[2])*t]}}
function pc(t){{return t<.5?lc(C0,C1,t*2):lc(C1,C2,(t-.5)*2)}}

function rotY(x,y,z,a){{let c=Math.cos(a),s=Math.sin(a);return[x*c+z*s,y,-x*s+z*c]}}
function rotX(x,y,z,a){{let c=Math.cos(a),s=Math.sin(a);return[x,y*c-z*s,y*s+z*c]}}

const can=document.createElement('canvas');
const ctx=can.getContext('2d');
document.getElementById('v').appendChild(can);
const vp=document.getElementById('v');
let W=vp.clientWidth||600,H=vp.clientHeight||340;

function resize(){{
W=vp.clientWidth||600;H=vp.clientHeight||340;
const dpr=Math.min(window.devicePixelRatio||1,2);
can.width=W*dpr;can.height=H*dpr;
can.style.width=W+'px';can.style.height=H+'px';
ctx.setTransform(dpr,0,0,dpr,0,0);
}}
resize();
const ro=new ResizeObserver(resize);ro.observe(vp);

function proj(x,y,z,w,h){{
const d=zoom;
const sc=d/(d+z);
return{{sx:x*sc+w/2,sy:-y*sc+h/2,dep:z,sz:sc}}
}}

function draw(t){{
const prog=Math.min(Math.max(t/dur,0),1);
const dc=Math.min(Math.floor(prog*n),n);
ctx.clearRect(0,0,W,H);
ctx.fillStyle='#070714';ctx.fillRect(0,0,W,H);

if(orbit!==0)theta+=orbit*.003;

let tx=0,ty=0,tz=0;
if(pan==='mid'&&dc>0&&dc<=n){{
const idx=dc-1;
tx=prefX[idx]/dc;ty=prefY[idx]/dc;tz=prefZ[idx]/dc*stretch;
}}

const ax=3;

// grid
for(let g=0;g<3;g++){{
let ox=0,oy=0,oz=0;
if(g==0)oy=-ax;
else if(g==1)ox=-ax;
const cnt=16,stp=ax*2/cnt;
ctx.strokeStyle='rgba(100,100,170,'+(g==0?.22:.12)+')';
ctx.lineWidth=.5;ctx.beginPath();
for(let i=0;i<=cnt;i++){{
const p=-ax+i*stp;
let x1,y1,z1,x2,y2,z2;
if(g==0){{x1=p;y1=0;z1=-ax;x2=p;y2=0;z2=ax}}
else if(g==1){{x1=0;y1=p;z1=-ax;x2=0;y2=p;z2=ax}}
else{{x1=-ax;y1=p;z1=0;x2=ax;y2=p;z2=0}}
let a,b;a=rotY(x1+ox,y1+oy,z1+oz,theta);b=rotY(x2+ox,y2+oy,z2+oz,theta);
a=rotX(a[0],a[1],a[2],phi);b=rotX(b[0],b[1],b[2],phi);
const p1=proj(a[0],a[1],a[2],W,H),p2=proj(b[0],b[1],b[2],W,H);
ctx.moveTo(p1.sx,p1.sy);ctx.lineTo(p2.sx,p2.sy);
}}
for(let i=0;i<=cnt;i++){{
const p=-ax+i*stp;
let x1,y1,z1,x2,y2,z2;
if(g==0){{x1=-ax;y1=0;z1=p;x2=ax;y2=0;z2=p}}
else if(g==1){{x1=0;y1=-ax;z1=p;x2=0;y2=ax;z2=p}}
else{{x1=-ax;y1=-ax;z1=0;x2=ax;y2=ax;z2=0}}
let a,b;a=rotY(x1+ox,y1+oy,z1+oz,theta);b=rotY(x2+ox,y2+oy,z2+oz,theta);
a=rotX(a[0],a[1],a[2],phi);b=rotX(b[0],b[1],b[2],phi);
const p1=proj(a[0],a[1],a[2],W,H),p2=proj(b[0],b[1],b[2],W,H);
ctx.moveTo(p1.sx,p1.sy);ctx.lineTo(p2.sx,p2.sy);
}}
ctx.stroke();
}}

// axes
ctx.strokeStyle='rgba(0,210,255,.45)';ctx.lineWidth=1;ctx.beginPath();
let a=rotY(-ax,0,0,theta);a=rotX(a[0],a[1],a[2],phi);let p=proj(a[0],a[1],a[2],W,H);ctx.moveTo(p.sx,p.sy);
a=rotY(ax,0,0,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.lineTo(p.sx,p.sy);
a=rotY(0,-ax,0,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.moveTo(p.sx,p.sy);
a=rotY(0,ax,0,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.lineTo(p.sx,p.sy);
a=rotY(0,0,-.1,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.moveTo(p.sx,p.sy);
a=rotY(0,0,1.1,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.lineTo(p.sx,p.sy);
ctx.stroke();
ctx.fillStyle='rgba(0,210,255,.7)';ctx.font='13px sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
a=rotY(ax+.35,0,0,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.fillText('PC1',p.sx,p.sy);
a=rotY(0,ax+.35,0,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.fillText('PC2',p.sx,p.sy);
a=rotY(0,0,1.25,theta);a=rotX(a[0],a[1],a[2],phi);p=proj(a[0],a[1],a[2],W,H);ctx.fillText('Time',p.sx,p.sy);

// time slices
if(slices>0){{
const op=slOp/100;
const stp=1/slices;
for(let z=0;z<=1.001;z+=stp){{
const h=ax*2;
const c=[[-ax,-ax,z],[ax,-ax,z],[ax,ax,z],[-ax,ax,z]];
let pp=[];
for(let i=0;i<4;i++){{
let r=rotY(c[i][0],c[i][1],c[i][2]*stretch,theta);
r=rotX(r[0],r[1],r[2],phi);
pp.push(proj(r[0],r[1],r[2],W,H));
}}
ctx.fillStyle='rgba(100,100,170,'+(op*.8)+')';
ctx.beginPath();ctx.moveTo(pp[0].sx,pp[0].sy);
for(let i=1;i<4;i++)ctx.lineTo(pp[i].sx,pp[i].sy);ctx.closePath();ctx.fill();
ctx.strokeStyle='rgba(136,136,204,'+(op*1.5)+')';ctx.lineWidth=.5;
ctx.beginPath();ctx.moveTo(pp[0].sx,pp[0].sy);
for(let i=1;i<4;i++)ctx.lineTo(pp[i].sx,pp[i].sy);ctx.closePath();ctx.stroke();
}}
}}

// trajectory line
if(dc>1){{
ctx.strokeStyle='rgba(255,255,255,.2)';ctx.lineWidth=1.2;ctx.beginPath();
for(let i=0;i<dc;i++){{
let r=rotY(pts[i][0],pts[i][1],pts[i][2]*stretch,theta);
r=rotX(r[0],r[1],r[2],phi);
const pj=proj(r[0],r[1],r[2],W,H);
if(i==0)ctx.moveTo(pj.sx,pj.sy);else ctx.lineTo(pj.sx,pj.sy);
}}
ctx.stroke();
}}

// trajectory points
if(dc>0){{
const idxs=Array.from({{length:dc}},(_,i)=>i);
idxs.sort((a,b)=>{{
let ra=rotY(pts[a][0],pts[a][1],pts[a][2]*stretch,theta);ra=rotX(ra[0],ra[1],ra[2],phi);
let rb=rotY(pts[b][0],pts[b][1],pts[b][2]*stretch,theta);rb=rotX(rb[0],rb[1],rb[2],phi);
return rb[2]-ra[2];
}});
for(let ii=0;ii<dc;ii++){{
const i=idxs[ii];
const rec=Math.pow((i+1)/dc,fade);
const sz=1.5+5*rec;
const al=80+175*rec;
const ct=(cts[Math.min(i,cts.length-1)]-cMin)/cRng;
const col=pc(ct);
let r=rotY(pts[i][0],pts[i][1],pts[i][2]*stretch,theta);
r=rotX(r[0],r[1],r[2],phi);
const pj=proj(r[0],r[1],r[2],W,H);
if(pj.sx<-50||pj.sx>W+50||pj.sy<-50||pj.sy>H+50)continue;
ctx.beginPath();ctx.arc(pj.sx,pj.sy,sz*pj.sz,0,Math.PI*2);
ctx.fillStyle='rgba('+col[0]+','+col[1]+','+col[2]+','+(al/255)+')';
ctx.fill();
}}
}}

// midpoint target
if(pan==='mid'&&dc>0){{
let r=rotY(tx,ty,tz,theta);r=rotX(r[0],r[1],r[2],phi);
const pj=proj(r[0],r[1],r[2],W,H);
if(pj.sx>0&&pj.sx<W&&pj.sy>0&&pj.sy<H){{
ctx.strokeStyle='rgba(255,215,0,.5)';ctx.lineWidth=1.5;
ctx.beginPath();ctx.arc(pj.sx,pj.sy,8,0,Math.PI*2);ctx.stroke();
ctx.fillStyle='rgba(255,215,0,.8)';
ctx.beginPath();ctx.arc(pj.sx,pj.sy,2.5,0,Math.PI*2);ctx.fill();
}}
}}
}}

function anim(){{
if(running)requestAnimationFrame(anim);
const t=play?getTime():pauseAt;
draw(t);
upUI(t);
if(t>=dur&&play){{
if(loop){{pauseAt=0;src=null;pl()}}else pause()
}}
}}
function getTime(){{return!play||!aCtx?pauseAt:aCtx.currentTime-startT+pauseAt}}
function b2a(b){{const s=atob(b),b2=new ArrayBuffer(s.length),v=new Uint8Array(b2);for(let i=0;i<s.length;i++)v[i]=s.charCodeAt(i);return b2}}
function initA(){{
if(aCtx)return;
aCtx=new(window.AudioContext||window.webkitAudioContext)();
gain=aCtx.createGain();gain.gain.value=vol;gain.connect(aCtx.destination);
const buf=b2a(D.b64);
aCtx.decodeAudioData(buf,function(b){{aBuf=b}},function(e){{console.error('Audio decode:',e)}});
if(aCtx.state==='suspended')aCtx.resume();
}}
function mkSrc(){{const s=aCtx.createBufferSource();s.buffer=aBuf;s.playbackRate.value=spd;s.connect(gain);return s}}
function pl(){{
initA();if(!aBuf)return;
if(aCtx.state==='suspended')aCtx.resume();
if(pauseAt>=dur)pauseAt=0;
src=mkSrc();src.start(0,pauseAt);startT=aCtx.currentTime;play=true;
document.getElementById('pb').innerHTML='⏸';
}}
function pause(){{
if(src){{pauseAt+=aCtx.currentTime-startT;src.stop();src.disconnect();src=null}}
play=false;document.getElementById('pb').innerHTML='▶';
}}
function tg(){{if(play)pause();else pl()}}
function seek(t){{t=Math.max(0,Math.min(t,dur));pauseAt=t;if(play){{if(src){{src.stop();src.disconnect()}}src=mkSrc();src.start(0,pauseAt);startT=aCtx.currentTime}}}}
function upUI(t){{
const m=Math.floor(t/60),s=Math.floor(t%60);
const tm=Math.floor(dur/60),ts=Math.floor(dur%60);
document.getElementById('tm').textContent=m+':'+s.toString().padStart(2,'0')+' / '+tm+':'+ts.toString().padStart(2,'0');
document.getElementById('sk').value=dur>0?(t/dur)*1000:0;
}}

// controllers
document.getElementById('pb').onclick=tg;
document.getElementById('lp').onclick=function(){{loop=!loop;this.style.opacity=loop?'1':'.4';this.style.background=loop?'linear-gradient(135deg,#ffd700,#ff8c00)':'linear-gradient(135deg,#00d2ff,#3a7bd5)'}};
document.getElementById('sk').oninput=function(){{const t=(parseFloat(this.value)/1000)*dur;pauseAt=t;if(play)seek(t)}};
document.getElementById('vl').oninput=function(){{vol=parseFloat(this.value)/100;document.getElementById('vlv').textContent=Math.round(vol*100)+'%';if(gain)gain.gain.setValueAtTime(vol,aCtx.currentTime)}};
document.getElementById('sd').oninput=function(){{spd=parseFloat(this.value);document.getElementById('sdv').textContent=spd+'x';if(src)src.playbackRate.setValueAtTime(spd,aCtx.currentTime)}};
document.getElementById('ob').oninput=function(){{orbit=parseFloat(this.value);document.getElementById('obv').textContent=orbit.toFixed(2)}};
document.getElementById('st').oninput=function(){{stretch=parseFloat(this.value);document.getElementById('stv').textContent=stretch.toFixed(1)}};
document.getElementById('sl').oninput=function(){{slices=parseInt(this.value);document.getElementById('slv').textContent=slices}};
document.getElementById('op').oninput=function(){{slOp=parseInt(this.value);document.getElementById('opv').textContent=slOp}};
document.getElementById('zm').oninput=function(){{zoom=parseInt(this.value);document.getElementById('zmv').textContent=zoom}};
document.getElementById('fd').oninput=function(){{fade=parseFloat(this.value)/10;document.getElementById('fdv').textContent=fade.toFixed(1)}};
document.getElementById('pn').onchange=function(){{pan=this.value}};
document.getElementById('fs').onclick=function(){{if(!document.fullscreenElement)vp.requestFullscreen();else document.exitFullscreen()}};
document.addEventListener('fullscreenchange',function(){{document.getElementById('fs').textContent=document.fullscreenElement?'✕':'⛶'}});
document.addEventListener('webkitfullscreenchange',function(){{document.getElementById('fs').textContent=document.fullscreenElement?'✕':'⛶'}});

document.onkeydown=function(e){{
if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;
switch(e.code){{
case'Space':e.preventDefault();tg();break;
case'ArrowLeft':seek(Math.max(0,pauseAt-5));break;
case'ArrowRight':seek(Math.min(dur,pauseAt+5));break;
case'ArrowUp':const vu=document.getElementById('vl');vu.value=Math.min(100,parseInt(vu.value)+5);vu.dispatchEvent(new Event('input'));break;
case'ArrowDown':const vd=document.getElementById('vl');vd.value=Math.max(0,parseInt(vd.value)-5);vd.dispatchEvent(new Event('input'));break;
}}
}};

vp.onmousedown=function(e){{md=true;mx=e.clientX;my=e.clientY;return false}};
document.onmousemove=function(e){{if(!md)return;const dx=e.clientX-mx,dy=e.clientY-my;mx=e.clientX;my=e.clientY;theta-=dx*.006;phi+=dy*.006;phi=Math.max(-1.3,Math.min(1.3,phi))}};
document.onmouseup=function(){{md=false}};
vp.addEventListener('wheel',function(e){{e.preventDefault();zoom=Math.max(5,Math.min(50,zoom+e.deltaY*.05));document.getElementById('zm').value=zoom;document.getElementById('zmv').textContent=Math.round(zoom)}},{{passive:false}});

initA();
anim();
}})();
</script>"""

st.components.v1.html(HTML, height=580)
