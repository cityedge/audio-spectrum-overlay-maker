# -*- coding: utf-8 -*-
"""Audio Spectrum Overlay Maker v1.0.0 GUI."""
from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path
from typing import Any

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser, simpledialog
from tkinter.scrolledtext import ScrolledText

try:
    from PIL import Image, ImageTk
except Exception as exc:
    raise SystemExit("Pillow is required. Please run setup.bat first.") from exc

from preset_manager import CUSTOM_LABEL, PresetManager
from spectrum_engine import (
    VERSION,
    RenderStyle,
    MotionSettings,
    EncodeSettings,
    analyze_preview_segment,
    build_default_output_path,
    color_to_hex,
    draw_spectrum_frame,
    find_loud_segment_start,
    parse_color,
    render_audio_to_video,
    still_preview_values,
    suggest_frequency_range,
)
from ui_tooltips import ToolTip

APP_TITLE = f"Audio Spectrum Overlay Maker {VERSION}"
APP_DIR = Path(__file__).resolve().parent
USER_PRESETS_FILE = APP_DIR / "presets_user.json"

TOOLTIPS: dict[str, str] = {
    "input_file": "解析するWAV / MP3 / M4Aなどの音源ファイルです。出力動画には音声は入りません。",
    "audio_file": "解析するWAV / MP3 / M4Aなどの音源ファイルです。出力動画には音声は入りません。",
    "output_dir": "生成したスペアナ動画を保存するフォルダです。未指定の場合は音源ファイルと同じフォルダに保存します。",
    "preset": "全設定をまとめて呼び出すプリセットです。システムプリセットは削除できません。設定を変更するとカスタムになります。",
    "width": "生成するスペアナ素材の横幅です。",
    "height": "生成するスペアナ素材の高さです。",
    "fps": "動画のフレームレートです。標準は30fpsです。",
    "bars": "横に並ぶ表示バー数です。内部解析バー数とは分離されています。18/24/32のほか、高解像度用に48/64も選べます。",
    "background_color": "素材動画の背景色です。標準は黒です。比較（明）合成や黒をクロマキーで抜く用途に向きます。",
    "bar_color": "スペアナバーの色です。標準は白です。黒背景に白バーが最も安定した基本形です。",
    "bar_width_percent": "各バーの太さです。値を下げるとバーの中心位置はそのままで、バーだけが細くなり、バー間隔が広がります。",
    "corner_radius": "バーの角丸半径です。大きくするとカプセル形状に近づきます。",
    "max_height_percent": "バーが使う最大高さです。値を上げるとピーク時のバーが高くなります。",
    "side_margin_percent": "左右の余白です。値を上げると全体が中央寄りに狭くなります。",
    "bottom_margin_percent": "下端からバーの基準線までの余白です。値を上げるとバー全体が少し上に移動します。",
    "frequency_mode": "周波数範囲を自動推定するか、最低・最高周波数を手動指定するかを選びます。通常は自動がおすすめです。",
    "freq_min": "手動設定時に使う最低周波数です。自動設定時はこの値は直接使われません。",
    "freq_max": "手動設定時に使う最高周波数です。自動設定時はこの値は直接使われません。",
    "response_speed": "バーが音の変化に追従する速さです。選択肢から内部のFFT/Attack/Releaseを自動計算します。",
    "bounce_strength": "ピーク後にどの程度下まで落ちるかの印象です。内部のPulse/Releaseなどを自動計算します。",
    "sensitivity_level": "音源に対する全体的な反応感度です。低め/標準/高めから選びます。",
    "motion_detail": "動きの細かさです。内部解析バー数や集約の効き方に影響します。",
    "contrast_profile": "バー同士の高低差の出方です。メリハリを強くすると帯域差が見えやすくなります。",
    "advanced_custom": "詳細設定を直接変更するとオンになります。オンの間は詳細設定の数値が優先されます。",
    "gain_db": "詳細設定用です。全体的な見かけ上の感度をdBで直接指定します。",
    "auto_preview_segment": "オンにすると、動きプレビューに適した区間を自動検出します。",
    "scan_seconds": "自動検出時に音源の先頭から何秒までを調べるかです。静かなイントロを避けるため、標準は120秒です。",
    "preview_start": "自動検出を使わない場合に、何秒地点からプレビューするかを指定します。",
    "motion_preview_duration": "GUI内で再生する動きプレビューの長さです。標準は10秒です。再生後は停止します。",
    "preview_duration": "動画編集ソフトで試すために書き出す短いプレビューMP4の長さです。プレビューMP4は常に音源の先頭から生成します。標準は30秒です。",
    "warmup": "プレビュー開始位置より少し前から内部解析する秒数です。曲中プレビューの動きを全体生成時に近づけます。",
    "sample_rate": "解析用に内部変換するサンプルレートです。通常は変更不要です。",
    "analysis_bands": "内部で解析するバー数です。表示バー数とは別に固定することで、表示バー数を変えても動きの印象が変わりにくくなります。",
    "fft_size": "周波数解析の窓サイズです。小さいほど反応が速く、大きいほど滑らかになります。",
    "min_db": "内部ゲート用の下限dBです。通常は変更不要です。",
    "max_db": "内部ゲート用の上限dBです。通常は変更不要です。",
    "attack": "バーが上がる時の追従係数です。1.0に近いほど素早く上がります。",
    "release": "バーが下がる時の追従係数です。1.0に近いほど素早く下がります。",
    "relative_range_db": "各フレームのピークからどの範囲をバー高さに変換するかです。小さいほど高低差が強く出ます。",
    "peak_percentile": "相対正規化でピーク扱いするパーセンタイルです。通常は90前後で十分です。",
    "base_cut": "相対正規化後の低い値を切る割合です。上げると低いバーがよりゼロに戻りやすくなります。",
    "pulse_amount": "持続音をいったん落とし、新しいピークを強調する量です。Dynamicの上下動の中心です。",
    "pulse_speed": "持続音を基準値として吸収する速さです。上げるとピーク後の落ち込みが強くなります。",
    "gamma": "バー高さの見た目補正です。1より小さいと低めの値でもバーが高く見えます。",
    "crf": "MP4の画質設定です。小さいほど高画質・大容量です。720x280素材なら18前後で十分です。",
    "encoder": "FFmpegの映像エンコーダーです。通常はlibx264で安定します。対応環境ならh264_nvencも使えます。",
    "x264_preset": "libx264の速度・圧縮設定です。veryfastは生成が速く、品質もこの用途では十分です。",
}
TOOLTIPS_EN: dict[str, str] = {
    "input_file": "Audio file to analyze. The generated overlay video does not include audio.",
    "audio_file": "Audio file to analyze. The generated overlay video does not include audio.",
    "output_dir": "Folder where generated spectrum videos are saved. If empty, the audio file folder is used.",
    "preset": "Loads/saves the settings in the right pane. System presets cannot be deleted.",
    "width": "Width of the generated spectrum overlay.",
    "height": "Height of the generated spectrum overlay.",
    "fps": "Video frame rate.",
    "bars": "Number of visible bars. Internal analysis bands are separate.",
    "background_color": "Background color of the overlay video.",
    "bar_color": "Spectrum bar color.",
    "bar_width_percent": "Bar width. Lower values make each bar thinner and gaps wider.",
    "corner_radius": "Rounded corner radius. Higher values make capsule-like bars.",
    "max_height_percent": "Maximum bar height.",
    "side_margin_percent": "Left/right margin.",
    "bottom_margin_percent": "Bottom margin.",
    "frequency_mode": "Choose automatic frequency analysis or manual min/max frequency.",
    "freq_min": "Manual minimum frequency. Not directly used in Auto mode.",
    "freq_max": "Manual maximum frequency. Not directly used in Auto mode.",
    "response_speed": "How quickly bars follow changes in the audio.",
    "bounce_strength": "How strongly bars drop after peaks.",
    "sensitivity_level": "Overall visual sensitivity.",
    "motion_detail": "Fine detail in motion. Affects internal analysis bands.",
    "contrast_profile": "How strongly the bar heights differ from each other.",
    "advanced_custom": "Enabled when detailed parameters are edited directly.",
    "gain_db": "Detailed setting: visual gain in dB.",
    "auto_preview_segment": "Automatically finds a suitable section for motion preview.",
    "scan_seconds": "How many seconds from the start are scanned for auto preview detection.",
    "preview_start": "Manual start time for motion preview when auto detection is off.",
    "motion_preview_duration": "Duration of the in-app motion preview.",
    "preview_duration": "Duration of the preview MP4. Preview MP4 is generated from the start of the audio.",
    "warmup": "Analyzes slightly before the preview start to make preview motion closer to full render.",
    "sample_rate": "Internal analysis sample rate.",
    "analysis_bands": "Number of internal analysis bands, separate from visible bar count.",
    "fft_size": "FFT window size.",
    "min_db": "Detailed lower dB gate.",
    "max_db": "Detailed upper dB gate.",
    "attack": "Rise-follow coefficient.",
    "release": "Fall-follow coefficient.",
    "relative_range_db": "Relative dB range from the frame peak.",
    "peak_percentile": "Percentile used as the frame peak for relative normalization.",
    "base_cut": "Cuts low values after relative normalization.",
    "pulse_amount": "Emphasizes new peaks against sustained sound.",
    "pulse_speed": "How quickly sustained sound is absorbed as baseline.",
    "gamma": "Visual height correction.",
    "crf": "MP4 quality setting. Lower means higher quality and larger file.",
    "encoder": "FFmpeg video encoder.",
    "x264_preset": "libx264 speed/compression preset.",
    "still_canvas": "Static preview of the generated overlay material.",
    "motion_canvas": "Actual-audio motion preview. It plays once and then stops.",
}

UI_TEXT = {
    "日本語": {
        "language_label": "言語",
        "choose": "選択...",
        "save_preset": "プリセット保存",
        "delete_preset": "プリセット削除",
        "still_preview": "見た目プレビュー",
        "motion_preview": "動きプレビュー",
        "stop": "停止",
        "not_played": "未再生",
        "motion_message": "音源を選択して「動きプレビュー」を押してください",
        "preview_video": "30秒プレビュー動画生成",
        "full_render": "全体生成",
        "open_output": "出力先を開く",
        "visual_tab": "見た目",
        "motion_tab": "生成・動き",
        "advanced_tab": "詳細設定",
        "audio_file": "音源",
        "output_dir": "出力先",
        "preset": "プリセット",
        "bars": "バー本数",
        "background_color": "背景色",
        "bar_color": "バー色",
        "bar_width_percent": "バー幅%",
        "corner_radius": "角丸半径px",
        "max_height_percent": "最大高さ%",
        "side_margin_percent": "左右余白%",
        "bottom_margin_percent": "下余白%",
        "width": "横幅",
        "height": "高さ",
        "fps": "fps",
        "auto_preview_segment": "動きプレビューに適した区間を自動検出",
        "preview_start": "手動開始秒",
        "motion_preview_duration": "動きプレビュー秒数",
        "preview_duration": "動画プレビュー秒数",
        "warmup": "ウォームアップ秒",
        "color_button": "色...",
        "advanced_recalc": "定性的設定から再計算",
        "frequency_mode": "周波数設定",
        "freq_min": "最低周波数Hz",
        "freq_max": "最高周波数Hz",
        "sample_rate": "sample rate",
        "fft_size": "FFT",
        "analysis_bands": "内部解析バー数",
        "advanced_custom": "詳細カスタム",
        "min_db": "min dB",
        "max_db": "max dB",
        "attack": "Attack",
        "release": "Release",
        "relative_range_db": "Relative range dB",
        "peak_percentile": "Peak %",
        "base_cut": "Base cut",
        "pulse_amount": "Pulse amount",
        "pulse_speed": "Pulse speed",
        "gamma": "Gamma",
        "crf": "CRF",
        "encoder": "Encoder",
        "x264_preset": "x264 preset",
        "response_speed": "反応の速さ",
        "bounce_strength": "上下動の強さ",
        "sensitivity_level": "感度",
        "motion_detail": "動きの細かさ",
        "contrast_profile": "高低差の出方",
    },
    "English": {
        "language_label": "Language",
        "choose": "Browse...",
        "save_preset": "Save Preset",
        "delete_preset": "Delete Preset",
        "still_preview": "Visual Preview",
        "motion_preview": "Motion Preview",
        "stop": "Stop",
        "not_played": "Not played",
        "motion_message": "Select an audio file and click Motion Preview.",
        "preview_video": "Generate 30s Preview Video",
        "full_render": "Generate Full Video",
        "open_output": "Open Output Folder",
        "visual_tab": "Visual",
        "motion_tab": "Motion",
        "advanced_tab": "Advanced",
        "audio_file": "Audio",
        "output_dir": "Output",
        "preset": "Preset",
        "bars": "Bars",
        "background_color": "Background",
        "bar_color": "Bar Color",
        "bar_width_percent": "Bar Width %",
        "corner_radius": "Corner Radius px",
        "max_height_percent": "Max Height %",
        "side_margin_percent": "Side Margin %",
        "bottom_margin_percent": "Bottom Margin %",
        "width": "Width",
        "height": "Height",
        "fps": "fps",
        "auto_preview_segment": "Auto-detect a good section for motion preview",
        "preview_start": "Manual Start sec",
        "motion_preview_duration": "Motion Preview sec",
        "preview_duration": "Video Preview sec",
        "warmup": "Warmup sec",
        "color_button": "Color...",
        "advanced_recalc": "Recalculate from qualitative controls",
        "frequency_mode": "Frequency Mode",
        "freq_min": "Min Frequency Hz",
        "freq_max": "Max Frequency Hz",
        "sample_rate": "sample rate",
        "fft_size": "FFT",
        "analysis_bands": "Internal Bands",
        "advanced_custom": "Advanced Custom",
        "min_db": "min dB",
        "max_db": "max dB",
        "attack": "Attack",
        "release": "Release",
        "relative_range_db": "Relative range dB",
        "peak_percentile": "Peak %",
        "base_cut": "Base cut",
        "pulse_amount": "Pulse amount",
        "pulse_speed": "Pulse speed",
        "gamma": "Gamma",
        "crf": "CRF",
        "encoder": "Encoder",
        "x264_preset": "x264 preset",
        "response_speed": "Response Speed",
        "bounce_strength": "Bounce Strength",
        "sensitivity_level": "Sensitivity",
        "motion_detail": "Motion Detail",
        "contrast_profile": "Height Contrast",
    }
}

CHOICE_OPTIONS = {
    "response_speed": {
        "日本語": ["ゆったり", "標準", "速い", "カスタム"],
        "English": ["Slow", "Standard", "Fast", "Custom"],
    },
    "bounce_strength": {
        "日本語": ["控えめ", "標準", "大きい", "カスタム"],
        "English": ["Subtle", "Standard", "Large", "Custom"],
    },
    "sensitivity_level": {
        "日本語": ["低め", "標準", "高め", "カスタム"],
        "English": ["Low", "Standard", "High", "Custom"],
    },
    "motion_detail": {
        "日本語": ["なめらか", "標準", "細かい", "カスタム"],
        "English": ["Smooth", "Standard", "Detailed", "Custom"],
    },
    "contrast_profile": {
        "日本語": ["フラット", "標準", "メリハリ", "カスタム"],
        "English": ["Flat", "Standard", "High Contrast", "Custom"],
    },
    "frequency_mode": {
        "日本語": ["自動", "手動"],
        "English": ["Auto", "Manual"],
    },
}

CHOICE_TO_JA = {}
for _key, _langs in CHOICE_OPTIONS.items():
    CHOICE_TO_JA[_key] = {}
    for _lang, _values in _langs.items():
        for _i, _v in enumerate(_values):
            CHOICE_TO_JA[_key][_v] = _langs["日本語"][_i]



QUALITATIVE_KEYS = {
    "response_speed",
    "bounce_strength",
    "sensitivity_level",
    "motion_detail",
    "contrast_profile",
}

ADVANCED_SETTING_KEYS = {
    # Frequency / analysis
    "frequency_mode", "freq_min", "freq_max",
    "sample_rate", "fft_size", "analysis_bands",
    # Dynamic motion internals
    "min_db", "max_db", "gain_db",
    "attack", "release",
    "relative_range_db", "peak_percentile",
    "base_cut", "pulse_amount", "pulse_speed",
    # Visual correction / encoder settings exposed in the advanced tab
    "gamma", "crf", "encoder", "x264_preset",
}

OPERATIONAL_KEYS = {
    "input_file", "output_dir", "preset", "language",
    "auto_preview_segment", "scan_seconds",
    "preview_start", "motion_preview_duration",
    "preview_duration", "warmup",
}


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1200x760")
        self.minsize(1020, 620)
        self.preset_manager = PresetManager(USER_PRESETS_FILE)
        self.control_widgets: dict[str, tk.Widget] = {}
        self.text_widgets: dict[str, list[tk.Widget]] = {}
        self.tooltip_widgets: dict[str, list[ToolTip]] = {}
        self.notebook_tabs: list[tuple[tk.Widget, str]] = []
        self.apply_in_progress = False
        self.motion_frames: list[np.ndarray] = []
        self.motion_photos: list[ImageTk.PhotoImage] = []
        self.motion_index = 0
        self.current_motion_photo: ImageTk.PhotoImage | None = None
        self.still_frame_array = None
        self.motion_after_id: str | None = None
        self.still_photo: ImageTk.PhotoImage | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker_thread: threading.Thread | None = None
        self.motion_thread: threading.Thread | None = None

        self._init_style()
        self._init_vars()
        self._build_ui()
        self._wire_traces()
        self.apply_preset("01 Dynamic Standard")
        self.after(100, self._process_log_queue)

    def _init_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TFrame", background="#f4f5f7")
        style.configure("Card.TFrame", background="#ffffff", relief="flat")
        style.configure("TLabel", background="#f4f5f7", foreground="#202124")
        style.configure("Card.TLabel", background="#ffffff", foreground="#202124")
        style.configure("Title.TLabel", background="#f4f5f7", foreground="#111827", font=("Yu Gothic UI", 16, "bold"))
        style.configure("Sub.TLabel", background="#f4f5f7", foreground="#6b7280")
        style.configure("Accent.TButton", padding=(14, 6))
        style.configure("Danger.TButton", foreground="#b91c1c")

    def _init_vars(self) -> None:
        self.vars: dict[str, tk.Variable] = {
            "input_file": tk.StringVar(),
            "output_dir": tk.StringVar(),
            "preset": tk.StringVar(),
            "language": tk.StringVar(value="日本語"),
            "width": tk.IntVar(value=720),
            "height": tk.IntVar(value=280),
            "fps": tk.IntVar(value=30),
            "bars": tk.IntVar(value=24),
            "background_color": tk.StringVar(value="#000000"),
            "bar_color": tk.StringVar(value="#FFFFFF"),
            "bar_width_percent": tk.IntVar(value=62),
            "corner_radius": tk.IntVar(value=18),
            "max_height_percent": tk.IntVar(value=78),
            "side_margin_percent": tk.IntVar(value=5),
            "bottom_margin_percent": tk.IntVar(value=8),
            "frequency_mode": tk.StringVar(value="自動"),
            "freq_min": tk.DoubleVar(value=80.0),
            "freq_max": tk.DoubleVar(value=12000.0),
            "response_speed": tk.StringVar(value="標準"),
            "bounce_strength": tk.StringVar(value="標準"),
            "sensitivity_level": tk.StringVar(value="標準"),
            "motion_detail": tk.StringVar(value="標準"),
            "contrast_profile": tk.StringVar(value="標準"),
            "advanced_custom": tk.BooleanVar(value=False),
            "gain_db": tk.DoubleVar(value=8.0),
            "auto_preview_segment": tk.BooleanVar(value=True),
            "scan_seconds": tk.DoubleVar(value=120.0),
            "preview_start": tk.DoubleVar(value=0.0),
            "motion_preview_duration": tk.DoubleVar(value=10.0),
            "preview_duration": tk.DoubleVar(value=30.0),
            "warmup": tk.DoubleVar(value=5.0),
            "sample_rate": tk.IntVar(value=24000),
            "fft_size": tk.IntVar(value=1024),
            "analysis_bands": tk.IntVar(value=64),
            "min_db": tk.DoubleVar(value=-60.0),
            "max_db": tk.DoubleVar(value=-6.0),
            "attack": tk.DoubleVar(value=0.95),
            "release": tk.DoubleVar(value=0.75),
            "relative_range_db": tk.DoubleVar(value=30.0),
            "peak_percentile": tk.DoubleVar(value=90.0),
            "base_cut": tk.DoubleVar(value=0.12),
            "pulse_amount": tk.DoubleVar(value=0.80),
            "pulse_speed": tk.DoubleVar(value=0.25),
            "gamma": tk.DoubleVar(value=0.85),
            "crf": tk.IntVar(value=18),
            "encoder": tk.StringVar(value="libx264"),
            "x264_preset": tk.StringVar(value="veryfast"),
        }

    def current_language(self) -> str:
        value = self.vars.get("language").get() if "language" in self.vars else "日本語"
        return "English" if value == "English" else "日本語"

    def ui(self, key: str) -> str:
        lang = self.current_language()
        return UI_TEXT.get(lang, UI_TEXT["日本語"]).get(key, UI_TEXT["日本語"].get(key, key))

    def tooltip_text(self, key: str) -> str:
        if self.current_language() == "English":
            return TOOLTIPS_EN.get(key, TOOLTIPS.get(key, ""))
        return TOOLTIPS.get(key, "")

    def register_text(self, widget: tk.Widget, key: str) -> None:
        self.text_widgets.setdefault(key, []).append(widget)

    def choice_values(self, key: str) -> list[Any]:
        if key in CHOICE_OPTIONS:
            return CHOICE_OPTIONS[key][self.current_language()]
        return []

    def choice_to_ja(self, key: str, value: Any) -> Any:
        if key in CHOICE_TO_JA:
            return CHOICE_TO_JA[key].get(str(value), value)
        return value

    def choice_from_ja(self, key: str, value: Any, lang: str | None = None) -> Any:
        if key not in CHOICE_OPTIONS:
            return value
        lang = lang or self.current_language()
        ja_values = CHOICE_OPTIONS[key]["日本語"]
        if value in ja_values:
            idx = ja_values.index(value)
        else:
            idx = ja_values.index(CHOICE_TO_JA[key].get(str(value), "標準" if "標準" in ja_values else ja_values[0]))
        return CHOICE_OPTIONS[key][lang][idx]

    def localize_choice_vars(self) -> None:
        was = self.apply_in_progress
        self.apply_in_progress = True
        try:
            lang = self.current_language()
            for key in CHOICE_OPTIONS:
                if key in self.vars:
                    current_ja = self.choice_to_ja(key, self.vars[key].get())
                    self.vars[key].set(self.choice_from_ja(key, current_ja, lang))
                    widget = self.control_widgets.get(key)
                    if widget is not None:
                        widget.configure(values=self.choice_values(key))
        finally:
            self.apply_in_progress = was

    def add_tooltip(self, widget: tk.Widget, key: str) -> ToolTip:
        tip = ToolTip(widget, self.tooltip_text(key))
        self.tooltip_widgets.setdefault(key, []).append(tip)
        return tip

    def apply_language(self) -> None:
        self.localize_choice_vars()
        for key, widgets in getattr(self, "text_widgets", {}).items():
            for widget in widgets:
                try:
                    widget.configure(text=self.ui(key))
                except Exception:
                    pass
        for key, tips in getattr(self, "tooltip_widgets", {}).items():
            for tip in tips:
                try:
                    tip.set_text(self.tooltip_text(key))
                except Exception:
                    pass
        for child, key in getattr(self, "notebook_tabs", []):
            try:
                self.notebook.tab(child, text=self.ui(key))
            except Exception:
                pass
        if not self.motion_frames:
            self._draw_canvas_message(self.motion_canvas, self.ui("motion_message"))
        self.update_advanced_state_label()

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=12)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(2, weight=1)

        header = ttk.Frame(root)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Audio Spectrum Overlay Maker", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Dynamic bar overlay generator", style="Sub.TLabel").grid(row=1, column=0, sticky="w")

        lang_box = ttk.Frame(header)
        lang_box.grid(row=0, column=1, rowspan=2, sticky="ne")
        lang_label = ttk.Label(lang_box, text=self.ui("language_label"))
        lang_label.pack(side="left", padx=(0, 6))
        self.register_text(lang_label, "language_label")
        self.language_combo = ttk.Combobox(lang_box, textvariable=self.vars["language"], values=["日本語", "English"], state="readonly", width=10)
        self.language_combo.pack(side="left")
        self.language_combo.bind("<<ComboboxSelected>>", lambda _e: self.apply_language())

        top = ttk.Frame(root, padding=10, style="Card.TFrame")
        top.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        # Match the main preview/settings pane ratio so the file fields end near
        # the right edge of the preview pane, and preset controls start near the
        # left edge of the settings pane.
        top.columnconfigure(0, weight=3)
        top.columnconfigure(1, weight=2)

        file_box = ttk.Frame(top, style="Card.TFrame")
        file_box.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        file_box.columnconfigure(1, weight=1)
        self._label(file_box, "音源", "audio_file").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=(0, 6))
        ttk.Entry(file_box, textvariable=self.vars["input_file"]).grid(row=0, column=1, sticky="ew", padx=(0, 6), pady=(0, 6))
        choose_input_btn = ttk.Button(file_box, text=self.ui("choose"), command=self.choose_input)
        choose_input_btn.grid(row=0, column=2, sticky="w", pady=(0, 6))
        self.register_text(choose_input_btn, "choose")
        self._label(file_box, "出力先", "output_dir").grid(row=1, column=0, sticky="w", padx=(0, 6))
        ttk.Entry(file_box, textvariable=self.vars["output_dir"]).grid(row=1, column=1, sticky="ew", padx=(0, 6))
        choose_output_btn = ttk.Button(file_box, text=self.ui("choose"), command=self.choose_output_dir)
        choose_output_btn.grid(row=1, column=2, sticky="w")
        self.register_text(choose_output_btn, "choose")

        preset_box = ttk.Frame(top, style="Card.TFrame")
        preset_box.grid(row=0, column=1, sticky="nw", padx=(10, 0))
        self._label(preset_box, "プリセット", "preset").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.preset_combo = ttk.Combobox(preset_box, textvariable=self.vars["preset"], values=self.preset_manager.names(), state="readonly", width=28)
        self.preset_combo.grid(row=0, column=1, sticky="w", padx=(0, 6))
        self.preset_combo.bind("<<ComboboxSelected>>", self.on_preset_selected)
        save_btn = ttk.Button(preset_box, text=self.ui("save_preset"), command=self.save_preset)
        save_btn.grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.register_text(save_btn, "save_preset")
        delete_btn = ttk.Button(preset_box, text=self.ui("delete_preset"), command=self.delete_preset, style="Danger.TButton")
        delete_btn.grid(row=0, column=3, sticky="w")
        self.register_text(delete_btn, "delete_preset")

        main = ttk.PanedWindow(root, orient="horizontal")
        main.grid(row=2, column=0, sticky="nsew")
        preview_frame = ttk.Frame(main, padding=10, style="Card.TFrame")
        settings_frame = ttk.Frame(main, padding=(10, 0, 0, 0))
        main.add(preview_frame, weight=3)
        main.add(settings_frame, weight=2)

        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1, minsize=150)
        preview_frame.rowconfigure(3, weight=1, minsize=150)
        still_title = ttk.Label(preview_frame, text=self.ui("still_preview"), style="Card.TLabel", font=("Yu Gothic UI", 10, "bold"))
        still_title.grid(row=0, column=0, sticky="w")
        self.register_text(still_title, "still_preview")
        self.still_canvas = tk.Canvas(preview_frame, background="#F2F2F2", highlightthickness=0)
        self.still_canvas.grid(row=1, column=0, sticky="nsew", pady=(4, 12))
        self.still_canvas.bind("<Configure>", lambda _e: self.redraw_still_canvas())
        self.add_tooltip(self.still_canvas, "still_canvas")

        motion_head = ttk.Frame(preview_frame, style="Card.TFrame")
        motion_head.grid(row=2, column=0, sticky="ew")
        motion_head.columnconfigure(0, weight=0)
        motion_head.columnconfigure(1, weight=1)
        motion_head.columnconfigure(2, weight=0)
        motion_head.columnconfigure(3, weight=0)
        motion_title = ttk.Label(motion_head, text=self.ui("motion_preview"), style="Card.TLabel", font=("Yu Gothic UI", 10, "bold"))
        motion_title.grid(row=0, column=0, sticky="w")
        self.register_text(motion_title, "motion_preview")
        self.motion_status = ttk.Label(motion_head, text=self.ui("not_played"), style="Card.TLabel", foreground="#6b7280", anchor="center")
        self.motion_status.grid(row=0, column=1, sticky="ew", padx=(12, 12))
        self.motion_button = ttk.Button(motion_head, text=self.ui("motion_preview"), command=self.start_motion_preview)
        self.motion_button.grid(row=0, column=2, sticky="e")
        self.register_text(self.motion_button, "motion_preview")
        self.stop_motion_button = ttk.Button(motion_head, text=self.ui("stop"), command=self.stop_motion_preview)
        self.stop_motion_button.grid(row=0, column=3, sticky="e", padx=(6, 0))
        self.register_text(self.stop_motion_button, "stop")
        self.motion_canvas = tk.Canvas(preview_frame, background="#F2F2F2", highlightthickness=0)
        self.motion_canvas.grid(row=3, column=0, sticky="nsew", pady=(4, 0))
        self.motion_canvas.bind("<Configure>", lambda _e: self.redraw_motion_canvas())
        self._draw_canvas_message(self.motion_canvas, self.ui("motion_message"))
        self.add_tooltip(self.motion_canvas, "motion_canvas")

        self.notebook = ttk.Notebook(settings_frame)
        self.notebook.pack(fill="both", expand=True)
        self._build_visual_tab()
        self._build_motion_tab()
        self._build_advanced_tab()

        bottom = ttk.Frame(root, padding=(0, 10, 0, 0))
        bottom.grid(row=3, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        actions = ttk.Frame(bottom)
        actions.grid(row=0, column=0, sticky="ew")
        self.preview_button = ttk.Button(actions, text=self.ui("preview_video"), command=lambda: self.start_render(preview=True), style="Accent.TButton")
        self.preview_button.pack(side="left")
        self.register_text(self.preview_button, "preview_video")
        self.full_button = ttk.Button(actions, text=self.ui("full_render"), command=lambda: self.start_render(preview=False), style="Accent.TButton")
        self.full_button.pack(side="left", padx=(6, 0))
        self.register_text(self.full_button, "full_render")
        open_btn = ttk.Button(actions, text=self.ui("open_output"), command=self.open_output_folder)
        open_btn.pack(side="right")
        self.register_text(open_btn, "open_output")
        self.log_text = ScrolledText(bottom, height=4, wrap="word", font=("Consolas", 9))
        self.log_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.log_text.configure(state="disabled")

    def _build_visual_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=self.ui("visual_tab"))
        self.notebook_tabs.append((tab, "visual_tab"))
        tab.columnconfigure(1, weight=1)
        row = 0
        self._combo(tab, row, "バー本数", "bars", [18, 24, 32, 48, 64]); row += 1
        self._color_row(tab, row, "背景色", "background_color"); row += 1
        self._color_row(tab, row, "バー色", "bar_color"); row += 1
        self._scale(tab, row, "バー幅%", "bar_width_percent", 10, 100); row += 1
        self._spin(tab, row, "角丸半径px", "corner_radius", 0, 160, 1); row += 1
        self._scale(tab, row, "最大高さ%", "max_height_percent", 10, 95); row += 1
        self._scale(tab, row, "左右余白%", "side_margin_percent", 0, 30); row += 1
        self._scale(tab, row, "下余白%", "bottom_margin_percent", 0, 30); row += 1
        ttk.Separator(tab).grid(row=row, column=0, columnspan=3, sticky="ew", pady=12); row += 1
        self._spin(tab, row, "横幅", "width", 320, 1920, 10); row += 1
        self._spin(tab, row, "高さ", "height", 120, 1080, 10); row += 1
        self._combo(tab, row, "fps", "fps", [24, 30, 60]); row += 1

    def _build_motion_tab(self) -> None:
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text=self.ui("motion_tab"))
        self.notebook_tabs.append((tab, "motion_tab"))
        tab.columnconfigure(1, weight=1)
        row = 0
        self._combo(tab, row, "反応の速さ", "response_speed", ["ゆったり", "標準", "速い", "カスタム"]); row += 1
        self._combo(tab, row, "上下動の強さ", "bounce_strength", ["控えめ", "標準", "大きい", "カスタム"]); row += 1
        self._combo(tab, row, "感度", "sensitivity_level", ["低め", "標準", "高め", "カスタム"]); row += 1
        self._combo(tab, row, "動きの細かさ", "motion_detail", ["なめらか", "標準", "細かい", "カスタム"]); row += 1
        self._combo(tab, row, "高低差の出方", "contrast_profile", ["フラット", "標準", "メリハリ", "カスタム"]); row += 1
        self.advanced_state_label = ttk.Label(tab, text=("Using qualitative controls" if self.current_language()=="English" else "定性的設定を使用中"), foreground="#4b5563")
        self.advanced_state_label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 4)); row += 1
        ttk.Separator(tab).grid(row=row, column=0, columnspan=3, sticky="ew", pady=12); row += 1
        self._check(tab, row, "動きプレビューに適した区間を自動検出", "auto_preview_segment"); row += 1
        self._spin_float(tab, row, "スキャン秒数", "scan_seconds", 10, 300, 10); row += 1
        self._spin_float(tab, row, "手動開始秒", "preview_start", 0, 99999, 1); row += 1
        self._spin_float(tab, row, "動きプレビュー秒数", "motion_preview_duration", 3, 30, 1); row += 1
        self._spin_float(tab, row, "動画プレビュー秒数", "preview_duration", 5, 120, 5); row += 1
        self._spin_float(tab, row, "ウォームアップ秒", "warmup", 0, 30, 1); row += 1

    def _build_advanced_tab(self) -> None:
        tab = self._make_scrollable_tab("詳細設定")
        row = 0
        self._combo(tab, row, "周波数設定", "frequency_mode", ["自動", "手動"]); row += 1
        self._spin_float(tab, row, "最低周波数Hz", "freq_min", 20, 1000, 5); row += 1
        self._spin_float(tab, row, "最高周波数Hz", "freq_max", 1000, 20000, 100); row += 1
        ttk.Separator(tab).grid(row=row, column=0, columnspan=3, sticky="ew", pady=12); row += 1
        recalc_btn = ttk.Button(tab, text=self.ui("advanced_recalc"), command=self.reset_advanced_from_qualitative)
        recalc_btn.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.register_text(recalc_btn, "advanced_recalc")
        row += 1
        self._check(tab, row, "詳細カスタム", "advanced_custom"); row += 1
        self._spin(tab, row, "sample rate", "sample_rate", 8000, 48000, 1000); row += 1
        self._combo(tab, row, "FFT", "fft_size", [512, 1024, 2048, 4096]); row += 1
        self._combo(tab, row, "内部解析バー数", "analysis_bands", [48, 64, 96, 128]); row += 1
        self._spin_float(tab, row, "min dB", "min_db", -120, 0, 1); row += 1
        self._spin_float(tab, row, "max dB", "max_db", -60, 12, 1); row += 1
        self._spin_float(tab, row, "Attack", "attack", 0.01, 1.0, 0.01); row += 1
        self._spin_float(tab, row, "Release", "release", 0.01, 1.0, 0.01); row += 1
        self._spin_float(tab, row, "Relative range dB", "relative_range_db", 6, 60, 1); row += 1
        self._spin_float(tab, row, "Peak %", "peak_percentile", 50, 99.5, 0.5); row += 1
        self._spin_float(tab, row, "Base cut", "base_cut", 0, 0.8, 0.01); row += 1
        self._spin_float(tab, row, "Pulse amount", "pulse_amount", 0, 1.0, 0.01); row += 1
        self._spin_float(tab, row, "Pulse speed", "pulse_speed", 0.01, 0.95, 0.01); row += 1
        self._spin_float(tab, row, "Gamma", "gamma", 0.30, 2.00, 0.01); row += 1
        ttk.Separator(tab).grid(row=row, column=0, columnspan=3, sticky="ew", pady=12); row += 1
        self._spin(tab, row, "CRF", "crf", 10, 35, 1); row += 1
        self._combo(tab, row, "Encoder", "encoder", ["libx264", "h264_nvenc"]); row += 1
        self._combo(tab, row, "x264 preset", "x264_preset", ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium"]); row += 1

    def _label(self, parent: tk.Widget, text: str, key: str) -> ttk.Label:
        label = ttk.Label(parent, text=self.ui(key) if key in UI_TEXT["日本語"] else text)
        if key in UI_TEXT["日本語"]:
            self.register_text(label, key)
        self.add_tooltip(label, key)
        return label

    def _row_label(self, parent: tk.Widget, row: int, text: str, key: str) -> None:
        self._label(parent, text, key).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=5)

    def _spin(self, parent: tk.Widget, row: int, text: str, key: str, frm: int, to: int, inc: int) -> None:
        self._row_label(parent, row, text, key)
        widget = ttk.Spinbox(parent, textvariable=self.vars[key], from_=frm, to=to, increment=inc, width=12)
        widget.grid(row=row, column=1, sticky="w", pady=5)
        self.add_tooltip(widget, key)

    def _spin_float(self, parent: tk.Widget, row: int, text: str, key: str, frm: float, to: float, inc: float) -> None:
        self._row_label(parent, row, text, key)
        widget = ttk.Spinbox(parent, textvariable=self.vars[key], from_=frm, to=to, increment=inc, width=12)
        widget.grid(row=row, column=1, sticky="w", pady=5)
        self.add_tooltip(widget, key)

    def _combo(self, parent: tk.Widget, row: int, text: str, key: str, values: list[Any]) -> None:
        self._row_label(parent, row, text, key)
        widget_values = self.choice_values(key) if key in CHOICE_OPTIONS else values
        widget = ttk.Combobox(parent, textvariable=self.vars[key], values=widget_values, state="readonly", width=14)
        widget.grid(row=row, column=1, sticky="w", pady=5)
        self.control_widgets[key] = widget
        self.add_tooltip(widget, key)

    def _check(self, parent: tk.Widget, row: int, text: str, key: str) -> None:
        self._row_label(parent, row, text, key)
        widget = ttk.Checkbutton(parent, variable=self.vars[key])
        widget.grid(row=row, column=1, sticky="w", pady=5)
        self.add_tooltip(widget, key)

    def _scale(self, parent: tk.Widget, row: int, text: str, key: str, frm: int, to: int) -> None:
        self._row_label(parent, row, text, key)
        box = ttk.Frame(parent)
        box.grid(row=row, column=1, sticky="ew", pady=5)
        box.columnconfigure(0, weight=1)
        scale = ttk.Scale(box, from_=frm, to=to, variable=self.vars[key], orient="horizontal")
        scale.grid(row=0, column=0, sticky="ew")
        spin = ttk.Spinbox(box, textvariable=self.vars[key], from_=frm, to=to, increment=1, width=6)
        spin.grid(row=0, column=1, sticky="e", padx=(8, 0))
        self.add_tooltip(scale, key)
        self.add_tooltip(spin, key)

    def _color_row(self, parent: tk.Widget, row: int, text: str, key: str) -> None:
        self._row_label(parent, row, text, key)
        box = ttk.Frame(parent)
        box.grid(row=row, column=1, sticky="w", pady=5)
        entry = ttk.Entry(box, textvariable=self.vars[key], width=10)
        entry.pack(side="left")
        btn = ttk.Button(box, text=self.ui("color_button"), command=lambda k=key: self.choose_color(k))
        btn.pack(side="left", padx=(6, 0))
        self.register_text(btn, "color_button")
        self.add_tooltip(entry, key)
        self.add_tooltip(btn, key)

    def _make_scrollable_tab(self, title: str) -> ttk.Frame:
        outer = ttk.Frame(self.notebook)
        self.notebook.add(outer, text=self.ui("advanced_tab") if title == "詳細設定" else title)
        if title == "詳細設定":
            self.notebook_tabs.append((outer, "advanced_tab"))
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, highlightthickness=0, background="#f4f5f7")
        scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        inner = ttk.Frame(canvas, padding=12)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_frame_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event):
            canvas.itemconfigure(inner_id, width=event.width)

        def _on_mousewheel(event):
            delta = -1 * int(event.delta / 120) if event.delta else 0
            if delta:
                canvas.yview_scroll(delta, "units")

        inner.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind("<Enter>", lambda _e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        canvas.bind("<Leave>", lambda _e: canvas.unbind_all("<MouseWheel>"))
        inner.columnconfigure(1, weight=1)
        return inner

    def _wire_traces(self) -> None:
        for key, var in self.vars.items():
            if key in {"input_file", "output_dir", "preset"}:
                continue
            var.trace_add("write", lambda *_args, k=key: self.on_setting_changed(k))

    def on_setting_changed(self, key: str) -> None:
        if self.apply_in_progress:
            return

        if key not in OPERATIONAL_KEYS and self.vars["preset"].get() != CUSTOM_LABEL:
            self.vars["preset"].set(CUSTOM_LABEL)

        if key == "advanced_custom":
            if bool(self.vars["advanced_custom"].get()):
                self._set_advanced_custom_state(True)
            self.update_advanced_state_label()
            return

        if key in ADVANCED_SETTING_KEYS:
            # Direct edits in the detailed tab put the app in advanced-custom mode.
            # This includes gamma, frequency, analysis, motion internals, and encoder settings.
            self._set_advanced_custom_state(True)

        if key in QUALITATIVE_KEYS:
            # Qualitative controls own the detailed values unless the user chooses Custom.
            if str(self.choice_to_ja(key, self.vars[key].get())) != "カスタム":
                self.recompute_advanced_from_qualitative()

        if key in {"width", "height", "bars", "background_color", "bar_color", "bar_width_percent", "corner_radius", "max_height_percent", "side_margin_percent", "bottom_margin_percent", "gamma"}:
            if key == "bars" and not bool(self.vars["advanced_custom"].get()):
                self.recompute_advanced_from_qualitative()
            self.after_idle(self.update_still_preview)

        if key not in {"input_file", "output_dir", "preset"}:
            self.motion_status.configure(text=("Needs update" if self.current_language()=="English" else "要更新"))
        self.update_advanced_state_label()

    def _set_advanced_custom_state(self, enabled: bool) -> None:
        was = self.apply_in_progress
        self.apply_in_progress = True
        try:
            self.vars["advanced_custom"].set(bool(enabled))
            if enabled:
                for k in QUALITATIVE_KEYS:
                    if k in self.vars:
                        self.vars[k].set(self.choice_from_ja(k, "カスタム"))
        finally:
            self.apply_in_progress = was
        self.update_advanced_state_label()

    def reset_advanced_from_qualitative(self) -> None:
        # If all qualitative controls currently show Custom, return to the standard profile.
        was = self.apply_in_progress
        self.apply_in_progress = True
        try:
            defaults = {
                "response_speed": "標準",
                "bounce_strength": "標準",
                "sensitivity_level": "標準",
                "motion_detail": "標準",
                "contrast_profile": "標準",
            }
            for k, v in defaults.items():
                if str(self.choice_to_ja(k, self.vars[k].get())) == "カスタム":
                    self.vars[k].set(self.choice_from_ja(k, v))
            self.vars["advanced_custom"].set(False)
        finally:
            self.apply_in_progress = was
        self.recompute_advanced_from_qualitative()
        self.motion_status.configure(text=("Needs update" if self.current_language()=="English" else "要更新"))
        self.update_advanced_state_label()

    def update_advanced_state_label(self) -> None:
        is_advanced = bool(self.vars["advanced_custom"].get())
        for key in QUALITATIVE_KEYS:
            widget = getattr(self, "control_widgets", {}).get(key)
            if widget is not None:
                try:
                    widget.configure(state="disabled" if is_advanced else "readonly")
                except Exception:
                    pass
        if not hasattr(self, "advanced_state_label"):
            return
        if is_advanced:
            self.advanced_state_label.configure(
                text=("Advanced settings are active. Qualitative controls are locked." if self.current_language()=="English" else "詳細設定を使用中（定性的設定はロック中。戻す場合は詳細設定の「定性的設定から再計算」）"),
                foreground="#b45309",
            )
        else:
            self.advanced_state_label.configure(text=("Using qualitative controls" if self.current_language()=="English" else "定性的設定を使用中"), foreground="#4b5563")

    def recompute_advanced_from_qualitative(self) -> None:
        """Compute detailed Dynamic parameters from qualitative choices.

        The mapping is intentionally contextual: visual bar count and fps are
        considered so the same qualitative choice feels similar across layouts.
        """
        speed = str(self.choice_to_ja("response_speed", self.vars["response_speed"].get()))
        bounce = str(self.choice_to_ja("bounce_strength", self.vars["bounce_strength"].get()))
        sensitivity = str(self.choice_to_ja("sensitivity_level", self.vars["sensitivity_level"].get()))
        detail = str(self.choice_to_ja("motion_detail", self.vars["motion_detail"].get()))
        contrast = str(self.choice_to_ja("contrast_profile", self.vars["contrast_profile"].get()))
        if "カスタム" in {speed, bounce, sensitivity, detail, contrast}:
            return

        bars = max(1, int(self.vars["bars"].get()))
        fps = max(1, int(self.vars["fps"].get()))

        # Base speed profile.
        speed_map = {
            "ゆったり": {"fft_size": 2048, "attack": 0.84, "release": 0.58},
            "標準": {"fft_size": 1024, "attack": 0.95, "release": 0.76},
            "速い": {"fft_size": 512, "attack": 1.00, "release": 0.88},
        }
        values = dict(speed_map.get(speed, speed_map["標準"]))

        # Base bounce profile.
        bounce_map = {
            "控えめ": {"relative_range_db": 34.0, "base_cut": 0.10, "pulse_amount": 0.65, "pulse_speed": 0.18},
            "標準": {"relative_range_db": 30.0, "base_cut": 0.12, "pulse_amount": 0.80, "pulse_speed": 0.25},
            "大きい": {"relative_range_db": 28.0, "base_cut": 0.16, "pulse_amount": 0.90, "pulse_speed": 0.35},
        }
        values.update(bounce_map.get(bounce, bounce_map["標準"]))

        sensitivity_map = {"低め": 4.0, "標準": 8.0, "高め": 12.0}
        values["gain_db"] = sensitivity_map.get(sensitivity, 8.0)

        detail_bands = {"なめらか": 48, "標準": 64, "細かい": 96}.get(detail, 64)
        if bars <= 18:
            detail_bands = max(detail_bands, 72)
            values["release"] = min(1.0, values["release"] + 0.05)
            values["pulse_amount"] = min(1.0, values["pulse_amount"] + 0.04)
        elif bars >= 48:
            detail_bands = max(detail_bands, bars)
            values["release"] = max(0.05, values["release"] - 0.03)
            values["pulse_amount"] = max(0.0, values["pulse_amount"] - 0.04)
        elif bars >= 32:
            detail_bands = max(detail_bands, 64)
            values["release"] = max(0.05, values["release"] - 0.02)
            values["pulse_amount"] = max(0.0, values["pulse_amount"] - 0.03)

        if detail == "なめらか":
            values["fft_size"] = max(values["fft_size"], 1024)
            values["release"] = max(0.05, values["release"] - 0.04)
            values["pulse_speed"] = max(0.01, values["pulse_speed"] - 0.03)
        elif detail == "細かい":
            values["fft_size"] = min(values["fft_size"], 1024)
            values["release"] = min(1.0, values["release"] + 0.05)
            values["pulse_speed"] = min(0.95, values["pulse_speed"] + 0.05)

        # 60fps should not feel twice as twitchy as 30fps.
        if fps >= 50:
            values["release"] = max(0.05, values["release"] - 0.05)
            values["pulse_speed"] = max(0.01, values["pulse_speed"] - 0.04)

        if contrast == "フラット":
            values["relative_range_db"] += 4.0
            values["base_cut"] = max(0.0, values["base_cut"] - 0.03)
            values["peak_percentile"] = 88.0
            gamma = 0.95
        elif contrast == "メリハリ":
            values["relative_range_db"] = max(6.0, values["relative_range_db"] - 4.0)
            values["base_cut"] = min(0.8, values["base_cut"] + 0.04)
            values["peak_percentile"] = 92.0
            gamma = 0.80
        else:
            values["peak_percentile"] = 90.0
            gamma = 0.85

        values["analysis_bands"] = int(detail_bands)
        values["min_db"] = -60.0
        values["max_db"] = -6.0

        was = self.apply_in_progress
        self.apply_in_progress = True
        try:
            for k, v in values.items():
                if k in self.vars:
                    self.vars[k].set(v)
            self.vars["gamma"].set(gamma)
            self.vars["advanced_custom"].set(False)
        finally:
            self.apply_in_progress = was
        self.update_advanced_state_label()

    def choose_input(self) -> None:
        path = filedialog.askopenfilename(
            title="音源ファイルを選択",
            filetypes=[("Audio files", "*.wav *.mp3 *.m4a *.flac *.aac *.ogg"), ("All files", "*.*")],
        )
        if path:
            self.vars["input_file"].set(path)
            if not self.vars["output_dir"].get():
                self.vars["output_dir"].set(str(Path(path).parent))
            self.motion_status.configure(text=("Needs update" if self.current_language()=="English" else "要更新"))

    def choose_output_dir(self) -> None:
        path = filedialog.askdirectory(title="出力先フォルダを選択")
        if path:
            self.vars["output_dir"].set(path)

    def choose_color(self, key: str) -> None:
        color = colorchooser.askcolor(color=self.vars[key].get(), title="色を選択")
        if color and color[1]:
            self.vars[key].set(color[1].upper())

    def on_preset_selected(self, _event=None) -> None:
        name = self.vars["preset"].get()
        if name and name != CUSTOM_LABEL:
            self.apply_preset(name)

    def apply_preset(self, name: str) -> None:
        p = self.preset_manager.get(name)
        if not p:
            return
        self.apply_in_progress = True
        try:
            values = dict(p.get("values", {}))
            values.setdefault("frequency_mode", "自動")
            values.setdefault("sensitivity_level", "標準")
            values.setdefault("motion_detail", "標準")
            values.setdefault("contrast_profile", "標準")
            values.setdefault("advanced_custom", False)
            # Backward compatibility for older Japanese labels.
            if values.get("response_speed") == "遅い":
                values["response_speed"] = "ゆったり"
            if values.get("bounce_strength") == "弱い":
                values["bounce_strength"] = "控えめ"
            if values.get("bounce_strength") == "強い":
                values["bounce_strength"] = "大きい"
            for key, value in values.items():
                if key in self.vars:
                    self.vars[key].set(value)
            self.vars["preset"].set(name)
        finally:
            self.apply_in_progress = False
        self.localize_choice_vars()
        if not bool(self.vars["advanced_custom"].get()):
            self.recompute_advanced_from_qualitative()
        self.update_preset_combo_values()
        self.update_still_preview()
        self.motion_status.configure(text=("Needs update" if self.current_language()=="English" else "要更新"))
        self.update_advanced_state_label()

    def update_preset_combo_values(self) -> None:
        values = self.preset_manager.names()
        if self.vars["preset"].get() == CUSTOM_LABEL:
            values = [CUSTOM_LABEL] + values
        self.preset_combo.configure(values=values)

    def get_values(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, var in self.vars.items():
            if key in OPERATIONAL_KEYS:
                continue
            result[key] = var.get()
        return result

    def save_preset(self) -> None:
        name = simpledialog.askstring("プリセット保存", "保存するプリセット名を入力してください。", parent=self)
        if not name:
            return
        name = name.strip()
        existing = self.preset_manager.get(name)
        if existing and existing.get("system"):
            messagebox.showerror("保存できません", "システムプリセットと同じ名前では保存できません。")
            return
        if existing and not messagebox.askyesno("上書き確認", f"'{name}' は既に存在します。上書きしますか？"):
            return
        try:
            self.preset_manager.upsert_user_preset(name, self.get_values())
            self.vars["preset"].set(name)
            self.update_preset_combo_values()
            self.log(f"プリセットを保存しました: {name}")
        except Exception as exc:
            messagebox.showerror("保存エラー", str(exc))

    def delete_preset(self) -> None:
        name = self.vars["preset"].get()
        if not name or name == CUSTOM_LABEL:
            messagebox.showinfo("削除", "削除するユーザープリセットを選択してください。")
            return
        if self.preset_manager.is_system(name):
            messagebox.showinfo("削除できません", "システムプリセットは削除できません。")
            return
        if not messagebox.askyesno("削除確認", f"ユーザープリセット '{name}' を削除しますか？"):
            return
        try:
            self.preset_manager.delete_user_preset(name)
            self.update_preset_combo_values()
            self.apply_preset("01 Dynamic Standard")
            self.log(f"プリセットを削除しました: {name}")
        except Exception as exc:
            messagebox.showerror("削除エラー", str(exc))

    def current_style(self) -> RenderStyle:
        return RenderStyle(
            width=int(self.vars["width"].get()),
            height=int(self.vars["height"].get()),
            fps=int(self.vars["fps"].get()),
            bars=int(self.vars["bars"].get()),
            background_color=parse_color(self.vars["background_color"].get(), (0, 0, 0)),
            bar_color=parse_color(self.vars["bar_color"].get(), (255, 255, 255)),
            max_height_ratio=float(self.vars["max_height_percent"].get()) / 100.0,
            bottom_margin_ratio=float(self.vars["bottom_margin_percent"].get()) / 100.0,
            side_margin_ratio=float(self.vars["side_margin_percent"].get()) / 100.0,
            bar_width_scale=float(self.vars["bar_width_percent"].get()) / 100.0,
            corner_radius=int(self.vars["corner_radius"].get()),
            gamma=float(self.vars["gamma"].get()),
        )

    def current_motion(self) -> MotionSettings:
        return MotionSettings(
            sample_rate=int(self.vars["sample_rate"].get()),
            fft_size=int(self.vars["fft_size"].get()),
            analysis_bands=int(self.vars["analysis_bands"].get()),
            freq_min=float(self.vars["freq_min"].get()),
            freq_max=float(self.vars["freq_max"].get()),
            min_db=float(self.vars["min_db"].get()),
            max_db=float(self.vars["max_db"].get()),
            gain_db=float(self.vars["gain_db"].get()),
            attack=float(self.vars["attack"].get()),
            release=float(self.vars["release"].get()),
            relative_range_db=float(self.vars["relative_range_db"].get()),
            peak_percentile=float(self.vars["peak_percentile"].get()),
            base_cut=float(self.vars["base_cut"].get()),
            pulse_amount=float(self.vars["pulse_amount"].get()),
            pulse_speed=float(self.vars["pulse_speed"].get()),
        )

    def resolve_frequency_range_for_run(self, input_path: Path, motion: MotionSettings, scan_seconds: float) -> MotionSettings:
        """Return a run-local MotionSettings with resolved frequency range.

        In automatic mode, the GUI preset values are intentionally not overwritten.
        This prevents selecting a preset and pressing motion preview from turning
        the preset into Custom merely because the auto analyzer found a range.
        """
        if str(self.choice_to_ja("frequency_mode", self.vars["frequency_mode"].get())) == "自動":
            low_hz, high_hz = suggest_frequency_range(
                input_path=input_path,
                sample_rate=motion.sample_rate,
                scan_seconds=scan_seconds,
                log_callback=self.log_from_thread,
            )
            motion.freq_min = low_hz
            motion.freq_max = high_hz
            self.log_from_thread(f"Using auto frequency range: {low_hz:.0f} - {high_hz:.0f} Hz")
        else:
            self.log_from_thread(f"Using manual frequency range: {motion.freq_min:.0f} - {motion.freq_max:.0f} Hz")
        return motion

    def current_encode(self) -> EncodeSettings:
        return EncodeSettings(
            crf=int(self.vars["crf"].get()),
            preset=str(self.vars["x264_preset"].get()),
            encoder=str(self.vars["encoder"].get()),
        )

    def _fit_photo(self, frame: np.ndarray, canvas: tk.Canvas) -> ImageTk.PhotoImage:
        image = Image.fromarray(frame)
        canvas.update_idletasks()
        avail_w = max(240, canvas.winfo_width() or 640)
        avail_h = max(120, canvas.winfo_height() or 220)
        ratio = min(avail_w / image.width, avail_h / image.height)
        new_w = max(1, int(image.width * ratio))
        new_h = max(1, int(image.height * ratio))
        image = image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)

    def _draw_canvas_message(self, canvas: tk.Canvas, message: str) -> None:
        canvas.delete("all")
        canvas.update_idletasks()
        w = max(240, canvas.winfo_width() or 640)
        h = max(120, canvas.winfo_height() or 220)
        canvas.create_text(w // 2, h // 2, text=message, fill="#6b7280", font=("Yu Gothic UI", 10))

    def _draw_on_canvas(self, canvas: tk.Canvas, photo: ImageTk.PhotoImage) -> None:
        canvas.delete("all")
        canvas.update_idletasks()
        w = max(240, canvas.winfo_width() or 640)
        h = max(120, canvas.winfo_height() or 220)
        x = w // 2
        y = h // 2
        canvas.create_image(x, y, image=photo, anchor="center")

    def redraw_still_canvas(self) -> None:
        if self.still_frame_array is None:
            self._draw_canvas_message(self.still_canvas, "プレビューを描画できません")
            return
        self.still_photo = self._fit_photo(self.still_frame_array, self.still_canvas)
        self._draw_on_canvas(self.still_canvas, self.still_photo)

    def redraw_motion_canvas(self) -> None:
        if not self.motion_frames:
            if self.motion_status.cget("text") == "解析中":
                self._draw_canvas_message(self.motion_canvas, "Analyzing audio..." if self.current_language()=="English" else "実音源を解析しています...")
            else:
                self._draw_canvas_message(self.motion_canvas, "音源を選択して「動きプレビュー」を押してください")
            return
        idx = min(max(self.motion_index - 1, 0), len(self.motion_frames) - 1)
        self.current_motion_photo = self._fit_photo(self.motion_frames[idx], self.motion_canvas)
        self._draw_on_canvas(self.motion_canvas, self.current_motion_photo)

    def update_still_preview(self) -> None:
        try:
            style = self.current_style()
            if style.width <= 0 or style.height <= 0:
                return
            vals = still_preview_values(style.bars)
            self.still_frame_array = draw_spectrum_frame(vals, style)
            self.redraw_still_canvas()
        except Exception:
            # While the user is editing numeric/color fields, temporary invalid
            # values should not replace the preview with an error message.
            return

    def stop_motion_animation(self) -> None:
        if self.motion_after_id:
            try:
                self.after_cancel(self.motion_after_id)
            except Exception:
                pass
        self.motion_after_id = None
        self.motion_index = 0

    def stop_motion_preview(self) -> None:
        self.stop_motion_animation()
        try:
            self.motion_status.configure(text="Stopped" if self.current_language() == "English" else "停止")
        except Exception:
            pass

    def start_motion_preview(self) -> None:
        if self.motion_thread and self.motion_thread.is_alive():
            messagebox.showinfo("Analyzing", "Please wait until the current motion preview analysis finishes.")
            return
        input_path = self._validated_input_path()
        if input_path is None:
            return
        self.stop_motion_animation()
        self.motion_frames = []
        self.motion_photos = []
        self._draw_canvas_message(self.motion_canvas, "Analyzing audio..." if self.current_language()=="English" else "実音源を解析しています...")
        self.motion_status.configure(text="Analyzing" if self.current_language()=="English" else "解析中")
        self.motion_button.configure(state="disabled")
        style = self.current_style()
        motion = self.current_motion()
        auto = bool(self.vars["auto_preview_segment"].get())
        start = float(self.vars["preview_start"].get())
        duration = float(self.vars["motion_preview_duration"].get())
        warmup = float(self.vars["warmup"].get())
        scan_seconds = float(self.vars["scan_seconds"].get())

        def worker() -> None:
            try:
                self.resolve_frequency_range_for_run(input_path, motion, scan_seconds)
                values, detected_start = analyze_preview_segment(
                    input_path=input_path,
                    style=style,
                    motion=motion,
                    start=start,
                    duration=duration,
                    warmup=warmup,
                    auto_detect=auto,
                    scan_seconds=scan_seconds,
                    log_callback=self.log_from_thread,
                )
                self.after(0, lambda v=values, st=detected_start, sty=style: self._load_motion_frames(v, st, sty))
            except Exception as exc:
                self.log_from_thread("ERROR: " + str(exc))
                self.after(0, lambda e=str(exc): self._motion_preview_failed(e))

        self.motion_thread = threading.Thread(target=worker, daemon=True)
        self.motion_thread.start()

    def _load_motion_frames(self, values, detected_start: float, style: RenderStyle) -> None:
        try:
            frames: list[np.ndarray] = []
            for v in values:
                frame = draw_spectrum_frame(v, style)
                frames.append(frame)
            self.motion_frames = frames
            self.motion_photos = []
            self.motion_index = 0
            if self.vars["auto_preview_segment"].get():
                # Auto-detected preview position is an operational value, not a
                # preset edit.  Do not let this trace flip the preset to Custom.
                was_applying = self.apply_in_progress
                self.apply_in_progress = True
                try:
                    self.vars["preview_start"].set(round(float(detected_start), 2))
                finally:
                    self.apply_in_progress = was_applying
            self.motion_status.configure(text=(f"Playing {detected_start:.1f}s-" if self.current_language()=="English" else f"再生中 {detected_start:.1f}s〜"))
            self.motion_button.configure(state="normal")
            self._animate_motion_once()
        except Exception as exc:
            self._motion_preview_failed(str(exc))

    def _motion_preview_failed(self, message: str) -> None:
        self.motion_button.configure(state="normal")
        self.motion_status.configure(text=("Error" if self.current_language()=="English" else "エラー"))
        self._draw_canvas_message(self.motion_canvas, f"Motion preview error: {message}")
        messagebox.showerror("Motion Preview Error", message)

    def _animate_motion_once(self) -> None:
        if not self.motion_frames:
            return
        if self.motion_index >= len(self.motion_frames):
            self.motion_after_id = None
            self.motion_status.configure(text="Stopped" if self.current_language()=="English" else "停止")
            return
        frame = self.motion_frames[self.motion_index]
        self.current_motion_photo = self._fit_photo(frame, self.motion_canvas)
        self._draw_on_canvas(self.motion_canvas, self.current_motion_photo)
        self.motion_index += 1
        delay = int(1000 / max(1, int(self.vars["fps"].get())))
        self.motion_after_id = self.after(delay, self._animate_motion_once)

    def _validated_input_path(self) -> Path | None:
        input_text = self.vars["input_file"].get().strip()
        if not input_text:
            messagebox.showerror("Input Error", "Please select an audio file.")
            return None
        input_path = Path(input_text)
        if not input_path.exists():
            messagebox.showerror("Input Error", f"Audio file was not found.\n{input_path}")
            return None
        return input_path

    def start_render(self, preview: bool) -> None:
        if self.worker_thread and self.worker_thread.is_alive():
            messagebox.showinfo("Rendering", "Please wait until the current render finishes.")
            return
        input_path = self._validated_input_path()
        if input_path is None:
            return
        out_dir_text = self.vars["output_dir"].get().strip()
        output_dir = Path(out_dir_text) if out_dir_text else input_path.parent
        style = self.current_style()
        motion = self.current_motion()
        encode = self.current_encode()
        # The exported preview MP4 is intended to be placed at the beginning of
        # the editor timeline, so it is always generated from the beginning of
        # the audio.  GUI motion preview still uses auto-detected loud sections.
        start = 0.0
        duration = float(self.vars["preview_duration"].get()) if preview else None
        warmup = 0.0 if preview else 0.0
        output_path = build_default_output_path(input_path, output_dir, style, preview, start, duration)
        self.preview_button.configure(state="disabled")
        self.full_button.configure(state="disabled")
        self.motion_button.configure(state="disabled")
        self.log("----------------------------------------")
        self.log("Starting render.")

        def worker() -> None:
            nonlocal start, output_path
            try:
                scan_seconds = float(self.vars["scan_seconds"].get())
                self.resolve_frequency_range_for_run(input_path, motion, scan_seconds)
                # Preview MP4 is always from the head of the track.
                if preview:
                    start = 0.0
                    output_path = build_default_output_path(input_path, output_dir, style, preview, start, duration)
                actual = render_audio_to_video(
                    input_path=input_path,
                    output_path=output_path,
                    style=style,
                    motion=motion,
                    encode=encode,
                    start=start,
                    duration=duration,
                    warmup=warmup,
                    log_callback=self.log_from_thread,
                )
                self.log_from_thread(f"Saved to: {actual}")
            except Exception as exc:
                self.log_from_thread("ERROR: " + str(exc))
                self.after(0, lambda e=str(exc): messagebox.showerror("Render Error", e))
            finally:
                self.after(0, self._render_finished)

        self.worker_thread = threading.Thread(target=worker, daemon=True)
        self.worker_thread.start()

    def _render_finished(self) -> None:
        self.preview_button.configure(state="normal")
        self.full_button.configure(state="normal")
        self.motion_button.configure(state="normal")

    def log_from_thread(self, message: str) -> None:
        self.log_queue.put(message)

    def _process_log_queue(self) -> None:
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self.log(msg)
        self.after(100, self._process_log_queue)

    def log(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def open_output_folder(self) -> None:
        out = self.vars["output_dir"].get().strip()
        if not out:
            inp = self.vars["input_file"].get().strip()
            out = str(Path(inp).parent) if inp else str(APP_DIR)
        try:
            os.startfile(out)  # type: ignore[attr-defined]
        except Exception as exc:
            messagebox.showerror("エラー", str(exc))


if __name__ == "__main__":
    app = App()
    app.mainloop()
