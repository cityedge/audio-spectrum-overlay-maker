# -*- coding: utf-8 -*-
"""Display transformation layer.

This layer converts generic motion-shaped SpectrumData into display-ready band
values.  Options such as integer band-rotation scrolling, mountain/valley
shaping, and display-band remapping live here instead of the audio analysis
layer.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from spectrum_types import MotionSettings, SpectrumData, TransformSettings
from spectrum_motion import map_db_to_dynamic_values

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


def apply_integer_scroll(values: np.ndarray, mode: str = "none", step_frames: int = 2) -> np.ndarray:
    """Apply integer band-rotation scrolling across frames.

    Bar positions stay fixed. Only the source band assigned to each bar shifts
    over time. This avoids cropped edge bars and keeps the visual stable for
    overlay use.

    Modes:
    - none: no scrolling
    - left: features appear to move left
    - right: features appear to move right
    """
    vals = np.asarray(values, dtype=np.float32)
    mode = (mode or "none").lower()
    step_frames = max(1, int(step_frames or 1))
    if mode in {"none", "off", "なし", "no"} or vals.ndim != 2 or vals.shape[1] <= 1:
        return vals
    frames, bars = vals.shape
    base = np.arange(bars, dtype=np.int64)[None, :]
    offsets = (np.arange(frames, dtype=np.int64) // step_frames)[:, None]
    if mode in {"left", "左", "leftward"}:
        src = (base + offsets) % bars
    elif mode in {"right", "右", "rightward"}:
        src = (base - offsets) % bars
    else:
        return vals
    return np.take_along_axis(vals, src, axis=1)

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

def high_frequency_boost_exponent(curve: str) -> float:
    curve_key = str(curve or "standard").lower()
    if curve_key in {"gentle", "smooth", "なだらか"}:
        return 2.0
    if curve_key in {"moderately_steep", "slightly_steep", "やや急"}:
        return 6.0
    if curve_key in {"steep", "急"}:
        return 8.0
    return 4.0


def high_frequency_boost_db_by_band(data: SpectrumData, amount_db: float, curve: str) -> np.ndarray:
    amount = max(0.0, float(amount_db or 0.0))
    bars = int(data.raw_db.shape[1])
    if amount <= 1.0e-9 or bars <= 0:
        return np.zeros((bars,), dtype=np.float32)
    edges = np.asarray(data.freq_edges, dtype=np.float64)
    if edges.size != bars + 1:
        edges = np.geomspace(max(1.0, float(data.freq_min)), max(float(data.freq_min) + 1.0, float(data.freq_max)), bars + 1)
    edges = np.maximum(edges, 1.0e-6)
    centers = np.sqrt(edges[:-1] * edges[1:])
    lo = max(1.0e-6, float(np.min(centers)))
    hi = max(lo + 1.0e-6, float(np.max(centers)))
    position = np.log(centers / lo) / max(1.0e-6, math.log(hi / lo))
    position = np.clip(position, 0.0, 1.0)
    boost = amount * np.power(position, high_frequency_boost_exponent(curve))
    return boost.astype(np.float32)


def boosted_spectrum_values(data: SpectrumData, motion: MotionSettings, transform: TransformSettings) -> np.ndarray:
    amount = max(0.0, min(36.0, float(getattr(transform, "high_frequency_boost_db", 0.0) or 0.0)))
    if amount <= 1.0e-9:
        return np.asarray(data.values, dtype=np.float32)
    boost = high_frequency_boost_db_by_band(data, amount, str(getattr(transform, "high_frequency_boost_curve", "standard") or "standard"))
    boosted_db = np.asarray(data.raw_db, dtype=np.float32) + boost[None, :]
    return map_db_to_dynamic_values(boosted_db, motion)


def transform_spectrum_data(
    data: SpectrumData,
    transform: TransformSettings,
    motion: MotionSettings | None = None,
    apply_high_frequency_boost: bool = True,
) -> np.ndarray:
    """Transform generic SpectrumData into display-ready values.

    The transformation order is deliberately display-oriented:

    1. Optionally apply display-only high-frequency dB boost.
    2. Convert internal analysis bands to the final visible bar count.
    3. Apply integer band-rotation scrolling to those visible bars.
    4. Apply position-based shape profiles to the visible positions.

    This keeps "one scroll step" equal to one visible bar, not one internal
    analysis band.
    """
    source_values = np.asarray(data.values, dtype=np.float32)
    if apply_high_frequency_boost and motion is not None:
        source_values = boosted_spectrum_values(data, motion, transform)
    values = aggregate_analysis_bars(source_values, int(transform.display_bars))
    if transform.scroll_offset:
        values = np.roll(values, int(transform.scroll_offset), axis=1)
    values = apply_integer_scroll(values, transform.scroll_mode, transform.scroll_step_frames)
    values = apply_shape_profile(values, transform.shape_profile)
    return np.clip(values, 0.0, 1.0).astype(np.float32)

def slice_spectrum_data(data: SpectrumData, start_frame: int, end_frame: int) -> SpectrumData:
    """Return a frame-sliced SpectrumData object."""
    start_frame = max(0, int(start_frame))
    end_frame = max(start_frame, int(end_frame))
    return replace(
        data,
        values=data.values[start_frame:end_frame, :],
        raw_db=data.raw_db[start_frame:end_frame, :],
    )
