# -*- coding: utf-8 -*-
"""Low-level drawing primitives.

This module is independent from audio analysis, motion shaping, and visual
parts.  Visual parts emit Primitive objects; this renderer draws them onto a
numpy RGB frame.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np

from spectrum_types import RGB

PrimitiveKind = Literal["rect", "rounded_rect", "top_rounded_rect", "bottom_rounded_rect"]

@dataclass(frozen=True)
class Primitive:
    kind: PrimitiveKind
    x0: int
    y0: int
    x1: int
    y1: int
    color: RGB
    radius: int = 0
    z_index: int = 0
    color2: RGB | None = None


def create_frame(width: int, height: int, background_color: RGB) -> np.ndarray:
    width = max(1, int(width))
    height = max(1, int(height))
    frame = np.empty((height, width, 3), dtype=np.uint8)
    frame[:, :, 0] = int(background_color[0])
    frame[:, :, 1] = int(background_color[1])
    frame[:, :, 2] = int(background_color[2])
    return frame


def draw_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB) -> None:
    if x1 <= x0 or y1 <= y0:
        return
    frame[y0:y1, x0:x1, :] = color


def _clamped_radius(x0: int, y0: int, x1: int, y1: int, radius: int) -> float:
    h = int(y1 - y0)
    w = int(x1 - x0)
    if w <= 0 or h <= 0:
        return 0.0
    requested = float(max(0, radius))
    if requested <= 0:
        return 0.0
    return float(min(requested, w / 2.0, h / 2.0))


def _rounded_alpha(h: int, w: int, radius: float) -> np.ndarray:
    yy, xx = np.indices((h, w), dtype=np.float32)
    px = xx + 0.5 - (w / 2.0)
    py = yy + 0.5 - (h / 2.0)
    half_w = w / 2.0
    half_h = h / 2.0
    qx = np.abs(px) - (half_w - radius)
    qy = np.abs(py) - (half_h - radius)
    ox = np.maximum(qx, 0.0)
    oy = np.maximum(qy, 0.0)
    outside = np.sqrt(ox * ox + oy * oy)
    inside = np.minimum(np.maximum(qx, qy), 0.0)
    dist = outside + inside - radius
    return np.clip(0.5 - dist, 0.0, 1.0).astype(np.float32)


def _primitive_alpha(kind: PrimitiveKind, x0: int, y0: int, x1: int, y1: int, radius: int) -> np.ndarray:
    h = int(y1 - y0)
    w = int(x1 - x0)
    if w <= 0 or h <= 0:
        return np.zeros((0, 0), dtype=np.float32)
    if kind == 'rect':
        return np.ones((h, w), dtype=np.float32)
    r = _clamped_radius(x0, y0, x1, y1, radius)
    if r <= 0:
        return np.ones((h, w), dtype=np.float32)
    alpha = _rounded_alpha(h, w, r)
    if kind == 'rounded_rect':
        return alpha
    rr = int(np.ceil(r))
    out = alpha.copy()
    if kind == 'top_rounded_rect':
        if rr < h:
            out[rr:, :] = 1.0
        return out
    if kind == 'bottom_rounded_rect':
        if rr < h:
            out[:max(0, h - rr), :] = 1.0
        return out
    raise ValueError(f'Unknown primitive kind: {kind}')


def _fill_image(h: int, w: int, color1: RGB, color2: RGB | None) -> np.ndarray:
    if color2 is None or tuple(color1) == tuple(color2):
        img = np.empty((h, w, 3), dtype=np.float32)
        img[:, :, :] = np.array(color1, dtype=np.float32)[None, None, :]
        return img
    c1 = np.array(color1, dtype=np.float32)
    c2 = np.array(color2, dtype=np.float32)
    t = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    row = c1[None, None, :] * (1.0 - t) + c2[None, None, :] * t
    return np.repeat(row, w, axis=1)


def _render_primitive(frame: np.ndarray, primitive: Primitive) -> None:
    x0, y0, x1, y1 = primitive.x0, primitive.y0, primitive.x1, primitive.y1
    if x1 <= x0 or y1 <= y0:
        return
    alpha = _primitive_alpha(primitive.kind, x0, y0, x1, y1, int(primitive.radius))
    if alpha.size == 0 or not np.any(alpha > 0):
        return
    region = frame[y0:y1, x0:x1, :]
    fill = _fill_image(y1 - y0, x1 - x0, primitive.color, primitive.color2)
    a = alpha[:, :, None]
    blended = region.astype(np.float32) * (1.0 - a) + fill * a
    region[:, :, :] = np.clip(blended, 0, 255).astype(np.uint8)


def draw_rounded_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB, radius: int) -> None:
    _render_primitive(frame, Primitive(kind='rounded_rect', x0=x0, y0=y0, x1=x1, y1=y1, color=color, radius=radius))


def draw_top_rounded_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB, radius: int) -> None:
    _render_primitive(frame, Primitive(kind='top_rounded_rect', x0=x0, y0=y0, x1=x1, y1=y1, color=color, radius=radius))


def draw_bottom_rounded_rect(frame: np.ndarray, x0: int, y0: int, x1: int, y1: int, color: RGB, radius: int) -> None:
    _render_primitive(frame, Primitive(kind='bottom_rounded_rect', x0=x0, y0=y0, x1=x1, y1=y1, color=color, radius=radius))


def draw_primitive(frame: np.ndarray, primitive: Primitive) -> None:
    _render_primitive(frame, primitive)


def draw_primitives(frame: np.ndarray, primitives: Iterable[Primitive]) -> None:
    for primitive in sorted(list(primitives), key=lambda p: p.z_index):
        draw_primitive(frame, primitive)
