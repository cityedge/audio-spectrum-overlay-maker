# -*- coding: utf-8 -*-
"""Shared data models for Audio Spectrum Overlay Maker.

This module intentionally contains no processing logic.  It defines the stable
objects passed between the analysis, motion, transformation, drawing, and
encoding layers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Tuple

import numpy as np

VERSION = "1.3.0"
RGB = Tuple[int, int, int]
LogFn = Callable[[str], None] | None

@dataclass
class RenderStyle:
    width: int = 720
    height: int = 280
    fps: int = 30
    bars: int = 24
    display_mode: str = "single"
    background_color: RGB = (0, 0, 0)
    bar_color: RGB = (255, 255, 255)
    bar_color2: RGB = (255, 255, 255)
    color_mode: str = "vertical"
    max_height_ratio: float = 0.78
    bottom_margin_ratio: float = 0.08
    side_margin_ratio: float = 0.05
    bar_width_scale: float = 0.62
    corner_radius: int = 18
    digital_enabled: bool = False
    digital_segments: int = 16
    digital_gap_px: int = 2
    peak_hold_enabled: bool = False
    peak_hold_ms: int = 100
    peak_decay_ms: int = 300
    peak_size_percent: int = 4
    digital_peak_segments: int = 1
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
    scroll_mode: str = "none"
    scroll_step_frames: int = 2
    scroll_offset: int = 0

@dataclass
class PostTransformModulation:
    """Optional time modulation for future post-transform parameters."""
    enabled: bool = False
    amplitude: float = 0.0
    period_seconds: float = 4.0
    phase_degrees: float = 0.0

@dataclass
class PostTransformSettings:
    """Coordinate mapping applied after a complete frame has been drawn.

    The default is the historical identity mapping:
    (x, y) -> (x, y).
    """
    transform_type: str = "none"
    angle_degrees: float = 0.0
    scale_percent: float = 100.0
    audio_scale_enabled: bool = False
    audio_scale_max_percent: float = 115.0
    audio_scale_low_only: bool = True
    audio_scale_low_band_percent: int = 25
    audio_scale_floor_percent: float = 10.0
    audio_scale_ceiling_percent: float = 50.0
    audio_scale_hold_ms: int = 66
    audio_scale_decay_ms: int = 167
    trapezoid_top_scale: float = 1.0
    trapezoid_bottom_scale: float = 1.0
    trapezoid_vertical_percent: float = 0.0
    trapezoid_horizontal_percent: float = 0.0
    angle_modulation: PostTransformModulation = field(default_factory=PostTransformModulation)
    trapezoid_modulation: PostTransformModulation = field(default_factory=PostTransformModulation)
