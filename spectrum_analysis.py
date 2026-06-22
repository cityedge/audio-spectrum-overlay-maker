# -*- coding: utf-8 -*-
"""Audio spectrum analysis layer.

This layer converts decoded audio samples into internal SpectrumData.  It keeps
FFT, frequency-band allocation, and raw dB matrix construction separate from
both display transformations and final drawing.
"""
from __future__ import annotations

import math
from typing import List

import numpy as np

from spectrum_types import LogFn, MotionSettings, RenderStyle, SpectrumData, TransformSettings
from spectrum_utils import log
from spectrum_motion import map_db_to_dynamic_values
from spectrum_transform import transform_spectrum_data

def build_band_indices(sample_rate: int, fft_size: int, bars: int, freq_min: float, freq_max: float) -> List[np.ndarray]:
    """Build non-overlapping FFT-bin groups for logarithmic spectrum bars.

    Earlier prototypes used nearest-bin fallback for empty low-frequency bands.
    With a narrow auto range such as 20-3000 Hz, adjacent low bands could resolve
    to the same FFT bin, making pairs of bars move identically.  This version
    forces monotonic bin boundaries where there are enough bins, so each bar gets
    a distinct frequency region.
    """
    nyquist = sample_rate / 2.0
    freq_max = min(freq_max, nyquist)
    if freq_min <= 0 or freq_min >= freq_max:
        raise ValueError(f"Invalid frequency range: {freq_min} - {freq_max}")

    freqs = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    start_bin = int(np.searchsorted(freqs, freq_min, side="left"))
    end_bin = int(np.searchsorted(freqs, freq_max, side="right"))
    start_bin = max(1, min(start_bin, len(freqs) - 1))
    end_bin = max(start_bin + 1, min(end_bin, len(freqs)))

    available = end_bin - start_bin
    if available >= bars:
        edges = np.geomspace(max(freq_min, freqs[start_bin]), min(freq_max, freqs[end_bin - 1]), bars + 1)
        raw = np.searchsorted(freqs, edges, side="left").astype(np.int64)
        raw[0] = start_bin
        raw[-1] = end_bin
        # Enforce one-or-more bins per bar.
        for i in range(1, bars + 1):
            min_allowed = raw[i - 1] + 1
            remaining = bars - i
            max_allowed = end_bin - remaining
            raw[i] = int(np.clip(raw[i], min_allowed, max_allowed))
        band_indices = [np.arange(raw[i], raw[i + 1], dtype=np.int64) for i in range(bars)]
    else:
        # Extremely narrow ranges: create unique nearest-bin assignments as far
        # as possible, then repeat the last bin only as a final fallback.
        indices = np.linspace(start_bin, end_bin - 1, bars)
        indices = np.round(indices).astype(np.int64)
        indices = np.clip(indices, start_bin, end_bin - 1)
        band_indices = [np.array([idx], dtype=np.int64) for idx in indices]
    return band_indices

def build_frequency_edges(sample_rate: int, analysis_bars: int, freq_min: float, freq_max: float) -> np.ndarray:
    """Return log-spaced frequency edges for metadata.

    The FFT-bin allocator may adjust the exact bins for stability, but these
    edges define the intended frequency meaning of each internal band.
    """
    nyquist = sample_rate / 2.0
    hi = min(float(freq_max), nyquist)
    lo = max(1.0, float(freq_min))
    if lo >= hi:
        hi = min(nyquist, lo + 1.0)
    return np.geomspace(lo, hi, int(analysis_bars) + 1).astype(np.float32)

def analyze_spectrum_data(audio: np.ndarray, style: RenderStyle, motion: MotionSettings, log_callback: LogFn = None) -> SpectrumData:
    """Analyze audio into generic internal SpectrumData.

    This is the analysis layer.  It deliberately returns internal values before
    display-bar aggregation so future visual styles can choose their own
    resolution and transformation.
    """
    sample_rate = motion.sample_rate
    fps = style.fps
    display_bars = int(style.bars)
    analysis_bars = max(display_bars, int(getattr(motion, "analysis_bands", 64) or 64))
    fft_size = motion.fft_size
    hop = sample_rate / float(fps)
    frame_count = int(math.ceil(audio.size / hop))
    if frame_count <= 0:
        raise RuntimeError("Frame count became zero.")

    log(f"Analysis: {audio.size / sample_rate:.2f}s / {frame_count:,} frames / analysis {analysis_bars} bands", log_callback)
    log(f"Frequency range: {motion.freq_min:g} - {min(motion.freq_max, sample_rate/2):g} Hz", log_callback)

    half = fft_size // 2
    padded = np.pad(audio, (half, half + fft_size), mode="constant")
    window = np.hanning(fft_size).astype(np.float32)
    window_norm = float(np.sum(window) / 2.0) or float(fft_size / 2)
    band_indices = build_band_indices(sample_rate, fft_size, analysis_bars, motion.freq_min, motion.freq_max)

    db_values = np.zeros((frame_count, analysis_bars), dtype=np.float32)
    chunk_frames = 512
    itemsize = padded.dtype.itemsize

    for start_frame in range(0, frame_count, chunk_frames):
        end_frame = min(frame_count, start_frame + chunk_frames)
        n = end_frame - start_frame
        start_sample = int(round(start_frame * hop))
        local = padded[start_sample : start_sample + int(round((n - 1) * hop)) + fft_size]

        if abs(hop - round(hop)) < 1e-9:
            hop_i = int(round(hop))
            frames = np.lib.stride_tricks.as_strided(
                local,
                shape=(n, fft_size),
                strides=(hop_i * itemsize, itemsize),
                writeable=False,
            )
        else:
            indices = (
                np.round(np.arange(start_frame, end_frame) * hop).astype(np.int64)[:, None]
                + np.arange(fft_size, dtype=np.int64)[None, :]
            )
            frames = padded[indices]

        spectrum = np.fft.rfft(frames * window[None, :], axis=1)
        magnitude = np.abs(spectrum).astype(np.float32) / window_norm

        band_values = np.zeros((n, analysis_bars), dtype=np.float32)
        for b, idx in enumerate(band_indices):
            m = magnitude[:, idx]
            band_values[:, b] = np.sqrt(np.mean(m * m, axis=1))

        db_values[start_frame:end_frame, :] = 20.0 * np.log10(np.maximum(band_values, 1.0e-8)) + motion.gain_db

        if frame_count >= 1000 and (start_frame == 0 or end_frame == frame_count or end_frame % (chunk_frames * 10) == 0):
            log(f"Analyzing: {100.0 * end_frame / frame_count:5.1f}%", log_callback)

    internal_values = map_db_to_dynamic_values(db_values, motion)
    freq_edges = build_frequency_edges(sample_rate, analysis_bars, motion.freq_min, motion.freq_max)
    return SpectrumData(
        values=internal_values,
        raw_db=db_values,
        freq_edges=freq_edges,
        fps=int(fps),
        sample_rate=int(sample_rate),
        analysis_bands=int(analysis_bars),
        freq_min=float(motion.freq_min),
        freq_max=float(min(motion.freq_max, sample_rate / 2.0)),
    )

def analyze_bars(audio: np.ndarray, style: RenderStyle, motion: MotionSettings, log_callback: LogFn = None) -> np.ndarray:
    """Compatibility wrapper: analysis layer + default transformation layer."""
    data = analyze_spectrum_data(audio, style, motion, log_callback)
    return transform_spectrum_data(data, TransformSettings(display_bars=style.bars))

