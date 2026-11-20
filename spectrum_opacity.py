"""Matched front/matte opacity and checkerboard preview composition."""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache

import numpy as np

from spectrum_output_canvas import canvas_position, output_dimensions, place_on_output_canvas
from spectrum_types import RenderStyle


def prepare_opacity_style(style: RenderStyle) -> RenderStyle:
    p = style.opacity_percent
    if not isinstance(p, int) or not 0 <= p <= 100:
        raise ValueError("Opacity must be an integer from 0 to 100.")
    if p == 100:
        return style
    fill = (255, 255, 255) if style.is_matte else (0, 0, 0)
    # Main-only glow is additive light, not matched alpha coverage. Preserve the
    # legacy behavior at 100%, but omit it for the Difference-compatible pair.
    return replace(style, background_color=fill, output_canvas_background=fill,
                   edge_glow_enabled=False, edge_glow_mode="none")


def make_matte_style(style: RenderStyle) -> RenderStyle:
    return replace(style, background_color=(255, 255, 255),
                   output_canvas_background=(255, 255, 255),
                   bar_color=(0, 0, 0), bar_color2=(0, 0, 0), color_mode="vertical",
                   edge_glow_enabled=False, edge_glow_mode="none", is_matte=True)


@lru_cache(maxsize=101)
def _opacity_tables(percent: int) -> tuple[np.ndarray, np.ndarray]:
    levels = np.arange(256, dtype=np.uint16)
    front = (levels * percent // 100).astype(np.uint8)
    matte = (255 - (255 - levels) * percent // 100).astype(np.uint8)
    return front, matte


def apply_output_opacity(frame: np.ndarray, style: RenderStyle) -> np.ndarray:
    if style.opacity_percent == 100:
        return frame
    table = _opacity_tables(style.opacity_percent)[1 if style.is_matte else 0]
    return table[frame]


def preview_output_frame(front: np.ndarray, style: RenderStyle, matte: np.ndarray | None = None) -> np.ndarray:
    """Compose over a checkerboard only in the GUI; never export that background.

    Source-sized masks can be retained for motion previews. The output-sized
    canvas is created only when displaying a frame.
    """
    if matte is None:
        return place_on_output_canvas(front, style)
    width, height = output_dimensions(style)
    cell = max(8, min(width, height) // 24)
    pattern = ((np.arange(height)[:, None] // cell + np.arange(width)[None, :] // cell) % 2)
    out = np.repeat(np.where(pattern == 0, 80, 128).astype(np.uint8)[:, :, None], 3, axis=2)
    source_h, source_w = front.shape[:2]
    x, y = canvas_position(style.output_canvas, source_w, source_h) if style.output_canvas.enabled else (0, 0)
    x0, y0, x1, y1 = max(0, x), max(0, y), min(width, x + source_w), min(height, y + source_h)
    if x1 > x0 and y1 > y0:
        f = front[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.uint16)
        m = matte[y0 - y:y1 - y, x0 - x:x1 - x]
        if m.ndim == 2:
            m = m[:, :, None]
        result = f + (out[y0:y1, x0:x1].astype(np.uint16) * m + 127) // 255
        out[y0:y1, x0:x1] = np.clip(result, 0, 255).astype(np.uint8)
    return out
