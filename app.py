import argparse
import os
from pathlib import Path

import streamlit as st
import numpy as np

from utils.audio_utils import load_audio, compute_waveform_peaks
from utils.latent_utils import LatentEncoder
from static_analysis import render_static_analysis_tab
from render_2d import build_render_2d


def _parse_cli_args():
    parser = argparse.ArgumentParser(description="Audio Latent Space Visualizer", add_help=False)
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
    else:
        msg = f"File not found: {_AUTO_PATH}"
        if CLI_ARGS.file:
            st.error(msg)
        else:
            st.warning(f"AUDIO_FILE={_AUTO_PATH} not found")

st.set_page_config(page_title="Audio Latent Space Visualizer", layout="wide")
HAS_AUTO = "auto_file" in st.session_state

st.title("Audio Latent Space Visualizer")

with st.sidebar:
    st.header("Controls")
    if HAS_AUTO:
        st.success(f"Loaded: {st.session_state['auto_file_name']}")
        uploaded_file = st.file_uploader(
            "Replace audio file",
            type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
        )
    else:
        uploaded_file = None

    st.divider()
    st.markdown("### Settings")
    n_mels = st.slider("Mel bands", 32, 256, 128, 32)
    hop_length = st.slider("Hop length", 128, 2048, 512, 128)
    max_playback = st.slider("Max playback (s)", 10, 600, 120, 10)

if not HAS_AUTO:
    main_uf = st.file_uploader(
        "Choose an audio file",
        type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
    )
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
    audio, sr = load_audio(file_bytes)
    encoder = LatentEncoder(n_mels=n_mels, hop_length=hop_length)
    latent_points, latent_times, centroids, rms = encoder.encode(audio, sr)
    waveform_peaks = compute_waveform_peaks(audio)
    expl_var = (
        sum(encoder.explained_variance_ratio)
        if encoder.explained_variance_ratio is not None
        else None
    )
    return audio, sr, latent_points, latent_times, centroids, rms, waveform_peaks, expl_var


with st.spinner("Processing audio …"):
    audio, sr, latent_points, latent_times, centroids, rms, waveform_peaks, expl_var_ratio = (
        _process_audio(file_bytes, n_mels, hop_length)
    )

duration = len(audio) / sr

col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Duration", f"{duration:.1f}s")
col_m2.metric("Sample Rate", f"{sr} Hz")
col_m3.metric("Latent Frames", f"{len(latent_points)}")
col_m4.metric("Expl. Variance (2D)", f"{expl_var_ratio:.1%}" if expl_var_ratio else "—")

tab1, tab2 = st.tabs(["Static Analysis", "Real-Time Player"])

with tab1:
    render_static_analysis_tab(audio, sr, latent_points, latent_times, file_bytes)

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
        centroids=pb_centroids,
        rms=pb_rms,
        waveform_peaks=pb_peaks,
    )
    st.components.v1.html(html, height=800)
