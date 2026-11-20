"""Place completed spectrum frames on an output canvas without rescaling."""
from __future__ import annotations

import numpy as np

from spectrum_primitives import create_frame
from spectrum_types import OutputCanvasSettings, RenderStyle


CANVAS_ANCHORS = (
    "top_left", "top_center", "top_right",
    "center_left", "center", "center_right",
    "bottom_left", "bottom_center", "bottom_right",
)


def validate_output_canvas(settings: OutputCanvasSettings) -> None:
    if not settings.enabled:
        return
    for value in (settings.width, settings.height):
        if not isinstance(value, int) or not 2 <= value <= 7680 or value % 2:
            raise ValueError("Output canvas dimensions must be even integers from 2 to 7680.")
    if settings.anchor not in CANVAS_ANCHORS:
        raise ValueError("Unknown output canvas anchor.")
    if not isinstance(settings.offset_x, int) or not isinstance(settings.offset_y, int):
        raise ValueError("Output canvas offsets must be integers.")


def output_dimensions(style: RenderStyle) -> tuple[int, int]:
    settings = style.output_canvas
    validate_output_canvas(settings)
    return (settings.width, settings.height) if settings.enabled else (style.width, style.height)


def canvas_position(settings: OutputCanvasSettings, width: int, height: int) -> tuple[int, int]:
    index = CANVAS_ANCHORS.index(settings.anchor)
    row, col = divmod(index, 3)
    x = (0, (settings.width - width) // 2, settings.width - width)[col]
    y = (0, (settings.height - height) // 2, settings.height - height)[row]
    return (x + (-settings.offset_x if col == 2 else settings.offset_x),
            y + (-settings.offset_y if row == 2 else settings.offset_y))


def place_on_output_canvas(frame: np.ndarray, style: RenderStyle) -> np.ndarray:
    settings = style.output_canvas
    if not settings.enabled:
        return frame
    width, height = output_dimensions(style)
    out = create_frame(width, height, style.output_canvas_background)
    source_h, source_w = frame.shape[:2]
    x, y = canvas_position(settings, source_w, source_h)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(width, x + source_w), min(height, y + source_h)
    if x1 > x0 and y1 > y0:
        out[y0:y1, x0:x1] = frame[y0 - y:y1 - y, x0 - x:x1 - x]
    return out
