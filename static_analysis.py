import numpy as np
import plotly.graph_objects as go
import streamlit as st
import librosa


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


def render_static_analysis_tab(audio, sr, latent_points, file_bytes):
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
