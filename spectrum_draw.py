# -*- coding: utf-8 -*-
"""Current bar-spectrum drawing facade.

v1.1.0 keeps the public drawing API stable while routing the current bar
visual through BarSpectrumPart + primitive rendering.
"""
from __future__ import annotations

from typing import List, Tuple

import numpy as np

from spectrum_types import MotionSettings, RGB, RenderStyle, SpectrumData
from spectrum_motion import map_db_to_dynamic_values
from spectrum_parts import BarSpectrumPart
from spectrum_digital import draw_digital_frame
from spectrum_primitives import (
    create_frame,
    draw_primitives,
    draw_rect,
    draw_rounded_rect,
)
from spectrum_scene import CanvasSpec, Scene


def apply_edge_glow(frame: np.ndarray, background_color: RGB, mode: str = "standard") -> np.ndarray:
    """Add a one-pixel glow around non-black drawn pixels.

    This is intentionally a black-background feature.  It spreads the already
    drawn RGB colors by one pixel in four directions, then places the original
    frame back on top so the core spectrum shape is unchanged.  Old simple and
    advanced mode names are accepted as the standard strength.
    """
    if tuple(background_color) != (0, 0, 0):
        return frame
    glow_mode = str(mode or "standard").lower()
    if glow_mode in {"none", "off"}:
        return frame
    shifts = {
        "light": 3,
        "simple": 2,
        "standard": 2,
        "advanced": 2,
        "strong": 1,
    }
    shift_bits = shifts.get(glow_mode, 2)
    offsets = ((0, -1), (-1, 0), (1, 0), (0, 1))

    glow = np.zeros_like(frame)
    for dx, dy in offsets:
        src_y0 = max(0, -dy)
        src_y1 = frame.shape[0] - max(0, dy)
        src_x0 = max(0, -dx)
        src_x1 = frame.shape[1] - max(0, dx)
        dst_y0 = max(0, dy)
        dst_y1 = frame.shape[0] - max(0, -dy)
        dst_x0 = max(0, dx)
        dst_x1 = frame.shape[1] - max(0, -dx)
        shifted = frame[src_y0:src_y1, src_x0:src_x1] >> shift_bits
        glow[dst_y0:dst_y1, dst_x0:dst_x1] = np.maximum(glow[dst_y0:dst_y1, dst_x0:dst_x1], shifted)

    out = glow
    drawn = np.any(frame != 0, axis=2)
    out[drawn] = frame[drawn]
    return out

def build_layout(style: RenderStyle) -> Tuple[List[Tuple[int, int]], int, int]:
    layout = BarSpectrumPart(style).build_layout()
    return layout.positions, layout.base_y, layout.max_height

def build_bar_scene(values: np.ndarray, style: RenderStyle, band_color_offset: int = 0, peak_values: np.ndarray | None = None) -> Scene:
    canvas = CanvasSpec(width=int(style.width), height=int(style.height), background_color=style.background_color)
    scene = Scene(canvas=canvas)
    scene.extend(BarSpectrumPart(style, band_color_offset=band_color_offset).primitives_for_values(values, peak_values=peak_values))
    return scene

def draw_spectrum_frame(values: np.ndarray, style: RenderStyle, band_color_offset: int = 0, peak_values: np.ndarray | None = None) -> np.ndarray:
    frame = None
    if bool(getattr(style, "digital_enabled", False)):
        frame = draw_digital_frame(values, style, band_color_offset, peak_values)
    if frame is None:
        scene = build_bar_scene(values, style, band_color_offset=band_color_offset, peak_values=peak_values)
        frame = create_frame(scene.canvas.width, scene.canvas.height, scene.canvas.background_color)
        draw_primitives(frame, scene.primitives)
    if bool(getattr(style, "edge_glow_enabled", False)):
        frame = apply_edge_glow(
            frame,
            style.background_color,
            str(getattr(style, "edge_glow_mode", "standard") or "standard"),
        )
    return frame



def compute_band_color_offset(frame_index: int, scroll_mode: str, scroll_step_frames: int) -> int:
    mode = str(scroll_mode or 'none')
    step_frames = max(1, int(scroll_step_frames or 1))
    steps = max(0, int(frame_index)) // step_frames
    if mode == 'left':
        return steps
    if mode == 'right':
        return -steps
    return 0

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


def still_preview_spectrum_data(bars: int, motion: MotionSettings, fps: int) -> SpectrumData:
    """Create deterministic synthetic spectrum data for the still preview.

    The raw dB values let display-only corrections, including high-frequency
    boost, use the same transform path as real audio without requiring a file.
    """
    bands = max(1, int(bars))
    base_values = still_preview_values(bands)
    min_db = float(motion.min_db)
    max_db = max(min_db + 1.0, float(motion.max_db))
    # Keep the familiar preview silhouette while leaving headroom for a visible
    # high-frequency dB boost.
    raw_db = min_db + (0.22 + 0.68 * base_values) * (max_db - min_db)
    raw_db = raw_db.astype(np.float32, copy=False)[None, :]
    hi = min(float(motion.freq_max), float(motion.sample_rate) / 2.0)
    lo = max(1.0, float(motion.freq_min))
    if hi <= lo:
        hi = lo + 1.0
    return SpectrumData(
        values=map_db_to_dynamic_values(raw_db, motion),
        raw_db=raw_db,
        freq_edges=np.geomspace(lo, hi, bands + 1).astype(np.float32),
        fps=max(1, int(fps)),
        sample_rate=int(motion.sample_rate),
        analysis_bands=bands,
        freq_min=lo,
        freq_max=hi,
    )

def generate_dummy_dynamic_values(frames: int, bars: int, motion: MotionSettings) -> np.ndarray:
    """Create deterministic pseudo-audio Dynamic values for GUI motion preview."""
    t = np.arange(frames, dtype=np.float32) / 30.0
    b = np.arange(bars, dtype=np.float32)[None, :]
    low = -42 + 17 * np.sin(2 * np.pi * (0.95 * t[:, None] + b / max(1, bars) * 0.25))
    mid = 10 * np.sin(2 * np.pi * (2.7 * t[:, None] + b / max(1, bars) * 1.8))
    beat = (np.maximum(0, np.sin(2 * np.pi * 1.65 * t)) ** 8)[:, None] * 28
    sweep_center = (0.15 + 0.70 * (0.5 + 0.5 * np.sin(2 * np.pi * 0.23 * t)))[:, None] * bars
    sweep = 18 * np.exp(-((b - sweep_center) / max(2.5, bars * 0.12)) ** 2)
    rng = np.random.default_rng(12345)
    grain = rng.normal(0, 2.2, size=(frames, bars)).astype(np.float32)
    db = low + mid + beat + sweep + grain
    return map_db_to_dynamic_values(db.astype(np.float32), motion)
