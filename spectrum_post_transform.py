# -*- coding: utf-8 -*-
"""Post-render frame coordinate transforms.

This layer intentionally works on a completed RGB frame.  Bar layout, digital
segments, gradients, scrolling, peak hold, and matte drawing all finish before
this module receives the image.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from spectrum_types import PostTransformModulation, PostTransformSettings, RGB


def _modulated_value(base: float, modulation: PostTransformModulation, time_seconds: float) -> float:
    if not modulation.enabled or abs(float(modulation.amplitude)) <= 1.0e-9:
        return float(base)
    period = max(1.0e-6, float(modulation.period_seconds or 1.0))
    phase = math.radians(float(modulation.phase_degrees or 0.0))
    return float(base) + float(modulation.amplitude) * math.sin((2.0 * math.pi * float(time_seconds) / period) + phase)


@dataclass(frozen=True)
class ResolvedPostTransform:
    transform_type: str
    angle_degrees: float = 0.0
    scale_percent: float = 100.0
    audio_scale_enabled: bool = False
    audio_scale_max_percent: float = 115.0
    audio_scale_floor_percent: float = 10.0
    audio_scale_ceiling_percent: float = 50.0
    audio_scale_hold_ms: int = 66
    audio_scale_decay_ms: int = 167
    trapezoid_top_scale: float = 1.0
    trapezoid_bottom_scale: float = 1.0
    trapezoid_vertical_percent: float = 0.0
    trapezoid_horizontal_percent: float = 0.0


def resolve_post_transform(
    settings: PostTransformSettings | None,
    time_seconds: float = 0.0,
    audio_energy: float = 0.0,
) -> ResolvedPostTransform:
    if settings is None:
        return ResolvedPostTransform("none")

    transform_type = str(getattr(settings, "transform_type", "none") or "none").lower()
    if transform_type not in {"none", "rotate", "trapezoid", "combined"}:
        transform_type = "none"

    angle = _modulated_value(
        float(getattr(settings, "angle_degrees", 0.0) or 0.0),
        getattr(settings, "angle_modulation", PostTransformModulation()),
        time_seconds,
    )
    scale_percent = float(getattr(settings, "scale_percent", 100.0) or 100.0)
    audio_scale_enabled = bool(getattr(settings, "audio_scale_enabled", False))
    audio_scale_max_percent = float(getattr(settings, "audio_scale_max_percent", 115.0) or 115.0)
    audio_scale_floor_percent = float(getattr(settings, "audio_scale_floor_percent", 10.0) or 0.0)
    audio_scale_ceiling_percent = float(getattr(settings, "audio_scale_ceiling_percent", 50.0) or 0.0)
    audio_scale_hold_ms = int(getattr(settings, "audio_scale_hold_ms", 66) or 0)
    audio_scale_decay_ms = int(getattr(settings, "audio_scale_decay_ms", 167) or 1)
    if audio_scale_enabled and abs(audio_scale_max_percent - 100.0) > 1.0e-9:
        energy = max(0.0, min(1.0, float(audio_energy or 0.0)))
        scale_percent = 100.0 + (audio_scale_max_percent - 100.0) * energy
    trapezoid_offset = _modulated_value(
        0.0,
        getattr(settings, "trapezoid_modulation", PostTransformModulation()),
        time_seconds,
    )
    top_scale = float(getattr(settings, "trapezoid_top_scale", 1.0) or 1.0) + trapezoid_offset
    bottom_scale = float(getattr(settings, "trapezoid_bottom_scale", 1.0) or 1.0) - trapezoid_offset
    top_scale = max(0.05, top_scale)
    bottom_scale = max(0.05, bottom_scale)
    vertical_percent = float(getattr(settings, "trapezoid_vertical_percent", 0.0) or 0.0)
    horizontal_percent = float(getattr(settings, "trapezoid_horizontal_percent", 0.0) or 0.0)

    # Backward compatibility: older presets stored vertical trapezoid as top
    # and bottom widths.  The new UI exposes a single -100..100 vertical skew.
    if abs(vertical_percent) <= 1.0e-9 and transform_type == "trapezoid":
        if abs(top_scale - 1.0) > 1.0e-9 and abs(bottom_scale - 1.0) <= 1.0e-9:
            vertical_percent = (top_scale - 1.0) * 100.0
        elif abs(bottom_scale - 1.0) > 1.0e-9 and abs(top_scale - 1.0) <= 1.0e-9:
            vertical_percent = (1.0 - bottom_scale) * 100.0

    if transform_type == "none":
        has_static_transform = (
            abs(angle) > 1.0e-9
            or abs(scale_percent - 100.0) > 1.0e-9
            or abs(vertical_percent) > 1.0e-9
            or abs(horizontal_percent) > 1.0e-9
            or abs(top_scale - 1.0) > 1.0e-9
            or abs(bottom_scale - 1.0) > 1.0e-9
        )
        if has_static_transform or (audio_scale_enabled and abs(audio_scale_max_percent - 100.0) > 1.0e-9):
            transform_type = "combined"

    return ResolvedPostTransform(
        transform_type=transform_type,
        angle_degrees=angle,
        scale_percent=max(5.0, min(500.0, scale_percent)),
        audio_scale_enabled=audio_scale_enabled,
        audio_scale_max_percent=max(5.0, min(500.0, audio_scale_max_percent)),
        audio_scale_floor_percent=max(0.0, min(95.0, audio_scale_floor_percent)),
        audio_scale_ceiling_percent=max(1.0, min(100.0, audio_scale_ceiling_percent)),
        audio_scale_hold_ms=max(0, audio_scale_hold_ms),
        audio_scale_decay_ms=max(1, audio_scale_decay_ms),
        trapezoid_top_scale=top_scale,
        trapezoid_bottom_scale=bottom_scale,
        trapezoid_vertical_percent=max(-100.0, min(100.0, vertical_percent)),
        trapezoid_horizontal_percent=max(-100.0, min(100.0, horizontal_percent)),
    )


def is_identity_post_transform(settings: PostTransformSettings | ResolvedPostTransform | None) -> bool:
    if settings is None:
        return True
    resolved = settings if isinstance(settings, ResolvedPostTransform) else resolve_post_transform(settings)
    transform_type = str(getattr(resolved, "transform_type", "none") or "none").lower()
    if transform_type == "none":
        return True
    return (
        abs(float(getattr(resolved, "angle_degrees", 0.0) or 0.0)) <= 1.0e-9
        and abs(float(getattr(resolved, "scale_percent", 100.0) or 100.0) - 100.0) <= 1.0e-9
        and (
            not bool(getattr(resolved, "audio_scale_enabled", False))
            or abs(float(getattr(resolved, "audio_scale_max_percent", 100.0) or 100.0) - 100.0) <= 1.0e-9
        )
        and abs(float(getattr(resolved, "trapezoid_vertical_percent", 0.0) or 0.0)) <= 1.0e-9
        and abs(float(getattr(resolved, "trapezoid_horizontal_percent", 0.0) or 0.0)) <= 1.0e-9
    )


def _normalized_output_grid(width: int, height: int) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    yy, xx = np.indices((height, width), dtype=np.float32)
    cx = (float(width) - 1.0) * 0.5
    cy = (float(height) - 1.0) * 0.5
    scale = max(1.0, min(float(width), float(height)) * 0.5)
    return (xx - cx) / scale, (yy - cy) / scale, cx, cy, scale


def _trapezoid_scales(resolved: ResolvedPostTransform) -> tuple[float, float, float, float]:
    vertical = float(resolved.trapezoid_vertical_percent) / 100.0
    horizontal = float(resolved.trapezoid_horizontal_percent) / 100.0

    top_scale = max(0.05, 1.0 + vertical) if vertical < 0.0 else 1.0
    bottom_scale = max(0.05, 1.0 - vertical) if vertical > 0.0 else 1.0
    left_scale = max(0.05, 1.0 + horizontal) if horizontal < 0.0 else 1.0
    right_scale = max(0.05, 1.0 - horizontal) if horizontal > 0.0 else 1.0
    return top_scale, bottom_scale, left_scale, right_scale


def _source_corners(axis_x: float, axis_y: float) -> np.ndarray:
    return np.array(
        [
            [-axis_x, -axis_y],
            [axis_x, -axis_y],
            [axis_x, axis_y],
            [-axis_x, axis_y],
        ],
        dtype=np.float64,
    )


def _destination_corners(resolved: ResolvedPostTransform, axis_x: float, axis_y: float) -> np.ndarray:
    top_scale, bottom_scale, left_scale, right_scale = _trapezoid_scales(resolved)
    scale_factor = max(0.05, float(resolved.scale_percent) / 100.0)
    axis_x *= scale_factor
    axis_y *= scale_factor
    corners = np.array(
        [
            [-axis_x * top_scale, -axis_y * left_scale],
            [axis_x * top_scale, -axis_y * right_scale],
            [axis_x * bottom_scale, axis_y * right_scale],
            [-axis_x * bottom_scale, axis_y * left_scale],
        ],
        dtype=np.float64,
    )

    if abs(float(resolved.angle_degrees)) > 1.0e-9:
        angle = math.radians(float(resolved.angle_degrees))
        c = math.cos(angle)
        s = math.sin(angle)
        x = corners[:, 0].copy()
        y = corners[:, 1].copy()
        corners[:, 0] = c * x - s * y
        corners[:, 1] = s * x + c * y

    return corners


def _homography_from_points(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    rows: list[list[float]] = []
    values: list[float] = []
    for (x, y), (u, v) in zip(src, dst):
        rows.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y])
        values.append(u)
        rows.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y])
        values.append(v)
    h = np.linalg.solve(np.array(rows, dtype=np.float64), np.array(values, dtype=np.float64))
    return np.array(
        [
            [h[0], h[1], h[2]],
            [h[3], h[4], h[5]],
            [h[6], h[7], 1.0],
        ],
        dtype=np.float64,
    )


def _apply_homography(x: np.ndarray, y: np.ndarray, matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    denominator = matrix[2, 0] * x + matrix[2, 1] * y + matrix[2, 2]
    denominator = np.where(np.abs(denominator) <= 1.0e-9, 1.0e-9, denominator)
    mapped_x = (matrix[0, 0] * x + matrix[0, 1] * y + matrix[0, 2]) / denominator
    mapped_y = (matrix[1, 0] * x + matrix[1, 1] * y + matrix[1, 2]) / denominator
    return mapped_x, mapped_y


def _source_map(width: int, height: int, resolved: ResolvedPostTransform) -> tuple[np.ndarray, np.ndarray]:
    x, y, cx, cy, scale = _normalized_output_grid(width, height)

    if resolved.transform_type in {"rotate", "trapezoid", "combined"}:
        axis_x = cx / scale
        axis_y = cy / scale
        src_corners = _source_corners(axis_x, axis_y)
        dst_corners = _destination_corners(resolved, axis_x, axis_y)
        # Forward mapping is one planar quad transform: first shape the source
        # rectangle into a trapezoid, then rotate that resulting plane as a unit.
        inverse_matrix = _homography_from_points(dst_corners, src_corners)
        x, y = _apply_homography(x, y, inverse_matrix)

    if resolved.transform_type == "trapezoid" and abs(float(resolved.trapezoid_vertical_percent)) <= 1.0e-9 and abs(float(resolved.trapezoid_horizontal_percent)) <= 1.0e-9:
        # Legacy direct settings: x' = x * scale(y), y' = y.
        t = np.clip((y + 1.0) * 0.5, 0.0, 1.0)
        legacy_scale_y = (1.0 - t) * float(resolved.trapezoid_top_scale) + t * float(resolved.trapezoid_bottom_scale)
        legacy_scale_y = np.maximum(legacy_scale_y, 0.05)
        x = x / legacy_scale_y
    return (x * scale + cx).astype(np.float32), (y * scale + cy).astype(np.float32)


def _sample_bilinear(frame: np.ndarray, source_x: np.ndarray, source_y: np.ndarray, fill_color: RGB) -> np.ndarray:
    height, width = frame.shape[:2]
    out = np.empty_like(frame)
    out[:, :, 0] = int(fill_color[0])
    out[:, :, 1] = int(fill_color[1])
    out[:, :, 2] = int(fill_color[2])

    valid = (source_x >= 0.0) & (source_x <= float(width - 1)) & (source_y >= 0.0) & (source_y <= float(height - 1))
    if not np.any(valid):
        return out

    x0 = np.floor(source_x[valid]).astype(np.int32)
    y0 = np.floor(source_y[valid]).astype(np.int32)
    x1 = np.minimum(x0 + 1, width - 1)
    y1 = np.minimum(y0 + 1, height - 1)

    wx = (source_x[valid] - x0).astype(np.float32)
    wy = (source_y[valid] - y0).astype(np.float32)

    top = frame[y0, x0].astype(np.float32) * (1.0 - wx[:, None]) + frame[y0, x1].astype(np.float32) * wx[:, None]
    bottom = frame[y1, x0].astype(np.float32) * (1.0 - wx[:, None]) + frame[y1, x1].astype(np.float32) * wx[:, None]
    sampled = top * (1.0 - wy[:, None]) + bottom * wy[:, None]
    out[valid] = np.clip(np.rint(sampled), 0, 255).astype(np.uint8)
    return out


class PostTransformApplier:
    """Apply post transforms while caching static inverse-mapping grids."""

    def __init__(self, settings: PostTransformSettings | None, width: int, height: int, fps: int, fill_color: RGB) -> None:
        self.settings = settings
        self.width = int(width)
        self.height = int(height)
        self.fps = max(1, int(fps))
        self.fill_color = fill_color
        self._cached_key: ResolvedPostTransform | None = None
        self._cached_map: tuple[np.ndarray, np.ndarray] | None = None
        self._audio_peak_value = 0.0
        self._audio_hold_frames_left = 0

    def _audio_energy(self, values: np.ndarray | None) -> float:
        if values is None:
            return 0.0
        data = np.asarray(values, dtype=np.float32)
        if data.size <= 0:
            return 0.0
        if self.settings is not None and bool(getattr(self.settings, "audio_scale_low_only", True)):
            percent = max(1.0, min(100.0, float(getattr(self.settings, "audio_scale_low_band_percent", 25) or 25)))
            count = max(1, int(math.ceil(float(data.size) * percent / 100.0)))
            data = data[:count]
        return float(np.clip(np.mean(data), 0.0, 1.0))

    def _audio_reactive_energy(self, raw_energy: float) -> float:
        settings = self.settings
        if settings is None:
            return 0.0
        floor = max(0.0, min(0.95, float(getattr(settings, "audio_scale_floor_percent", 10.0) or 0.0) / 100.0))
        ceiling = max(0.01, min(1.0, float(getattr(settings, "audio_scale_ceiling_percent", 50.0) or 0.0) / 100.0))
        ceiling = max(ceiling, floor + 0.01)
        raw = max(0.0, min(1.0, float(raw_energy or 0.0)))
        if raw <= floor:
            return 0.0
        return max(0.0, min(1.0, (raw - floor) / (ceiling - floor)))

    def _audio_peak_hold_energy(self, raw_energy: float) -> float:
        settings = self.settings
        if (
            settings is None
            or not bool(getattr(settings, "audio_scale_enabled", False))
            or abs(float(getattr(settings, "audio_scale_max_percent", 100.0) or 100.0) - 100.0) <= 1.0e-9
        ):
            return 0.0

        raw = self._audio_reactive_energy(raw_energy)
        hold_ms = max(0, int(getattr(settings, "audio_scale_hold_ms", 66) or 0))
        hold_frames = max(0, int(math.ceil((float(hold_ms) * float(self.fps)) / 1000.0)) - 1)
        decay_ms = max(1, int(getattr(settings, "audio_scale_decay_ms", 167) or 1))
        decay_per_frame = 1000.0 / (float(decay_ms) * float(self.fps))

        if raw >= self._audio_peak_value:
            self._audio_peak_value = raw
            self._audio_hold_frames_left = hold_frames
        elif self._audio_hold_frames_left > 0:
            self._audio_hold_frames_left -= 1
        else:
            self._audio_peak_value = max(raw, self._audio_peak_value - decay_per_frame)

        return self._audio_peak_value

    def apply(self, frame: np.ndarray, frame_index: int = 0, audio_values: np.ndarray | None = None) -> np.ndarray:
        time_seconds = float(frame_index) / float(self.fps)
        audio_energy = self._audio_peak_hold_energy(self._audio_energy(audio_values))
        resolved = resolve_post_transform(self.settings, time_seconds, audio_energy)
        if is_identity_post_transform(resolved):
            return frame

        if self._cached_key != resolved or self._cached_map is None:
            self._cached_map = _source_map(self.width, self.height, resolved)
            self._cached_key = resolved

        source_x, source_y = self._cached_map
        return _sample_bilinear(frame, source_x, source_y, self.fill_color)


def apply_post_transform(
    frame: np.ndarray,
    settings: PostTransformSettings | None,
    frame_index: int = 0,
    fps: int = 30,
    fill_color: RGB = (0, 0, 0),
    audio_values: np.ndarray | None = None,
) -> np.ndarray:
    return PostTransformApplier(settings, frame.shape[1], frame.shape[0], fps, fill_color).apply(frame, frame_index, audio_values)
