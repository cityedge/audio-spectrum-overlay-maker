"""Cached digital-bar rasterization, before glow and Post Transform."""
from __future__ import annotations

from functools import lru_cache
import math

import numpy as np

from spectrum_parts import BarSpectrumPart
from spectrum_primitives import _primitive_alpha, create_frame
from spectrum_types import RenderStyle


_TEMPLATE_FIELDS = (
    "width", "height", "bars", "display_mode", "background_color",
    "bar_color", "bar_color2", "color_mode", "max_height_ratio",
    "bottom_margin_ratio", "side_margin_ratio", "bar_width_scale",
    "corner_radius", "digital_segments", "digital_gap_px",
)


@lru_cache(maxsize=4)
def _prepare(key: tuple):
    style = RenderStyle(**dict(zip(_TEMPLATE_FIELDS, key)))
    part = BarSpectrumPart(style)
    layout = part.build_layout()
    # Very narrow canvases can put several bars on the same pixel. Keep the
    # reference renderer's ordered alpha compositing in that unusual case.
    if any(left[1] > right[0] for left, right in zip(layout.positions, layout.positions[1:])):
        return None
    count, segment_h, gap = part._digital_layout(layout.max_height)
    segments = np.full(style.height, -1, dtype=np.int32)
    spans = []
    for direction in ((-1, 1) if layout.mode == "dual" else (-1,)):
        for s in range(count):
            if direction < 0:
                y1 = layout.base_y - s * (segment_h + gap)
                y0 = y1 - segment_h
            else:
                y0 = layout.base_y + s * (segment_h + gap)
                y1 = y0 + segment_h
            y0, y1 = max(0, y0), min(style.height, y1)
            if y1 > y0:
                segments[y0:y1] = s
                spans.append((s, y0, y1))
    horizontal = style.color_mode in {"band", "loop_band"}
    palette = np.asarray([
        part._digital_color(i if horizontal else 0, 0 if horizontal else i, count, style.color_mode)
        for i in range(style.bars if horizontal else count)
    ], dtype=np.float32)
    kind = "rounded_rect" if gap > 0 and style.corner_radius > 0 else "rect"
    background = np.asarray(style.background_color, dtype=np.float32)
    templates = {}
    for width in {x1 - x0 for x0, x1 in layout.positions}:
        alpha = np.zeros((style.height, width, 1), dtype=np.float32)
        for _, y0, y1 in spans:
            alpha[y0:y1, :, 0] = _primitive_alpha(kind, 0, y0, width, y1, style.corner_radius)
        if horizontal:
            colors = palette[:, None, None, :]
        else:
            colors = palette[np.maximum(segments, 0)][None, :, None, :]
        templates[width] = np.clip(
            background * (1.0 - alpha) + colors * alpha, 0, 255
        ).astype(np.uint8)
    return layout, count, segments, templates, horizontal


def draw_digital_frame(values, style, band_color_offset=0, peak_values=None):
    """Return a digital frame, or None when ordered overlap needs the fallback.

    Cached strips contain the exact reference alpha/color blend against the
    background. Body and peak pieces occupy disjoint cells, so selecting rows
    reproduces both without allocating and compositing thousands of primitives.
    Cached arrays are read-only in use and safe for concurrent main/matte draws.
    """
    key = tuple(tuple(v) if isinstance(v, (list, np.ndarray)) else v
                for v in (getattr(style, name) for name in _TEMPLATE_FIELDS))
    prepared = _prepare(key)
    if prepared is None:
        return None
    layout, count, segments, templates, horizontal = prepared
    vals = np.asarray(values, dtype=np.float32)
    peaks = np.asarray(peak_values, dtype=np.float32) if peak_values is not None else None
    mode = str(style.peak_hold_mode or "marker").lower()
    if mode in {"off", "none", "なし"}:
        peaks = None
    elif peaks is None and mode in {"peaks_only", "peak_bars"}:
        peaks = vals
    if mode == "peak_bars" and peaks is not None:
        vals, peaks = peaks, None
    frame = create_frame(style.width, style.height, style.background_color)
    valid = segments >= 0
    for b, value in enumerate(vals[:int(style.bars)]):
        raw = float(np.clip(value, 0.0, 1.0))
        current = raw ** style.gamma if style.gamma != 1.0 else raw
        lit = max(0, min(count, round(current * count)))
        selected = valid & (segments < lit) if mode != "peaks_only" else np.zeros_like(valid)
        if peaks is not None and b < len(peaks):
            peak = float(np.clip(peaks[b], 0.0, 1.0))
            peak_current = 0.0 if mode == "peaks_only" else raw
            if peak > peak_current + 1e-5:
                if style.gamma != 1.0:
                    peak = peak ** style.gamma
                    peak_current = peak_current ** style.gamma
                peak_lit = max(0, min(count, round(peak_current * count)))
                last = max(0, min(count - 1, math.floor(peak * count)))
                first = max(peak_lit, last - max(1, int(style.digital_peak_segments or 1)) + 1)
                selected |= valid & (segments >= first) & (segments <= last)
        x0, x1 = layout.positions[b]
        color_index = (b + int(band_color_offset)) % int(style.bars) if horizontal else 0
        tile = templates[x1 - x0][color_index]
        frame[selected, x0:x1] = tile[selected]
    return frame
