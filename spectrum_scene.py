# -*- coding: utf-8 -*-
"""Scene, bounds, and canvas helpers.

This is the foundation for future canvas/part-based rendering.  The current GUI
still uses explicit width/height values for compatibility, but visual parts can
now describe bounds independently from video encoding.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from spectrum_types import RGB
from spectrum_primitives import Primitive

@dataclass(frozen=True)
class Bounds:
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, float(self.x1 - self.x0))

    @property
    def height(self) -> float:
        return max(0.0, float(self.y1 - self.y0))

    def padded(self, padding: float) -> "Bounds":
        p = max(0.0, float(padding))
        return Bounds(self.x0 - p, self.y0 - p, self.x1 + p, self.y1 + p)

    def translated(self, dx: float, dy: float) -> "Bounds":
        return Bounds(self.x0 + dx, self.y0 + dy, self.x1 + dx, self.y1 + dy)

    @staticmethod
    def union(bounds_list: Iterable["Bounds"]) -> "Bounds":
        items = list(bounds_list)
        if not items:
            return Bounds(0.0, 0.0, 0.0, 0.0)
        return Bounds(
            min(b.x0 for b in items),
            min(b.y0 for b in items),
            max(b.x1 for b in items),
            max(b.y1 for b in items),
        )

@dataclass(frozen=True)
class CanvasSpec:
    width: int
    height: int
    background_color: RGB = (0, 0, 0)

    def even_size(self) -> tuple[int, int]:
        w = max(2, int(self.width))
        h = max(2, int(self.height))
        if w % 2:
            w += 1
        if h % 2:
            h += 1
        return w, h

@dataclass
class Scene:
    canvas: CanvasSpec
    primitives: list[Primitive] = field(default_factory=list)

    def add(self, primitive: Primitive) -> None:
        self.primitives.append(primitive)

    def extend(self, primitives: Iterable[Primitive]) -> None:
        self.primitives.extend(list(primitives))

    def primitive_bounds(self) -> Bounds:
        bounds = [
            Bounds(p.x0, p.y0, p.x1, p.y1)
            for p in self.primitives
            if p.x1 > p.x0 and p.y1 > p.y0
        ]
        return Bounds.union(bounds)
