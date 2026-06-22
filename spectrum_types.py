# -*- coding: utf-8 -*-
"""Shared data models for Audio Spectrum Overlay Maker.

This module intentionally contains no processing logic.  It defines the stable
objects passed between the analysis, motion, transformation, drawing, and
encoding layers.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Tuple

import numpy as np

VERSION = "1.1.2"
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
