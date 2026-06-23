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

    def _loop_band_color(self, index: int) -> RGB:
        style = self.style
        bars = max(1, int(style.bars))
        idx = (int(index) + int(self.band_color_offset)) % bars
        if bars <= 1:
            t = 0.0
        else:
            x = float(idx) / float(max(1, bars - 1))
            t = 1.0 - abs(x * 2.0 - 1.0)
        return _lerp_color(style.bar_color, style.bar_color2, t)

    def _horizontal_band_color(self, index: int, color_mode: str) -> RGB:
        if color_mode == 'loop_band':
            return self._loop_band_color(index)
        return self._band_color(index)

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

    def _digital_layout(self, max_height: int) -> tuple[int, int, int]:
        """Return drawable segment count, segment height, and gap pixels."""
        max_height = max(1, int(max_height))
        requested_count = max(1, int(getattr(self.style, "digital_segments", 16) or 16))
        gap = max(0, int(getattr(self.style, "digital_gap_px", 2) or 0))
        count = min(requested_count, max_height)
        if count <= 1:
            return 1, max_height, 0
        gap = min(gap, max(0, (max_height - count) // (count - 1)))
        segment_h = max(1, (max_height - gap * (count - 1)) // count)
        return count, segment_h, gap

    def _digital_color(self, band_index: int, segment_index: int, segment_count: int, color_mode: str) -> RGB:
        if color_mode in {'band', 'loop_band'}:
            return self._horizontal_band_color(band_index, color_mode)
        if segment_count <= 1:
            t = 1.0
        else:
            t = float(segment_index) / float(max(1, segment_count - 1))
        return _lerp_color(self.style.bar_color, self.style.bar_color2, t)

    def _append_digital_segments(
        self,
        primitives: list[Primitive],
        *,
        band_index: int,
        x0: int,
        x1: int,
        base_y: int,
        max_height: int,
        value: float,
        direction: int,
        frame_top: int,
        frame_bottom: int,
        color_mode: str,
    ) -> None:
        count, segment_h, gap = self._digital_layout(max_height)
        lit = int(round(float(np.clip(value, 0.0, 1.0)) * count))
        lit = max(0, min(count, lit))
        if lit <= 0:
            return
        kind = "rounded_rect" if gap > 0 and int(self.style.corner_radius) > 0 else "rect"
        for s in range(lit):
            if direction < 0:
                y1 = int(base_y) - s * (segment_h + gap)
                y0 = y1 - segment_h
            else:
                y0 = int(base_y) + s * (segment_h + gap)
                y1 = y0 + segment_h
            y0 = max(frame_top, y0)
            y1 = min(frame_bottom, y1)
            if y1 <= y0:
                continue
            color = self._digital_color(band_index, s, count, color_mode)
            primitives.append(self._primitive(x0, x1, y0, y1, kind=kind, color=color, color2=None))

    def primitives_for_values(self, values: np.ndarray) -> list[Primitive]:
        layout = self.build_layout()
        vals = np.asarray(values, dtype=np.float32)
        style = self.style
        primitives: list[Primitive] = []
        frame_top = int(self.origin_y)
        frame_bottom = int(self.origin_y + int(style.height))
        color_mode = str(getattr(style, 'color_mode', 'vertical') or 'vertical')
        digital_enabled = bool(getattr(style, "digital_enabled", False))

        for b, value in enumerate(vals[:int(style.bars)]):
            v = float(np.clip(value, 0.0, 1.0))
            if style.gamma != 1.0:
                v = v ** style.gamma
            h = int(round(v * layout.max_height))
            if h <= 0:
                continue

            x0, x1 = layout.positions[b]
            if digital_enabled:
                if layout.mode == "dual":
                    center = int(layout.base_y)
                    self._append_digital_segments(
                        primitives,
                        band_index=b,
                        x0=x0,
                        x1=x1,
                        base_y=center,
                        max_height=layout.max_height,
                        value=v,
                        direction=-1,
                        frame_top=frame_top,
                        frame_bottom=frame_bottom,
                        color_mode=color_mode,
                    )
                    self._append_digital_segments(
                        primitives,
                        band_index=b,
                        x0=x0,
                        x1=x1,
                        base_y=center,
                        max_height=layout.max_height,
                        value=v,
                        direction=1,
                        frame_top=frame_top,
                        frame_bottom=frame_bottom,
                        color_mode=color_mode,
                    )
                else:
                    self._append_digital_segments(
                        primitives,
                        band_index=b,
                        x0=x0,
                        x1=x1,
                        base_y=int(layout.base_y),
                        max_height=layout.max_height,
                        value=v,
                        direction=-1,
                        frame_top=frame_top,
                        frame_bottom=frame_bottom,
                        color_mode=color_mode,
                    )
                continue

            if layout.mode != "dual":
                x0, x1 = self._effective_x_span(x0, x1, h)

            if color_mode in {'band', 'loop_band'}:
                solid = self._horizontal_band_color(b, color_mode)
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
