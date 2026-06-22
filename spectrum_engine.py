# -*- coding: utf-8 -*-
"""Compatibility facade for Audio Spectrum Overlay Maker engine APIs.

v1.1.1 splits the internal implementation into focused modules while
keeping the public imports used by app.py and existing scripts stable.
"""
from __future__ import annotations

from spectrum_types import (
    VERSION,
    RGB,
    LogFn,
    RenderStyle,
    MotionSettings,
    EncodeSettings,
    SpectrumData,
    TransformSettings,
)
from spectrum_utils import log, parse_color, color_to_hex, unique_path, runtime_app_dir, find_external_tool, resolve_external_tool
from spectrum_audio import check_environment, run_ffprobe_duration, decode_audio_to_float32_mono
from spectrum_motion import map_db_to_dynamic_values, smooth_values
from spectrum_transform import (
    aggregate_analysis_bars,
    apply_integer_scroll,
    apply_shape_profile,
    transform_spectrum_data,
    slice_spectrum_data,
)
from spectrum_analysis import (
    build_band_indices,
    build_frequency_edges,
    analyze_spectrum_data,
    analyze_bars,
)
from spectrum_primitives import (
    Primitive,
    create_frame,
    draw_primitives,
    draw_rect,
    draw_rounded_rect,
    draw_top_rounded_rect,
    draw_bottom_rounded_rect,
)
from spectrum_scene import Bounds, CanvasSpec, Scene
from spectrum_parts import BarLayout, BarSpectrumPart
from spectrum_draw import (
    build_layout,
    build_bar_scene,
    draw_spectrum_frame,
    compute_band_color_offset,
    still_preview_values,
    generate_dummy_dynamic_values,
)
from spectrum_encoder import open_ffmpeg_encoder, render_video
from spectrum_workflow import (
    find_loud_segment_start,
    suggest_frequency_range,
    analyze_preview_segment,
    render_audio_to_video,
    build_default_output_path,
    build_matte_output_path,
    unique_output_pair,
)

__all__ = [
    "VERSION", "RGB", "LogFn",
    "RenderStyle", "MotionSettings", "EncodeSettings", "SpectrumData", "TransformSettings",
    "log", "parse_color", "color_to_hex", "unique_path", "runtime_app_dir", "find_external_tool", "resolve_external_tool",
    "check_environment", "run_ffprobe_duration", "decode_audio_to_float32_mono",
    "map_db_to_dynamic_values", "smooth_values",
    "aggregate_analysis_bars", "apply_integer_scroll", "apply_shape_profile", "transform_spectrum_data", "slice_spectrum_data",
    "build_band_indices", "build_frequency_edges", "analyze_spectrum_data", "analyze_bars",
    "Primitive", "create_frame", "draw_primitives",
    "Bounds", "CanvasSpec", "Scene", "BarLayout", "BarSpectrumPart",
    "build_layout", "build_bar_scene", "draw_rect", "draw_rounded_rect", "draw_top_rounded_rect", "draw_bottom_rounded_rect", "draw_spectrum_frame", "compute_band_color_offset",
    "still_preview_values", "generate_dummy_dynamic_values",
    "open_ffmpeg_encoder", "render_video",
    "find_loud_segment_start", "suggest_frequency_range", "analyze_preview_segment",
    "render_audio_to_video", "build_default_output_path", "build_matte_output_path", "unique_output_pair",
]

