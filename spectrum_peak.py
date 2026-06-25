# -*- coding: utf-8 -*-
"""Peak-hold value generation for display-ready bar values."""
from __future__ import annotations

import numpy as np

from spectrum_types import RenderStyle, TransformSettings
from spectrum_transform import apply_integer_scroll


def _opposite_scroll_mode(mode: str) -> str:
    mode = str(mode or "none").lower()
    if mode in {"left", "蟾ｦ", "leftward"}:
        return "right"
    if mode in {"right", "蜿ｳ", "rightward"}:
        return "left"
    return "none"


def compute_peak_hold_values(
    bar_values: np.ndarray,
    style: RenderStyle,
    transform: TransformSettings | None = None,
) -> np.ndarray | None:
    """Return per-frame peak-hold values for each display bar.

    The input and output values are continuous 0..1 display values. Drawing code
    decides how to render those values for normal bars or digital segmented bars.
    When integer scrolling is active, peaks are tracked in source-band order and
    then scrolled back into display order so held markers move with the bars.
    """
    if not bool(getattr(style, "peak_hold_enabled", False)):
        return None

    values = np.asarray(bar_values, dtype=np.float32)
    if values.ndim != 2 or values.size == 0:
        return None

    if transform is not None:
        inverse_mode = _opposite_scroll_mode(getattr(transform, "scroll_mode", "none"))
        values = apply_integer_scroll(values, inverse_mode, getattr(transform, "scroll_step_frames", 1))

    frame_count, bars = values.shape
    fps = max(1, int(getattr(style, "fps", 30) or 30))
    hold_frames = max(0, int(round(float(getattr(style, "peak_hold_ms", 400) or 0) * fps / 1000.0)))
    decay_frames = max(1, int(round(float(getattr(style, "peak_decay_ms", 700) or 1) * fps / 1000.0)))
    decay_per_frame = 1.0 / float(decay_frames)

    peaks = np.zeros((frame_count, bars), dtype=np.float32)
    peak_value = np.zeros(bars, dtype=np.float32)
    hold_left = np.zeros(bars, dtype=np.int32)

    for frame_index in range(frame_count):
        current = np.clip(values[frame_index], 0.0, 1.0)
        rising = current >= peak_value
        peak_value[rising] = current[rising]
        hold_left[rising] = hold_frames

        falling = ~rising
        holding = falling & (hold_left > 0)
        hold_left[holding] -= 1

        decaying = falling & ~holding
        if np.any(decaying):
            peak_value[decaying] -= decay_per_frame
            absorbed = decaying & (peak_value <= current)
            peak_value[absorbed] = current[absorbed]

        peak_value = np.clip(peak_value, 0.0, 1.0)
        peaks[frame_index] = peak_value

    if transform is not None:
        peaks = apply_integer_scroll(peaks, getattr(transform, "scroll_mode", "none"), getattr(transform, "scroll_step_frames", 1))

    return peaks
