# -*- coding: utf-8 -*-
"""Preset management for Audio Spectrum Overlay Maker."""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List

CUSTOM_LABEL = "カスタム"

# Public preset values.  All system presets intentionally share the same
# black/white visual style and differ mainly in motion behavior.
SYSTEM_PRESETS: list[dict[str, Any]] = [
    {
        "name": "01 Dynamic Standard",
        "system": True,
        "description": "標準。Dynamicの基本となる上下動。",
        "values": {
            "width": 720, "height": 280, "fps": 30, "bars": 24, "display_mode": "片側バー", "scroll_mode": "なし", "scroll_step_frames": 2,
            "background_color": "#000000", "bar_color": "#FFFFFF", "bar_color2": "#FFFFFF", "color_mode": "縦グラデーション",
            "bar_width_percent": 62, "corner_radius": 18,
            "max_height_percent": 78, "side_margin_percent": 5, "bottom_margin_percent": 8,
            "freq_min": 80.0, "freq_max": 12000.0,
                "frequency_mode": "自動",
            "response_speed": "標準", "bounce_strength": "標準",
            "sensitivity_level": "標準", "motion_detail": "標準", "contrast_profile": "標準",
            "advanced_custom": False,
            "gain_db": 8.0,
            "auto_preview_segment": True, "scan_seconds": 120.0, "preview_start": 0.0, "motion_preview_duration": 10.0, "preview_duration": 30.0, "warmup": 5.0,
            "sample_rate": 24000, "fft_size": 1024, "analysis_bands": 64,
            "min_db": -60.0, "max_db": -6.0,
            "attack": 0.95, "release": 0.75,
            "relative_range_db": 30.0, "peak_percentile": 90.0,
            "base_cut": 0.12, "pulse_amount": 0.80, "pulse_speed": 0.25,
            "gamma": 0.85,
            "crf": 18, "encoder": "libx264", "x264_preset": "veryfast",
        },
    },
    {
        "name": "02 Dynamic Active",
        "system": True,
        "description": "上下動を強めた設定。ピークからより下まで戻りやすい。",
        "values": {
            "width": 720, "height": 280, "fps": 30, "bars": 24, "display_mode": "片側バー", "scroll_mode": "なし", "scroll_step_frames": 2,
            "background_color": "#000000", "bar_color": "#FFFFFF", "bar_color2": "#FFFFFF", "color_mode": "縦グラデーション",
            "bar_width_percent": 62, "corner_radius": 18,
            "max_height_percent": 80, "side_margin_percent": 5, "bottom_margin_percent": 8,
            "freq_min": 80.0, "freq_max": 12000.0,
                "frequency_mode": "自動",
            "response_speed": "速い", "bounce_strength": "大きい",
            "sensitivity_level": "標準", "motion_detail": "細かい", "contrast_profile": "メリハリ",
            "advanced_custom": False,
            "gain_db": 8.0,
            "auto_preview_segment": True, "scan_seconds": 120.0, "preview_start": 0.0, "motion_preview_duration": 10.0, "preview_duration": 30.0, "warmup": 5.0,
            "sample_rate": 24000, "fft_size": 512, "analysis_bands": 96,
            "min_db": -60.0, "max_db": -6.0,
            "attack": 1.00, "release": 0.85,
            "relative_range_db": 28.0, "peak_percentile": 90.0,
            "base_cut": 0.16, "pulse_amount": 0.90, "pulse_speed": 0.35,
            "gamma": 0.85,
            "crf": 18, "encoder": "libx264", "x264_preset": "veryfast",
        },
    },
    {
        "name": "03 Dynamic Smooth",
        "system": True,
        "description": "長尺動画向け。動きを少し落ち着かせた設定。",
        "values": {
            "width": 720, "height": 280, "fps": 30, "bars": 24, "display_mode": "片側バー", "scroll_mode": "なし", "scroll_step_frames": 2,
            "background_color": "#000000", "bar_color": "#FFFFFF", "bar_color2": "#FFFFFF", "color_mode": "縦グラデーション",
            "bar_width_percent": 62, "corner_radius": 18,
            "max_height_percent": 76, "side_margin_percent": 5, "bottom_margin_percent": 8,
            "freq_min": 80.0, "freq_max": 12000.0,
                "frequency_mode": "自動",
            "response_speed": "ゆったり", "bounce_strength": "控えめ",
            "sensitivity_level": "標準", "motion_detail": "なめらか", "contrast_profile": "フラット",
            "advanced_custom": False,
            "gain_db": 8.0,
            "auto_preview_segment": True, "scan_seconds": 120.0, "preview_start": 0.0, "motion_preview_duration": 10.0, "preview_duration": 30.0, "warmup": 5.0,
            "sample_rate": 24000, "fft_size": 2048, "analysis_bands": 48,
            "min_db": -60.0, "max_db": -6.0,
            "attack": 0.85, "release": 0.55,
            "relative_range_db": 34.0, "peak_percentile": 90.0,
            "base_cut": 0.10, "pulse_amount": 0.65, "pulse_speed": 0.18,
            "gamma": 0.88,
            "crf": 18, "encoder": "libx264", "x264_preset": "veryfast",
        },
    },
]


def _blank_user_file(path: Path) -> None:
    path.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")


class PresetManager:
    def __init__(self, user_file: Path) -> None:
        self.user_file = Path(user_file)
        self.user_presets: list[dict[str, Any]] = []
        self.load()

    def load(self) -> None:
        if not self.user_file.exists():
            self.user_file.parent.mkdir(parents=True, exist_ok=True)
            _blank_user_file(self.user_file)
            self.user_presets = []
            return
        try:
            data = json.loads(self.user_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self.user_presets = [p for p in data if isinstance(p, dict) and "name" in p and "values" in p]
            else:
                self.user_presets = []
        except Exception:
            backup = self.user_file.with_suffix(".broken.json")
            try:
                self.user_file.replace(backup)
            except Exception:
                pass
            _blank_user_file(self.user_file)
            self.user_presets = []

    def save(self) -> None:
        self.user_file.parent.mkdir(parents=True, exist_ok=True)
        self.user_file.write_text(json.dumps(self.user_presets, ensure_ascii=False, indent=2), encoding="utf-8")

    def all_presets(self) -> list[dict[str, Any]]:
        return deepcopy(SYSTEM_PRESETS) + deepcopy(self.user_presets)

    def names(self) -> list[str]:
        return [p["name"] for p in self.all_presets()]

    def get(self, name: str) -> dict[str, Any] | None:
        for p in self.all_presets():
            if p.get("name") == name:
                return deepcopy(p)
        return None

    def is_system(self, name: str) -> bool:
        p = self.get(name)
        return bool(p and p.get("system"))

    def upsert_user_preset(self, name: str, values: dict[str, Any]) -> None:
        name = name.strip()
        if not name:
            raise ValueError("プリセット名が空です。")
        if self.is_system(name):
            raise ValueError("システムプリセットと同じ名前では保存できません。")
        for p in self.user_presets:
            if p.get("name") == name:
                p["values"] = deepcopy(values)
                p["system"] = False
                self.save()
                return
        self.user_presets.append({"name": name, "system": False, "description": "", "values": deepcopy(values)})
        self.save()

    def delete_user_preset(self, name: str) -> bool:
        if self.is_system(name):
            raise ValueError("システムプリセットは削除できません。")
        before = len(self.user_presets)
        self.user_presets = [p for p in self.user_presets if p.get("name") != name]
        changed = len(self.user_presets) != before
        if changed:
            self.save()
        return changed

    def first_system_values(self) -> dict[str, Any]:
        return deepcopy(SYSTEM_PRESETS[0]["values"])
