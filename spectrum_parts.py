# -*- coding: utf-8 -*-
"""Visual parts for spectrum rendering.

A visual part converts display-ready numeric values into geometric primitives.
The current horizontal bar spectrum is represented as BarSpectrumPart and now
supports both the classic single-sided mode and a mirrored dual-sided mode.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import List, Tuple

import numpy as np

from spectrum_types import RenderStyle, RGB
from spectrum_primitives import Primitive
from spectrum_scene import Bounds


def _lerp_color(c1: RGB, c2: RGB, t: float) -> RGB:
    t = float(np.clip(t, 0.0, 1.0))
    return (
        int(round(c1[0] * (1.0 - t) + c2[0] * t)),
        int(round(c1[1] * (1.0 - t) + c2[1] * t)),
        int(round(c1[2] * (1.0 - t) + c2[2] * t)),
    )

@dataclass
class BarLayout:
    positions: List[Tuple[int, int]]
    base_y: int
    max_height: int
    bounds: Bounds
    mode: str = "single"
    mirror_base_y: int | None = None

@dataclass
class BarSpectrumPart:
    """Current horizontal bar-spectrum visual as a reusable part.

    Supported display modes:
    - single: classic one-sided bars rising upward from the bottom baseline
    - dual: mirrored bars growing away from the center line
    """
    style: RenderStyle
    origin_x: int = 0
    origin_y: int = 0
    band_color_offset: int = 0

    def build_layout(self) -> BarLayout:
        style = self.style
        width, height, bars = int(style.width), int(style.height), int(style.bars)
        margin_x = max(0, int(round(width * style.side_margin_ratio)))
        area_w = max(bars, width - margin_x * 2)
        slot_w = area_w / float(bars)
        fill = float(np.clip(style.bar_width_scale, 0.05, 1.00))
        bar_w = max(1, int(round(slot_w * fill)))
        bar_w = min(bar_w, max(1, int(math.floor(slot_w))))

        positions: List[Tuple[int, int]] = []
        ox = int(self.origin_x)
        oy = int(self.origin_y)
        for b in range(bars):
            center = margin_x + (b + 0.5) * slot_w
            x0 = int(round(center - bar_w / 2.0))
            x1 = x0 + bar_w
            x0 = max(0, min(width - 1, x0))
            x1 = max(x0 + 1, min(width, x1))
            positions.append((x0 + ox, x1 + ox))

        mode = str(getattr(style, "display_mode", "single") or "single")
        if mode == "dual":
            outer_margin = max(0, int(round(height * style.bottom_margin_ratio)))
            center_y = height // 2
            top_space = max(1, center_y - outer_margin)
            bottom_space = max(1, height - center_y - outer_margin)
            max_h = max(1, int(round(min(top_space, bottom_space) * style.max_height_ratio)))
            return BarLayout(
                positions=positions,
                base_y=center_y + oy,
                max_height=max_h,
                bounds=Bounds(float(ox), float(oy), float(ox + width), float(oy + height)),
                mode="dual",
                mirror_base_y=center_y + oy,
            )

        bottom_margin = max(0, int(round(height * style.bottom_margin_ratio)))
        base_y = max(1, min(height, height - bottom_margin))
        max_h = max(1, int(round(height * style.max_height_ratio)))
        max_h = min(max_h, base_y)
        return BarLayout(
            positions=positions,
            base_y=base_y + oy,
            max_height=max_h,
            bounds=Bounds(float(ox), float(oy), float(ox + width), float(oy + height)),
            mode="single",
            mirror_base_y=None,
        )

    def required_bounds(self) -> Bounds:
        return self.build_layout().bounds

    def _effective_x_span(self, x0: int, x1: int, h: int) -> tuple[int, int]:
        """Rounded-bar emergence: low bars start as a small pill."""
        style = self.style
        full_w = max(1, int(x1 - x0))
        if int(style.corner_radius) <= 0 or h >= full_w:
            return x0, x1

        min_w = max(1.5, full_w * 0.24)
        grow_h = max(1.0, full_w * 0.85)
        t = float(np.clip(h / grow_h, 0.0, 1.0))
        t = t * t * (3.0 - 2.0 * t)
        eff_w = min(full_w, max(min_w, min_w + (full_w - min_w) * t))
        cx = (x0 + x1) / 2.0
        nx0 = int(round(cx - eff_w / 2.0))
        nx1 = int(round(cx + eff_w / 2.0))
        if nx1 <= nx0:
            nx1 = nx0 + 1
        nx0 = max(int(self.origin_x), nx0)
        nx1 = min(int(self.origin_x + int(style.width)), nx1)
        return nx0, nx1

    def _band_color(self, index: int) -> RGB:
        style = self.style
        bars = max(1, int(style.bars))
        idx = (int(index) + int(self.band_color_offset)) % bars
        t = 0.0 if bars <= 1 else float(idx) / float(max(1, bars - 1))
        return _lerp_color(style.bar_color, style.bar_color2, t)

    def _primitive(self, x0: int, x1: int, y0: int, y1: int, kind: str | None = None, color: RGB | None = None, color2: RGB | None = None) -> Primitive:
        style = self.style
        if kind is None:
            kind = "rounded_rect" if int(style.corner_radius) > 0 else "rect"
        return Primitive(
            kind=kind,
            x0=int(x0), y0=int(y0), x1=int(x1), y1=int(y1),
            color=(style.bar_color if color is None else color),
            color2=color2,
            radius=int(style.corner_radius),
            z_index=0,
        )

    def primitives_for_values(self, values: np.ndarray) -> list[Primitive]:
        layout = self.build_layout()
        vals = np.asarray(values, dtype=np.float32)
        style = self.style
        primitives: list[Primitive] = []
        frame_top = int(self.origin_y)
        frame_bottom = int(self.origin_y + int(style.height))
        color_mode = str(getattr(style, 'color_mode', 'vertical') or 'vertical')

        for b, value in enumerate(vals[:int(style.bars)]):
            v = float(np.clip(value, 0.0, 1.0))
            if style.gamma != 1.0:
                v = v ** style.gamma
            h = int(round(v * layout.max_height))
            if h <= 0:
                continue

            x0, x1 = layout.positions[b]
            if layout.mode != "dual":
                x0, x1 = self._effective_x_span(x0, x1, h)

            if color_mode == 'band':
                solid = self._band_color(b)
                top_outer = solid
                bottom_inner = None
                bottom_outer = solid
            else:
                top_outer = style.bar_color2
                bottom_inner = style.bar_color
                bottom_outer = style.bar_color2

            if layout.mode == "dual":
                center = int(layout.base_y)
                y0 = max(frame_top, center - h)
                y1 = min(frame_bottom, center)
                if y1 > y0:
                    primitives.append(self._primitive(
                        x0, x1, y0, y1,
                        kind=("top_rounded_rect" if int(style.corner_radius) > 0 else "rect"),
                        color=top_outer,
                        color2=bottom_inner,
                    ))
                y0 = max(frame_top, center)
                y1 = min(frame_bottom, center + h)
                if y1 > y0:
                    primitives.append(self._primitive(
                        x0, x1, y0, y1,
                        kind=("bottom_rounded_rect" if int(style.corner_radius) > 0 else "rect"),
                        color=(bottom_inner if bottom_inner is not None else bottom_outer),
                        color2=(bottom_outer if bottom_inner is not None else None),
                    ))
            else:
                y0 = max(frame_top, int(layout.base_y) - h)
                y1 = min(frame_bottom, int(layout.base_y))
                if y1 > y0:
                    primitives.append(self._primitive(x0, x1, y0, y1, color=top_outer, color2=bottom_inner))

        return primitives
