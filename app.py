import argparse
import os
import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import numpy as np
import librosa

from audio_processor import load_audio, compute_waveform_peaks
from latent_encoder import LatentEncoder
from realtime_component import build_realtime_component
from realtime_3d import build_3d_component


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

# ---------- theme state: inject light/dark CSS before sidebar renders ----------
if "app_theme" not in st.session_state:
    st.session_state.app_theme = "Dark"

is_dark = st.session_state.app_theme == "Dark"
if not is_dark:
    st.markdown("""
    <style>
    .stApp { background: #f0f2f5 !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp .stMarkdown,
    .stApp .stMetric label, .stApp .stMetric value,
    .stApp .stTabs button {
        color: #333 !important;
    }
    .stSidebar { background: #e8eaed !important; }
    .stSidebar .stMarkdown { color: #333 !important; }
    .stSidebar .stMarkdown p { word-break: break-word; overflow-wrap: break-word; }
    .stSidebar .stMarkdown code { word-break: break-all; white-space: pre-wrap; }
    </style>
    """, unsafe_allow_html=True)

# Scrollable tab content
st.markdown("""
<style>
div[data-testid="stTabContent"] > div {
    overflow-y: auto;
    max-height: calc(100vh - 200px);
}
</style>
""", unsafe_allow_html=True)

st.title("Audio Latent Space Visualizer")
st.markdown("Upload an audio file to explore its waveform and 2D latent-space projection in real time.")

# ---------- sidebar: file uploader, mel/hop/playback settings, theme selector ----------
with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
    )

    if uploaded_file is None and "auto_file" in st.session_state:
        st.success(f"Loaded: {st.session_state['auto_file_name']}")

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
    st.markdown("### Appearance")
    sel = st.select_slider("Theme", options=["Dark", "Light"], value=st.session_state.app_theme, key="app_theme")
    # update is_dark used below
    is_dark = (sel == "Dark")

    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "The **latent space** is built by computing a mel-spectrogram over the entire "
        "audio, then running PCA to project each frame into 2D.  The result is a "
        "trajectory through the latent space that reveals the spectral evolution of the sound."
    )

# ---------- Plotly figure builders for waveform, FFT, and latent-space scatter ----------
_HIGH_RES_CONFIG = {
    "toImageButtonOptions": {
        "format": "png",
        "width": 3840,
        "height": 2160,
        "scale": 2,
    },
    "displayModeBar": True,
    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
}


def _build_waveform_figure(audio, sr):
    t_axis = np.arange(len(audio)) / sr
    dur = len(audio) / sr

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_axis,
        y=audio,
        mode="lines",
        line=dict(color="rgba(0,210,255,0.5)", width=1),
        fill="tozeroy",
        fillcolor="rgba(0,210,255,0.06)",
        name="Waveform",
    ))

    fig.update_layout(
        title="Waveform",
        xaxis_title="Time (s)",
        yaxis_title="Amplitude",
        height=180,
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc", size=10),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="x",
    )
    fig.update_xaxes(range=[0, dur])
    return fig


def _build_fft_figure(audio, sr):
    n_fft = 2048
    hop_length = n_fft // 4
    S = np.abs(librosa.stft(audio, n_fft=n_fft, hop_length=hop_length))
    avg_mag = np.mean(S, axis=1)
    avg_mag_db = librosa.amplitude_to_db(avg_mag, ref=np.max)
    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=freqs,
        y=avg_mag_db,
        mode="lines",
        line=dict(color="#ff6b6b", width=1),
        fill="tozeroy",
        fillcolor="rgba(255,107,107,0.08)",
        name="Avg Spectrum",
    ))

    fig.update_layout(
        title="Frequency Spectrum",
        xaxis_title="Frequency (Hz)",
        yaxis_title="Magnitude (dB)",
        height=180,
        margin=dict(l=0, r=0, t=36, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc", size=10),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            type="log",
            range=[np.log10(20), np.log10(sr / 2)],
        ),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="x",
    )
    return fig


def _build_latent_figure(latent_points):
    n = len(latent_points)
    t_frac = np.linspace(0, 1, n) if n > 1 else np.array([0])
    colors = [[0, "rgb(0,210,255)"], [0.5, "rgb(123,47,247)"], [1, "rgb(255,107,107)"]]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=latent_points[:, 0],
        y=latent_points[:, 1],
        mode="lines",
        line=dict(color="rgba(255,255,255,0.12)", width=2),
        showlegend=False,
        hoverinfo="skip",
    ))

    fig.add_trace(go.Scatter(
        x=latent_points[:, 0],
        y=latent_points[:, 1],
        mode="markers",
        marker=dict(
            size=4,
            color=t_frac,
            colorscale=colors,
            showscale=True,
            colorbar=dict(title="Time", len=0.6, x=1.02),
            line=dict(width=0),
        ),
        name="Trajectory",
    ))

    fig.update_layout(
        title="Latent Space (2D PCA projection)",
        xaxis_title="Component 1",
        yaxis_title="Component 2",
        height=480,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", scaleanchor="y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="closest",
    )
    return fig


# ---------- processing: load audio, run encoder, compute waveform peaks ----------
auto_file = st.session_state.get("auto_file")

if uploaded_file is not None:
    file_bytes = uploaded_file.read()
elif auto_file is not None:
    file_bytes = auto_file
else:
    st.info("Upload an audio file in the sidebar to get started.")
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

# ---------- download helper ----------
def _st_download_html(fig, filename, label):
    import plotly.io as pio
    html_str = pio.to_html(fig, include_plotlyjs="cdn", full_html=False)
    st.download_button(
        label=f"Download {label}",
        data=html_str,
        file_name=filename,
        mime="text/html",
        width='stretch',
    )


# ---------- tabs: Static Analysis | Real-Time Player | 3D Render ----------
tab1, tab2, tab3 = st.tabs(["Static Analysis", "2D Player", "3D Manifold"])

with tab1:
    latent_fig = _build_latent_figure(latent_points)
    st.plotly_chart(latent_fig, config=_HIGH_RES_CONFIG, width='stretch')

    col_wave, col_fft = st.columns(2)

    with col_wave:
        wave_fig = _build_waveform_figure(audio, sr)
        st.plotly_chart(wave_fig, config=_HIGH_RES_CONFIG, width='stretch')

    with col_fft:
        fft_fig = _build_fft_figure(audio, sr)
        st.plotly_chart(fft_fig, config=_HIGH_RES_CONFIG, width='stretch')

    st.audio(file_bytes)

    with st.expander("Download plots", expanded=False):
        dl_col1, dl_col2, dl_col3 = st.columns(3)
        with dl_col1:
            _st_download_html(latent_fig, "latent_space.html", "Latent Space")
        with dl_col2:
            _st_download_html(wave_fig, "waveform.html", "Waveform")
        with dl_col3:
            _st_download_html(fft_fig, "frequency_spectrum.html", "Frequency Spectrum")

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
    html = build_realtime_component(
        audio=pb_audio,
        sr=sr,
        latent_points=pb_latent,
        latent_times=pb_times,
        waveform_peaks=pb_peaks,
    )
    st.components.v1.html(html, height=680)

with tab3:
    html_3d = build_3d_component(
        audio=pb_audio,
        sr=sr,
        latent_points=pb_latent,
        latent_times=pb_times,
        centroids=pb_centroids,
        rms=pb_rms,
        waveform_peaks=pb_peaks,
        is_dark=is_dark,
    )
    st.components.v1.html(html_3d, height=960)
