import argparse
import os
import sys
from pathlib import Path

import streamlit as st
import numpy as np

from utils.audio_utils import load_audio, compute_waveform_peaks
from utils.latent_utils import LatentEncoder
from static_analysis import render_static_analysis_tab
from render_2d import build_render_2d
from render_3d import build_render_3d


# ---------- CLI args: support --file / -f and AUDIO_FILE env var ----------
def _parse_cli_args():
    parser = argparse.ArgumentParser(
        description="Audio Latent Space Visualizer",
        add_help=False,
    )
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

if _AUTO_PATH is not None:
    if _AUTO_PATH.exists():
        st.session_state.setdefault("auto_file", _AUTO_PATH.read_bytes())
        st.session_state.setdefault("auto_file_name", _AUTO_PATH.name)
        st.session_state.setdefault("auto_file_path", str(_AUTO_PATH.resolve()))
    else:
        msg = f"File not found: {_AUTO_PATH}"
        if CLI_ARGS.file:
            st.error(msg)
        else:
            st.warning(f"AUDIO_FILE={_AUTO_PATH} not found")

st.set_page_config(page_title="Audio Latent Space Visualizer", layout="wide")

HAS_AUTO = "auto_file" in st.session_state

# ---------- inject global CSS ----------

# Scrollable tab content
st.markdown("""
<style>
div[data-testid="stTabContent"] > div {
    overflow-y: auto;
    max-height: none;
}
section[data-testid="stSidebar"] .stMarkdown p { word-break: break-word; overflow-wrap: break-word; }
section[data-testid="stSidebar"] .stMarkdown code { word-break: break-all; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

st.title("Audio Latent Space Visualizer")

# ---------- sidebar: file uploader (auto-mode only), mel/hop/playback settings ----------
with st.sidebar:
    st.header("Controls")
    if HAS_AUTO:
        st.success(f"Loaded: {st.session_state['auto_file_name']}")
        uploaded_file = st.file_uploader(
            "Replace audio file",
            type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
            key="sidebar_uploader",
        )
    else:
        uploaded_file = None

    st.divider()
    st.markdown("### Settings")
    n_mels = st.slider("Mel bands", 32, 256, 128, 32,
                       help="Number of mel-frequency bands fed into PCA. "
                            "More bands (128-256) capture finer spectral detail "
                            "but produce a noisier, higher-dimensional latent trajectory. "
                            "Fewer bands (32-64) smooth out the trajectory, "
                            "revealing only the coarsest timbral shifts.")
    hop_length = st.slider("Hop length", 128, 2048, 512, 128,
                           help="Sample distance between consecutive analysis frames. "
                                "Smaller values (128-256) yield a dense, high-resolution "
                                "latent path at the cost of more PCA points. "
                                "Larger values (1024-2048) produce a coarser, faster-to-compute "
                                "trajectory. Use low hop for percussive/quickly-changing audio, "
                                "high hop for steady drones or long samples.")

    max_playback = st.slider("Max playback (s)", 10, 600, 120, 10,
                             help="Long audio is truncated to this duration for the "
                                  "Real-Time Player to stay within Streamlit's 200 MB "
                                  "message size limit.  The Static Analysis tab always "
                                  "uses the full file.")

    st.divider()
    st.markdown("### Launch with a file")
    st.code("streamlit run app.py -- -f song.wav", language="bash")
    st.markdown("Also `AUDIO_FILE=song.wav streamlit run app.py`.")

    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "The **latent space** is built by computing a mel-spectrogram over the entire "
        "audio, then running PCA to project each frame into 2D.  The result is a "
        "trajectory through the latent space that reveals the spectral evolution of the sound."
    )

# ---------- file uploader (main page) when not launched with a CLI argument ----------
if not HAS_AUTO:
    main_uf = st.file_uploader(
        "Choose an audio file",
        type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
        key="main_uploader",
    )
    if main_uf is not None:
        uploaded_file = main_uf

# ---------- processing: load audio, run encoder, compute waveform peaks ----------
auto_file = st.session_state.get("auto_file")

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
elif auto_file is not None:
    file_bytes = auto_file
else:
    st.info("Upload an audio file to get started.")
    st.stop()

with st.spinner("Processing audio …"):
    audio, sr = load_audio(file_bytes)
    encoder = LatentEncoder(n_mels=n_mels, hop_length=hop_length)
    latent_points, latent_times, centroids, rms = encoder.encode(audio, sr)
    waveform_peaks = compute_waveform_peaks(audio)

duration = len(audio) / sr

# ---------- metrics row ----------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Duration", f"{duration:.1f}s")
col_m2.metric("Sample Rate", f"{sr} Hz")
col_m3.metric("Latent Frames", f"{len(latent_points)}")
col_m4.metric("Expl. Variance (2D)", f"{sum(encoder.explained_variance_ratio):.1%}" if encoder.explained_variance_ratio else "—")

# ---------- tabs: Static Analysis | Real-Time Player | 3D Render ----------
tab1, tab2, tab3 = st.tabs(["Static Analysis", "2D Player", "3D Manifold"])

with tab1:
    render_static_analysis_tab(audio, sr, latent_points, file_bytes)

# ---------- truncate audio and latent data to max_playback for the real-time tabs ----------
max_samples = int(max_playback * sr)
if len(audio) > max_samples:
    pb_audio = audio[:max_samples]
    pb_n = np.searchsorted(latent_times, max_playback) + 1
    pb_latent = latent_points[:pb_n]
    pb_times = latent_times[:pb_n]
    pb_peaks = compute_waveform_peaks(pb_audio)
    pb_centroids = centroids[:pb_n]
    pb_rms = rms[:pb_n]
    st.caption(
        f"Real-Time Player uses the first {max_playback}s "
        f"({pb_n} frames) of {duration:.0f}s total."
    )
else:
    pb_audio = audio
    pb_latent = latent_points
    pb_times = latent_times
    pb_peaks = waveform_peaks
    pb_centroids = centroids
    pb_rms = rms

with tab2:
    html = build_render_2d(
        audio=pb_audio,
        sr=sr,
        latent_points=pb_latent,
        latent_times=pb_times,
        waveform_peaks=pb_peaks,
    )
    st.components.v1.html(html, height=680)

with tab3:
    st.subheader("3D Latent Space Manifold")
    html_3d = build_render_3d(
        audio=pb_audio,
        sr=sr,
        latent_points=pb_latent,
        latent_times=pb_times,
        centroids=pb_centroids,
        rms=pb_rms,
        waveform_peaks=pb_peaks,
    )
    st.components.v1.html(html_3d, height=3500)
