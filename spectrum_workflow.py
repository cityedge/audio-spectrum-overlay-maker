# -*- coding: utf-8 -*-
"""High-level render and preview workflows.

This layer composes environment checks, audio decoding, analysis, display
transformation, and encoding.  GUI code should normally call this layer through
the compatibility facade in spectrum_engine.py.
"""
from __future__ import annotations

import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from spectrum_types import EncodeSettings, LogFn, MotionSettings, RenderStyle, TransformSettings
from spectrum_utils import log, unique_path
from spectrum_audio import check_environment, decode_audio_to_float32_mono, run_ffprobe_duration
from spectrum_analysis import analyze_spectrum_data
from spectrum_transform import slice_spectrum_data, transform_spectrum_data
from spectrum_encoder import render_video

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
    transform: TransformSettings | None = None,
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
    transform = transform or TransformSettings(display_bars=style.bars)
    values = transform_spectrum_data(data, transform)
    return values, render_start

def build_matte_output_path(main_output_path: Path) -> Path:
    """Return the matte-path paired with a main output path."""
    main_output_path = Path(main_output_path)
    return main_output_path.with_name(f"{main_output_path.stem}_matte_dark{main_output_path.suffix}")


def unique_output_pair(base_output_path: Path) -> tuple[Path, Path]:
    """Return a non-overwriting main/matte path pair.

    If either the main path or the paired matte path already exists, both names
    advance to the same numeric suffix.  This keeps the pair easy to identify:
    `name (1).mp4` and `name (1)_matte_dark.mp4`.
    """
    base_output_path = Path(base_output_path)
    parent = base_output_path.parent
    stem = base_output_path.stem
    suffix = base_output_path.suffix

    for i in range(10000):
        if i == 0:
            main = base_output_path
        else:
            main = parent / f"{stem} ({i}){suffix}"
        matte = build_matte_output_path(main)
        if not main.exists() and not matte.exists():
            return main, matte

    raise RuntimeError("Could not find a non-overwriting output filename pair.")

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
    transform: TransformSettings | None = None,
    write_matte: bool = False,
) -> Path:
    transform = transform or TransformSettings(display_bars=style.bars)
    ok, msg = check_environment()
    if not ok:
        raise RuntimeError(msg)
    input_path = Path(input_path).expanduser().resolve()
    if not input_path.exists() or not input_path.is_file():
        raise RuntimeError(f"Audio file was not found: {input_path}")

    raw_output_path = Path(output_path).expanduser().resolve()
    if write_matte:
        output_path, matte_path = unique_output_pair(raw_output_path)
    else:
        output_path = unique_path(raw_output_path)
        matte_path = None

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
    bar_values = transform_spectrum_data(data, transform)

    # Main output is always the user's normal spectrum material.
    render_video(bar_values, output_path, style, encode, log_callback, transform=transform)
    log(f"Done main: {output_path}", log_callback)

    if write_matte:
        assert matte_path is not None
        matte_style = replace(
            style,
            background_color=(255, 255, 255),
            bar_color=(0, 0, 0),
            bar_color2=(0, 0, 0),
            color_mode="vertical",
        )
        log("Writing matte output for Compare/Darken compositing.", log_callback)
        render_video(bar_values, matte_path, matte_style, encode, log_callback, transform=transform)
        log(f"Done matte: {matte_path}", log_callback)

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

