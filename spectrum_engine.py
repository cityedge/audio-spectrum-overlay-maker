# -*- coding: utf-8 -*-
"""Rendering engine for Audio Spectrum Overlay Maker v1.0-alpha1.

This module contains no GUI code.  It keeps the stable Dynamic spectrum
logic from the v0.9 prototype, with neutral public-facing names.
"""
from __future__ import annotations

import math
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict, replace
from pathlib import Path
from typing import Callable, Iterable, List, Tuple

import numpy as np

VERSION = "1.0.0"
RGB = Tuple[int, int, int]
LogFn = Callable[[str], None] | None


@dataclass
class RenderStyle:
    width: int = 720
    height: int = 280
    fps: int = 30
    bars: int = 24
    background_color: RGB = (0, 0, 0)
    bar_color: RGB = (255, 255, 255)
    max_height_ratio: float = 0.78
    bottom_margin_ratio: float = 0.08
    side_margin_ratio: float = 0.05
    bar_width_scale: float = 0.62
    corner_radius: int = 18
    gamma: float = 0.85


@dataclass
class MotionSettings:
    sample_rate: int = 24000
    fft_size: int = 1024
    analysis_bands: int = 64
    freq_min: float = 80.0
    freq_max: float = 12000.0
    min_db: float = -60.0
    max_db: float = -6.0
    gain_db: float = 8.0
    attack: float = 0.95
    release: float = 0.75
    relative_range_db: float = 30.0
    peak_percentile: float = 90.0
    base_cut: float = 0.12
    pulse_amount: float = 0.80
    pulse_speed: float = 0.25


@dataclass
class EncodeSettings:
    crf: int = 18
    preset: str = "veryfast"
    encoder: str = "libx264"


@dataclass
class SpectrumData:
    """Generic analysis-layer output.

    `values` are Dynamic-processed internal spectrum values in 0..1.
    They are intentionally not tied to the final display bar count.
    `raw_db` keeps the pre-Dynamic dB matrix for future visualizers.
    """
    values: np.ndarray
    raw_db: np.ndarray
    freq_edges: np.ndarray
    fps: int
    sample_rate: int
    analysis_bands: int
    freq_min: float
    freq_max: float


@dataclass
class TransformSettings:
    """Transformation-layer settings between analysis and drawing."""
    display_bars: int = 24
    shape_profile: str = "neutral"  # future: neutral / mountain / valley
    scroll_offset: int = 0


def log(message: str, callback: LogFn = None) -> None:
    if callback:
        callback(message)
    else:
        print(message, flush=True)


def check_environment() -> tuple[bool, str]:
    missing = []
    if shutil.which("ffmpeg") is None:
        missing.append("ffmpeg")
    if shutil.which("ffprobe") is None:
        missing.append("ffprobe")
    if missing:
        return False, "Missing from PATH: " + ", ".join(missing)
    return True, "OK"


def parse_color(value: str | None, default: RGB = (0, 0, 0)) -> RGB:
    if value is None or str(value).strip() == "":
        return default
    text = str(value).strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        raise ValueError(f"Invalid color: {value}. Use #RRGGBB.")
    return (int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16))


def color_to_hex(color: RGB) -> str:
    return "#%02X%02X%02X" % tuple(int(np.clip(c, 0, 255)) for c in color)


def unique_path(path: Path) -> Path:
    """Return a non-existing path by appending ' (1)', ' (2)', ... if needed."""
    path = Path(path)
    if not path.exists():
        return path
    parent = path.parent
    stem = path.stem
    suffix = path.suffix
    for i in range(1, 10000):
        candidate = parent / f"{stem} ({i}){suffix}"
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not create a unique filename for: {path}")


def run_ffprobe_duration(path: Path) -> float | None:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        value = proc.stdout.strip()
        if not value:
            return None
        duration = float(value)
        if math.isfinite(duration) and duration > 0:
            return duration
    except Exception:
        return None
    return None


def decode_audio_to_float32_mono(path: Path, sample_rate: int, start: float, duration: float | None, log_callback: LogFn = None) -> np.ndarray:
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error"]
    if start > 0:
        cmd += ["-ss", f"{start:.6f}"]
    cmd += ["-i", str(path)]
    if duration is not None and duration > 0:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += [
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1",
    ]
    log("Loading audio...", log_callback)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        stderr = proc.stderr.decode("utf-8", errors="replace")
        raise RuntimeError("Failed to load audio with ffmpeg.\n" + stderr)
    if not proc.stdout:
        raise RuntimeError("No audio data was loaded.")
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    audio = np.clip(audio, -1.0, 1.0)
    if audio.size == 0:
        raise RuntimeError("No audio samples were found.")
    return audio


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


def map_db_to_dynamic_values(
    db: np.ndarray,
    motion: MotionSettings,
) -> np.ndarray:
    """Map per-frame/per-band dB values to 0..1 Dynamic bar values.

    This is the public-name equivalent of the stable v0.9 Filmora-like mode:
    per-frame relative peak normalization + temporal pulse/baseline emphasis.
    """
    rng = max(6.0, float(motion.relative_range_db))
    pct = float(np.clip(motion.peak_percentile, 50.0, 99.5))
    peak = np.percentile(db, pct, axis=1, keepdims=True)
    floor = peak - rng
    rel = np.clip((db - floor) / rng, 0.0, 1.0)

    cut = float(np.clip(motion.base_cut, 0.0, 0.80))
    if cut > 0:
        rel = np.clip((rel - cut) / (1.0 - cut), 0.0, 1.0)

    # Absolute energy gate.
    #
    # Relative peak normalization alone is not enough for silence: when all FFT
    # bands are near the noise floor, the "relative" values can still become
    # high because every band is close to the frame peak.  Earlier versions kept
    # a minimum gate of 0.18, which left small bars visible in near-silent parts.
    # Here the gate reaches true zero below min_db, while still fading in
    # smoothly for quiet musical passages.
    denom = max(1.0e-6, float(motion.max_db - motion.min_db))
    energy = np.clip((peak - motion.min_db) / denom, 0.0, 1.0)
    gate = energy * energy * (3.0 - 2.0 * energy)  # smoothstep, 0..1
    values = np.clip(rel * gate, 0.0, 1.0).astype(np.float32)

    # Temporal trough/pulse emphasis.
    pulse_amount = float(np.clip(motion.pulse_amount, 0.0, 1.0))
    pulse_speed = float(np.clip(motion.pulse_speed, 0.01, 0.95))
    if pulse_amount > 0:
        frame_count, bars = values.shape
        pulsed = np.zeros_like(values)
        baseline = np.zeros((bars,), dtype=np.float32)
        for i in range(frame_count):
            v = values[i]
            baseline = baseline + (v - baseline) * pulse_speed
            diff = np.maximum(v - baseline, 0.0)
            denom = np.maximum(1.0 - baseline, 1.0e-4)
            p = np.clip(diff / denom, 0.0, 1.0)
            pulsed[i] = (1.0 - pulse_amount) * v + pulse_amount * p
        values = pulsed

    return smooth_values(values, motion.attack, motion.release)


def smooth_values(values: np.ndarray, attack: float, release: float) -> np.ndarray:
    attack = float(np.clip(attack, 0.01, 1.0))
    release = float(np.clip(release, 0.01, 1.0))
    smoothed = np.zeros_like(values)
    current = np.zeros((values.shape[1],), dtype=np.float32)
    for i in range(values.shape[0]):
        target = values[i]
        coeff = np.where(target >= current, attack, release).astype(np.float32)
        current = current + (target - current) * coeff
        smoothed[i] = current
    return smoothed



def aggregate_analysis_bars(values: np.ndarray, display_bars: int) -> np.ndarray:
    """Convert fixed internal analysis bars to display bars.

    This is now part of the transformation layer rather than the analysis layer.
    A top-mean blend keeps the Filmora-like responsiveness even when the
    display bar count is low, avoiding slow motion caused by wide-band averaging.
    """
    values = np.asarray(values, dtype=np.float32)
    frames, analysis_bars = values.shape
    display_bars = int(display_bars)
    if display_bars <= 0:
        raise ValueError("display_bars must be positive")
    if analysis_bars == display_bars:
        return values.copy()
    out = np.zeros((frames, display_bars), dtype=np.float32)
    edges = np.linspace(0, analysis_bars, display_bars + 1)
    last_hi = 0
    for i in range(display_bars):
        lo = int(round(edges[i]))
        hi = int(round(edges[i + 1]))
        lo = max(last_hi, min(lo, analysis_bars - 1))
        hi = max(lo + 1, min(hi, analysis_bars))
        last_hi = hi
        block = values[:, lo:hi]
        if block.shape[1] == 1:
            out[:, i] = block[:, 0]
        else:
            k = max(1, int(math.ceil(block.shape[1] * 0.35)))
            top = np.partition(block, block.shape[1] - k, axis=1)[:, -k:]
            top_mean = top.mean(axis=1)
            mean = block.mean(axis=1)
            out[:, i] = np.clip(0.35 * mean + 0.65 * top_mean, 0.0, 1.0)
    return out


def apply_shape_profile(values: np.ndarray, profile: str = "neutral") -> np.ndarray:
    """Apply position-based visual weighting.

    Currently used as a neutral pass-through, but it is intentionally placed in
    the transformation layer so future mountain/valley profiles can be added
    without touching audio analysis.
    """
    profile = (profile or "neutral").lower()
    if profile in {"neutral", "none", "flat"}:
        return np.asarray(values, dtype=np.float32)
    vals = np.asarray(values, dtype=np.float32)
    bars = vals.shape[1]
    x = np.linspace(-1.0, 1.0, bars, dtype=np.float32)
    if profile in {"valley", "谷型"}:
        weight = 0.70 + 0.45 * np.abs(x)
    elif profile in {"mountain", "山型"}:
        weight = 0.80 + 0.35 * (1.0 - np.abs(x))
    else:
        return vals
    return np.clip(vals * weight[None, :], 0.0, 1.0)


def transform_spectrum_data(data: SpectrumData, transform: TransformSettings) -> np.ndarray:
    """Transform generic SpectrumData into display-ready values.

    Future renderers should call this or a sibling transformation function before
    drawing.  This keeps analysis data reusable for bars, mirrored bars, circular
    bars, area graphs, dots, scrolling, and rotation.
    """
    values = np.asarray(data.values, dtype=np.float32)
    if transform.scroll_offset:
        values = np.roll(values, int(transform.scroll_offset), axis=1)
    values = apply_shape_profile(values, transform.shape_profile)
    return aggregate_analysis_bars(values, int(transform.display_bars))


def slice_spectrum_data(data: SpectrumData, start_frame: int, end_frame: int) -> SpectrumData:
    """Return a frame-sliced SpectrumData object."""
    start_frame = max(0, int(start_frame))
    end_frame = max(start_frame, int(end_frame))
    return replace(
        data,
        values=data.values[start_frame:end_frame, :],
        raw_db=data.raw_db[start_frame:end_frame, :],
    )


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


def build_layout(style: RenderStyle) -> Tuple[List[Tuple[int, int]], int, int]:
    width, height, bars = style.width, style.height, style.bars
    margin_x = max(0, int(round(width * style.side_margin_ratio)))
    bottom_margin = max(0, int(round(height * style.bottom_margin_ratio)))
    base_y = max(1, min(height, height - bottom_margin))
    max_h = max(1, int(round(height * style.max_height_ratio)))
    max_h = min(max_h, base_y)
    area_w = max(bars, width - margin_x * 2)
    slot_w = area_w / float(bars)
    fill = float(np.clip(style.bar_width_scale, 0.05, 1.00))
    bar_w = max(1, int(round(slot_w * fill)))
    bar_w = min(bar_w, max(1, int(math.floor(slot_w))))

    positions: List[Tuple[int, int]] = []
    for b in range(bars):
        center = margin_x + (b + 0.5) * slot_w
        x0 = int(round(center - bar_w / 2.0))
        x1 = x0 + bar_w
        x0 = max(0, min(width - 1, x0))
        x1 = max(x0 + 1, min(width, x1))
        positions.append((x0, x1))
    return positions, base_y, max_h


def draw_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB) -> None:
    if x1 <= x0 or y1 <= y0:
        return
    frame[y0:y1, x0:x1, :] = color


def draw_rounded_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB, radius: int) -> None:
    """Draw an anti-aliased rounded rectangle.

    Earlier versions used a hard binary mask.  Very low bars then looked almost
    square until they became tall enough for the corner radius to be visible.
    This signed-distance-field renderer blends edge pixels, so small rising bars
    keep a smoother rounded look instead of switching abruptly from square to
    rounded.
    """
    h = int(y1 - y0)
    w = int(x1 - x0)
    if w <= 0 or h <= 0:
        return
    requested = float(max(0, radius))
    if requested <= 0:
        draw_rect(frame, x0, y0, x1, y1, color)
        return

    # Clamp to the mathematically possible radius, then render with soft edges.
    # For very short bars this becomes a small pill/oval rather than a hard
    # rectangular dash.
    r = float(min(requested, w / 2.0, h / 2.0))
    yy, xx = np.indices((h, w), dtype=np.float32)

    # Coordinates centered on the rectangle.  Pixel centers are used so the SDF
    # behaves consistently for odd/even sizes and very small heights.
    px = xx + 0.5 - (w / 2.0)
    py = yy + 0.5 - (h / 2.0)
    half_w = w / 2.0
    half_h = h / 2.0

    # Rounded-box signed distance.
    qx = np.abs(px) - (half_w - r)
    qy = np.abs(py) - (half_h - r)
    ox = np.maximum(qx, 0.0)
    oy = np.maximum(qy, 0.0)
    outside = np.sqrt(ox * ox + oy * oy)
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    dist = outside + inside - r

    # One-pixel antialiasing band.  Coverage is 1 inside, 0 outside.
    alpha = np.clip(0.5 - dist, 0.0, 1.0).astype(np.float32)
    if not np.any(alpha > 0):
        return

    region = frame[y0:y1, x0:x1, :]
    a = alpha[:, :, None]
    col = np.array(color, dtype=np.float32)[None, None, :]
    blended = region.astype(np.float32) * (1.0 - a) + col * a
    region[:, :, :] = np.clip(blended, 0, 255).astype(np.uint8)


def draw_spectrum_frame(values: np.ndarray, style: RenderStyle) -> np.ndarray:
    frame = np.empty((style.height, style.width, 3), dtype=np.uint8)
    frame[:, :, 0] = style.background_color[0]
    frame[:, :, 1] = style.background_color[1]
    frame[:, :, 2] = style.background_color[2]

    positions, base_y, max_h = build_layout(style)
    vals = np.asarray(values, dtype=np.float32)
    for b, value in enumerate(vals[:style.bars]):
        v = float(np.clip(value, 0.0, 1.0))
        if style.gamma != 1.0:
            v = v ** style.gamma
        h = int(round(v * max_h))
        if h <= 0:
            continue
        x0, x1 = positions[b]
        full_w = max(1, int(x1 - x0))

        # Emergence shape:
        # For very low bars, do not draw the full bar width immediately.
        # Instead, let the bar appear from the center as a small lemon/pill
        # shape, then expand to the normal width as height grows.
        if style.corner_radius > 0 and h < full_w:
            min_w = max(1.5, full_w * 0.24)
            grow_h = max(1.0, full_w * 0.85)
            t = float(np.clip(h / grow_h, 0.0, 1.0))
            t = t * t * (3.0 - 2.0 * t)  # smoothstep
            eff_w = min(full_w, max(min_w, min_w + (full_w - min_w) * t))
            cx = (x0 + x1) / 2.0
            nx0 = int(round(cx - eff_w / 2.0))
            nx1 = int(round(cx + eff_w / 2.0))
            if nx1 <= nx0:
                nx1 = nx0 + 1
            x0 = max(0, nx0)
            x1 = min(style.width, nx1)

        y0 = max(0, base_y - h)
        y1 = min(style.height, base_y)
        draw_rounded_rect(frame, x0, y0, x1, y1, style.bar_color, int(style.corner_radius))
    return frame


def still_preview_values(bars: int) -> np.ndarray:
    x = np.linspace(0.0, 1.0, bars, dtype=np.float32)
    values = (
        0.18
        + 0.70 * np.exp(-((x - 0.18) / 0.14) ** 2)
        + 0.58 * np.exp(-((x - 0.50) / 0.15) ** 2)
        + 0.42 * np.exp(-((x - 0.78) / 0.07) ** 2)
        + 0.15 * np.sin(2.0 * np.pi * (x * 4.0 + 0.2)) ** 2
    )
    return np.clip(values, 0.04, 1.0)


def generate_dummy_dynamic_values(frames: int, bars: int, motion: MotionSettings) -> np.ndarray:
    """Create deterministic pseudo-audio Dynamic values for GUI motion preview."""
    t = np.arange(frames, dtype=np.float32) / 30.0
    b = np.arange(bars, dtype=np.float32)[None, :]
    # Pseudo dB pattern with strong transients and moving spectral emphasis.
    low = -42 + 17 * np.sin(2 * np.pi * (0.95 * t[:, None] + b / max(1, bars) * 0.25))
    mid = 10 * np.sin(2 * np.pi * (2.7 * t[:, None] + b / max(1, bars) * 1.8))
    beat = (np.maximum(0, np.sin(2 * np.pi * 1.65 * t)) ** 8)[:, None] * 28
    sweep_center = (0.15 + 0.70 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t)))[:, None] * bars
    sweep = 18 * np.exp(-((b - sweep_center) / max(2.5, bars * 0.12)) ** 2)
    rng = np.random.default_rng(12345)
    grain = rng.normal(0, 2.2, size=(frames, bars)).astype(np.float32)
    db = low + mid + beat + sweep + grain
    return map_db_to_dynamic_values(db.astype(np.float32), motion)


def open_ffmpeg_encoder(output_path: Path, width: int, height: int, fps: int, encode: EncodeSettings) -> subprocess.Popen:
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "pipe:0", "-an", "-c:v", encode.encoder,
    ]
    if encode.encoder in {"libx264", "libx265"}:
        cmd += ["-preset", encode.preset, "-crf", str(encode.crf)]
    elif "nvenc" in encode.encoder:
        cmd += ["-preset", "p4", "-cq", str(encode.crf)]
    cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)


def render_video(bar_values: np.ndarray, output_path: Path, style: RenderStyle, encode: EncodeSettings, log_callback: LogFn = None) -> None:
    frame_count, bars = bar_values.shape
    if bars != style.bars:
        raise RuntimeError("Internal error: bar_values does not match style.bars.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"Writing video: {output_path}", log_callback)
    proc = open_ffmpeg_encoder(output_path, style.width, style.height, style.fps, encode)
    if proc.stdin is None:
        raise RuntimeError("Could not open ffmpeg input pipe.")
    progress_step = max(1, frame_count // 20)
    try:
        for i in range(frame_count):
            frame = draw_spectrum_frame(bar_values[i], style)
            proc.stdin.write(frame.tobytes())
            if frame_count >= 300 and ((i + 1) % progress_step == 0 or i + 1 == frame_count):
                log(f"Writing: {100.0 * (i + 1) / frame_count:5.1f}%", log_callback)
    except BrokenPipeError:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError("ffmpeg stopped unexpectedly.\n" + stderr)
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    return_code = proc.wait()
    if return_code != 0:
        raise RuntimeError("Video encoding failed with ffmpeg.\n" + stderr)




def find_loud_segment_start(
    input_path: Path,
    sample_rate: int = 24000,
    scan_seconds: float = 120.0,
    segment_seconds: float = 10.0,
    log_callback: LogFn = None,
) -> float:
    """Return the start second of a loud segment near the beginning of the audio.

    The scan is intentionally simple and robust: decode the first N seconds, compute
    RMS power for sliding windows, and choose the 10-second area with the largest
    average power.  This is used only for preview selection, not for final render.
    """
    input_path = Path(input_path).expanduser().resolve()
    scan_seconds = max(1.0, float(scan_seconds or 120.0))
    segment_seconds = max(1.0, float(segment_seconds or 10.0))
    duration_hint = run_ffprobe_duration(input_path)
    if duration_hint:
        scan_seconds = min(scan_seconds, duration_hint)
        if duration_hint <= segment_seconds:
            return 0.0
    log(f"Auto-detecting preview segment: scanning first {scan_seconds:.0f}s", log_callback)
    audio = decode_audio_to_float32_mono(input_path, sample_rate, 0.0, scan_seconds, log_callback)
    n = audio.size
    win = int(round(segment_seconds * sample_rate))
    if n <= win or win <= 0:
        return 0.0
    hop = max(1, int(round(0.5 * sample_rate)))
    sq = (audio.astype(np.float64) ** 2)
    csum = np.concatenate([[0.0], np.cumsum(sq)])
    starts = np.arange(0, n - win + 1, hop, dtype=np.int64)
    # Average window power.  Add a tiny preference against absolute 0 so a silent
    # intro is avoided when another equally loud section exists.
    powers = (csum[starts + win] - csum[starts]) / float(win)
    if powers.size == 0:
        return 0.0
    best = int(starts[int(np.argmax(powers))])
    start_sec = float(best) / float(sample_rate)
    log(f"Auto-detected preview start: {start_sec:.2f}s", log_callback)
    return start_sec




def suggest_frequency_range(
    input_path: Path,
    sample_rate: int = 24000,
    scan_seconds: float = 120.0,
    log_callback: LogFn = None,
) -> tuple[float, float]:
    """Suggest a practical frequency range from real audio near the beginning.

    This is intentionally conservative for overlay visuals: it tries to avoid
    wasting bars in almost-empty upper bands while keeping enough range so the
    spectrum still feels natural.
    """
    input_path = Path(input_path).expanduser().resolve()
    scan_seconds = max(5.0, float(scan_seconds or 120.0))
    duration_hint = run_ffprobe_duration(input_path)
    if duration_hint:
        scan_seconds = min(scan_seconds, duration_hint)
    log(f"Auto-analyzing frequency range: first {scan_seconds:.0f}s", log_callback)
    audio = decode_audio_to_float32_mono(input_path, sample_rate, 0.0, scan_seconds, log_callback)
    if audio.size < 2048:
        return 80.0, min(12000.0, sample_rate / 2.0)

    fft_size = 2048
    hop = fft_size // 2
    window = np.hanning(fft_size).astype(np.float32)
    window_norm = float(np.sum(window) / 2.0) or float(fft_size / 2)
    usable = max(0, (audio.size - fft_size) // hop + 1)
    if usable <= 0:
        return 80.0, min(12000.0, sample_rate / 2.0)

    max_frames = min(600, usable)
    if usable > max_frames:
        starts = np.linspace(0, audio.size - fft_size, num=max_frames, dtype=np.int64)
    else:
        starts = np.arange(0, usable * hop, hop, dtype=np.int64)

    acc = None
    count = 0
    for s in starts:
        frame = audio[int(s): int(s) + fft_size]
        if frame.size < fft_size:
            break
        spectrum = np.fft.rfft(frame * window)
        power = (np.abs(spectrum).astype(np.float64) / window_norm) ** 2
        if acc is None:
            acc = power
        else:
            acc += power
        count += 1
    if acc is None or count == 0:
        return 80.0, min(12000.0, sample_rate / 2.0)

    avg_power = acc / float(count)
    freqs = np.fft.rfftfreq(fft_size, d=1.0 / sample_rate)
    valid = (freqs >= 20.0) & (freqs <= min(sample_rate / 2.0, 18000.0))
    freqs = freqs[valid]
    power = avg_power[valid]
    if power.size == 0 or float(np.sum(power)) <= 0.0:
        return 80.0, min(12000.0, sample_rate / 2.0)

    # Light smoothing to reduce narrow-bin spikes.
    kernel = np.array([1, 2, 3, 2, 1], dtype=np.float64)
    kernel /= kernel.sum()
    power = np.convolve(power, kernel, mode='same')

    csum = np.cumsum(power)
    total = float(csum[-1])
    low_idx = int(np.searchsorted(csum, total * 0.002))
    high_idx = int(np.searchsorted(csum, total * 0.992))
    low_hz = float(freqs[min(low_idx, freqs.size - 1)])
    high_hz = float(freqs[min(high_idx, freqs.size - 1)])

    # Also find the highest region that is still meaningfully energetic.
    peak = float(np.max(power))
    if peak > 0.0:
        norm = power / peak
        energetic = np.where(norm >= 0.02)[0]
        if energetic.size > 0:
            high_hz = min(high_hz, float(freqs[int(energetic[-1])]))

    # For visual bar overlays, too narrow a range causes adjacent bars to behave
    # too similarly.  Keep the lower bound out of the sub-bass area and keep a
    # moderate upper range even when the scan has little very-high-frequency
    # energy.  This still avoids wasting the full 12 kHz range for Suno tracks
    # whose useful spectrum often ends much lower.
    low_hz = float(np.clip(low_hz, 60.0, 160.0))
    high_hz = float(np.clip(high_hz, max(5000.0, low_hz + 3000.0), min(sample_rate / 2.0, 16000.0)))
    # Round to friendly values.
    if low_hz < 100:
        low_hz = round(low_hz / 10.0) * 10.0
    else:
        low_hz = round(low_hz / 20.0) * 20.0
    high_hz = round(high_hz / 100.0) * 100.0
    log(f"Auto frequency range: {low_hz:.0f} - {high_hz:.0f} Hz", log_callback)
    return low_hz, high_hz

def analyze_preview_segment(
    input_path: Path,
    style: RenderStyle,
    motion: MotionSettings,
    start: float | None = None,
    duration: float = 10.0,
    warmup: float = 5.0,
    auto_detect: bool = True,
    scan_seconds: float = 120.0,
    log_callback: LogFn = None,
) -> tuple[np.ndarray, float]:
    """Analyze a short preview segment from actual audio and return bar values.

    If auto_detect is true, the start second is chosen by scanning the beginning of
    the track for a loud segment.  Warmup audio is analyzed but removed from the
    returned frames, so the preview behaves closer to a full-length render.
    """
    ok, msg = check_environment()
    if not ok:
        raise RuntimeError(msg)
    input_path = Path(input_path).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise RuntimeError(f"Audio file was not found: {input_path}")
    duration = max(1.0, float(duration or 10.0))
    if auto_detect:
        render_start = find_loud_segment_start(
            input_path=input_path,
            sample_rate=motion.sample_rate,
            scan_seconds=scan_seconds,
            segment_seconds=duration,
            log_callback=log_callback,
        )
    else:
        render_start = max(0.0, float(start or 0.0))
    warmup_req = max(0.0, float(warmup or 0.0))
    decode_start = max(0.0, render_start - warmup_req)
    effective_warmup = render_start - decode_start
    decode_duration = duration + effective_warmup
    log(f"Motion preview analysis: {render_start:.2f}s for {duration:.2f}s", log_callback)
    audio = decode_audio_to_float32_mono(input_path, motion.sample_rate, decode_start, decode_duration, log_callback)
    data = analyze_spectrum_data(audio, style, motion, log_callback)
    skip_frames = int(round(effective_warmup * style.fps))
    render_frames = int(math.ceil(duration * style.fps))
    data = slice_spectrum_data(data, skip_frames, skip_frames + render_frames)
    if data.values.shape[0] <= 0:
        raise RuntimeError("Preview range became empty. Check start time, duration, and warmup.")
    values = transform_spectrum_data(data, TransformSettings(display_bars=style.bars))
    return values, render_start

def render_audio_to_video(
    input_path: Path,
    output_path: Path,
    style: RenderStyle,
    motion: MotionSettings,
    encode: EncodeSettings,
    start: float = 0.0,
    duration: float | None = None,
    warmup: float = 0.0,
    log_callback: LogFn = None,
) -> Path:
    ok, msg = check_environment()
    if not ok:
        raise RuntimeError(msg)
    input_path = Path(input_path).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise RuntimeError(f"Audio file was not found: {input_path}")

    output_path = unique_path(Path(output_path).expanduser().resolve())
    duration_hint = run_ffprobe_duration(input_path)
    preview = duration is not None and duration > 0
    render_start = max(0.0, float(start or 0.0))
    warmup_req = max(0.0, float(warmup or 0.0)) if preview else 0.0
    decode_start = max(0.0, render_start - warmup_req)
    effective_warmup = render_start - decode_start
    decode_duration = None
    if preview:
        decode_duration = float(duration) + effective_warmup

    if duration_hint:
        if preview:
            log(f"Source duration: {duration_hint:.2f}s / preview from {render_start:.2f}s for {duration:.2f}s", log_callback)
        else:
            log(f"Source duration: {duration_hint:.2f}s / full render", log_callback)

    audio = decode_audio_to_float32_mono(input_path, motion.sample_rate, decode_start, decode_duration, log_callback)
    data = analyze_spectrum_data(audio, style, motion, log_callback)
    if preview and effective_warmup > 0:
        skip_frames = int(round(effective_warmup * style.fps))
        render_frames = int(math.ceil(float(duration) * style.fps))
        data = slice_spectrum_data(data, skip_frames, skip_frames + render_frames)
        if data.values.shape[0] <= 0:
            raise RuntimeError("Preview range became empty. Check start time, duration, and warmup.")
        log(f"Preview after warmup: {data.values.shape[0]:,} frames", log_callback)
    elif preview:
        render_frames = int(math.ceil(float(duration) * style.fps))
        data = slice_spectrum_data(data, 0, render_frames)
    bar_values = transform_spectrum_data(data, TransformSettings(display_bars=style.bars))
    render_video(bar_values, output_path, style, encode, log_callback)
    log(f"Done: {output_path}", log_callback)
    return output_path


def build_default_output_path(input_path: Path, output_dir: Path, style: RenderStyle, preview: bool, start: float = 0.0, duration: float | None = None) -> Path:
    output_dir = Path(output_dir)
    bw = int(round(style.bar_width_scale * 100))
    base = f"{input_path.stem}_spectrum_{style.width}x{style.height}_{style.bars}bars_bw{bw}_r{style.corner_radius}"
    if preview:
        dur = int(round(float(duration or 0)))
        st = int(round(float(start or 0)))
        base += f"_preview_s{st}_d{dur}"
    return output_dir / f"{base}.mp4"

