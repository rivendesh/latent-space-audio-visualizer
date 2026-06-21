import streamlit as st
import plotly.graph_objects as go
import numpy as np

from audio_processor import load_audio, compute_waveform_peaks
from latent_encoder import LatentEncoder
from realtime_component import build_realtime_component

st.set_page_config(page_title="Audio Latent Space Visualizer", page_icon="🎵", layout="wide")

st.title("🎵 Audio Latent Space Visualizer")
st.markdown("Upload an audio file to explore its waveform and 2D latent-space projection in real time.")

# ---------- sidebar ----------
with st.sidebar:
    st.header("Controls")
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=["wav", "mp3", "flac", "ogg", "m4a", "aiff"],
    )

    st.divider()
    st.markdown("### Settings")
    n_mels = st.slider("Mel bands", 32, 256, 128, 32,
                       help="Number of mel-frequency bands used for feature extraction.")
    hop_length = st.slider("Hop length", 128, 2048, 512, 128,
                           help="Step size (in samples) between analysis frames.  Lower = higher temporal resolution.")

    st.divider()
    st.markdown("### How it works")
    st.markdown(
        "The **latent space** is built by computing a mel-spectrogram over the entire "
        "audio, then running PCA to project each frame into 2D.  The result is a "
        "trajectory through the latent space that reveals the spectral evolution of the sound."
    )

# ---------- processing ----------
if uploaded_file is None:
    st.info("Upload an audio file in the sidebar to get started.", icon="🎤")
    st.stop()

file_bytes = uploaded_file.read()

with st.spinner("Processing audio …"):
    audio, sr = load_audio(file_bytes)
    encoder = LatentEncoder(n_mels=n_mels, hop_length=hop_length)
    latent_points, latent_times = encoder.encode(audio, sr)
    waveform_peaks = compute_waveform_peaks(audio)

duration = len(audio) / sr

# ---------- metrics row ----------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)
col_m1.metric("Duration", f"{duration:.1f}s")
col_m2.metric("Sample Rate", f"{sr} Hz")
col_m3.metric("Latent Frames", f"{len(latent_points)}")
col_m4.metric("Expl. Variance (2D)", f"{sum(encoder.explained_variance_ratio):.1%}" if encoder.explained_variance_ratio else "—")

# ---------- tabs ----------
tab1, tab2 = st.tabs(["📊 Static Analysis", "🎬 Real-Time Player"])

with tab1:
    t = st.slider(
        "Time (seconds)",
        min_value=0.0,
        max_value=duration,
        value=0.0,
        step=0.05,
        key="static_time",
    )

    col_left, col_right = st.columns(2)

    with col_left:
        wave_fig = _build_waveform_figure(audio, sr, t)
        st.plotly_chart(wave_fig, use_container_width=True)

    with col_right:
        latent_fig = _build_latent_figure(latent_points, latent_times, t)
        st.plotly_chart(latent_fig, use_container_width=True)

    st.audio(file_bytes)

with tab2:
    st.markdown(
        "Press **Play** to hear the audio while the waveform and latent-space "
        "visualizations update in real time."
    )

    html = build_realtime_component(
        audio=audio,
        sr=sr,
        latent_points=latent_points,
        latent_times=latent_times,
        waveform_peaks=waveform_peaks,
    )
    st.components.v1.html(html, height=620)


# ---------- plotting helpers ----------
def _build_waveform_figure(audio, sr, current_time):
    t_axis = np.arange(len(audio)) / sr
    duration = len(audio) / sr

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_axis,
        y=audio,
        mode="lines",
        line=dict(color="rgba(0,210,255,0.6)", width=1),
        fill="tozeroy",
        fillcolor="rgba(0,210,255,0.08)",
        name="Waveform",
    ))

    # cursor
    cursor_idx = int(current_time * sr)
    cursor_idx = min(cursor_idx, len(audio) - 1)
    fig.add_vline(
        x=current_time,
        line=dict(color="white", width=2, dash="solid"),
        annotation_text=f"{current_time:.2f}s",
        annotation_position="top right",
    )

    fig.update_layout(
        title="Waveform",
        xaxis_title="Time (s)",
        yaxis_title="Amplitude",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="x",
    )
    fig.update_xaxes(range=[0, duration])
    return fig


def _build_latent_figure(latent_points, latent_times, current_time):
    n = len(latent_points)
    t_frac = np.linspace(0, 1, n) if n > 1 else np.array([0])
    colors = [[0, "rgb(0,210,255)"], [0.5, "rgb(123,47,247)"], [1, "rgb(255,107,107)"]]

    fig = go.Figure()

    # trajectory line
    fig.add_trace(go.Scatter(
        x=latent_points[:, 0],
        y=latent_points[:, 1],
        mode="lines",
        line=dict(color="rgba(255,255,255,0.15)", width=2),
        showlegend=False,
        hoverinfo="skip",
    ))

    # trajectory markers colored by time
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

    # current position
    cur_pos = _interpolate_latent(latent_points, latent_times, current_time)
    fig.add_trace(go.Scatter(
        x=[cur_pos[0]],
        y=[cur_pos[1]],
        mode="markers",
        marker=dict(size=14, color="#ffd700", line=dict(width=2, color="#fff")),
        name=f"t = {current_time:.2f}s",
    ))

    fig.update_layout(
        title="Latent Space (2D PCA projection)",
        xaxis_title="Component 1",
        yaxis_title="Component 2",
        height=280,
        margin=dict(l=0, r=0, t=40, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ccc"),
        xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", scaleanchor="y"),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)"),
        hovermode="closest",
    )
    return fig


def _interpolate_latent(points, times, t):
    n = len(times)
    if n == 0:
        return [0, 0]
    if t <= times[0]:
        return points[0]
    if t >= times[-1]:
        return points[-1]
    idx = np.searchsorted(times, t) - 1
    idx = max(0, min(idx, n - 2))
    t0, t1 = times[idx], times[idx + 1]
    frac = (t - t0) / (t1 - t0 + 1e-10)
    return points[idx] + frac * (points[idx + 1] - points[idx])
