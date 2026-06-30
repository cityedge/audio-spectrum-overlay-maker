"""
SRT Spectrum Video Composer - prototype

A lightweight Tkinter front-end that combines:
  - background image
  - audio file
  - SRT subtitle file
  - color spectrum video
  - optional mask video
into a final MP4 using local FFmpeg / FFprobe.

FFmpeg search order:
  1. <app dir>/bin/ffmpeg.exe and ffprobe.exe
  2. PATH

This is a prototype. It intentionally avoids heavy Python video/image libraries.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, asdict, field, fields
from pathlib import Path
from tkinter import (
    Tk, Frame, Label, Button, Entry, StringVar, IntVar, DoubleVar, BooleanVar,
    Text, END, filedialog, messagebox, ttk, Canvas, PhotoImage, Scale, Spinbox, Toplevel, PanedWindow
)
from tkinter import colorchooser, font as tkfont, simpledialog

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


APP_NAME = "SRT Spectrum Video Composer"
APP_VERSION = "0.1.8-stable"
PROJECT_SCHEMA_VERSION = 1
HANDOFF_SCHEMA_VERSION = 1
HANDOFF_TYPE = "audio_spectrum_overlay_maker_to_srt_spectrum_video_composer"
LEGACY_HANDOFF_TYPES = {"spectrum_maker_to_final_composer"}

BACKGROUND_SIZE_PRESET = "背景画像と同じサイズ / Background size"
OUTPUT_MIN_WIDTH = 320
OUTPUT_MIN_HEIGHT = 240
NO_WINDOW_SUBPROCESS_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

VIDEO_PRESETS = {
    BACKGROUND_SIZE_PRESET: None,
    "1920x1080": (1920, 1080),
    "1280x720": (1280, 720),
    "1080x1920": (1080, 1920),
    "1080x1080": (1080, 1080),
    "Custom": None,
}

QUALITY_PRESETS = {
    "Low size / CRF 26": 26,
    "Standard / CRF 23": 23,
    "High quality / CRF 20": 20,
    "Very high / CRF 18": 18,
    "Custom": None,
}

COMPOSE_MODES = [
    "mask_alpha",
    "black_colorkey",
    "darken_lighten_experimental",
]

COMPOSE_MODE_LABELS = {
    "mask_alpha": "標準：マスク動画をアルファとして使用",
    "black_colorkey": "簡易：黒背景を透過",
    "darken_lighten_experimental": "実験：比較(暗)＋比較(明)",
}

ALIGNMENTS = {
    "下中央": 2,
    "中央": 5,
    "上中央": 8,
    "自由XY": 5,
}


TITLE_ALIGNMENTS = {
    "左上": 7,
    "上中央": 8,
    "右上": 9,
    "左中央": 4,
    "中央": 5,
    "右中央": 6,
    "左下": 1,
    "下中央": 2,
    "右下": 3,
    "自由XY": 7,
}

LANGUAGES = {
    "ja": "日本語",
    "en": "English",
}
LANGUAGE_LABEL_TO_KEY = {v: k for k, v in LANGUAGES.items()}

TRANSLATIONS = {
    "ja": {
        "tab_files": "ファイル", "tab_srt": "字幕行", "tab_title": "タイトル", "tab_subtitle": "字幕",
        "tab_slideshow": "紙芝居",
        "tab_spectrum": "スペアナ", "tab_output": "出力", "tab_advanced": "詳細", "tab_presets": "プリセット",
        "language": "言語／Language", "background": "背景画像", "audio": "音源", "srt": "SRT字幕",
        "spectrum_color": "カラースペアナ", "spectrum_mask": "マスク動画", "output_mp4": "出力MP4",
        "select": "選択", "files_note": "作業に最低限必要なのは背景画像と音源だけです。スペアナ動画やSRTは任意です。スペアナ動画のみでマスク動画がない場合は、自動的に黒背景透過で処理します。",
        "reload_srt": "SRT再読み込み", "srt_note": "行を選択すると、その行の中央時刻がプレビュー時刻になります。",
        "start": "開始", "end": "終了", "body": "本文",
        "text_style": "文字スタイル", "font": "フォント", "font_size": "文字サイズ", "bold": "太字", "italic": "斜体", "text_color": "文字色",
        "outline_color": "縁取り色", "outline_width": "縁取り幅", "shadow": "影", "position": "表示位置",
        "alignment": "基準位置", "margin": "下/上からの距離", "custom_x": "自由X", "custom_y": "自由Y",
        "title_enabled": "タイトルを表示", "title_text": "タイトル文字列",
        "title_note": "デフォルトでは音源ファイル名（拡張子なし）をタイトル文字列にします。字幕とは別レイヤーとしてASSに焼き込みます。",
        "geom": "位置とサイズ", "appearance": "表示", "display_transform": "表示・変形", "x_pos": "X位置", "y_pos": "Y位置", "width": "幅", "height": "高さ", "center": "中央",
        "transform": "変形", "flip_h": "左右反転", "flip_v": "上下反転",
        "compose_mode": "合成方式", "compose_note": "標準はマスク動画方式です。マスク動画がない場合は自動的に黒背景透過へフォールバックします。",
        "video_settings": "動画設定", "resolution": "解像度", "fps": "FPS", "quality": "品質", "quality_preset": "画質プリセット",
        "encoder_preset": "x264 preset", "stillimage_tune": "静止画チューニング", "bitrate": "ビットレート", "video_bitrate": "最大ビットレート 任意", "audio_bitrate": "音声ビットレート",
        "bitrate_note": "空欄でCRF中心の品質指定になります。YouTube向け通常用途では標準CRFで十分です。",
        "black_key": "マスク動画なし時（黒背景透過）", "black_similarity": "黒背景透過しきい値", "black_blend": "黒背景透過なめらかさ",
        "mask_proc": "マスク動画使用時（標準）", "mask_binarize": "マスクを二値化する", "mask_threshold": "マスク二値化しきい値", "alpha_strength": "マスク濃度補正", "spectrum_opacity": "透明度",
        "mask_proc_note": "マスク動画がある場合の標準合成で使います。二値化しきい値は「マスクを二値化する」がオンの時だけ有効です。",
        "black_key_note": "マスク動画がない場合の自動フォールバックで使います。カラースペアナ動画の黒背景を透過します。",
        "advanced_note": "注：darken/lighten自体にはしきい値がありません。ここでは黒透過・マスク処理の補正値を詳細設定として扱います。",
        "quick_preview": "簡易プレビュー更新", "time_sec": "時刻(秒)", "still_preview": "静止画生成", "movie_duration": "動画秒数", "movie_preview": "動画生成して開く",
        "save_preset": "プロジェクトを保存", "load_preset": "プロジェクトを読み込み", "show_command": "FFmpegコマンドをログに表示", "render_start": "レンダー開始", "open_output_dir": "出力先を開く", "log": "ログ",
        "layout_presets": "レイアウトプリセット", "output_presets": "出力プリセット", "apply_preset": "適用", "save_user_preset": "現在の設定を保存", "delete_user_preset": "削除",
        "preset_note": "システムプリセットは編集・削除できません。ユーザープリセットは素材ファイルパスを保存しません。",
        "choose_color": "色を選択", "subtitle_sample": "字幕サンプル", "title_sample": "タイトルサンプル", "ffmpeg_preview": "FFmpeg preview",
        "preview_window": "静止画プレビュー", "close": "閉じる",
        "slideshow_enabled": "紙芝居モード", "slideshow_load_timesheet": "タイムシートの読み込み",
        "slideshow_image_count": "画像数", "slideshow_fade_transition": "フェードトランジション",
        "slideshow_timesheet": "タイムシート",
        "slideshow_note": "紙芝居モードでは、ファイルタブの背景画像とタイトルタブのタイトル文字列をこのタブの設定で上書きします。タイトルのフォント、サイズ、位置などはタイトルタブの設定を使います。",
        "slideshow_scene_number": "番号", "slideshow_start_time": "開始時間", "slideshow_title": "タイトル",
        "slideshow_image_file": "画像ファイル", "slideshow_thumbnail": "サムネイル",
        "slideshow_jump_to_cut": "切り替えへジャンプ",
        "slideshow_no_image": "No image", "slideshow_preview_error": "Preview error",
    },
    "en": {
        "tab_files": "Files", "tab_srt": "Subtitle Lines", "tab_title": "Title", "tab_subtitle": "Subtitle",
        "tab_slideshow": "Slideshow",
        "tab_spectrum": "Spectrum", "tab_output": "Output", "tab_advanced": "Advanced", "tab_presets": "Presets",
        "language": "Language", "background": "Background image", "audio": "Audio", "srt": "SRT subtitle",
        "spectrum_color": "Color spectrum", "spectrum_mask": "Mask video", "output_mp4": "Output MP4",
        "select": "Browse", "files_note": "Only a background image and audio file are required. Spectrum video and SRT are optional. If a spectrum video is set without a mask video, black-background keying is used automatically.",
        "reload_srt": "Reload SRT", "srt_note": "Selecting a line sets the preview time to the middle of that subtitle line.",
        "start": "Start", "end": "End", "body": "Text",
        "text_style": "Text style", "font": "Font", "font_size": "Font size", "bold": "Bold", "italic": "Italic", "text_color": "Text color",
        "outline_color": "Outline color", "outline_width": "Outline width", "shadow": "Shadow", "position": "Position",
        "alignment": "Anchor", "margin": "Margin from edge", "custom_x": "Custom X", "custom_y": "Custom Y",
        "title_enabled": "Show title", "title_text": "Title text",
        "title_note": "By default the audio filename without extension is used as the title. It is burned in as a separate ASS layer.",
        "geom": "Position and size", "appearance": "Appearance", "display_transform": "Display / transform", "x_pos": "X", "y_pos": "Y", "width": "Width", "height": "Height", "center": "Center",
        "transform": "Transform", "flip_h": "Flip horizontal", "flip_v": "Flip vertical",
        "compose_mode": "Compositing mode", "compose_note": "The standard mode is mask-alpha compositing. If no mask video is set, it automatically falls back to black-background keying.",
        "video_settings": "Video settings", "resolution": "Resolution", "fps": "FPS", "quality": "Quality", "quality_preset": "Quality preset",
        "encoder_preset": "x264 preset", "stillimage_tune": "Still-image tuning", "bitrate": "Bitrate", "video_bitrate": "Max video bitrate optional", "audio_bitrate": "Audio bitrate",
        "bitrate_note": "Leave max bitrate blank to use CRF-based quality. Standard CRF is usually sufficient for YouTube.",
        "black_key": "When no mask video is available", "black_similarity": "Black key threshold", "black_blend": "Black key softness",
        "mask_proc": "When using a mask video", "mask_binarize": "Binarize mask", "mask_threshold": "Mask threshold", "alpha_strength": "Mask density correction", "spectrum_opacity": "Transparency",
        "mask_proc_note": "Used by the standard mask-video compositing mode. The threshold is used only when mask binarization is enabled.",
        "black_key_note": "Used by the automatic fallback when no mask video is available. It keys out the black background of the color spectrum video.",
        "advanced_note": "Note: darken/lighten itself has no threshold. These settings are correction values for black keying and mask processing.",
        "quick_preview": "Refresh quick preview", "time_sec": "Time (sec)", "still_preview": "Generate still", "movie_duration": "Movie length", "movie_preview": "Generate movie and open",
        "save_preset": "Save project", "load_preset": "Load project", "show_command": "Show FFmpeg command in log", "render_start": "Start render", "open_output_dir": "Open output folder", "log": "Log",
        "layout_presets": "Layout presets", "output_presets": "Output presets", "apply_preset": "Apply", "save_user_preset": "Save current", "delete_user_preset": "Delete",
        "preset_note": "System presets cannot be edited or deleted. User presets do not save media file paths.",
        "choose_color": "Choose color", "subtitle_sample": "Subtitle sample", "title_sample": "Title sample", "ffmpeg_preview": "FFmpeg preview",
        "preview_window": "Still preview", "close": "Close",
        "slideshow_enabled": "Slideshow mode", "slideshow_load_timesheet": "Load timesheet",
        "slideshow_image_count": "Image count", "slideshow_fade_transition": "Fade transition",
        "slideshow_timesheet": "Timesheet",
        "slideshow_note": "In slideshow mode, the background image from the Files tab and the title text from the Title tab are overridden by the settings in this tab. Font, size, and position still come from the Title tab.",
        "slideshow_scene_number": "Number", "slideshow_start_time": "Start time", "slideshow_title": "Title",
        "slideshow_image_file": "Image file", "slideshow_thumbnail": "Thumbnail",
        "slideshow_jump_to_cut": "Jump to cut",
        "slideshow_no_image": "No image", "slideshow_preview_error": "Preview error",
    },
}

TOOLTIPS = {
    "language": {"ja": "画面表示とヒントの言語を切り替えます。", "en": "Switches the UI and tooltip language."},
    "background": {"ja": "動画の背景に使う静止画像です。等倍モードではリサイズせず、その画像サイズを出力解像度にします。", "en": "Still image used as the video background. In background-size mode, it is not resized and its size becomes the output resolution."},
    "audio": {"ja": "最終動画に入れる音源です。選択すると出力名とタイトルが自動候補になります。", "en": "Audio for the final video. Selecting it auto-suggests the output filename and title."},
    "srt": {"ja": "SRT字幕ファイルです。字幕行タブに読み込まれます。", "en": "SRT subtitle file. Its lines are loaded into the subtitle-lines tab."},
    "spectrum_color": {"ja": "黒背景にカラースペアナが描かれたMP4です。対応する_matte_dark.mp4があれば自動読み込みします。", "en": "MP4 with colored spectrum bars on black. A matching _matte_dark.mp4 is auto-loaded if found."},
    "spectrum_mask": {"ja": "白地に黒スペアナのマスク動画です。標準合成モードで使用します。", "en": "White-background/black-spectrum mask video used by the standard compositing mode."},
    "output_mp4": {"ja": "これから作成する出力MP4の保存先です。既存ファイルである必要はありません。", "en": "Destination path for the output MP4. It does not need to exist yet."},
    "font": {"ja": "OSにインストールされているフォント名から選択します。", "en": "Choose from font families installed in the OS."},
    "font_size": {"ja": "焼き込み文字のサイズです。ASS字幕のFontsizeに反映します。", "en": "Burned-in text size. This maps to ASS Fontsize."},
    "color": {"ja": "クリックすると色ピッカーを開きます。", "en": "Click to open a color picker."},
    "outline_width": {"ja": "文字の縁取り幅です。0で縁取りなしになります。", "en": "Text outline width. Set 0 for no outline."},
    "shadow": {"ja": "文字の影の強さです。0で影なしになります。", "en": "Text shadow strength. Set 0 for no shadow."},
    "alignment": {"ja": "文字配置の基準位置です。自由XYでは座標を直接使います。", "en": "Anchor point for text placement. Custom XY uses explicit coordinates."},
    "margin": {"ja": "上下配置時の画面端からの距離です。", "en": "Distance from the screen edge for top/bottom anchored placement."},
    "custom_xy": {"ja": "自由XY配置時に使用する座標です。", "en": "Coordinates used for custom XY placement."},
    "title_enabled": {"ja": "タイトル文字列を字幕とは別に焼き込みます。", "en": "Burns a separate title string in addition to subtitles."},
    "title_text": {"ja": "動画に焼き込むタイトル文字列です。空なら表示されません。", "en": "Title string to burn into the video. Empty text is not displayed."},
    "spec_pos": {"ja": "スペアナの左上位置です。出力解像度上のピクセル座標です。", "en": "Top-left position of the spectrum in output pixels."},
    "spec_size": {"ja": "スペアナの表示サイズです。", "en": "Displayed size of the spectrum layer."},
    "flip": {"ja": "カラースペアナとマスクに同じ反転を適用します。", "en": "Applies the same flip to color spectrum and mask."},
    "compose_mode": {"ja": "通常は標準のマスク動画方式を使います。", "en": "Normally use the standard mask-video mode."},
    "resolution": {"ja": "最終動画の解像度です。「背景画像と同じサイズ」では背景画像を等倍で使います。", "en": "Final video resolution. Background-size mode uses the background image at native size."},
    "stillimage_tune": {"ja": "x264のstillimageチューニングを使います。静止画中心の動画向けですが、スペアナが大きい場合は容量が増えることがあります。", "en": "Uses x264 stillimage tuning. Useful for still-image videos, but large spectrum overlays may increase file size."},
    "fps": {"ja": "最終動画のフレームレートです。", "en": "Frame rate of the final video."},
    "crf": {"ja": "x264の品質値です。小さいほど高画質・大容量です。", "en": "x264 quality value. Lower means higher quality and larger files."},
    "bitrate": {"ja": "必要な場合だけ最大ビットレートを指定します。通常は空欄で構いません。", "en": "Set a max video bitrate only if needed. Usually leave blank."},
    "black_key": {"ja": "黒背景透過モードで使う黒判定の許容範囲です。", "en": "Tolerance used for black-background keying mode."},
    "mask_proc": {"ja": "マスク動画の二値化やアルファ強度を補正します。", "en": "Adjusts mask binarization and alpha strength."},
    "preview_time": {"ja": "静止画・動画プレビューに使う元動画上の時刻です。", "en": "Source timeline time used for still/movie previews."},
    "preview_duration": {"ja": "短尺動画プレビューの長さです。", "en": "Length of the short movie preview."},
    "slideshow_enabled": {"ja": "ONにすると、ファイルタブの背景画像とタイトルタブのタイトル文字列を紙芝居設定で上書きします。", "en": "When enabled, slideshow settings override the Files tab background image and the Title tab title text."},
    "slideshow_load_timesheet": {"ja": "UTF-8のタイムシートを読み込み、開始時間とタイトルをまとめて入力します。画像ファイルは個別に選択します。", "en": "Loads a UTF-8 timesheet to fill start times and titles. Image files are still selected individually."},
    "slideshow_image_count": {"ja": "紙芝居に使う場面数です。2〜20の範囲で指定します。", "en": "Number of scenes in the slideshow. Choose from 2 to 20."},
    "slideshow_fade_transition": {"ja": "ONにすると、切り替え時刻の前後0.5秒、合計1秒でフェードします。", "en": "When enabled, each cut uses a 1-second fade centered on the cut point: 0.5 seconds before and 0.5 seconds after."},
    "slideshow_timesheet": {"ja": "読み込んだタイムシートのパスです。タイムシートは補助入力で、必須ではありません。", "en": "Path to the loaded timesheet. Timesheets are optional helper input."},
    "slideshow_scene_number": {"ja": "場面のIDです。01、02のように自動で割り当てます。", "en": "Scene ID assigned automatically, such as 01 or 02."},
    "slideshow_start_time": {"ja": "この場面を開始する時刻です。形式は mm:ss,ms です。1枚目は 00:00,000 固定です。", "en": "Start time for this scene. Use mm:ss,ms. The first scene is fixed at 00:00,000."},
    "slideshow_title": {"ja": "この場面で表示するタイトル文字列です。空欄でも構いません。見た目はタイトルタブの設定を使います。", "en": "Title text shown for this scene. It may be blank. Styling comes from the Title tab."},
    "slideshow_image_file": {"ja": "この場面で背景に使う画像です。空欄の場合は黒背景になります。", "en": "Background image for this scene. Leave blank to use a black background."},
    "slideshow_select_image": {"ja": "この場面の画像ファイルを選択します。", "en": "Select the image file for this scene."},
    "slideshow_thumbnail": {"ja": "選択した画像の確認用サムネイルです。", "en": "Thumbnail preview of the selected image."},
    "slideshow_jump_to_cut": {"ja": "プレビュー用時刻を、この場面の開始時間にセットします。動画生成して開くと切り替わりを中心に確認できます。", "en": "Sets the preview time to this scene's start time, making the movie preview centered on the cut."},
}



TOOLTIPS.update({
    "spectrum_opacity": {"ja": "スペアナ全体の透明度です。値を大きくすると背景が透けて見えます。", "en": "Transparency of the spectrum layer. Higher values let the background show through."},
    "center_spectrum": {"ja": "スペアナの幅または高さを考慮して、この軸の中央に配置します。", "en": "Centers the spectrum on this axis, accounting for its width or height."},
    "quick_preview": {"ja": "背景、タイトル、字幕、スペアナ枠を軽量表示します。FFmpegの最終結果とは完全一致しません。", "en": "Refreshes the lightweight layout preview. It is not a pixel-perfect FFmpeg render."},
    "still_preview": {"ja": "現在の設定でFFmpeg静止画プレビューを生成します。", "en": "Generates a still preview with FFmpeg using the current settings."},
    "movie_preview": {"ja": "指定時刻を中心に短い動画プレビューを生成して開きます。", "en": "Generates and opens a short movie preview around the selected time."},
    "show_command": {"ja": "現在の設定から生成されるFFmpegコマンドをログに表示します。", "en": "Prints the FFmpeg command generated from the current settings to the log."},
    "render_start": {"ja": "現在の設定で最終MP4を生成します。出力の長さは音源の長さに合わせます。", "en": "Starts the final MP4 render. Output duration is matched to the audio duration."},
    "open_output_dir": {"ja": "出力MP4の保存先フォルダを開きます。", "en": "Opens the output MP4 destination folder."},
    "save_project": {"ja": "素材ファイルパスを含めて現在の作業状態をプロジェクトファイルに保存します。", "en": "Saves the current work state, including media file paths, as a project file."},
    "load_project": {"ja": "保存済みプロジェクトファイルから素材ファイルパスと設定を復元します。", "en": "Loads media file paths and settings from a saved project file."},
    "layout_preset": {"ja": "タイトル、字幕、スペアナの位置やサイズを保存したレイアウトプリセットです。", "en": "Layout preset for title, subtitle, and spectrum position and size."},
    "output_preset": {"ja": "解像度や品質など、出力設定を保存したプリセットです。", "en": "Output preset for resolution, quality, and related render settings."},
    "apply_preset": {"ja": "選択中のプリセットを現在の設定に適用します。", "en": "Applies the selected preset to the current settings."},
    "save_user_preset": {"ja": "現在の設定をユーザープリセットとして保存します。素材ファイルパスは保存しません。", "en": "Saves the current settings as a user preset. Media file paths are not saved."},
    "delete_user_preset": {"ja": "選択中のユーザープリセットを削除します。システムプリセットは削除できません。", "en": "Deletes the selected user preset. System presets cannot be deleted."},
})


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = app_dir()
BIN_DIR = APP_DIR / "bin"
WORK_DIR = APP_DIR / "work"
PRESET_DIR = APP_DIR / "presets"
LAYOUT_PRESET_DIR = PRESET_DIR / "layout"
OUTPUT_PRESET_DIR = PRESET_DIR / "output"


def local_app_data_dir(folder_name: str = "SRTSpectrumVideoComposer") -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / folder_name
    return APP_DIR


HANDOFF_DIR = local_app_data_dir() / "handoff"
STARTUP_HANDOFF_PATH = HANDOFF_DIR / "startup_handoff.json"
LEGACY_STARTUP_HANDOFF_PATH = local_app_data_dir("FinalComposer") / "handoff" / "startup_handoff.json"


def find_tool(name: str) -> str:
    exe = f"{name}.exe" if os.name == "nt" else name
    local = BIN_DIR / exe
    if local.exists():
        return str(local)
    found = shutil.which(name) or shutil.which(exe)
    if found:
        return found
    raise FileNotFoundError(
        f"{exe} が見つかりません。\n"
        f"{local} に配置するか、PATHを通してください。"
    )


def format_duration_seconds(seconds: float) -> str:
    return f"{max(0.0, seconds):.6f}".rstrip("0").rstrip(".")


def no_window_subprocess_kwargs() -> dict[str, int]:
    if NO_WINDOW_SUBPROCESS_FLAGS:
        return {"creationflags": NO_WINDOW_SUBPROCESS_FLAGS}
    return {}


def probe_media_duration(path: str) -> float:
    ffprobe = find_tool("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path,
    ]
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        **no_window_subprocess_kwargs(),
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed to read duration: {result.stderr.strip() or path}")
    try:
        duration = float(result.stdout.strip())
    except Exception as exc:
        raise RuntimeError(f"ffprobe returned an invalid duration: {result.stdout.strip()!r}") from exc
    if duration <= 0:
        raise RuntimeError(f"audio duration must be positive: {duration}")
    return duration


def ensure_dirs() -> None:
    WORK_DIR.mkdir(exist_ok=True)
    PRESET_DIR.mkdir(exist_ok=True)
    LAYOUT_PRESET_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PRESET_DIR.mkdir(parents=True, exist_ok=True)


def safe_preset_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name.strip())
    cleaned = re.sub(r"\s+", "_", cleaned).strip("._ ")
    return cleaned or "preset"


def parse_startup_args(argv: list[str]) -> Path | None:
    handoff_path: Path | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("--srt-spectrum-video-composer", "--final-composer"):
            i += 1
            continue
        if arg == "--handoff":
            if i + 1 >= len(argv):
                raise ValueError("--handoff requires a JSON file path")
            handoff_path = Path(argv[i + 1])
            i += 2
            continue
        if arg.startswith("--handoff="):
            handoff_path = Path(arg.split("=", 1)[1])
            i += 1
            continue
        i += 1
    return handoff_path


def first_text_value(*values) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def nested_text(data: dict, section: str, key: str) -> str:
    value = data.get(section)
    if isinstance(value, dict):
        result = value.get(key)
        if isinstance(result, str):
            return result.strip()
    return ""


def nested2_text(data: dict, section: str, subsection: str, key: str) -> str:
    value = data.get(section)
    if isinstance(value, dict):
        subvalue = value.get(subsection)
        if isinstance(subvalue, dict):
            result = subvalue.get(key)
            if isinstance(result, str):
                return result.strip()
    return ""


def default_output_path_from_audio(audio_path: str) -> str:
    """Return a safe default MP4 output path based on the audio filename."""
    if not audio_path:
        return ""
    audio = Path(audio_path)
    if not audio.name:
        return ""
    return unique_output_path(str(audio.with_suffix(".mp4")))


def normalize_output_path(output_path: str) -> str:
    """Ensure an output path has an extension; default to .mp4."""
    if not output_path:
        return ""
    p = Path(output_path)
    if not p.suffix:
        p = p.with_suffix(".mp4")
    return str(p)


def unique_output_path(output_path: str) -> str:
    """Return a non-existing output path by appending (1), (2), ... when needed."""
    if not output_path:
        return ""
    p = Path(normalize_output_path(output_path))
    if not p.exists():
        return str(p)
    for i in range(1, 10000):
        candidate = p.with_name(f"{p.stem}({i}){p.suffix}")
        if not candidate.exists():
            return str(candidate)
    raise RuntimeError(f"出力ファイル名の自動採番に失敗しました: {p}")


def parse_srt_optional(path: str | Path) -> list[tuple[int, int, str]]:
    """Parse SRT only when a valid path is provided; otherwise return no subtitle items."""
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    return parse_srt(p)


@dataclass
class SlideshowScene:
    scene_id: str = ""
    start_ms: int = 0
    title: str = ""
    path: str = ""


@dataclass
class BackgroundSettings:
    mode: str = "single"
    timesheet: str = ""
    image_dir: str = ""
    fade_transition: bool = False
    scenes: list[SlideshowScene] = field(default_factory=list)


def parse_timesheet_time(value: str) -> int:
    text = value.strip().replace(",", ".")
    parts = text.split(":")
    if len(parts) == 2:
        minutes = int(parts[0])
        seconds = float(parts[1])
        return int(round((minutes * 60 + seconds) * 1000))
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return int(round((hours * 3600 + minutes * 60 + seconds) * 1000))
    raise ValueError(f"Invalid timesheet time: {value}")


def parse_timesheet(path: str | Path) -> list[SlideshowScene]:
    p = Path(path)
    scenes: list[SlideshowScene] = []
    for line_no, raw in enumerate(p.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 2)
        if len(parts) < 2:
            parts = line.split(None, 2)
        if len(parts) < 2:
            raise ValueError(f"Invalid timesheet line {line_no}: {raw}")
        scene_id = parts[0].strip()
        start_ms = parse_timesheet_time(parts[1])
        title = parts[2].strip() if len(parts) >= 3 else scene_id
        scenes.append(SlideshowScene(scene_id=scene_id, start_ms=start_ms, title=title))
    scenes.sort(key=lambda scene: scene.start_ms)
    return scenes


def format_timesheet_time(ms: int) -> str:
    ms = max(0, int(ms))
    minutes, rest = divmod(ms, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f"{minutes:02d}:{seconds:02d},{millis:03d}"


def preview_time_for_slideshow_cut(start_ms: int) -> float:
    return round(max(0, int(start_ms)) / 1000, 3)


SLIDESHOW_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".webp")


def resolve_slideshow_image(scene_id: str, image_dir: str) -> str:
    if not scene_id or not image_dir:
        return ""
    folder = Path(image_dir)
    if not folder.exists():
        return ""
    raw = Path(scene_id)
    candidates: list[Path] = []
    if raw.suffix:
        candidates.append(folder / raw.name)
    else:
        candidates.extend(folder / f"{scene_id}{ext}" for ext in SLIDESHOW_IMAGE_EXTENSIONS)
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return ""


def is_slideshow_enabled(settings: AppSettings) -> bool:
    return settings.background.mode == "slideshow" and bool(settings.background.scenes)


def slideshow_scenes_sorted(settings: AppSettings) -> list[SlideshowScene]:
    return sorted(settings.background.scenes, key=lambda scene: scene.start_ms)


def slideshow_segments_for_window(
    settings: AppSettings,
    window_start_ms: int,
    duration_ms: int,
) -> list[tuple[SlideshowScene, int, int]]:
    scenes = slideshow_scenes_sorted(settings)
    if not scenes or duration_ms <= 0:
        return []
    window_end_ms = window_start_ms + duration_ms
    segments: list[tuple[SlideshowScene, int, int]] = []
    for index, scene in enumerate(scenes):
        next_start = scenes[index + 1].start_ms if index + 1 < len(scenes) else window_end_ms
        scene_start = max(scene.start_ms, window_start_ms)
        scene_end = min(next_start, window_end_ms)
        if scene_end <= scene_start:
            continue
        segments.append((scene, scene_start - window_start_ms, scene_end - window_start_ms))
    return segments


def active_slideshow_scene(settings: AppSettings, time_ms: int) -> SlideshowScene | None:
    active = None
    for scene in slideshow_scenes_sorted(settings):
        if scene.start_ms <= time_ms:
            active = scene
        else:
            break
    return active


def has_existing_file(path: str) -> bool:
    return bool(path and Path(path).exists())


def effective_compose_mode(settings: AppSettings) -> str | None:
    """Return actual spectrum compositing mode.

    - No color spectrum video: no spectrum layer.
    - Mask modes without an existing mask: fall back to black colorkey mode.
    """
    if not has_existing_file(settings.files.spectrum_color):
        return None
    mode = settings.spectrum.compose_mode
    if mode in ("mask_alpha", "darken_lighten_experimental") and not has_existing_file(settings.files.spectrum_mask):
        return "black_colorkey"
    return mode


def normalize_path_for_filter(path: str | Path) -> str:
    """Escape a path for FFmpeg filter arguments such as subtitles=..."""
    p = Path(path).resolve().as_posix()
    # Escape characters that FFmpeg filter parser treats specially.
    # Drive colon is the most important one on Windows.
    p = p.replace("\\", "/")
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    p = p.replace(",", r"\,")
    p = p.replace("[", r"\[").replace("]", r"\]")
    return f"'{p}'"




def fit_size(src_w: int, src_h: int, max_w: int, max_h: int) -> tuple[int, int]:
    """Fit src size into max box and return even positive dimensions."""
    src_w = max(1, int(src_w))
    src_h = max(1, int(src_h))
    scale = min(max_w / src_w, max_h / src_h)
    w = max(2, int(src_w * scale))
    h = max(2, int(src_h * scale))
    # Many video encoders prefer even dimensions.
    if w % 2:
        w -= 1
    if h % 2:
        h -= 1
    return max(2, w), max(2, h)


def open_in_default_app(path: str | Path) -> None:
    """Open a file with the OS default application."""
    p = str(Path(path).resolve())
    if os.name == "nt":
        os.startfile(p)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", p])
    else:
        subprocess.Popen(["xdg-open", p])


def ms_to_srt_time(ms: int) -> str:
    ms = max(0, int(ms))
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    ms %= 1000
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def hex_to_ass_color(hex_color: str, alpha_hex: str = "00") -> str:
    """Convert #RRGGBB to ASS &HAABBGGRR."""
    s = hex_color.strip()
    if not re.fullmatch(r"#?[0-9A-Fa-f]{6}", s):
        s = "#FFFFFF"
    s = s.lstrip("#")
    rr, gg, bb = s[0:2], s[2:4], s[4:6]
    return f"&H{alpha_hex.upper()}{bb.upper()}{gg.upper()}{rr.upper()}"


def parse_srt_time(value: str) -> int:
    """Return milliseconds."""
    m = re.match(r"\s*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*", value)
    if not m:
        raise ValueError(f"Invalid SRT time: {value}")
    h, mn, sec, ms = m.groups()
    ms = ms.ljust(3, "0")[:3]
    return (int(h) * 3600 + int(mn) * 60 + int(sec)) * 1000 + int(ms)


def ass_time(ms: int) -> str:
    cs = round(ms / 10)
    h = cs // 360000
    cs %= 360000
    m = cs // 6000
    cs %= 6000
    s = cs // 100
    cs %= 100
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_escape_text(text: str) -> str:
    text = text.replace("\\", r"\\")
    text = text.replace("{", r"\{").replace("}", r"\}")
    lines = [line.strip() for line in text.splitlines()]
    return r"\N".join(lines)


def parse_srt(path: str | Path) -> list[tuple[int, int, str]]:
    raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    raw = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    blocks = re.split(r"\n\s*\n", raw)
    items: list[tuple[int, int, str]] = []
    time_re = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*"
        r"(\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
    )
    for block in blocks:
        lines = [line for line in block.split("\n") if line.strip() != ""]
        if not lines:
            continue
        time_line_index = None
        for i, line in enumerate(lines):
            if "-->" in line:
                time_line_index = i
                break
        if time_line_index is None:
            continue
        tm = time_re.search(lines[time_line_index])
        if not tm:
            continue
        start = parse_srt_time(tm.group(1))
        end = parse_srt_time(tm.group(2))
        text = "\n".join(lines[time_line_index + 1:])
        if end > start and text.strip():
            items.append((start, end, text))
    return items


class Tooltip:
    """Small Tkinter tooltip with language-aware text callback."""
    def __init__(self, widget, text_getter, delay_ms: int = 450):
        self.widget = widget
        self.text_getter = text_getter
        self.delay_ms = delay_ms
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _schedule(self, _event=None):
        self._cancel()
        self.after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self):
        self._cancel()
        text = self.text_getter() if callable(self.text_getter) else str(self.text_getter)
        if not text:
            return
        if self.tip is not None:
            return
        try:
            x = self.widget.winfo_rootx() + 18
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        except Exception:
            x = y = 0
        self.tip = Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        label = Label(
            self.tip,
            text=text,
            justify="left",
            background="#ffffe8",
            foreground="#222222",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=5,
            wraplength=360,
        )
        label.pack()

    def _hide(self, _event=None):
        self._cancel()
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


@dataclass
class FileSettings:
    background: str = ""
    audio: str = ""
    srt: str = ""
    spectrum_color: str = ""
    spectrum_mask: str = ""
    output: str = ""


@dataclass
class SubtitleSettings:
    font_name: str = "Yu Gothic"
    font_size: int = 54
    bold: bool = False
    italic: bool = False
    text_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 4
    shadow: int = 2
    alignment_label: str = "下中央"
    bottom_margin: int = 80
    custom_x: int = 960
    custom_y: int = 930


@dataclass
class TitleSettings:
    enabled: bool = True
    text: str = ""
    font_name: str = "Yu Gothic"
    font_size: int = 72
    bold: bool = False
    italic: bool = False
    text_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    outline_width: int = 3
    shadow: int = 1
    alignment_label: str = "左上"
    margin_x: int = 60
    margin_y: int = 40
    custom_x: int = 60
    custom_y: int = 60


@dataclass
class SpectrumSettings:
    x: int = 100
    y: int = 820
    width: int = 600
    height: int = 180
    opacity: int = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    compose_mode: str = "mask_alpha"
    black_similarity: float = 0.03
    black_blend: float = 0.02
    mask_binarize: bool = False
    mask_threshold: int = 128
    alpha_strength: float = 1.0


@dataclass
class OutputSettings:
    width: int = 1920
    height: int = 1080
    fps: int = 30
    crf: int = 20
    video_bitrate: str = ""
    audio_bitrate: str = "192k"
    preset: str = "medium"
    use_stillimage_tune: bool = False
    background_native_size: bool = False
    format_label: str = "MP4 / H.264 + AAC"


@dataclass
class AppSettings:
    files: FileSettings
    background: BackgroundSettings
    subtitle: SubtitleSettings
    title: TitleSettings
    spectrum: SpectrumSettings
    output: OutputSettings


def dataclass_from_dict(cls, data: dict | None):
    if not isinstance(data, dict):
        data = {}
    valid = {field.name for field in fields(cls)}
    return cls(**{key: value for key, value in data.items() if key in valid})


def background_settings_from_dict(data: dict | None) -> BackgroundSettings:
    if not isinstance(data, dict):
        return BackgroundSettings()
    values = {key: value for key, value in data.items() if key != "scenes"}
    settings = dataclass_from_dict(BackgroundSettings, values)
    scenes: list[SlideshowScene] = []
    for item in data.get("scenes", []):
        if isinstance(item, dict):
            scenes.append(dataclass_from_dict(SlideshowScene, item))
    settings.scenes = scenes
    return settings


def app_settings_from_dict(data: dict) -> AppSettings:
    return AppSettings(
        files=dataclass_from_dict(FileSettings, data.get("files")),
        background=background_settings_from_dict(data.get("background")),
        subtitle=dataclass_from_dict(SubtitleSettings, data.get("subtitle")),
        title=dataclass_from_dict(TitleSettings, data.get("title")),
        spectrum=dataclass_from_dict(SpectrumSettings, data.get("spectrum")),
        output=dataclass_from_dict(OutputSettings, data.get("output")),
    )


def project_data_from_settings(settings: AppSettings, ui_state: dict | None = None) -> dict:
    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "app_name": APP_NAME,
        "app_version": APP_VERSION,
        "settings": asdict(settings),
        "ui": ui_state or {},
    }


def settings_and_ui_from_project_data(data: dict) -> tuple[AppSettings, dict]:
    if "schema_version" not in data:
        return app_settings_from_dict(data), {}

    version = int(data.get("schema_version", 0))
    if version > PROJECT_SCHEMA_VERSION:
        raise ValueError(
            f"このプロジェクトファイルは新しい形式です。schema_version={version}, supported={PROJECT_SCHEMA_VERSION}"
        )
    settings_data = data.get("settings", {})
    if not isinstance(settings_data, dict):
        raise ValueError("プロジェクトファイルのsettingsが不正です。")
    ui_state = data.get("ui", {})
    if not isinstance(ui_state, dict):
        ui_state = {}
    return app_settings_from_dict(settings_data), ui_state



def _title_margins_and_alignment(title: TitleSettings) -> tuple[int, int, int, int]:
    alignment = TITLE_ALIGNMENTS.get(title.alignment_label, 7)
    margin_l = title.margin_x if alignment in (1, 4, 7) else 40
    margin_r = title.margin_x if alignment in (3, 6, 9) else 40
    margin_v = title.margin_y
    return alignment, margin_l, margin_r, margin_v


def ass_bool(value: bool) -> int:
    return -1 if value else 0


def write_ass_items(
    items: list[tuple[int, int, str]],
    ass_path: str,
    sub: SubtitleSettings,
    out: OutputSettings,
    title: TitleSettings | None = None,
    title_items: list[tuple[int, int, str]] | None = None,
) -> None:
    primary = hex_to_ass_color(sub.text_color, "00")
    outline = hex_to_ass_color(sub.outline_color, "00")
    shadow_color = hex_to_ass_color("#000000", "80")
    alignment = ALIGNMENTS.get(sub.alignment_label, 2)
    margin_v = sub.bottom_margin if sub.alignment_label != "自由XY" else 0

    title_style_line = ""
    title_dialogue = ""
    effective_title_items = title_items or []
    if title is not None and title.enabled and (title.text.strip() or effective_title_items):
        title_primary = hex_to_ass_color(title.text_color, "00")
        title_outline = hex_to_ass_color(title.outline_color, "00")
        title_shadow = hex_to_ass_color("#000000", "80")
        title_alignment, title_margin_l, title_margin_r, title_margin_v = _title_margins_and_alignment(title)
        title_style_line = (
            f"Style: Title,{title.font_name},{title.font_size},{title_primary},&H000000FF,"
            f"{title_outline},{title_shadow},{ass_bool(title.bold)},{ass_bool(title.italic)},0,0,100,100,0,0,1,{title.outline_width},"
            f"{title.shadow},{title_alignment},{title_margin_l},{title_margin_r},{title_margin_v},1\n"
        )
        title_body = ass_escape_text(title.text)
        if title.alignment_label == "自由XY":
            title_body = rf"{{\pos({title.custom_x},{title.custom_y})}}" + title_body
        title_dialogue = f"Dialogue: 1,0:00:00.00,23:59:59.00,Title,,0,0,0,,{title_body}\n"
        if effective_title_items:
            timed_title_lines: list[str] = []
            for start_ms, end_ms, text in effective_title_items:
                if end_ms <= start_ms or not text.strip():
                    continue
                timed_body = ass_escape_text(text)
                if title.alignment_label == "���RXY":
                    timed_body = rf"{{\pos({title.custom_x},{title.custom_y})}}" + timed_body
                timed_title_lines.append(
                    f"Dialogue: 1,{ass_time(start_ms)},{ass_time(end_ms)},Title,,0,0,0,,{timed_body}\n"
                )
            title_dialogue = "".join(timed_title_lines)

    header = f"""[Script Info]
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
PlayResX: {out.width}
PlayResY: {out.height}
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{sub.font_name},{sub.font_size},{primary},&H000000FF,{outline},{shadow_color},{ass_bool(sub.bold)},{ass_bool(sub.italic)},0,0,100,100,0,0,1,{sub.outline_width},{sub.shadow},{alignment},40,40,{margin_v},1
{title_style_line}
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    if title_dialogue:
        lines.append(title_dialogue)
    for start_ms, end_ms, text in items:
        if end_ms <= start_ms or not text.strip():
            continue
        body = ass_escape_text(text)
        if sub.alignment_label == "自由XY":
            body = rf"{{\pos({sub.custom_x},{sub.custom_y})}}" + body
        lines.append(
            f"Dialogue: 0,{ass_time(start_ms)},{ass_time(end_ms)},Default,,0,0,0,,{body}\n"
        )
    Path(ass_path).write_text("".join(lines), encoding="utf-8-sig")


def slideshow_title_items(background: BackgroundSettings, duration_ms: int) -> list[tuple[int, int, str]]:
    items: list[tuple[int, int, str]] = []
    scenes = sorted(background.scenes, key=lambda scene: scene.start_ms)
    for index, scene in enumerate(scenes):
        end_ms = scenes[index + 1].start_ms if index + 1 < len(scenes) else duration_ms
        if end_ms > scene.start_ms and scene.title.strip():
            items.append((scene.start_ms, end_ms, scene.title))
    return items


def slideshow_preview_title_items(
    background: BackgroundSettings,
    start_ms: int,
    duration_ms: int,
) -> list[tuple[int, int, str]]:
    end_ms = start_ms + duration_ms
    items: list[tuple[int, int, str]] = []
    scenes = sorted(background.scenes, key=lambda scene: scene.start_ms)
    for index, scene in enumerate(scenes):
        scene_end = scenes[index + 1].start_ms if index + 1 < len(scenes) else end_ms
        if scene_end <= start_ms or scene.start_ms >= end_ms:
            continue
        dst_start = max(0, scene.start_ms - start_ms)
        dst_end = min(duration_ms, scene_end - start_ms)
        if dst_end > dst_start and scene.title.strip():
            items.append((dst_start, dst_end, scene.title))
    return items


def generate_ass(
    srt_path: str,
    ass_path: str,
    sub: SubtitleSettings,
    title: TitleSettings,
    out: OutputSettings,
    background: BackgroundSettings | None = None,
    duration_ms: int | None = None,
) -> None:
    items = parse_srt_optional(srt_path)
    title_items = None
    if background is not None and background.mode == "slideshow" and duration_ms is not None:
        title_items = slideshow_title_items(background, duration_ms)
    write_ass_items(items, ass_path, sub, out, title, title_items=title_items)


def generate_preview_ass_static(
    srt_path: str,
    ass_path: str,
    sub: SubtitleSettings,
    title: TitleSettings,
    out: OutputSettings,
    preview_ms: int,
    selected_index: int | None = None,
    background: BackgroundSettings | None = None,
) -> None:
    """Create a temporary ASS that displays the selected/active subtitle at t=0."""
    items = parse_srt_optional(srt_path)
    preview_items: list[tuple[int, int, str]] = []
    if selected_index is not None and 0 <= selected_index < len(items):
        text = items[selected_index][2]
        preview_items.append((0, 10000, text))
    else:
        for start_ms, end_ms, text in items:
            if start_ms <= preview_ms < end_ms:
                preview_items.append((0, 10000, text))
    title_items = None
    if background is not None and background.mode == "slideshow":
        active = None
        for scene in sorted(background.scenes, key=lambda item: item.start_ms):
            if scene.start_ms <= preview_ms:
                active = scene
            else:
                break
        if active is not None and active.title.strip():
            title_items = [(0, 10000, active.title)]
    write_ass_items(preview_items, ass_path, sub, out, title, title_items=title_items)


def generate_preview_ass_segment(
    srt_path: str,
    ass_path: str,
    sub: SubtitleSettings,
    title: TitleSettings,
    out: OutputSettings,
    start_ms: int,
    duration_ms: int,
    background: BackgroundSettings | None = None,
) -> None:
    """Create a temporary ASS shifted to a short preview segment starting at 0."""
    items = parse_srt_optional(srt_path)
    end_ms = start_ms + duration_ms
    preview_items: list[tuple[int, int, str]] = []
    for src_start, src_end, text in items:
        if src_end <= start_ms or src_start >= end_ms:
            continue
        dst_start = max(0, src_start - start_ms)
        dst_end = min(duration_ms, src_end - start_ms)
        if dst_end > dst_start:
            preview_items.append((dst_start, dst_end, text))
    title_items = None
    if background is not None and background.mode == "slideshow":
        title_items = slideshow_preview_title_items(background, start_ms, duration_ms)
    write_ass_items(preview_items, ass_path, sub, out, title, title_items=title_items)

def optional_flip_chain(label_in: str, spec: SpectrumSettings, label_out: str) -> str:
    filters = []
    if spec.flip_horizontal:
        filters.append("hflip")
    if spec.flip_vertical:
        filters.append("vflip")
    if not filters:
        return f"{label_in}null{label_out};"
    return f"{label_in}{','.join(filters)}{label_out};"


def spectrum_opacity_factor(spec: SpectrumSettings) -> float:
    opacity = min(100, max(0, int(getattr(spec, "opacity", 0))))
    return max(0.0, min(1.0, 1.0 - opacity / 100.0))


def rgba_alpha_multiplier_filter(factor: float) -> str:
    if factor >= 0.999:
        return ""
    return f",colorchannelmixer=aa={factor:.4f}"


def get_image_size(path: str) -> tuple[int, int] | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists() or Image is None:
        return None
    try:
        with Image.open(p) as im:
            return int(im.width), int(im.height)
    except Exception:
        return None


def build_background_chain(settings: AppSettings) -> str:
    out = settings.output
    if out.background_native_size:
        return f"[0:v]setsar=1,fps={out.fps},format=rgba[bg];"
    return (
        f"[0:v]scale=w={out.width}:h={out.height}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={out.width}:{out.height},setsar=1,fps={out.fps},format=rgba[bg];"
    )


def background_video_filter(settings: AppSettings, input_index: int, duration_ms: int, label: str) -> str:
    out = settings.output
    duration = format_duration_seconds(max(1, duration_ms) / 1000.0)
    if out.background_native_size:
        chain = f"[{input_index}:v]setsar=1,fps={out.fps},format=rgba"
    else:
        chain = (
            f"[{input_index}:v]scale=w={out.width}:h={out.height}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={out.width}:{out.height},setsar=1,fps={out.fps},format=rgba"
        )
    return f"{chain},trim=duration={duration},setpts=PTS-STARTPTS[{label}];"


def build_slideshow_background_inputs_and_chain(
    settings: AppSettings,
    window_start_ms: int,
    duration_ms: int,
) -> tuple[list[str], str, int]:
    segments = slideshow_segments_for_window(settings, window_start_ms, duration_ms)
    if not segments:
        return [], "", 0

    args: list[str] = []
    filters: list[str] = []
    concat_inputs: list[str] = []
    segment_durations_ms: list[int] = []
    fade_enabled = bool(getattr(settings.background, "fade_transition", False)) and len(segments) > 1
    fade_ms = 1000
    fade_half_ms = fade_ms // 2
    input_index = 0
    for index, (scene, _seg_start, seg_end) in enumerate(segments):
        seg_start = segments[index][1]
        seg_duration_ms = max(1, seg_end - seg_start)
        input_duration_ms = seg_duration_ms + (fade_ms if fade_enabled else 0)
        label = f"bgseg{index}"
        if scene.path:
            args.extend([
                "-loop", "1",
                "-framerate", str(settings.output.fps),
                "-t", format_duration_seconds(input_duration_ms / 1000.0),
                "-i", scene.path,
            ])
            filters.append(background_video_filter(settings, input_index, input_duration_ms, label))
            input_index += 1
        else:
            duration = format_duration_seconds(input_duration_ms / 1000.0)
            filters.append(
                f"color=c=black:s={settings.output.width}x{settings.output.height}:r={settings.output.fps},"
                f"format=rgba,trim=duration={duration},setpts=PTS-STARTPTS[{label}];"
            )
        concat_inputs.append(f"[{label}]")
        segment_durations_ms.append(seg_duration_ms)

    if len(concat_inputs) == 1:
        filters.append(f"{concat_inputs[0]}null[bg];")
    elif fade_enabled:
        current = concat_inputs[0]
        offset_ms = 0
        for index in range(1, len(concat_inputs)):
            offset_ms += segment_durations_ms[index - 1]
            fade_start_ms = max(0, offset_ms - fade_half_ms)
            output_label = "bg" if index + 1 == len(concat_inputs) else f"bgfade{index}"
            filters.append(
                f"{current}{concat_inputs[index]}xfade=transition=fade:duration=1:"
                f"offset={format_duration_seconds(fade_start_ms / 1000.0)}[{output_label}];"
            )
            current = f"[{output_label}]"
    else:
        filters.append(f"{''.join(concat_inputs)}concat=n={len(concat_inputs)}:v=1:a=0[bg];")
    return args, "".join(filters), input_index


def build_visual_filter_complex(
    settings: AppSettings,
    ass_path: str,
    spectrum_index: int | None,
    mask_index: int | None,
    out_label: str = "outv",
    final_scale: tuple[int, int] | None = None,
    reset_overlay_pts: bool = False,
    duration_sec: float | None = None,
    background_chain: str | None = None,
) -> str:
    out = settings.output
    spec = settings.spectrum
    sub_filter = f"subtitles={normalize_path_for_filter(ass_path)}"
    opacity_factor = spectrum_opacity_factor(spec)

    bg = background_chain or build_background_chain(settings)

    def finish(label: str) -> str:
        tail = "null"
        if final_scale:
            pw, ph = final_scale
            tail = f"scale={pw}:{ph}"
        if duration_sec is not None:
            tail += f",trim=duration={format_duration_seconds(duration_sec)},setpts=PTS-STARTPTS"
        return f"{label}{tail}[{out_label}]"

    def video_in(index: int) -> str:
        if reset_overlay_pts:
            return f"[{index}:v]setpts=PTS-STARTPTS,"
        return f"[{index}:v]"

    mode = effective_compose_mode(settings)

    # Background + title/subtitles only. This is valid when no spectrum video is set.
    if mode is None or spectrum_index is None:
        return bg + f"[bg]{sub_filter}[with_sub];" + finish("[with_sub]")

    if mode == "mask_alpha":
        if mask_index is None:
            # Safety fallback. validate/effective_mode should normally handle this.
            mode = "black_colorkey"
        else:
            mask_chain = f"{video_in(mask_index)}scale={spec.width}:{spec.height},format=gray"
            if spec.mask_binarize:
                mask_chain += f",geq=lum='if(gte(lum(X,Y),{spec.mask_threshold}),255,0)'"
            mask_chain += ",negate"
            alpha_multiplier = spec.alpha_strength * opacity_factor
            if abs(alpha_multiplier - 1.0) > 0.001:
                mask_chain += f",lut=y='clip(val*{alpha_multiplier:.4f},0,255)'"
            mask_chain += "[alpha0];"

            fc = (
                bg
                + f"{video_in(spectrum_index)}scale={spec.width}:{spec.height},format=rgba[spec0];"
                + mask_chain
                + "[spec0][alpha0]alphamerge[speca0];"
                + optional_flip_chain("[speca0]", spec, "[speca]")
                + f"[bg][speca]overlay={spec.x}:{spec.y}:shortest=0[with_spec];"
                + f"[with_spec]{sub_filter}[with_sub];"
                + finish("[with_sub]")
            )
            return fc

    if mode == "black_colorkey":
        fc = (
            bg
            + f"{video_in(spectrum_index)}scale={spec.width}:{spec.height},format=rgba,"
            + f"colorkey=0x000000:{spec.black_similarity:.4f}:{spec.black_blend:.4f}"
            + rgba_alpha_multiplier_filter(opacity_factor)
            + "[speca0];"
            + optional_flip_chain("[speca0]", spec, "[speca]")
            + f"[bg][speca]overlay={spec.x}:{spec.y}:shortest=0[with_spec];"
            + f"[with_spec]{sub_filter}[with_sub];"
            + finish("[with_sub]")
        )
        return fc

    if mask_index is None:
        # Darken/lighten needs a mask. Fall back to black colorkey instead of failing.
        fc = (
            bg
            + f"{video_in(spectrum_index)}scale={spec.width}:{spec.height},format=rgba,"
            + f"colorkey=0x000000:{spec.black_similarity:.4f}:{spec.black_blend:.4f}"
            + rgba_alpha_multiplier_filter(opacity_factor)
            + "[speca0];"
            + optional_flip_chain("[speca0]", spec, "[speca]")
            + f"[bg][speca]overlay={spec.x}:{spec.y}:shortest=0[with_spec];"
            + f"[with_spec]{sub_filter}[with_sub];"
            + finish("[with_sub]")
        )
        return fc

    dark_bg = bg
    bg_label = "bg"
    result_label = "with_spec"
    if opacity_factor < 0.999:
        dark_bg += "[bg]split=2[bg_main][bg_ref];"
        bg_label = "bg_main"
        result_label = "with_spec_op"

    fc = (
        dark_bg
        + f"{video_in(spectrum_index)}scale={spec.width}:{spec.height},format=rgb24[spec_s0];"
        + f"{video_in(mask_index)}scale={spec.width}:{spec.height},format=rgb24[mask_s0];"
        + optional_flip_chain("[spec_s0]", spec, "[spec_s]")
        + optional_flip_chain("[mask_s0]", spec, "[mask_s]")
        + f"color=c=white:s={out.width}x{out.height}:r={out.fps},format=rgb24[white];"
        + f"color=c=black:s={out.width}x{out.height}:r={out.fps},format=rgb24[black];"
        + f"[white][mask_s]overlay={spec.x}:{spec.y}:shortest=0[mask_full];"
        + f"[black][spec_s]overlay={spec.x}:{spec.y}:shortest=0[spec_full];"
        + f"[mask_full][{bg_label}]blend=all_mode=darken[cut];"
        + "[spec_full][cut]blend=all_mode=lighten[with_spec];"
    )
    if opacity_factor < 0.999:
        fc += f"[with_spec][bg_ref]blend=all_mode=normal:all_opacity={opacity_factor:.4f}[with_spec_op];"
    fc += (
        f"[{result_label}]{sub_filter}[with_sub];"
        + finish("[with_sub]")
    )
    return fc


def build_filter_complex(settings: AppSettings, ass_path: str, duration_sec: float | None = None) -> str:
    mode = effective_compose_mode(settings)
    spectrum_index = 2 if mode is not None else None
    mask_index = 3 if mode in ("mask_alpha", "darken_lighten_experimental") else None
    return build_visual_filter_complex(
        settings,
        ass_path,
        spectrum_index=spectrum_index,
        mask_index=mask_index,
        out_label="outv",
        duration_sec=duration_sec,
    )

def build_ffmpeg_command(settings: AppSettings, ass_path: str) -> list[str]:
    ffmpeg = find_tool("ffmpeg")
    files = settings.files
    out = settings.output
    mode = effective_compose_mode(settings)
    audio_duration = probe_media_duration(files.audio)
    duration_arg = format_duration_seconds(audio_duration)
    background_args: list[str]
    background_chain: str | None = None
    if is_slideshow_enabled(settings):
        background_args, background_chain, background_input_count = build_slideshow_background_inputs_and_chain(
            settings,
            0,
            int(round(audio_duration * 1000)),
        )
    else:
        background_args = [
            "-loop", "1",
            "-framerate", str(out.fps),
            "-i", files.background,
        ]
        background_input_count = 1
    audio_index = background_input_count
    spectrum_index = audio_index + 1 if mode is not None else None
    mask_index = audio_index + 2 if mode in ("mask_alpha", "darken_lighten_experimental") else None
    fc = build_visual_filter_complex(
        settings,
        ass_path,
        spectrum_index=spectrum_index,
        mask_index=mask_index,
        out_label="outv",
        duration_sec=audio_duration,
        background_chain=background_chain,
    )

    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
    ] + background_args + ["-i", files.audio]
    if mode is not None:
        cmd += ["-i", files.spectrum_color]
    if mode in ("mask_alpha", "darken_lighten_experimental"):
        cmd += ["-i", files.spectrum_mask]

    cmd += [
        "-filter_complex", fc,
        "-map", "[outv]",
        "-map", f"{audio_index}:a:0",
        "-t", duration_arg,
        "-af", f"atrim=duration={duration_arg},asetpts=PTS-STARTPTS",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", out.preset,
    ]
    if out.use_stillimage_tune:
        cmd += ["-tune", "stillimage"]
    cmd += [
        "-crf", str(out.crf),
    ]
    if out.video_bitrate.strip():
        cmd += ["-maxrate", out.video_bitrate.strip(), "-bufsize", out.video_bitrate.strip()]
    cmd += [
        "-c:a", "aac",
        "-b:a", out.audio_bitrate,
        "-movflags", "+faststart",
        files.output,
    ]
    return cmd




def build_preview_png_command(settings: AppSettings, ass_path: str, preview_path: str, preview_sec: float) -> list[str]:
    ffmpeg = find_tool("ffmpeg")
    files = settings.files
    mode = effective_compose_mode(settings)
    # Generate a reasonably large still preview. The GUI scales it down for the side preview
    # and shows it larger in a dialog after generation.
    pw, ph = fit_size(settings.output.width, settings.output.height, 1280, 720)
    if settings.output.height > settings.output.width:
        pw, ph = fit_size(settings.output.width, settings.output.height, 720, 1280)
    if is_slideshow_enabled(settings):
        background_args, background_chain, background_input_count = build_slideshow_background_inputs_and_chain(
            settings,
            int(round(preview_sec * 1000)),
            1000,
        )
    else:
        background_args = [
            "-loop", "1",
            "-framerate", str(settings.output.fps),
            "-i", files.background,
        ]
        background_chain = None
        background_input_count = 1
    spectrum_index = background_input_count if mode is not None else None
    mask_index = background_input_count + 1 if mode in ("mask_alpha", "darken_lighten_experimental") else None
    fc = build_visual_filter_complex(
        settings,
        ass_path,
        spectrum_index=spectrum_index,
        mask_index=mask_index,
        out_label="previewv",
        final_scale=(pw, ph),
        reset_overlay_pts=True,
        background_chain=background_chain,
    )
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
    ] + background_args
    if mode is not None:
        cmd += ["-ss", f"{preview_sec:.3f}", "-i", files.spectrum_color]
    if mode in ("mask_alpha", "darken_lighten_experimental"):
        cmd += ["-ss", f"{preview_sec:.3f}", "-i", files.spectrum_mask]
    cmd += [
        "-filter_complex", fc,
        "-map", "[previewv]",
        "-frames:v", "1",
        preview_path,
    ]
    return cmd


def build_preview_video_command(settings: AppSettings, ass_path: str, preview_path: str, start_sec: float, duration_sec: float) -> list[str]:
    ffmpeg = find_tool("ffmpeg")
    files = settings.files
    mode = effective_compose_mode(settings)
    pw, ph = fit_size(settings.output.width, settings.output.height, 960, 540)
    # For vertical output, fit_size naturally returns e.g. 304x540 when max is 960x540.
    # Use a taller box for vertical formats to preserve usable preview size.
    if settings.output.height > settings.output.width:
        pw, ph = fit_size(settings.output.width, settings.output.height, 540, 960)
    start_ms = int(round(start_sec * 1000))
    duration_ms = int(round(duration_sec * 1000))
    if is_slideshow_enabled(settings):
        background_args, background_chain, background_input_count = build_slideshow_background_inputs_and_chain(
            settings,
            start_ms,
            duration_ms,
        )
    else:
        background_args = [
            "-loop", "1",
            "-framerate", str(settings.output.fps),
            "-t", f"{duration_sec:.3f}",
            "-i", files.background,
        ]
        background_chain = None
        background_input_count = 1
    audio_index = background_input_count
    spectrum_index = audio_index + 1 if mode is not None else None
    mask_index = audio_index + 2 if mode in ("mask_alpha", "darken_lighten_experimental") else None
    fc = build_visual_filter_complex(
        settings,
        ass_path,
        spectrum_index=spectrum_index,
        mask_index=mask_index,
        out_label="previewv",
        final_scale=(pw, ph),
        reset_overlay_pts=True,
        background_chain=background_chain,
    )
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
    ] + background_args + [
        "-ss", f"{start_sec:.3f}",
        "-t", f"{duration_sec:.3f}",
        "-i", files.audio,
    ]
    if mode is not None:
        cmd += ["-ss", f"{start_sec:.3f}", "-t", f"{duration_sec:.3f}", "-i", files.spectrum_color]
    if mode in ("mask_alpha", "darken_lighten_experimental"):
        cmd += ["-ss", f"{start_sec:.3f}", "-t", f"{duration_sec:.3f}", "-i", files.spectrum_mask]
    cmd += [
        "-filter_complex", fc,
        "-map", "[previewv]",
        "-map", f"{audio_index}:a:0",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-crf", "30",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        "-shortest",
        preview_path,
    ]
    return cmd


def validate_settings(settings: AppSettings) -> None:
    files = settings.files
    required_inputs = {
        "背景画像": files.background,
        "音源": files.audio,
    }
    if is_slideshow_enabled(settings):
        background_key = next(iter(required_inputs), None)
        if background_key is not None:
            required_inputs.pop(background_key, None)

    missing = [name for name, path in required_inputs.items() if not path or not Path(path).exists()]
    if missing:
        raise FileNotFoundError("必要な入力ファイルが見つかりません: " + ", ".join(missing))

    if is_slideshow_enabled(settings):
        bad_times = [
            scene.scene_id or str(index + 1)
            for index, scene in enumerate(settings.background.scenes)
            if scene.start_ms < 0
        ]
        if bad_times:
            raise ValueError("Invalid slideshow start time: " + ", ".join(bad_times))
        bad_scenes = [
            scene.scene_id or str(index + 1)
            for index, scene in enumerate(settings.background.scenes)
            if scene.path and not Path(scene.path).exists()
        ]
        if bad_scenes:
            raise FileNotFoundError("Slideshow image file not found: " + ", ".join(bad_scenes))

    # Optional files are validated only when specified.
    optional_inputs = {
        "SRT字幕": files.srt,
        "カラースペアナ動画": files.spectrum_color,
        "マスク動画": files.spectrum_mask,
    }
    bad_optional = [name for name, path in optional_inputs.items() if path and not Path(path).exists()]
    if bad_optional:
        raise FileNotFoundError("指定された任意ファイルが見つかりません: " + ", ".join(bad_optional))

    if not files.output:
        files.output = default_output_path_from_audio(files.audio)
    files.output = normalize_output_path(files.output)
    if not files.output:
        raise ValueError("出力MP4ファイル名を指定してください。")

    output_parent = Path(files.output).expanduser().resolve().parent
    if not output_parent.exists():
        raise FileNotFoundError(f"出力先フォルダが見つかりません: {output_parent}")

    # Final render output must not overwrite an existing file. Preview files are handled separately.
    files.output = unique_output_path(files.output)

    if settings.output.width < OUTPUT_MIN_WIDTH or settings.output.height < OUTPUT_MIN_HEIGHT:
        raise ValueError(f"出力解像度は最低 {OUTPUT_MIN_WIDTH}x{OUTPUT_MIN_HEIGHT} が必要です。")
    if not settings.output.background_native_size:
        if settings.output.width % 2:
            settings.output.width -= 1
        if settings.output.height % 2:
            settings.output.height -= 1
        settings.output.width = max(OUTPUT_MIN_WIDTH, settings.output.width)
        settings.output.height = max(OUTPUT_MIN_HEIGHT, settings.output.height)
    if settings.spectrum.width <= 0 or settings.spectrum.height <= 0:
        raise ValueError("スペアナサイズが不正です。")
    if settings.output.fps <= 0:
        raise ValueError("FPSが不正です。")


class App(Tk):
    def __init__(self, handoff_path: Path | None = None) -> None:
        super().__init__()
        ensure_dirs()
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry("1040x760")
        self.minsize(900, 650)
        self.render_thread: threading.Thread | None = None
        self.preview_thread: threading.Thread | None = None
        self.output_auto_generated = False
        self.title_auto_generated = False
        self.srt_items: list[tuple[int, int, str]] = []
        self.slideshow_scenes: list[SlideshowScene] = []
        self.preview_photo = None
        self.ui_thread_id = threading.get_ident()
        self._pane_configure_bound = False
        self._layout_resolution: tuple[int, int] | None = None

        self.vars = self._create_vars()
        self.slideshow_row_vars: list[dict[str, StringVar]] = []
        self.slideshow_thumbnails: dict[int, object] = {}
        self._build_ui()
        self._apply_initial_system_presets()
        self._update_resolution_from_preset()
        self._update_quality_from_preset()
        self._update_mask_state()
        self._schedule_preview_redraw()
        self.after_idle(lambda path=handoff_path: self._load_startup_handoff(path))

    def _create_vars(self) -> dict[str, object]:
        return {
            "language": StringVar(value="ja"),
            "language_label": StringVar(value=LANGUAGES["ja"]),
            "background": StringVar(),
            "background_mode": StringVar(value="single"),
            "slideshow_enabled": BooleanVar(value=False),
            "slideshow_fade_transition": BooleanVar(value=False),
            "slideshow_image_count": IntVar(value=2),
            "timesheet": StringVar(),
            "audio": StringVar(),
            "srt": StringVar(),
            "spectrum_color": StringVar(),
            "spectrum_mask": StringVar(),
            "output": StringVar(),
            "font_name": StringVar(value="Yu Gothic"),
            "font_size": IntVar(value=54),
            "bold": BooleanVar(value=False),
            "italic": BooleanVar(value=False),
            "text_color": StringVar(value="#FFFFFF"),
            "outline_color": StringVar(value="#000000"),
            "outline_width": IntVar(value=4),
            "shadow": IntVar(value=2),
            "alignment_label": StringVar(value="下中央"),
            "bottom_margin": IntVar(value=80),
            "custom_x": IntVar(value=960),
            "custom_y": IntVar(value=930),
            "title_enabled": BooleanVar(value=True),
            "title_text": StringVar(),
            "title_font_name": StringVar(value="Yu Gothic"),
            "title_font_size": IntVar(value=72),
            "title_bold": BooleanVar(value=False),
            "title_italic": BooleanVar(value=False),
            "title_text_color": StringVar(value="#FFFFFF"),
            "title_outline_color": StringVar(value="#000000"),
            "title_outline_width": IntVar(value=3),
            "title_shadow": IntVar(value=1),
            "title_alignment_label": StringVar(value="左上"),
            "title_margin_x": IntVar(value=60),
            "title_margin_y": IntVar(value=40),
            "title_custom_x": IntVar(value=60),
            "title_custom_y": IntVar(value=60),
            "spec_x": IntVar(value=100),
            "spec_y": IntVar(value=820),
            "spec_w": IntVar(value=600),
            "spec_h": IntVar(value=180),
            "spec_opacity": IntVar(value=0),
            "flip_h": BooleanVar(value=False),
            "flip_v": BooleanVar(value=False),
            "compose_mode": StringVar(value="mask_alpha"),
            "black_similarity": DoubleVar(value=0.03),
            "black_blend": DoubleVar(value=0.02),
            "mask_binarize": BooleanVar(value=False),
            "mask_threshold": IntVar(value=128),
            "alpha_strength": DoubleVar(value=1.0),
            "resolution_preset": StringVar(value="1920x1080"),
            "out_w": IntVar(value=1920),
            "out_h": IntVar(value=1080),
            "fps": IntVar(value=30),
            "quality_preset": StringVar(value="High quality / CRF 20"),
            "crf": IntVar(value=20),
            "video_bitrate": StringVar(),
            "audio_bitrate": StringVar(value="192k"),
            "encoder_preset": StringVar(value="medium"),
            "use_stillimage_tune": BooleanVar(value=False),
            "preview_time": DoubleVar(value=0.0),
            "preview_duration": IntVar(value=5),
            "layout_preset": StringVar(),
            "output_preset": StringVar(),
        }

    def t(self, key: str) -> str:
        lang = self.vars.get("language")
        lang_key = lang.get() if lang is not None else "ja"
        return TRANSLATIONS.get(lang_key, TRANSLATIONS["ja"]).get(key, key)

    def tip_text(self, key: str) -> str:
        lang = self.vars.get("language")
        lang_key = lang.get() if lang is not None else "ja"
        value = TOOLTIPS.get(key, {})
        return value.get(lang_key) or value.get("ja") or ""

    def add_tip(self, widget, key: str):
        try:
            Tooltip(widget, lambda k=key: self.tip_text(k))
        except Exception:
            pass
        return widget

    def _on_language_changed(self, _event=None) -> None:
        label = self.vars["language_label"].get()
        self.vars["language"].set(LANGUAGE_LABEL_TO_KEY.get(label, "ja"))
        self._build_ui(rebuild=True)
        self._load_srt_items(show_message=False)
        self._update_color_buttons()
        self._update_dynamic_scale_ranges()
        self._draw_preview()

    def _build_ui(self, rebuild: bool = False) -> None:
        old_log = ""
        old_sash_x: int | None = None
        if rebuild and hasattr(self, "log"):
            try:
                old_log = self.log.get("1.0", END)
            except Exception:
                old_log = ""
        if rebuild and hasattr(self, "main_paned"):
            try:
                self.update_idletasks()
                old_sash_x = int(self.main_paned.sash_coord(0)[0])
            except Exception:
                old_sash_x = None
        if hasattr(self, "main_container"):
            self.main_container.destroy()
        self.color_buttons = {}
        self.scale_controls = {}
        root = Frame(self)
        self.main_container = root
        root.pack(fill="both", expand=True, padx=8, pady=8)

        self.main_paned = PanedWindow(root, orient="horizontal", sashrelief="raised", sashwidth=6, bd=0)
        self.main_paned.pack(fill="both", expand=True)

        left = Frame(self.main_paned)
        right = Frame(self.main_paned)
        self.left_pane = left
        self.right_pane = right
        self.main_paned.add(left, minsize=420)
        self.main_paned.add(right, minsize=420)
        if rebuild and old_sash_x is not None:
            self._schedule_pane_sash_restore(old_sash_x)
        else:
            self.after_idle(self._set_initial_pane_sizes)
        if not self._pane_configure_bound:
            self.bind("<Configure>", self._enforce_pane_min_width, add="+")
            self._pane_configure_bound = True

        self.notebook = ttk.Notebook(left)
        self.notebook.pack(fill="both", expand=True)

        self._build_files_tab()
        self._build_title_tab()
        self._build_spectrum_tab()
        self._build_subtitle_tab()
        self._build_srt_tab()
        self._build_slideshow_tab()
        self._build_output_tab()

        self.preview = Canvas(right, bg="#202020", width=420, height=270, highlightthickness=1, highlightbackground="#666")
        self.preview.pack(fill="x")

        pv = Frame(right)
        pv.pack(fill="x", padx=4, pady=(4, 8))
        quick_btn = Button(pv, text=self.t("quick_preview"), command=self._draw_preview)
        quick_btn.grid(row=0, column=0, columnspan=3, sticky="ew", pady=2)
        self.add_tip(quick_btn, "quick_preview")
        time_lbl = Label(pv, text=self.t("time_sec"))
        time_lbl.grid(row=1, column=0, sticky="w")
        time_ent = Entry(pv, textvariable=self.vars["preview_time"], width=8)
        time_ent.grid(row=1, column=1, sticky="w", padx=4)
        self.add_tip(time_lbl, "preview_time")
        self.add_tip(time_ent, "preview_time")
        still_btn = Button(pv, text=self.t("still_preview"), command=self.start_preview_png)
        still_btn.grid(row=1, column=2, sticky="ew")
        self.add_tip(still_btn, "still_preview")
        dur_lbl = Label(pv, text=self.t("movie_duration"))
        dur_lbl.grid(row=2, column=0, sticky="w")
        dur_cb = ttk.Combobox(pv, textvariable=self.vars["preview_duration"], values=[3, 5, 10], width=5, state="readonly")
        dur_cb.grid(row=2, column=1, sticky="w", padx=4)
        self.add_tip(dur_lbl, "preview_duration")
        self.add_tip(dur_cb, "preview_duration")
        movie_btn = Button(pv, text=self.t("movie_preview"), command=self.start_preview_video)
        movie_btn.grid(row=2, column=2, sticky="ew")
        self.add_tip(movie_btn, "movie_preview")
        pv.columnconfigure(2, weight=1)

        show_cmd_btn = Button(right, text=self.t("show_command"), command=self.show_command)
        show_cmd_btn.pack(fill="x", padx=4, pady=(8, 2))
        self.add_tip(show_cmd_btn, "show_command")
        render_btn = Button(right, text=self.t("render_start"), command=self.start_render)
        render_btn.pack(fill="x", padx=4, pady=(8, 2))
        self.add_tip(render_btn, "render_start")
        open_output_btn = Button(right, text=self.t("open_output_dir"), command=self.open_output_dir)
        open_output_btn.pack(fill="x", padx=4, pady=2)
        self.add_tip(open_output_btn, "open_output_dir")

        Label(right, text=self.t("log")).pack(anchor="w", padx=4, pady=(10, 2))
        self.log = Text(right, height=20, wrap="word")
        self.log.pack(fill="both", expand=True, padx=4)
        if old_log:
            self.log.insert(END, old_log)

    def _schedule_pane_sash_restore(self, sash_x: int) -> None:
        self.after_idle(lambda x=sash_x: self._restore_pane_sash(x))
        for delay_ms in (20, 80, 200):
            self.after(delay_ms, lambda x=sash_x: self._restore_pane_sash(x))

    def _restore_pane_sash(self, sash_x: int) -> None:
        try:
            self.update_idletasks()
            total = int(self.main_paned.winfo_width())
            if total <= 10:
                total = int(self.winfo_width()) - 16
            min_left = 420
            min_right = 360
            x = min(max(min_left, sash_x), max(min_left, total - min_right))
            self.main_paned.sash_place(0, x, 0)
        except Exception:
            pass

    def _set_initial_pane_sizes(self) -> None:
        """Set initial left/right pane ratio to roughly 1:1."""
        try:
            total = int(self.main_paned.winfo_width())
            if total <= 10:
                total = int(self.winfo_width()) - 16
            sash_x = max(420, total // 2)
            # Keep the right pane from becoming too small even at startup.
            if total - sash_x < 420:
                sash_x = max(420, total - 420)
            self.main_paned.sash_place(0, sash_x, 0)
        except Exception:
            pass

    def _enforce_pane_min_width(self, _event=None) -> None:
        """Do not continuously auto-resize panes, but rescue the right pane if it is too small."""
        try:
            if not hasattr(self, "main_paned"):
                return
            total = int(self.main_paned.winfo_width())
            if total <= 10:
                return
            min_right = 360
            current = self.main_paned.sash_coord(0)[0]
            if total - current < min_right:
                self.main_paned.sash_place(0, max(420, total - min_right), 0)
        except Exception:
            pass

    def _row(self, parent: Frame, label: str, var: StringVar, browse_cmd, row: int, tip_key: str | None = None) -> None:
        lbl = Label(parent, text=label, width=18, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=4, pady=4)
        ent = Entry(parent, textvariable=var)
        ent.grid(row=row, column=1, sticky="ew", padx=4, pady=4)
        btn = Button(parent, text=self.t("select"), command=browse_cmd)
        btn.grid(row=row, column=2, padx=4, pady=4)
        if tip_key:
            self.add_tip(lbl, tip_key)
            self.add_tip(ent, tip_key)
            self.add_tip(btn, tip_key)

    def _ensure_slideshow_row_vars(self, count: int | None = None) -> None:
        if count is None:
            count = int(self.vars["slideshow_image_count"].get())
        count = max(2, min(20, int(count)))
        while len(self.slideshow_row_vars) < count:
            index = len(self.slideshow_row_vars)
            self.slideshow_row_vars.append({
                "start": StringVar(value="00:00,000" if index == 0 else ""),
                "title": StringVar(),
                "path": StringVar(),
            })
        if len(self.slideshow_row_vars) > count:
            self.slideshow_row_vars = self.slideshow_row_vars[:count]
        if self.slideshow_row_vars:
            self.slideshow_row_vars[0]["start"].set("00:00,000")

    def _build_slideshow_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_slideshow"))
        f.columnconfigure(0, weight=1)
        f.rowconfigure(2, weight=1)

        top = Frame(f)
        top.grid(row=0, column=0, sticky="ew", padx=8, pady=8)
        top.columnconfigure(0, weight=1)

        chk = ttk.Checkbutton(
            top,
            text=self.t("slideshow_enabled"),
            variable=self.vars["slideshow_enabled"],
            command=self._on_slideshow_enabled_changed,
        )
        chk.grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.add_tip(chk, "slideshow_enabled")
        load_btn = Button(top, text=self.t("slideshow_load_timesheet"), command=self.pick_timesheet)
        load_btn.grid(row=1, column=0, sticky="w", pady=(0, 6))
        self.add_tip(load_btn, "slideshow_load_timesheet")
        count_label = Label(top, text=self.t("slideshow_image_count"), anchor="w")
        count_label.grid(row=2, column=0, sticky="w")
        self.add_tip(count_label, "slideshow_image_count")
        count_cb = ttk.Combobox(
            top,
            textvariable=self.vars["slideshow_image_count"],
            values=list(range(2, 21)),
            state="readonly",
            width=5,
        )
        count_cb.grid(row=3, column=0, sticky="w", pady=(0, 6))
        count_cb.bind("<<ComboboxSelected>>", lambda _e: self._on_slideshow_count_changed())
        self.add_tip(count_cb, "slideshow_image_count")
        fade_chk = ttk.Checkbutton(
            top,
            text=self.t("slideshow_fade_transition"),
            variable=self.vars["slideshow_fade_transition"],
            command=self._draw_preview,
        )
        fade_chk.grid(row=4, column=0, sticky="w", pady=(0, 6))
        self.add_tip(fade_chk, "slideshow_fade_transition")
        timesheet_label = Label(top, text=self.t("slideshow_timesheet"), anchor="w")
        timesheet_label.grid(row=5, column=0, sticky="w")
        self.add_tip(timesheet_label, "slideshow_timesheet")
        timesheet_entry = Entry(top, textvariable=self.vars["timesheet"])
        timesheet_entry.grid(row=6, column=0, sticky="ew", pady=(0, 4))
        self.add_tip(timesheet_entry, "slideshow_timesheet")

        note_label = Label(f, text=self.t("slideshow_note"), anchor="w", justify="left", wraplength=760, foreground="#555555")
        note_label.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 6))
        self.add_tip(note_label, "slideshow_enabled")

        canvas = Canvas(f, highlightthickness=0)
        scrollbar = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        rows = Frame(canvas)
        rows.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        rows_window = canvas.create_window((0, 0), window=rows, anchor="nw")
        canvas.bind("<Configure>", lambda e, item=rows_window: canvas.itemconfigure(item, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=2, column=0, sticky="nsew", padx=(8, 0), pady=(0, 8))
        scrollbar.grid(row=2, column=1, sticky="ns", pady=(0, 8))
        self.slideshow_rows_frame = rows
        self._rebuild_slideshow_rows()

    def _on_slideshow_enabled_changed(self) -> None:
        self.vars["background_mode"].set("slideshow" if bool(self.vars["slideshow_enabled"].get()) else "single")
        self._draw_preview()

    def _on_slideshow_count_changed(self) -> None:
        self._ensure_slideshow_row_vars()
        self._rebuild_slideshow_rows()
        self._draw_preview()

    def jump_to_slideshow_cut(self, index: int) -> None:
        if not (0 <= index < len(self.slideshow_row_vars)):
            return
        try:
            start_ms = parse_timesheet_time(self.slideshow_row_vars[index]["start"].get().strip())
        except Exception as exc:
            messagebox.showerror("Timesheet error", str(exc))
            return
        self.vars["preview_time"].set(preview_time_for_slideshow_cut(start_ms))
        self._draw_preview()

    def _rebuild_slideshow_rows(self) -> None:
        rows = getattr(self, "slideshow_rows_frame", None)
        if rows is None:
            return
        for child in rows.winfo_children():
            child.destroy()
        self._ensure_slideshow_row_vars()
        rows.columnconfigure(0, weight=1)
        count = int(self.vars["slideshow_image_count"].get())
        for index in range(count):
            row_vars = self.slideshow_row_vars[index]
            scene_id = f"{index + 1:02d}"
            scene = ttk.LabelFrame(rows, text=f"{scene_id}")
            scene.grid(row=index, column=0, sticky="ew", padx=4, pady=(0, 12))
            scene.columnconfigure(0, weight=1)

            number_label = Label(scene, text=self.t("slideshow_scene_number"), anchor="w")
            number_label.grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
            self.add_tip(number_label, "slideshow_scene_number")
            number_value = Label(scene, text=scene_id, anchor="w")
            number_value.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 6))
            self.add_tip(number_value, "slideshow_scene_number")

            start_label = Label(scene, text=self.t("slideshow_start_time"), anchor="w")
            start_label.grid(row=2, column=0, sticky="w", padx=8, pady=(0, 2))
            self.add_tip(start_label, "slideshow_start_time")
            start_row = Frame(scene)
            start_row.grid(row=3, column=0, sticky="w", padx=8, pady=(0, 6))
            start_entry = Entry(start_row, textvariable=row_vars["start"], width=14)
            if index == 0:
                row_vars["start"].set("00:00,000")
                start_entry.configure(state="readonly")
            start_entry.grid(row=0, column=0, sticky="w")
            start_entry.bind("<FocusOut>", lambda _e: self._draw_preview())
            self.add_tip(start_entry, "slideshow_start_time")
            if index > 0:
                jump_btn = Button(
                    start_row,
                    text=self.t("slideshow_jump_to_cut"),
                    command=lambda i=index: self.jump_to_slideshow_cut(i),
                )
                jump_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))
                self.add_tip(jump_btn, "slideshow_jump_to_cut")

            title_label = Label(scene, text=self.t("slideshow_title"), anchor="w")
            title_label.grid(row=4, column=0, sticky="w", padx=8, pady=(0, 2))
            self.add_tip(title_label, "slideshow_title")
            title_entry = Entry(scene, textvariable=row_vars["title"])
            title_entry.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 6))
            title_entry.bind("<FocusOut>", lambda _e: self._draw_preview())
            self.add_tip(title_entry, "slideshow_title")

            image_label = Label(scene, text=self.t("slideshow_image_file"), anchor="w")
            image_label.grid(row=6, column=0, sticky="w", padx=8, pady=(0, 2))
            self.add_tip(image_label, "slideshow_image_file")
            image_row = Frame(scene)
            image_row.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 8))
            image_row.columnconfigure(0, weight=1)
            path_entry = Entry(image_row, textvariable=row_vars["path"])
            path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
            self.add_tip(path_entry, "slideshow_image_file")
            select_btn = Button(image_row, text=self.t("select"), command=lambda i=index: self.pick_slideshow_image(i))
            select_btn.grid(row=0, column=1, sticky="e")
            self.add_tip(select_btn, "slideshow_select_image")

            thumb_label = Label(scene, text=self.t("slideshow_thumbnail"), anchor="w")
            thumb_label.grid(row=8, column=0, sticky="w", padx=8, pady=(0, 2))
            self.add_tip(thumb_label, "slideshow_thumbnail")
            thumb_box = Frame(scene, width=220, height=128, borderwidth=1, relief="sunken", bg="#202020")
            thumb_box.grid(row=9, column=0, sticky="w", padx=8, pady=(0, 8))
            thumb_box.grid_propagate(False)
            thumb = Label(thumb_box, text="", anchor="center", bg="#202020")
            thumb.place(relx=0.5, rely=0.5, anchor="center")
            self.add_tip(thumb_box, "slideshow_thumbnail")
            self.add_tip(thumb, "slideshow_thumbnail")
            self._update_slideshow_thumbnail(index, thumb)

    def _sync_slideshow_scenes_from_rows(self) -> None:
        self._ensure_slideshow_row_vars()
        count = int(self.vars["slideshow_image_count"].get())
        scenes: list[SlideshowScene] = []
        for index in range(count):
            row_vars = self.slideshow_row_vars[index]
            start_text = "00:00,000" if index == 0 else row_vars["start"].get().strip()
            try:
                start_ms = parse_timesheet_time(start_text)
            except Exception:
                start_ms = -1
            scenes.append(SlideshowScene(
                scene_id=f"{index + 1:02d}",
                start_ms=start_ms,
                title=row_vars["title"].get(),
                path=row_vars["path"].get(),
            ))
        self.slideshow_scenes = scenes

    def _load_slideshow_scenes_to_rows(self) -> None:
        count = max(2, min(20, len(self.slideshow_scenes) or int(self.vars["slideshow_image_count"].get())))
        self.vars["slideshow_image_count"].set(count)
        self._ensure_slideshow_row_vars(count)
        for index, scene in enumerate(self.slideshow_scenes[:count]):
            self.slideshow_row_vars[index]["start"].set("00:00,000" if index == 0 else format_timesheet_time(scene.start_ms))
            self.slideshow_row_vars[index]["title"].set(scene.title)
            self.slideshow_row_vars[index]["path"].set(scene.path)
        for index in range(len(self.slideshow_scenes), count):
            self.slideshow_row_vars[index]["start"].set("00:00,000" if index == 0 else "")
            self.slideshow_row_vars[index]["title"].set("")
            self.slideshow_row_vars[index]["path"].set("")
        self._rebuild_slideshow_rows()

    def pick_timesheet(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Text", "*.txt *.tsv"), ("All", "*.*")])
        if not path:
            return
        try:
            scenes = parse_timesheet(path)
        except Exception as exc:
            messagebox.showerror("Timesheet error", str(exc))
            return
        count = max(2, min(20, len(scenes)))
        self.vars["timesheet"].set(path)
        self.vars["slideshow_enabled"].set(True)
        self.vars["background_mode"].set("slideshow")
        self.vars["slideshow_image_count"].set(count)
        self._ensure_slideshow_row_vars(count)
        for index in range(count):
            scene = scenes[index] if index < len(scenes) else SlideshowScene(scene_id=f"{index + 1:02d}")
            self.slideshow_row_vars[index]["start"].set("00:00,000" if index == 0 else format_timesheet_time(scene.start_ms))
            self.slideshow_row_vars[index]["title"].set(scene.title)
        self._sync_slideshow_scenes_from_rows()
        self._rebuild_slideshow_rows()
        self._draw_preview()

    def pick_slideshow_image(self, index: int) -> None:
        if not (0 <= index < len(self.slideshow_row_vars)):
            return
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All", "*.*")])
        if not path:
            return
        self.slideshow_row_vars[index]["path"].set(path)
        self._sync_slideshow_scenes_from_rows()
        self._rebuild_slideshow_rows()
        self._draw_preview()

    def _update_slideshow_thumbnail(self, index: int, label: Label) -> None:
        path = self.slideshow_row_vars[index]["path"].get().strip() if index < len(self.slideshow_row_vars) else ""
        if not path or not Path(path).exists() or Image is None or ImageTk is None:
            label.configure(image="", text=self.t("slideshow_no_image"), fg="#dddddd")
            return
        try:
            with Image.open(path) as im:
                im = im.convert("RGB")
                im.thumbnail((210, 118), Image.LANCZOS)
                photo = ImageTk.PhotoImage(im)
            self.slideshow_thumbnails[index] = photo
            label.configure(image=photo, text="")
        except Exception:
            label.configure(image="", text=self.t("slideshow_preview_error"), fg="#dddddd")

    def _available_fonts(self) -> list[str]:
        """Return a sorted list of system font family names for the font selector."""
        try:
            fonts = sorted(set(tkfont.families(self)))
        except Exception:
            fonts = []
        preferred = ["Yu Gothic", "Yu Gothic UI", "Meiryo", "MS Gothic", "Noto Sans JP", "Arial"]
        merged: list[str] = []
        for name in preferred + fonts:
            if name and name not in merged:
                merged.append(name)
        return merged

    def _background_reference_path(self) -> str:
        if bool(self.vars["slideshow_enabled"].get()):
            self._sync_slideshow_scenes_from_rows()
            for scene in self.slideshow_scenes:
                if scene.path:
                    return scene.path
            return ""
        return self.vars["background"].get().strip()

    def _color_button_text(self, key: str) -> str:
        value = self.vars[key].get()
        return value if value else self.t("choose_color")

    def _canvas_font(self, family_key: str, size: int, bold_key: str, italic_key: str):
        styles = []
        if bool(self.vars[bold_key].get()):
            styles.append("bold")
        if bool(self.vars[italic_key].get()):
            styles.append("italic")
        family = self.vars[family_key].get() or "Arial"
        if styles:
            return (family, size, " ".join(styles))
        return (family, size)

    def _choose_color(self, key: str) -> None:
        current = self.vars[key].get() or "#FFFFFF"
        _rgb, hex_value = colorchooser.askcolor(color=current, title=self.t("choose_color"))
        if hex_value:
            self.vars[key].set(hex_value.upper())
            self._update_color_buttons()
            self._draw_preview()

    def _update_color_buttons(self) -> None:
        for key, btn in getattr(self, "color_buttons", {}).items():
            value = self.vars[key].get() or "#FFFFFF"
            btn.configure(text=value)
            try:
                btn.configure(bg=value, activebackground=value)
                # Choose readable foreground for common bright/dark colors.
                clean = value.lstrip("#")
                if len(clean) == 6:
                    r, g, b = int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16)
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    btn.configure(fg="#000000" if lum > 160 else "#FFFFFF")
            except Exception:
                pass

    def _build_color_row(self, parent: Frame, row: int, label: str, key: str, tip_key: str | None = None) -> None:
        lbl = Label(parent, text=label, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=6, pady=5)
        ent = Entry(parent, textvariable=self.vars[key], width=12)
        ent.grid(row=row, column=1, sticky="w", padx=6, pady=5)
        btn = Button(parent, text=self._color_button_text(key), width=12, command=lambda k=key: self._choose_color(k))
        btn.grid(row=row, column=2, sticky="w", padx=6, pady=5)
        self.color_buttons[key] = btn
        if tip_key:
            self.add_tip(lbl, tip_key)
            self.add_tip(ent, tip_key)
            self.add_tip(btn, tip_key)

    def _build_scale_row(
        self,
        parent: Frame,
        row: int,
        label: str,
        key: str,
        from_: float,
        to: float,
        resolution: float = 1,
        spin_width: int = 8,
        tip_key: str | None = None,
    ) -> None:
        lbl = Label(parent, text=label, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=6, pady=5)
        sc = Scale(
            parent,
            variable=self.vars[key],
            from_=from_,
            to=to,
            orient="horizontal",
            resolution=resolution,
            showvalue=False,
            length=260,
            command=lambda _v, k=key: self._on_scale_value_changed(k, normalize_output=True),
        )
        sc.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        sp = Spinbox(
            parent,
            textvariable=self.vars[key],
            from_=from_,
            to=to,
            increment=resolution,
            width=spin_width,
            command=lambda k=key: self._on_scale_value_changed(k, normalize_output=True),
        )
        sp.grid(row=row, column=2, sticky="w", padx=6, pady=5)
        sp.bind("<KeyRelease>", lambda _e, k=key: self._on_scale_value_changed(k))
        sp.bind("<FocusOut>", lambda _e, k=key: self._on_scale_value_changed(k, normalize_output=True))
        self.scale_controls[key] = (sc, sp)
        if tip_key:
            self.add_tip(lbl, tip_key)
            self.add_tip(sc, tip_key)
            self.add_tip(sp, tip_key)
        parent.columnconfigure(1, weight=1)

    def _build_spectrum_position_row(
        self,
        parent: Frame,
        row: int,
        label: str,
        key: str,
        to: float,
        axis: str,
        tip_key: str | None = None,
    ) -> None:
        lbl = Label(parent, text=label, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=6, pady=5)
        sc = Scale(
            parent,
            variable=self.vars[key],
            from_=0,
            to=to,
            orient="horizontal",
            resolution=1,
            showvalue=False,
            length=200,
            command=lambda _v, k=key: self._on_scale_value_changed(k),
        )
        sc.grid(row=row, column=1, sticky="ew", padx=6, pady=5)
        sp = Spinbox(
            parent,
            textvariable=self.vars[key],
            from_=0,
            to=to,
            increment=1,
            width=8,
            command=lambda k=key: self._on_scale_value_changed(k),
        )
        sp.grid(row=row, column=2, sticky="w", padx=6, pady=5)
        sp.bind("<KeyRelease>", lambda _e, k=key: self._on_scale_value_changed(k))
        sp.bind("<FocusOut>", lambda _e, k=key: self._on_scale_value_changed(k))
        btn = Button(parent, text=self.t("center"), command=lambda a=axis: self._center_spectrum_axis(a))
        btn.grid(row=row, column=3, sticky="ew", padx=6, pady=5)
        self.scale_controls[key] = (sc, sp)
        if tip_key:
            self.add_tip(lbl, tip_key)
            self.add_tip(sc, tip_key)
            self.add_tip(sp, tip_key)
            self.add_tip(btn, "center_spectrum")
        parent.columnconfigure(1, weight=1)

    def _on_scale_value_changed(self, key: str, normalize_output: bool = False) -> None:
        if key in ("out_w", "out_h"):
            if normalize_output:
                self._normalize_output_resolution()
                self._sync_layout_to_current_resolution()
            self._draw_preview()
            return
        self._draw_preview()

    def _center_spectrum_axis(self, axis: str) -> None:
        if axis == "x":
            total = self._int_var_value("out_w", 1920)
            size = self._int_var_value("spec_w", 600)
            key = "spec_x"
        else:
            total = self._int_var_value("out_h", 1080)
            size = self._int_var_value("spec_h", 180)
            key = "spec_y"
        value = max(0, int(round((total - size) / 2)))
        self.vars[key].set(value)
        self._update_dynamic_scale_ranges()
        self._draw_preview()

    def _int_var_value(self, key: str, default: int) -> int:
        try:
            return int(float(self.vars[key].get()))
        except Exception:
            return default

    def _set_scale_range(self, key: str, from_: float, to: float, clamp: bool = True) -> None:
        controls = getattr(self, "scale_controls", {}).get(key)
        if not controls:
            return
        scale, spinbox = controls
        if to < from_:
            to = from_
        scale.configure(from_=from_, to=to)
        spinbox.configure(from_=from_, to=to)
        if not clamp:
            return
        var = self.vars[key]
        try:
            value = float(var.get())
        except Exception:
            value = from_
        clamped = min(max(value, from_), to)
        if clamped != value:
            if isinstance(var, DoubleVar) or isinstance(from_, float) or isinstance(to, float):
                var.set(clamped)
            else:
                var.set(int(clamped))

    def _normalize_output_resolution(self) -> None:
        if self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
            return
        for key in ("out_w", "out_h"):
            min_value = OUTPUT_MIN_WIDTH if key == "out_w" else OUTPUT_MIN_HEIGHT
            value = max(min_value, self._int_var_value(key, min_value))
            if value % 2:
                value -= 1
            self.vars[key].set(value)

    def _scale_int_setting(self, key: str, factor: float, min_value: int = 0, max_value: int | None = None) -> None:
        value = self._int_var_value(key, min_value)
        scaled = int(round(value * factor))
        if max_value is not None:
            scaled = min(scaled, max_value)
        self.vars[key].set(max(min_value, scaled))

    def _sync_layout_to_current_resolution(self) -> None:
        new_w = max(1, self._int_var_value("out_w", 1920))
        new_h = max(1, self._int_var_value("out_h", 1080))
        old = self._layout_resolution
        if old is None:
            self._layout_resolution = (new_w, new_h)
            self._update_dynamic_scale_ranges()
            return

        old_w, old_h = old
        if old_w <= 0 or old_h <= 0 or (old_w, old_h) == (new_w, new_h):
            self._layout_resolution = (new_w, new_h)
            self._update_dynamic_scale_ranges()
            return

        x_ratio = new_w / old_w
        y_ratio = new_h / old_h
        size_ratio = max(new_w, new_h) / max(old_w, old_h)

        for key in ("custom_x", "title_custom_x", "title_margin_x", "spec_x"):
            self._scale_int_setting(key, x_ratio, min_value=0)
        for key in ("custom_y", "title_custom_y", "title_margin_y", "bottom_margin", "spec_y"):
            self._scale_int_setting(key, y_ratio, min_value=0)

        self._scale_int_setting("spec_w", size_ratio, min_value=1)
        self._scale_int_setting("spec_h", size_ratio, min_value=1)
        self._scale_int_setting("font_size", size_ratio, min_value=12, max_value=120)
        self._scale_int_setting("title_font_size", size_ratio, min_value=12, max_value=120)
        self._scale_int_setting("outline_width", size_ratio, min_value=0, max_value=12)
        self._scale_int_setting("title_outline_width", size_ratio, min_value=0, max_value=12)
        self._scale_int_setting("shadow", size_ratio, min_value=0, max_value=10)
        self._scale_int_setting("title_shadow", size_ratio, min_value=0, max_value=10)

        self._layout_resolution = (new_w, new_h)
        self._update_dynamic_scale_ranges()

    def _is_output_size_usable(self, size: tuple[int, int] | None) -> bool:
        return bool(size and size[0] >= OUTPUT_MIN_WIDTH and size[1] >= OUTPUT_MIN_HEIGHT)

    def _preview_info_text(self, out_w: int, out_h: int) -> str:
        bg_size = get_image_size(self._background_reference_path())
        src = f"{bg_size[0]}x{bg_size[1]}" if bg_size else "不明"
        return f"出力: {out_w}x{out_h}  元画像: {src}"

    def _layout_size_base(self, data: dict | None = None) -> int:
        w = max(1, self._int_var_value("out_w", 1920))
        h = max(1, self._int_var_value("out_h", 1080))
        if isinstance(data, dict) and data.get("size_reference") != "long_edge":
            return max(1, min(w, h))
        return max(1, max(w, h))

    def _current_layout_preset_data(self) -> dict:
        w = max(1, self._int_var_value("out_w", 1920))
        h = max(1, self._int_var_value("out_h", 1080))
        base = self._layout_size_base({"size_reference": "long_edge"})
        return {
            "base_width": w,
            "base_height": h,
            "size_reference": "long_edge",
            "subtitle": {
                "font_name": self.vars["font_name"].get(),
                "font_size_rel": self._int_var_value("font_size", 54) / base,
                "bold": bool(self.vars["bold"].get()),
                "italic": bool(self.vars["italic"].get()),
                "text_color": self.vars["text_color"].get(),
                "outline_color": self.vars["outline_color"].get(),
                "outline_width_rel": self._int_var_value("outline_width", 4) / base,
                "shadow_rel": self._int_var_value("shadow", 2) / base,
                "alignment_label": self.vars["alignment_label"].get(),
                "bottom_margin_rel": self._int_var_value("bottom_margin", 80) / h,
                "custom_x_rel": self._int_var_value("custom_x", w // 2) / w,
                "custom_y_rel": self._int_var_value("custom_y", h // 2) / h,
            },
            "title": {
                "enabled": bool(self.vars["title_enabled"].get()),
                "font_name": self.vars["title_font_name"].get(),
                "font_size_rel": self._int_var_value("title_font_size", 72) / base,
                "bold": bool(self.vars["title_bold"].get()),
                "italic": bool(self.vars["title_italic"].get()),
                "text_color": self.vars["title_text_color"].get(),
                "outline_color": self.vars["title_outline_color"].get(),
                "outline_width_rel": self._int_var_value("title_outline_width", 3) / base,
                "shadow_rel": self._int_var_value("title_shadow", 1) / base,
                "alignment_label": self.vars["title_alignment_label"].get(),
                "margin_x_rel": self._int_var_value("title_margin_x", 60) / w,
                "margin_y_rel": self._int_var_value("title_margin_y", 40) / h,
                "custom_x_rel": self._int_var_value("title_custom_x", 60) / w,
                "custom_y_rel": self._int_var_value("title_custom_y", 60) / h,
            },
            "spectrum": {
                "x_rel": self._int_var_value("spec_x", 100) / w,
                "y_rel": self._int_var_value("spec_y", 820) / h,
                "width_rel": self._int_var_value("spec_w", 600) / w,
                "height_rel": self._int_var_value("spec_h", 180) / h,
                "opacity": self._int_var_value("spec_opacity", 0),
                "flip_horizontal": bool(self.vars["flip_h"].get()),
                "flip_vertical": bool(self.vars["flip_v"].get()),
            },
        }

    def _apply_layout_preset_data(self, data: dict) -> None:
        w = max(1, self._int_var_value("out_w", 1920))
        h = max(1, self._int_var_value("out_h", 1080))
        base = self._layout_size_base(data)

        sub = data.get("subtitle", {})
        self.vars["font_name"].set(sub.get("font_name", self.vars["font_name"].get()))
        self.vars["font_size"].set(max(12, min(120, int(round(float(sub.get("font_size_rel", 54 / 1080)) * base)))))
        self.vars["bold"].set(bool(sub.get("bold", self.vars["bold"].get())))
        self.vars["italic"].set(bool(sub.get("italic", self.vars["italic"].get())))
        self.vars["text_color"].set(sub.get("text_color", self.vars["text_color"].get()))
        self.vars["outline_color"].set(sub.get("outline_color", self.vars["outline_color"].get()))
        self.vars["outline_width"].set(max(0, min(12, int(round(float(sub.get("outline_width_rel", 4 / 1080)) * base)))))
        self.vars["shadow"].set(max(0, min(10, int(round(float(sub.get("shadow_rel", 2 / 1080)) * base)))))
        if sub.get("alignment_label") in ALIGNMENTS:
            self.vars["alignment_label"].set(sub["alignment_label"])
        self.vars["bottom_margin"].set(max(0, int(round(float(sub.get("bottom_margin_rel", 80 / 1080)) * h))))
        self.vars["custom_x"].set(max(0, int(round(float(sub.get("custom_x_rel", 0.5)) * w))))
        self.vars["custom_y"].set(max(0, int(round(float(sub.get("custom_y_rel", 930 / 1080)) * h))))

        title = data.get("title", {})
        self.vars["title_enabled"].set(bool(title.get("enabled", self.vars["title_enabled"].get())))
        self.vars["title_font_name"].set(title.get("font_name", self.vars["title_font_name"].get()))
        self.vars["title_font_size"].set(max(12, min(120, int(round(float(title.get("font_size_rel", 72 / 1080)) * base)))))
        self.vars["title_bold"].set(bool(title.get("bold", self.vars["title_bold"].get())))
        self.vars["title_italic"].set(bool(title.get("italic", self.vars["title_italic"].get())))
        self.vars["title_text_color"].set(title.get("text_color", self.vars["title_text_color"].get()))
        self.vars["title_outline_color"].set(title.get("outline_color", self.vars["title_outline_color"].get()))
        self.vars["title_outline_width"].set(max(0, min(12, int(round(float(title.get("outline_width_rel", 3 / 1080)) * base)))))
        self.vars["title_shadow"].set(max(0, min(10, int(round(float(title.get("shadow_rel", 1 / 1080)) * base)))))
        if title.get("alignment_label") in TITLE_ALIGNMENTS:
            self.vars["title_alignment_label"].set(title["alignment_label"])
        self.vars["title_margin_x"].set(max(0, int(round(float(title.get("margin_x_rel", 60 / 1920)) * w))))
        self.vars["title_margin_y"].set(max(0, int(round(float(title.get("margin_y_rel", 40 / 1080)) * h))))
        self.vars["title_custom_x"].set(max(0, int(round(float(title.get("custom_x_rel", 60 / 1920)) * w))))
        self.vars["title_custom_y"].set(max(0, int(round(float(title.get("custom_y_rel", 60 / 1080)) * h))))

        spec = data.get("spectrum", {})
        self.vars["spec_x"].set(max(0, int(round(float(spec.get("x_rel", 100 / 1920)) * w))))
        self.vars["spec_y"].set(max(0, int(round(float(spec.get("y_rel", 820 / 1080)) * h))))
        self.vars["spec_w"].set(max(1, int(round(float(spec.get("width_rel", 600 / 1920)) * w))))
        self.vars["spec_h"].set(max(1, int(round(float(spec.get("height_rel", 180 / 1080)) * h))))
        self.vars["spec_opacity"].set(max(0, min(100, int(spec.get("opacity", self.vars["spec_opacity"].get())))))
        self.vars["flip_h"].set(bool(spec.get("flip_horizontal", self.vars["flip_h"].get())))
        self.vars["flip_v"].set(bool(spec.get("flip_vertical", self.vars["flip_v"].get())))
        self._update_dynamic_scale_ranges()
        self._update_color_buttons()
        self._draw_preview()

    def _current_output_preset_data(self) -> dict:
        self._normalize_output_resolution()
        return {
            "resolution_preset": self.vars["resolution_preset"].get(),
            "quality_preset": self.vars["quality_preset"].get(),
            "output": asdict(OutputSettings(
                width=self._int_var_value("out_w", 1920),
                height=self._int_var_value("out_h", 1080),
                fps=self._int_var_value("fps", 30),
                crf=self._int_var_value("crf", 20),
                video_bitrate=self.vars["video_bitrate"].get(),
                audio_bitrate=self.vars["audio_bitrate"].get(),
                preset=self.vars["encoder_preset"].get(),
                use_stillimage_tune=bool(self.vars["use_stillimage_tune"].get()),
                background_native_size=(self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET),
            )),
        }

    def _apply_output_preset_data(self, data: dict) -> None:
        out = dataclass_from_dict(OutputSettings, data.get("output", {}))
        self.vars["out_w"].set(out.width)
        self.vars["out_h"].set(out.height)
        self.vars["fps"].set(out.fps)
        self.vars["crf"].set(out.crf)
        self.vars["video_bitrate"].set(out.video_bitrate)
        self.vars["audio_bitrate"].set(out.audio_bitrate)
        self.vars["encoder_preset"].set(out.preset)
        self.vars["use_stillimage_tune"].set(out.use_stillimage_tune)
        resolution_preset = data.get("resolution_preset")
        if resolution_preset in VIDEO_PRESETS:
            self.vars["resolution_preset"].set(resolution_preset)
        elif out.background_native_size:
            self.vars["resolution_preset"].set(BACKGROUND_SIZE_PRESET)
        else:
            self.vars["resolution_preset"].set("Custom")
        quality_preset = data.get("quality_preset")
        if quality_preset in QUALITY_PRESETS:
            self.vars["quality_preset"].set(quality_preset)
        else:
            self.vars["quality_preset"].set("Custom")
        if self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
            self._update_resolution_from_preset()
            return
        self._normalize_output_resolution()
        self._sync_layout_to_current_resolution()
        self._draw_preview()

    def _default_layout_preset_data(self) -> dict:
        return {
            "base_width": 1920,
            "base_height": 1080,
            "size_reference": "long_edge",
            "subtitle": {
                "font_name": "Yu Gothic",
                "font_size_rel": 54 / 1920,
                "bold": False,
                "italic": False,
                "text_color": "#FFFFFF",
                "outline_color": "#000000",
                "outline_width_rel": 4 / 1920,
                "shadow_rel": 2 / 1920,
                "alignment_label": "下中央",
                "bottom_margin_rel": 80 / 1080,
                "custom_x_rel": 960 / 1920,
                "custom_y_rel": 930 / 1080,
            },
            "title": {
                "enabled": True,
                "font_name": "Yu Gothic",
                "font_size_rel": 72 / 1920,
                "bold": False,
                "italic": False,
                "text_color": "#FFFFFF",
                "outline_color": "#000000",
                "outline_width_rel": 3 / 1920,
                "shadow_rel": 1 / 1920,
                "alignment_label": "左上",
                "margin_x_rel": 60 / 1920,
                "margin_y_rel": 40 / 1080,
                "custom_x_rel": 60 / 1920,
                "custom_y_rel": 60 / 1080,
            },
            "spectrum": {
                "x_rel": 100 / 1920,
                "y_rel": 820 / 1080,
                "width_rel": 600 / 1920,
                "height_rel": 180 / 1080,
                "opacity": 0,
                "flip_horizontal": False,
                "flip_vertical": False,
            },
        }

    def _system_presets(self, kind: str) -> dict[str, dict]:
        if kind == "layout":
            def layout_data(subtitle_y: float, spec_x: float, spec_y: float, spec_w: float, spec_h: float, opacity: int) -> dict:
                return {
                    "base_width": 1920,
                    "base_height": 1080,
                    "size_reference": "long_edge",
                    "subtitle": {
                        "font_name": "Yu Gothic",
                        "font_size_rel": 50 / 1920,
                        "bold": True,
                        "italic": False,
                        "text_color": "#FFFFFF",
                        "outline_color": "#000000",
                        "outline_width_rel": 3 / 1920,
                        "shadow_rel": 1 / 1920,
                        "alignment_label": SubtitleSettings().alignment_label,
                        "bottom_margin_rel": 120 / 1080,
                        "custom_x_rel": 0.5,
                        "custom_y_rel": subtitle_y,
                    },
                    "title": {
                        "enabled": True,
                        "font_name": "Yu Gothic",
                        "font_size_rel": 70 / 1920,
                        "bold": True,
                        "italic": False,
                        "text_color": "#FFFF80",
                        "outline_color": "#000000",
                        "outline_width_rel": 3 / 1920,
                        "shadow_rel": 0.0,
                        "alignment_label": TitleSettings().alignment_label,
                        "margin_x_rel": 60 / 1920,
                        "margin_y_rel": 40 / 1080,
                        "custom_x_rel": 60 / 1920,
                        "custom_y_rel": 60 / 1080,
                    },
                    "spectrum": {
                        "x_rel": spec_x,
                        "y_rel": spec_y,
                        "width_rel": spec_w,
                        "height_rel": spec_h,
                        "opacity": opacity,
                        "flip_horizontal": False,
                        "flip_vertical": False,
                    },
                }
            return {
                "Small Spectrum": layout_data(0.9157407407407407, 0.06510416666666667, 0.6666666666666666, 0.375, 0.18518518518518517, 0),
                "Center Spectrum": layout_data(0.8611111111111112, 0.34375, 0.5370370370370371, 0.375, 0.25925925925925924, 30),
                "Big Spectrum": layout_data(0.8611111111111112, 0.1, 0.2222222222222222, 0.8, 0.5555555555555556, 50),
            }
        return {
            "1080P High Quality": {
                "resolution_preset": "1920x1080",
                "quality_preset": "High quality / CRF 20",
                "output": asdict(OutputSettings(width=1920, height=1080, fps=30, crf=20, preset="medium")),
            },
            "720P Standard": {
                "resolution_preset": "1280x720",
                "quality_preset": "Standard / CRF 23",
                "output": asdict(OutputSettings(width=1280, height=720, fps=30, crf=23, preset="medium")),
            },
            "Fit to Image HQ": {
                "resolution_preset": BACKGROUND_SIZE_PRESET,
                "quality_preset": "Very high / CRF 18",
                "output": asdict(OutputSettings(width=1360, height=768, fps=30, crf=18, preset="slow", background_native_size=True)),
            },
        }

    def _preset_dir(self, kind: str) -> Path:
        return LAYOUT_PRESET_DIR if kind == "layout" else OUTPUT_PRESET_DIR

    def _user_presets(self, kind: str) -> dict[str, dict]:
        result: dict[str, dict] = {}
        directory = self._preset_dir(kind)
        directory.mkdir(parents=True, exist_ok=True)
        for path in sorted(directory.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("preset_type") != kind:
                    continue
                name = str(data.get("name") or path.stem)
                preset_data = data.get("data")
                if isinstance(preset_data, dict):
                    result[name] = preset_data
            except Exception:
                continue
        return result

    def _preset_labels(self, kind: str) -> list[str]:
        labels = [f"System / {name}" for name in self._system_presets(kind)]
        labels += [f"User / {name}" for name in self._user_presets(kind)]
        return labels

    def _selected_preset_data(self, kind: str, label: str) -> tuple[str, str, dict] | None:
        if " / " not in label:
            return None
        source, name = label.split(" / ", 1)
        if source == "System":
            data = self._system_presets(kind).get(name)
        elif source == "User":
            data = self._user_presets(kind).get(name)
        else:
            data = None
        if data is None:
            return None
        return source, name, data

    def _refresh_preset_selectors(self) -> None:
        pairs = (
            ("layout", self.vars["layout_preset"], getattr(self, "layout_preset_combo", None)),
            ("output", self.vars["output_preset"], getattr(self, "output_preset_combo", None)),
        )
        for kind, var, combo in pairs:
            labels = self._preset_labels(kind)
            if combo is not None:
                combo.configure(values=labels)
            if labels and var.get() not in labels:
                var.set(labels[0])

    def _apply_selected_preset(self, kind: str) -> None:
        var = self.vars["layout_preset"] if kind == "layout" else self.vars["output_preset"]
        selected = self._selected_preset_data(kind, var.get())
        if selected is None:
            messagebox.showerror("プリセット", "プリセットを選択してください。")
            return
        _source, name, data = selected
        if kind == "layout":
            self._apply_layout_preset_data(data)
        else:
            self._apply_output_preset_data(data)
        self.append_log(f"{name} を適用しました。\n")

    def _apply_initial_system_presets(self) -> None:
        layout = self._selected_preset_data("layout", self.vars["layout_preset"].get())
        if layout is not None:
            _source, _name, data = layout
            self._apply_layout_preset_data(data)
        output = self._selected_preset_data("output", self.vars["output_preset"].get())
        if output is not None:
            _source, _name, data = output
            self._apply_output_preset_data(data)

    def _save_user_preset(self, kind: str) -> None:
        name = simpledialog.askstring("プリセット保存", "プリセット名を入力してください。", parent=self)
        if not name:
            return
        data = self._current_layout_preset_data() if kind == "layout" else self._current_output_preset_data()
        path = self._preset_dir(kind) / f"{safe_preset_filename(name)}.json"
        if path.exists() and not messagebox.askyesno("プリセット保存", "同名のプリセットを上書きしますか？"):
            return
        payload = {
            "schema_version": 1,
            "preset_type": kind,
            "name": name,
            "data": data,
        }
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        self._refresh_preset_selectors()
        target = self.vars["layout_preset"] if kind == "layout" else self.vars["output_preset"]
        target.set(f"User / {name}")
        self.append_log(f"ユーザープリセットを保存しました: {path}\n")

    def _delete_user_preset(self, kind: str) -> None:
        var = self.vars["layout_preset"] if kind == "layout" else self.vars["output_preset"]
        selected = self._selected_preset_data(kind, var.get())
        if selected is None:
            messagebox.showerror("プリセット", "プリセットを選択してください。")
            return
        source, name, _data = selected
        if source != "User":
            messagebox.showinfo("プリセット", "システムプリセットは削除できません。")
            return
        if not messagebox.askyesno("プリセット削除", f"{name} を削除しますか？"):
            return
        path = self._preset_dir(kind) / f"{safe_preset_filename(name)}.json"
        if path.exists():
            path.unlink()
        self._refresh_preset_selectors()
        self.append_log(f"ユーザープリセットを削除しました: {name}\n")

    def _update_dynamic_scale_ranges(self) -> None:
        out_w = max(1, self._int_var_value("out_w", 1920))
        out_h = max(1, self._int_var_value("out_h", 1080))

        # Keep output sliders able to display native-size images larger than the default range.
        self._set_scale_range("out_w", OUTPUT_MIN_WIDTH, max(3840, out_w), clamp=False)
        self._set_scale_range("out_h", OUTPUT_MIN_HEIGHT, max(2160, out_h), clamp=False)

        x_max = max(1, out_w)
        y_max = max(1, out_h)
        for key in ("custom_x", "title_custom_x", "spec_x"):
            self._set_scale_range(key, 0, x_max)
        for key in ("custom_y", "title_custom_y", "spec_y"):
            self._set_scale_range(key, 0, y_max)

        self._set_scale_range("spec_w", 1, x_max)
        self._set_scale_range("spec_h", 1, y_max)
        self._set_scale_range("bottom_margin", 0, y_max)
        self._set_scale_range("title_margin_x", 0, x_max)
        self._set_scale_range("title_margin_y", 0, y_max)

    def _build_spin_row(self, parent: Frame, row: int, label: str, key: str, values=None, from_=0, to=9999, increment=1, tip_key: str | None = None) -> None:
        lbl = Label(parent, text=label, anchor="w")
        lbl.grid(row=row, column=0, sticky="w", padx=6, pady=5)
        if values is not None:
            w = ttk.Combobox(parent, textvariable=self.vars[key], values=values, width=16)
            w.grid(row=row, column=1, sticky="w", padx=6, pady=5)
            w.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())
        else:
            w = Spinbox(parent, textvariable=self.vars[key], from_=from_, to=to, increment=increment, width=10, command=self._draw_preview)
            w.grid(row=row, column=1, sticky="w", padx=6, pady=5)
            w.bind("<KeyRelease>", lambda _e: self._draw_preview())
            w.bind("<FocusOut>", lambda _e: self._draw_preview())
        if tip_key:
            self.add_tip(lbl, tip_key)
            self.add_tip(w, tip_key)

    def _current_preview_text(self) -> str:
        idx = self._selected_srt_index() if hasattr(self, "srt_tree") else None
        if idx is not None and 0 <= idx < len(self.srt_items):
            return self.srt_items[idx][2]
        if self.srt_items:
            preview_ms = int(float(self.vars["preview_time"].get()) * 1000)
            for start_ms, end_ms, text in self.srt_items:
                if start_ms <= preview_ms < end_ms:
                    return text
        if self.vars["srt"].get().strip():
            return self.t("subtitle_sample")
        return ""

    def _build_files_tab(self) -> None:
        f = Frame(self.notebook)
        f.columnconfigure(1, weight=1)
        self.notebook.add(f, text=self.t("tab_files"))

        Label(f, text=self.t("language"), width=18, anchor="w").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        lang_cb = ttk.Combobox(f, textvariable=self.vars["language_label"], values=list(LANGUAGES.values()), state="readonly", width=16)
        lang_cb.grid(row=0, column=1, sticky="w", padx=4, pady=4)
        lang_cb.bind("<<ComboboxSelected>>", self._on_language_changed)
        self.add_tip(lang_cb, "language")

        project_buttons = Frame(f)
        project_buttons.grid(row=1, column=0, columnspan=3, sticky="ew", padx=4, pady=(0, 8))
        project_buttons.columnconfigure(0, weight=1, uniform="project_buttons")
        project_buttons.columnconfigure(1, weight=1, uniform="project_buttons")
        save_project_btn = Button(project_buttons, text=self.t("save_preset"), command=self.save_preset)
        save_project_btn.grid(row=0, column=0, sticky="ew", padx=(0, 4))
        load_project_btn = Button(project_buttons, text=self.t("load_preset"), command=self.load_preset)
        load_project_btn.grid(row=0, column=1, sticky="ew", padx=(4, 0))
        self.add_tip(save_project_btn, "save_project")
        self.add_tip(load_project_btn, "load_project")

        self._row(f, self.t("background"), self.vars["background"], lambda: self.pick_file("background", [("Images", "*.jpg *.jpeg *.png *.bmp"), ("All", "*.*")]), 2, "background")
        self._row(f, self.t("audio"), self.vars["audio"], lambda: self.pick_file("audio", [("Audio", "*.mp3 *.wav *.m4a *.aac"), ("All", "*.*")]), 3, "audio")
        self._row(f, self.t("srt"), self.vars["srt"], lambda: self.pick_file("srt", [("SubRip", "*.srt"), ("All", "*.*")]), 4, "srt")
        self._row(f, self.t("spectrum_color"), self.vars["spectrum_color"], lambda: self.pick_file("spectrum_color", [("MP4", "*.mp4"), ("All", "*.*")]), 5, "spectrum_color")
        self._row(f, self.t("spectrum_mask"), self.vars["spectrum_mask"], lambda: self.pick_file("spectrum_mask", [("MP4", "*.mp4"), ("All", "*.*")]), 6, "spectrum_mask")
        self._row(f, self.t("output_mp4"), self.vars["output"], self.pick_output, 7, "output_mp4")
        Label(f, text=self.t("files_note"), anchor="w", justify="left", wraplength=720).grid(row=8, column=0, columnspan=3, sticky="ew", padx=4, pady=(10, 4))
        presets = self._build_presets_section(f)
        presets.grid(row=9, column=0, columnspan=3, sticky="ew", padx=0, pady=(0, 8))


    def _build_srt_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_srt"))
        top = Frame(f)
        top.pack(fill="x", padx=4, pady=4)
        reload_btn = Button(top, text=self.t("reload_srt"), command=lambda: self._load_srt_items(show_message=True))
        reload_btn.pack(side="left")
        self.add_tip(reload_btn, "srt")
        Label(top, text=self.t("srt_note"), anchor="w").pack(side="left", padx=8)

        body = Frame(f)
        body.pack(fill="both", expand=True, padx=4, pady=4)
        columns = ("no", "start", "end", "text")
        self.srt_tree = ttk.Treeview(body, columns=columns, show="headings", height=16)
        self.srt_tree.heading("no", text="No")
        self.srt_tree.heading("start", text=self.t("start"))
        self.srt_tree.heading("end", text=self.t("end"))
        self.srt_tree.heading("text", text=self.t("body"))
        self.srt_tree.column("no", width=50, anchor="e", stretch=False)
        self.srt_tree.column("start", width=110, stretch=False)
        self.srt_tree.column("end", width=110, stretch=False)
        self.srt_tree.column("text", width=520, stretch=True)
        yscroll = ttk.Scrollbar(body, orient="vertical", command=self.srt_tree.yview)
        self.srt_tree.configure(yscrollcommand=yscroll.set)
        self.srt_tree.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")
        self.srt_tree.bind("<<TreeviewSelect>>", self._on_srt_selected)

    def _build_title_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_title"))
        self.color_buttons = getattr(self, "color_buttons", {})

        basic = ttk.LabelFrame(f, text=self.t("text_style"))
        basic.pack(fill="x", padx=8, pady=8)
        basic.columnconfigure(1, weight=1)

        chk = ttk.Checkbutton(basic, text=self.t("title_enabled"), variable=self.vars["title_enabled"], command=self._draw_preview)
        chk.grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=5)
        self.add_tip(chk, "title_enabled")

        lbl = Label(basic, text=self.t("title_text"), anchor="w")
        lbl.grid(row=1, column=0, sticky="w", padx=6, pady=5)
        ent = Entry(basic, textvariable=self.vars["title_text"])
        ent.grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        ent.bind("<KeyRelease>", self._on_title_text_edited)
        ent.bind("<FocusOut>", lambda _e: self._draw_preview())
        self.add_tip(lbl, "title_text")
        self.add_tip(ent, "title_text")

        Label(basic, text=self.t("font"), anchor="w").grid(row=2, column=0, sticky="w", padx=6, pady=5)
        font_values = self._available_fonts()
        font_cb = ttk.Combobox(basic, textvariable=self.vars["title_font_name"], values=font_values, width=34)
        font_cb.grid(row=2, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        font_cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())
        self.add_tip(font_cb, "font")

        self._build_scale_row(basic, 3, self.t("font_size"), "title_font_size", 12, 120, 1, tip_key="font_size")
        title_bold = ttk.Checkbutton(basic, text=self.t("bold"), variable=self.vars["title_bold"], command=self._draw_preview)
        title_bold.grid(row=4, column=0, sticky="w", padx=6, pady=5)
        title_italic = ttk.Checkbutton(basic, text=self.t("italic"), variable=self.vars["title_italic"], command=self._draw_preview)
        title_italic.grid(row=4, column=1, sticky="w", padx=6, pady=5)
        self.add_tip(title_bold, "font")
        self.add_tip(title_italic, "font")
        self._build_color_row(basic, 5, self.t("text_color"), "title_text_color", tip_key="color")
        self._build_color_row(basic, 6, self.t("outline_color"), "title_outline_color", tip_key="color")
        self._build_scale_row(basic, 7, self.t("outline_width"), "title_outline_width", 0, 12, 1, tip_key="outline_width")
        self._build_scale_row(basic, 8, self.t("shadow"), "title_shadow", 0, 10, 1, tip_key="shadow")

        pos = ttk.LabelFrame(f, text=self.t("position"))
        pos.pack(fill="x", padx=8, pady=8)
        pos.columnconfigure(1, weight=1)

        Label(pos, text=self.t("alignment"), anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        cb = ttk.Combobox(pos, textvariable=self.vars["title_alignment_label"], values=list(TITLE_ALIGNMENTS.keys()), state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="w", padx=6, pady=5)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())
        self.add_tip(cb, "alignment")

        self._build_scale_row(pos, 1, "X " + self.t("margin"), "title_margin_x", 0, 800, 1, tip_key="margin")
        self._build_scale_row(pos, 2, "Y " + self.t("margin"), "title_margin_y", 0, 800, 1, tip_key="margin")
        self._build_scale_row(pos, 3, self.t("custom_x"), "title_custom_x", 0, 3840, 1, tip_key="custom_xy")
        self._build_scale_row(pos, 4, self.t("custom_y"), "title_custom_y", 0, 2160, 1, tip_key="custom_xy")

        Label(f, text=self.t("title_note"), justify="left", anchor="w", foreground="#555555", wraplength=720).pack(fill="x", padx=10, pady=(2, 8))
        self._update_color_buttons()


    def _build_subtitle_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_subtitle"))
        self.color_buttons = getattr(self, "color_buttons", {})

        basic = ttk.LabelFrame(f, text=self.t("text_style"))
        basic.pack(fill="x", padx=8, pady=8)
        basic.columnconfigure(1, weight=1)

        Label(basic, text=self.t("font"), anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        font_values = self._available_fonts()
        font_cb = ttk.Combobox(basic, textvariable=self.vars["font_name"], values=font_values, width=34)
        font_cb.grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=5)
        font_cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())
        self.add_tip(font_cb, "font")

        self._build_scale_row(basic, 1, self.t("font_size"), "font_size", 12, 120, 1, tip_key="font_size")
        sub_bold = ttk.Checkbutton(basic, text=self.t("bold"), variable=self.vars["bold"], command=self._draw_preview)
        sub_bold.grid(row=2, column=0, sticky="w", padx=6, pady=5)
        sub_italic = ttk.Checkbutton(basic, text=self.t("italic"), variable=self.vars["italic"], command=self._draw_preview)
        sub_italic.grid(row=2, column=1, sticky="w", padx=6, pady=5)
        self.add_tip(sub_bold, "font")
        self.add_tip(sub_italic, "font")
        self._build_color_row(basic, 3, self.t("text_color"), "text_color", tip_key="color")
        self._build_color_row(basic, 4, self.t("outline_color"), "outline_color", tip_key="color")
        self._build_scale_row(basic, 5, self.t("outline_width"), "outline_width", 0, 12, 1, tip_key="outline_width")
        self._build_scale_row(basic, 6, self.t("shadow"), "shadow", 0, 10, 1, tip_key="shadow")

        pos = ttk.LabelFrame(f, text=self.t("position"))
        pos.pack(fill="x", padx=8, pady=8)
        pos.columnconfigure(1, weight=1)

        Label(pos, text=self.t("alignment"), anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        cb = ttk.Combobox(pos, textvariable=self.vars["alignment_label"], values=list(ALIGNMENTS.keys()), state="readonly", width=18)
        cb.grid(row=0, column=1, sticky="w", padx=6, pady=5)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._draw_preview())
        self.add_tip(cb, "alignment")

        self._build_scale_row(pos, 1, self.t("margin"), "bottom_margin", 0, 500, 1, tip_key="margin")
        self._build_scale_row(pos, 2, self.t("custom_x"), "custom_x", 0, 3840, 1, tip_key="custom_xy")
        self._build_scale_row(pos, 3, self.t("custom_y"), "custom_y", 0, 2160, 1, tip_key="custom_xy")

        note = (
            "通常は『下中央』と『下/上からの距離』だけで調整します。\n"
            "『自由XY』を選ぶと、自由X/自由Yの座標で字幕を配置します。"
        )
        Label(f, text=note, justify="left", anchor="w", foreground="#555555").pack(fill="x", padx=10, pady=(2, 8))
        self._update_color_buttons()

    def _build_spectrum_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_spectrum"))

        geom = ttk.LabelFrame(f, text=self.t("geom"))
        geom.pack(fill="x", padx=8, pady=8)
        geom.columnconfigure(1, weight=1)
        self._build_spectrum_position_row(geom, 0, self.t("x_pos"), "spec_x", 3840, "x", tip_key="spec_pos")
        self._build_spectrum_position_row(geom, 1, self.t("y_pos"), "spec_y", 2160, "y", tip_key="spec_pos")
        self._build_scale_row(geom, 2, self.t("width"), "spec_w", 1, 3840, 1, tip_key="spec_size")
        self._build_scale_row(geom, 3, self.t("height"), "spec_h", 1, 2160, 1, tip_key="spec_size")

        appearance = ttk.LabelFrame(f, text=self.t("display_transform"))
        appearance.pack(fill="x", padx=8, pady=8)
        appearance.columnconfigure(1, weight=1)
        self._build_scale_row(appearance, 0, self.t("spectrum_opacity"), "spec_opacity", 0, 100, 1, tip_key="spectrum_opacity")
        flip_h = ttk.Checkbutton(appearance, text=self.t("flip_h"), variable=self.vars["flip_h"], command=self._draw_preview)
        flip_h.grid(row=1, column=0, sticky="w", padx=6, pady=5)
        flip_v = ttk.Checkbutton(appearance, text=self.t("flip_v"), variable=self.vars["flip_v"], command=self._draw_preview)
        flip_v.grid(row=1, column=1, sticky="w", padx=6, pady=5)
        self.add_tip(flip_h, "flip")
        self.add_tip(flip_v, "flip")

        comp = ttk.LabelFrame(f, text=self.t("compose_mode"))
        comp.pack(fill="x", padx=8, pady=8)
        labels = [COMPOSE_MODE_LABELS[m] for m in COMPOSE_MODES]
        self.mode_label_to_key = {COMPOSE_MODE_LABELS[m]: m for m in COMPOSE_MODES}
        self.mode_key_to_label = {m: COMPOSE_MODE_LABELS[m] for m in COMPOSE_MODES}
        self.compose_mode_label_var = StringVar(value=COMPOSE_MODE_LABELS.get(self.vars["compose_mode"].get(), COMPOSE_MODE_LABELS["mask_alpha"]))
        mode = ttk.Combobox(comp, textvariable=self.compose_mode_label_var, values=labels, state="readonly", width=44)
        mode.grid(row=0, column=0, sticky="ew", padx=6, pady=5)
        comp.columnconfigure(0, weight=1)
        mode.bind("<<ComboboxSelected>>", self._on_mode_label_changed)
        self.add_tip(mode, "compose_mode")
        Label(comp, text=self.t("compose_note"), justify="left", foreground="#555555").grid(row=1, column=0, sticky="w", padx=6, pady=(2, 6))

        mask = ttk.LabelFrame(f, text=self.t("mask_proc"))
        mask.pack(fill="x", padx=8, pady=8)
        mask.columnconfigure(1, weight=1)
        Label(mask, text=self.t("mask_proc_note"), justify="left", foreground="#555555", wraplength=720).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(6, 2))
        self._build_scale_row(mask, 1, self.t("alpha_strength"), "alpha_strength", 0.0, 2.0, 0.05, spin_width=8, tip_key="mask_proc")
        mask_bin = ttk.Checkbutton(mask, text=self.t("mask_binarize"), variable=self.vars["mask_binarize"], command=self._draw_preview)
        mask_bin.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=5)
        self.add_tip(mask_bin, "mask_proc")
        self._build_scale_row(mask, 3, self.t("mask_threshold"), "mask_threshold", 0, 255, 1, tip_key="mask_proc")

        keying = ttk.LabelFrame(f, text=self.t("black_key"))
        keying.pack(fill="x", padx=8, pady=8)
        keying.columnconfigure(1, weight=1)
        Label(keying, text=self.t("black_key_note"), justify="left", foreground="#555555", wraplength=720).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=(6, 2))
        self._build_scale_row(keying, 1, self.t("black_similarity"), "black_similarity", 0.0, 0.3, 0.005, spin_width=8, tip_key="black_key")
        self._build_scale_row(keying, 2, self.t("black_blend"), "black_blend", 0.0, 0.3, 0.005, spin_width=8, tip_key="black_key")

    def _build_output_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_output"))

        video = ttk.LabelFrame(f, text=self.t("video_settings"))
        video.pack(fill="x", padx=8, pady=8)
        video.columnconfigure(1, weight=1)

        Label(video, text=self.t("resolution"), anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        res = ttk.Combobox(video, textvariable=self.vars["resolution_preset"], values=list(VIDEO_PRESETS.keys()), state="readonly", width=18)
        res.grid(row=0, column=1, sticky="w", padx=6, pady=5)
        res.bind("<<ComboboxSelected>>", lambda _e: self._update_resolution_from_preset())
        self.add_tip(res, "resolution")
        self._build_scale_row(video, 1, self.t("width"), "out_w", OUTPUT_MIN_WIDTH, 3840, 2, tip_key="resolution")
        self._build_scale_row(video, 2, self.t("height"), "out_h", OUTPUT_MIN_HEIGHT, 2160, 2, tip_key="resolution")
        self._build_spin_row(video, 3, self.t("fps"), "fps", values=[24, 30, 60], tip_key="fps")

        quality = ttk.LabelFrame(f, text=self.t("quality"))
        quality.pack(fill="x", padx=8, pady=8)
        quality.columnconfigure(1, weight=1)
        Label(quality, text=self.t("quality_preset"), anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=5)
        q = ttk.Combobox(quality, textvariable=self.vars["quality_preset"], values=list(QUALITY_PRESETS.keys()), state="readonly", width=24)
        q.grid(row=0, column=1, sticky="w", padx=6, pady=5)
        q.bind("<<ComboboxSelected>>", lambda _e: self._update_quality_from_preset())
        self.add_tip(q, "crf")
        self._build_scale_row(quality, 1, "CRF", "crf", 16, 32, 1, tip_key="crf")
        Label(quality, text=self.t("encoder_preset"), anchor="w").grid(row=2, column=0, sticky="w", padx=6, pady=5)
        enc = ttk.Combobox(quality, textvariable=self.vars["encoder_preset"], values=["ultrafast", "veryfast", "faster", "fast", "medium", "slow"], state="readonly", width=16)
        enc.grid(row=2, column=1, sticky="w", padx=6, pady=5)
        self.add_tip(enc, "crf")
        cb_still = ttk.Checkbutton(quality, text=self.t("stillimage_tune"), variable=self.vars["use_stillimage_tune"])
        cb_still.grid(row=3, column=0, columnspan=2, sticky="w", padx=6, pady=5)
        self.add_tip(cb_still, "stillimage_tune")

        audio = ttk.LabelFrame(f, text=self.t("bitrate"))
        audio.pack(fill="x", padx=8, pady=8)
        video_bitrate_lbl = Label(audio, text=self.t("video_bitrate"), anchor="w")
        video_bitrate_lbl.grid(row=0, column=0, sticky="w", padx=6, pady=5)
        video_bitrate_ent = Entry(audio, textvariable=self.vars["video_bitrate"], width=16)
        video_bitrate_ent.grid(row=0, column=1, sticky="w", padx=6, pady=5)
        audio_bitrate_lbl = Label(audio, text=self.t("audio_bitrate"), anchor="w")
        audio_bitrate_lbl.grid(row=1, column=0, sticky="w", padx=6, pady=5)
        audio_bitrate_cb = ttk.Combobox(audio, textvariable=self.vars["audio_bitrate"], values=["128k", "160k", "192k", "256k", "320k"], width=14)
        audio_bitrate_cb.grid(row=1, column=1, sticky="w", padx=6, pady=5)
        self.add_tip(video_bitrate_lbl, "bitrate")
        self.add_tip(video_bitrate_ent, "bitrate")
        self.add_tip(audio_bitrate_lbl, "bitrate")
        self.add_tip(audio_bitrate_cb, "bitrate")
        Label(audio, text=self.t("bitrate_note"), justify="left", foreground="#555555").grid(row=2, column=0, columnspan=2, sticky="w", padx=6, pady=(2, 6))

    def _build_advanced_tab(self) -> None:
        f = Frame(self.notebook)
        self.notebook.add(f, text=self.t("tab_advanced"))

        keying = ttk.LabelFrame(f, text=self.t("black_key"))
        keying.pack(fill="x", padx=8, pady=8)
        keying.columnconfigure(1, weight=1)
        self._build_scale_row(keying, 0, self.t("black_similarity"), "black_similarity", 0.0, 0.3, 0.005, spin_width=8, tip_key="black_key")
        self._build_scale_row(keying, 1, self.t("black_blend"), "black_blend", 0.0, 0.3, 0.005, spin_width=8, tip_key="black_key")

        mask = ttk.LabelFrame(f, text=self.t("mask_proc"))
        mask.pack(fill="x", padx=8, pady=8)
        mask.columnconfigure(1, weight=1)
        ttk.Checkbutton(mask, text=self.t("mask_binarize"), variable=self.vars["mask_binarize"]).grid(row=0, column=0, columnspan=3, sticky="w", padx=6, pady=5)
        self._build_scale_row(mask, 1, self.t("mask_threshold"), "mask_threshold", 0, 255, 1, tip_key="mask_proc")
        self._build_scale_row(mask, 2, self.t("alpha_strength"), "alpha_strength", 0.0, 2.0, 0.05, spin_width=8, tip_key="mask_proc")

        Label(
            f,
            text=self.t("advanced_note"),
            justify="left",
            foreground="#555555",
            wraplength=720,
        ).pack(fill="x", padx=10, pady=8)

    def _build_presets_section(self, parent: Frame) -> Frame:
        f = Frame(parent)

        def build_preset_group(parent: Frame, title_key: str, var_key: str, combo_attr: str, kind: str) -> None:
            group = ttk.LabelFrame(parent, text=self.t(title_key))
            group.pack(fill="x", padx=8, pady=8)
            for col in range(3):
                group.columnconfigure(col, weight=1, uniform="preset_buttons")

            combo = ttk.Combobox(
                group,
                textvariable=self.vars[var_key],
                values=[],
                state="readonly",
                width=42,
            )
            combo.grid(row=0, column=0, columnspan=3, sticky="ew", padx=6, pady=(6, 4))
            setattr(self, combo_attr, combo)
            self.add_tip(combo, "layout_preset" if kind == "layout" else "output_preset")

            apply_btn = Button(
                group,
                text=self.t("apply_preset"),
                command=lambda k=kind: self._apply_selected_preset(k),
            )
            apply_btn.grid(row=1, column=0, sticky="ew", padx=6, pady=(2, 6))
            save_btn = Button(
                group,
                text=self.t("save_user_preset"),
                command=lambda k=kind: self._save_user_preset(k),
            )
            save_btn.grid(row=1, column=1, sticky="ew", padx=6, pady=(2, 6))
            delete_btn = Button(
                group,
                text=self.t("delete_user_preset"),
                command=lambda k=kind: self._delete_user_preset(k),
            )
            delete_btn.grid(row=1, column=2, sticky="ew", padx=6, pady=(2, 6))
            self.add_tip(apply_btn, "apply_preset")
            self.add_tip(save_btn, "save_user_preset")
            self.add_tip(delete_btn, "delete_user_preset")

        build_preset_group(f, "layout_presets", "layout_preset", "layout_preset_combo", "layout")
        build_preset_group(f, "output_presets", "output_preset", "output_preset_combo", "output")
        Label(
            f,
            text=self.t("preset_note"),
            justify="left",
            foreground="#555555",
            wraplength=720,
        ).pack(fill="x", padx=10, pady=8)
        self._refresh_preset_selectors()
        return f

    def _auto_fill_output_from_audio(self, force: bool = False) -> None:
        audio_path = self.vars["audio"].get().strip()
        current_output = self.vars["output"].get().strip()
        if not audio_path:
            return
        if force or not current_output or self.output_auto_generated:
            default_output = default_output_path_from_audio(audio_path)
            if default_output:
                self.vars["output"].set(default_output)
                self.output_auto_generated = True

    def _auto_fill_title_from_audio(self, force: bool = False) -> None:
        audio_path = self.vars["audio"].get().strip()
        if not audio_path:
            return
        current = self.vars["title_text"].get().strip()
        if force or not current or self.title_auto_generated:
            title = Path(audio_path).stem
            if title:
                self.vars["title_text"].set(title)
                self.title_auto_generated = True
                self._draw_preview()

    def _on_title_text_edited(self, _event=None) -> None:
        self.title_auto_generated = False
        self._draw_preview()

    def _auto_load_mask_from_spectrum(self) -> None:
        color_path = self.vars["spectrum_color"].get().strip()
        if not color_path:
            return
        p = Path(color_path)
        candidate = p.with_name(f"{p.stem}_matte_dark.mp4")
        if candidate.exists():
            self.vars["spectrum_mask"].set(str(candidate))
            self.append_log(f"マスク動画を自動読み込みしました: {candidate}\n")

    def pick_file(self, key: str, filetypes) -> None:
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self.vars[key].set(path)
            if key == "audio":
                self._auto_fill_output_from_audio()
                self._auto_fill_title_from_audio()
            if key == "spectrum_color":
                self._auto_load_mask_from_spectrum()
                self._draw_preview()
            if key == "srt":
                self._load_srt_items(show_message=False)
                self._draw_preview()
            if key == "background":
                if self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
                    self._update_resolution_from_preset()
                else:
                    self._draw_preview()

    def pick_output(self) -> None:
        initialfile = ""
        initialdir = ""
        current = self.vars["output"].get().strip()
        if current:
            p = Path(current)
            initialdir = str(p.parent) if str(p.parent) != "." else ""
            initialfile = p.name
        else:
            audio_default = default_output_path_from_audio(self.vars["audio"].get().strip())
            if audio_default:
                p = Path(audio_default)
                initialdir = str(p.parent)
                initialfile = p.name
        path = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            initialdir=initialdir or None,
            initialfile=initialfile or None,
            filetypes=[("MP4", "*.mp4"), ("All", "*.*")],
        )
        if path:
            self.vars["output"].set(normalize_output_path(path))
            self.output_auto_generated = False

    def _load_startup_handoff(self, explicit_path: Path | None = None) -> None:
        candidates: list[tuple[Path, bool]] = []
        if explicit_path is not None:
            candidates.append((explicit_path, True))
        candidates.append((STARTUP_HANDOFF_PATH, False))
        candidates.append((LEGACY_STARTUP_HANDOFF_PATH, False))

        seen: set[Path] = set()
        for path, required in candidates:
            try:
                resolved = path.expanduser().resolve()
            except Exception:
                resolved = path
            if resolved in seen:
                continue
            seen.add(resolved)
            if not resolved.exists():
                if required:
                    self.append_log(f"handoff file not found: {resolved}\n")
                continue
            self._consume_handoff_file(resolved)
            return

    def _consume_handoff_file(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            applied = self._apply_handoff_data(data)
        except Exception as exc:
            self.append_log(f"handoff read error: {path} / {exc}\n")
            return
        if not applied:
            self.append_log(f"handoff ignored: no usable values in {path}\n")
            return
        try:
            path.unlink()
            deleted = "deleted"
        except Exception as exc:
            deleted = f"delete failed: {exc}"
        self.append_log(f"handoff applied ({', '.join(applied)}), {deleted}: {path}\n")

    def _apply_handoff_data(self, data: dict) -> list[str]:
        if not isinstance(data, dict):
            raise ValueError("handoff JSON root must be an object")
        version = int(data.get("schema_version", 0))
        if version > HANDOFF_SCHEMA_VERSION:
            raise ValueError(f"unsupported handoff schema_version={version}")
        handoff_type = data.get("handoff_type")
        if handoff_type and handoff_type != HANDOFF_TYPE and handoff_type not in LEGACY_HANDOFF_TYPES:
            raise ValueError(f"unsupported handoff_type={handoff_type}")

        applied: list[str] = []
        skipped: list[str] = []

        def read_file_value(key: str, *aliases: str) -> str:
            values = [
                nested_text(data, "files", key),
                nested_text(data, "file_paths", key),
                nested2_text(data, "settings", "files", key),
                data.get(key),
            ]
            values.extend(data.get(alias) for alias in aliases)
            return first_text_value(*values)

        file_map = {
            "background": ("background_image", "background_path"),
            "audio": ("audio_path",),
            "srt": ("srt_path", "subtitle_path"),
            "spectrum_color": ("spectrum_video", "color_spectrum", "color_spectrum_path", "spectrum_color_path"),
            "spectrum_mask": ("mask_video", "mask_path", "spectrum_mask_path"),
        }
        for key, aliases in file_map.items():
            value = read_file_value(key, *aliases)
            if not value:
                continue
            if not Path(value).exists():
                skipped.append(key)
                continue
            self.vars[key].set(value)
            applied.append(key)

        output_path = first_text_value(
            nested_text(data, "files", "output"),
            nested2_text(data, "settings", "files", "output"),
            nested_text(data, "suggested", "output_path"),
            data.get("output"),
            data.get("output_path"),
        )
        if output_path:
            self.vars["output"].set(normalize_output_path(output_path))
            self.output_auto_generated = False
            applied.append("output")

        title_text = first_text_value(
            nested_text(data, "suggested", "title_text"),
            nested2_text(data, "settings", "title", "text"),
            data.get("title_text"),
        )
        if title_text:
            self.vars["title_text"].set(title_text)
            self.title_auto_generated = False
            applied.append("title_text")

        if "preview_time" in data:
            try:
                self.vars["preview_time"].set(float(data["preview_time"]))
                applied.append("preview_time")
            except Exception:
                skipped.append("preview_time")

        if self.vars["srt"].get().strip():
            self._load_srt_items(show_message=False)
        if self.vars["audio"].get().strip() and not output_path:
            self._auto_fill_output_from_audio(force=True)
            if self.vars["output"].get().strip():
                applied.append("output_auto")
        if self.vars["audio"].get().strip() and not title_text:
            self._auto_fill_title_from_audio(force=True)
            if self.vars["title_text"].get().strip():
                applied.append("title_auto")
        if self.vars["spectrum_color"].get().strip() and not self.vars["spectrum_mask"].get().strip():
            self._auto_load_mask_from_spectrum()
        if self.vars["background"].get().strip() and self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
            self._update_resolution_from_preset()

        self._schedule_preview_redraw()
        if skipped:
            self.append_log(f"handoff skipped missing/invalid values: {', '.join(skipped)}\n")
        return applied

    def _load_srt_items(self, show_message: bool = False) -> None:
        path = self.vars["srt"].get().strip()
        self.srt_items = []
        if hasattr(self, "srt_tree"):
            self.srt_tree.delete(*self.srt_tree.get_children())
        if not path:
            return
        try:
            self.srt_items = parse_srt(path)
            if hasattr(self, "srt_tree"):
                for i, (start_ms, end_ms, text) in enumerate(self.srt_items, start=1):
                    one_line = " / ".join(line.strip() for line in text.splitlines() if line.strip())
                    self.srt_tree.insert("", "end", iid=str(i - 1), values=(i, ms_to_srt_time(start_ms), ms_to_srt_time(end_ms), one_line))
            if self.srt_items:
                start_ms, end_ms, _text = self.srt_items[0]
                self.vars["preview_time"].set(round(((start_ms + end_ms) / 2) / 1000, 3))
            if show_message:
                messagebox.showinfo("SRT読み込み", f"{len(self.srt_items)} 行を読み込みました。")
        except Exception as e:
            if show_message:
                messagebox.showerror("SRT読み込みエラー", str(e))
            self.append_log(f"SRT読み込みエラー: {e}\n")

    def _selected_srt_index(self) -> int | None:
        if not hasattr(self, "srt_tree"):
            return None
        sel = self.srt_tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _on_srt_selected(self, _event=None) -> None:
        idx = self._selected_srt_index()
        if idx is None or not (0 <= idx < len(self.srt_items)):
            return
        start_ms, end_ms, _text = self.srt_items[idx]
        self.vars["preview_time"].set(round(((start_ms + end_ms) / 2) / 1000, 3))
        self._draw_preview()

    def _on_mode_label_changed(self, _event=None) -> None:
        label = self.compose_mode_label_var.get()
        self.vars["compose_mode"].set(self.mode_label_to_key.get(label, "mask_alpha"))
        self._update_mask_state()

    def _update_mask_state(self) -> None:
        pass

    def _update_resolution_from_preset(self) -> None:
        preset = self.vars["resolution_preset"].get()
        if preset == BACKGROUND_SIZE_PRESET:
            size = get_image_size(self._background_reference_path())
            if size:
                if not self._is_output_size_usable(size):
                    messagebox.showerror(
                        "解像度エラー",
                        f"元画像サイズが小さすぎます。最低 {OUTPUT_MIN_WIDTH}x{OUTPUT_MIN_HEIGHT} が必要です。\n"
                        f"元画像: {size[0]}x{size[1]}",
                    )
                    self.vars["resolution_preset"].set("Custom")
                    self._normalize_output_resolution()
                    self._sync_layout_to_current_resolution()
                    self._draw_preview()
                    return
                self.vars["out_w"].set(size[0])
                self.vars["out_h"].set(size[1])
            self._sync_layout_to_current_resolution()
            self._draw_preview()
            return
        value = VIDEO_PRESETS.get(preset)
        if value:
            self.vars["out_w"].set(value[0])
            self.vars["out_h"].set(value[1])
        else:
            self._normalize_output_resolution()
        self._sync_layout_to_current_resolution()
        self._draw_preview()

    def _update_quality_from_preset(self) -> None:
        preset = self.vars["quality_preset"].get()
        value = QUALITY_PRESETS.get(preset)
        if value is not None:
            self.vars["crf"].set(value)

    def _settings(self) -> AppSettings:
        mode_label = getattr(self, "compose_mode_label_var", None)
        if mode_label is not None:
            self.vars["compose_mode"].set(self.mode_label_to_key.get(mode_label.get(), "mask_alpha"))
        self.vars["background_mode"].set("slideshow" if bool(self.vars["slideshow_enabled"].get()) else "single")
        self._sync_slideshow_scenes_from_rows()
        self._auto_fill_output_from_audio()
        normalized_output = normalize_output_path(self.vars["output"].get().strip())
        if normalized_output != self.vars["output"].get().strip():
            self.vars["output"].set(normalized_output)
        if self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
            size = get_image_size(self._background_reference_path())
            if size:
                self.vars["out_w"].set(size[0])
                self.vars["out_h"].set(size[1])
        else:
            self._normalize_output_resolution()
        self._sync_layout_to_current_resolution()
        return AppSettings(
            files=FileSettings(
                background=self.vars["background"].get(),
                audio=self.vars["audio"].get(),
                srt=self.vars["srt"].get(),
                spectrum_color=self.vars["spectrum_color"].get(),
                spectrum_mask=self.vars["spectrum_mask"].get(),
                output=self.vars["output"].get(),
            ),
            background=BackgroundSettings(
                mode="slideshow" if bool(self.vars["slideshow_enabled"].get()) else "single",
                timesheet=self.vars["timesheet"].get(),
                image_dir="",
                fade_transition=bool(self.vars["slideshow_fade_transition"].get()),
                scenes=[dataclass_from_dict(SlideshowScene, asdict(scene)) for scene in self.slideshow_scenes],
            ),
            subtitle=SubtitleSettings(
                font_name=self.vars["font_name"].get(),
                font_size=int(self.vars["font_size"].get()),
                bold=bool(self.vars["bold"].get()),
                italic=bool(self.vars["italic"].get()),
                text_color=self.vars["text_color"].get(),
                outline_color=self.vars["outline_color"].get(),
                outline_width=int(self.vars["outline_width"].get()),
                shadow=int(self.vars["shadow"].get()),
                alignment_label=self.vars["alignment_label"].get(),
                bottom_margin=int(self.vars["bottom_margin"].get()),
                custom_x=int(self.vars["custom_x"].get()),
                custom_y=int(self.vars["custom_y"].get()),
            ),
            title=TitleSettings(
                enabled=bool(self.vars["title_enabled"].get()),
                text=self.vars["title_text"].get(),
                font_name=self.vars["title_font_name"].get(),
                font_size=int(self.vars["title_font_size"].get()),
                bold=bool(self.vars["title_bold"].get()),
                italic=bool(self.vars["title_italic"].get()),
                text_color=self.vars["title_text_color"].get(),
                outline_color=self.vars["title_outline_color"].get(),
                outline_width=int(self.vars["title_outline_width"].get()),
                shadow=int(self.vars["title_shadow"].get()),
                alignment_label=self.vars["title_alignment_label"].get(),
                margin_x=int(self.vars["title_margin_x"].get()),
                margin_y=int(self.vars["title_margin_y"].get()),
                custom_x=int(self.vars["title_custom_x"].get()),
                custom_y=int(self.vars["title_custom_y"].get()),
            ),
            spectrum=SpectrumSettings(
                x=int(self.vars["spec_x"].get()),
                y=int(self.vars["spec_y"].get()),
                width=int(self.vars["spec_w"].get()),
                height=int(self.vars["spec_h"].get()),
                opacity=int(self.vars["spec_opacity"].get()),
                flip_horizontal=bool(self.vars["flip_h"].get()),
                flip_vertical=bool(self.vars["flip_v"].get()),
                compose_mode=self.vars["compose_mode"].get(),
                black_similarity=float(self.vars["black_similarity"].get()),
                black_blend=float(self.vars["black_blend"].get()),
                mask_binarize=bool(self.vars["mask_binarize"].get()),
                mask_threshold=int(self.vars["mask_threshold"].get()),
                alpha_strength=float(self.vars["alpha_strength"].get()),
            ),
            output=OutputSettings(
                width=int(self.vars["out_w"].get()),
                height=int(self.vars["out_h"].get()),
                fps=int(self.vars["fps"].get()),
                crf=int(self.vars["crf"].get()),
                video_bitrate=self.vars["video_bitrate"].get(),
                audio_bitrate=self.vars["audio_bitrate"].get(),
                preset=self.vars["encoder_preset"].get(),
                use_stillimage_tune=bool(self.vars["use_stillimage_tune"].get()),
                background_native_size=(self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET),
            ),
        )

    def _apply_settings(self, settings: AppSettings) -> None:
        self.vars["background"].set(settings.files.background)
        self.vars["audio"].set(settings.files.audio)
        self.vars["srt"].set(settings.files.srt)
        self.vars["spectrum_color"].set(settings.files.spectrum_color)
        self.vars["spectrum_mask"].set(settings.files.spectrum_mask)
        self.vars["output"].set(settings.files.output)
        background_mode = getattr(settings.background, "mode", "single")
        self.vars["background_mode"].set(background_mode)
        self.vars["slideshow_enabled"].set(background_mode == "slideshow")
        self.vars["slideshow_fade_transition"].set(bool(getattr(settings.background, "fade_transition", False)))
        self.vars["timesheet"].set(getattr(settings.background, "timesheet", ""))
        self.slideshow_scenes = [
            dataclass_from_dict(SlideshowScene, asdict(scene)) for scene in getattr(settings.background, "scenes", [])
        ]
        self._load_slideshow_scenes_to_rows()
        self._load_srt_items(show_message=False)
        self.output_auto_generated = False
        if not settings.files.output and settings.files.audio:
            self._auto_fill_output_from_audio(force=True)
        for field, value in asdict(settings.subtitle).items():
            key = {
                "font_name": "font_name",
                "font_size": "font_size",
                "bold": "bold",
                "italic": "italic",
                "text_color": "text_color",
                "outline_color": "outline_color",
                "outline_width": "outline_width",
                "shadow": "shadow",
                "alignment_label": "alignment_label",
                "bottom_margin": "bottom_margin",
                "custom_x": "custom_x",
                "custom_y": "custom_y",
            }[field]
            self.vars[key].set(value)
        title = getattr(settings, "title", TitleSettings())
        title_map = {
            "enabled": "title_enabled",
            "text": "title_text",
            "font_name": "title_font_name",
            "font_size": "title_font_size",
            "bold": "title_bold",
            "italic": "title_italic",
            "text_color": "title_text_color",
            "outline_color": "title_outline_color",
            "outline_width": "title_outline_width",
            "shadow": "title_shadow",
            "alignment_label": "title_alignment_label",
            "margin_x": "title_margin_x",
            "margin_y": "title_margin_y",
            "custom_x": "title_custom_x",
            "custom_y": "title_custom_y",
        }
        for field, value in asdict(title).items():
            if field in title_map:
                self.vars[title_map[field]].set(value)
        self.title_auto_generated = False
        sp = settings.spectrum
        self.vars["spec_x"].set(sp.x)
        self.vars["spec_y"].set(sp.y)
        self.vars["spec_w"].set(sp.width)
        self.vars["spec_h"].set(sp.height)
        self.vars["spec_opacity"].set(getattr(sp, "opacity", 0))
        self.vars["flip_h"].set(sp.flip_horizontal)
        self.vars["flip_v"].set(sp.flip_vertical)
        self.vars["compose_mode"].set(sp.compose_mode)
        self.compose_mode_label_var.set(self.mode_key_to_label.get(sp.compose_mode, COMPOSE_MODE_LABELS["mask_alpha"]))
        self.vars["black_similarity"].set(sp.black_similarity)
        self.vars["black_blend"].set(sp.black_blend)
        self.vars["mask_binarize"].set(sp.mask_binarize)
        self.vars["mask_threshold"].set(sp.mask_threshold)
        self.vars["alpha_strength"].set(sp.alpha_strength)
        self.vars["out_w"].set(settings.output.width)
        self.vars["out_h"].set(settings.output.height)
        self.vars["fps"].set(settings.output.fps)
        self.vars["crf"].set(settings.output.crf)
        self.vars["video_bitrate"].set(settings.output.video_bitrate)
        self.vars["audio_bitrate"].set(settings.output.audio_bitrate)
        self.vars["encoder_preset"].set(settings.output.preset)
        self.vars["use_stillimage_tune"].set(getattr(settings.output, "use_stillimage_tune", False))
        if getattr(settings.output, "background_native_size", False):
            self.vars["resolution_preset"].set(BACKGROUND_SIZE_PRESET)
        else:
            matched = None
            for label, size in VIDEO_PRESETS.items():
                if size == (settings.output.width, settings.output.height):
                    matched = label
                    break
            self.vars["resolution_preset"].set(matched or "Custom")
            self._normalize_output_resolution()
        self._layout_resolution = (self._int_var_value("out_w", settings.output.width), self._int_var_value("out_h", settings.output.height))
        self._update_dynamic_scale_ranges()
        self._update_color_buttons()
        self._draw_preview()

    def _project_ui_state(self) -> dict:
        return {
            "language": self.vars["language"].get(),
            "quality_preset": self.vars["quality_preset"].get(),
            "preview_time": float(self.vars["preview_time"].get()),
            "preview_duration": int(self.vars["preview_duration"].get()),
        }

    def _apply_project_ui_state(self, ui_state: dict) -> None:
        language = ui_state.get("language")
        if language in LANGUAGES:
            self.vars["language"].set(language)
            self.vars["language_label"].set(LANGUAGES[language])
        quality_preset = ui_state.get("quality_preset")
        if quality_preset in QUALITY_PRESETS:
            self.vars["quality_preset"].set(quality_preset)
        if "preview_time" in ui_state:
            try:
                self.vars["preview_time"].set(float(ui_state["preview_time"]))
            except Exception:
                pass
        if "preview_duration" in ui_state:
            try:
                self.vars["preview_duration"].set(int(ui_state["preview_duration"]))
            except Exception:
                pass

    def save_preset(self) -> None:
        path = filedialog.asksaveasfilename(
            initialdir=str(PRESET_DIR),
            defaultextension=".fcproj",
            filetypes=[("SRT Spectrum Video Composer Project", "*.fcproj"), ("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        settings = self._settings()
        project = project_data_from_settings(settings, self._project_ui_state())
        Path(path).write_text(json.dumps(project, ensure_ascii=False, indent=2), encoding="utf-8")
        self.append_log(f"プロジェクトを保存しました: {path}\n")

    def load_preset(self) -> None:
        path = filedialog.askopenfilename(
            initialdir=str(PRESET_DIR),
            filetypes=[("SRT Spectrum Video Composer Project", "*.fcproj"), ("JSON", "*.json"), ("All", "*.*")],
        )
        if not path:
            return
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        settings, ui_state = settings_and_ui_from_project_data(data)
        old_language = self.vars["language"].get()
        self._apply_project_ui_state(ui_state)
        if self.vars["language"].get() != old_language:
            self._build_ui(rebuild=True)
        self._apply_settings(settings)
        self.append_log(f"プロジェクトを読み込みました: {path}\n")

    def _preview_canvas_dimensions(self) -> tuple[int, int]:
        def configured_int(name: str, fallback: int) -> int:
            try:
                return int(float(self.preview.cget(name)))
            except Exception:
                return fallback

        try:
            cw = int(self.preview.winfo_width())
        except Exception:
            cw = 0
        try:
            ch = int(self.preview.winfo_height())
        except Exception:
            ch = 0
        if cw < 120:
            cw = configured_int("width", 420)
        if ch < 120:
            ch = configured_int("height", 270)
        return max(120, cw), max(120, ch)

    def _schedule_preview_redraw(self) -> None:
        self.after_idle(self._draw_preview)
        self.after(80, self._draw_preview)
        self.after(220, self._draw_preview)

    def _draw_preview(self) -> None:
        c = self.preview
        c.delete("all")
        try:
            w = int(self.vars["out_w"].get())
            h = int(self.vars["out_h"].get())
            sx = int(self.vars["spec_x"].get())
            sy = int(self.vars["spec_y"].get())
            sw = int(self.vars["spec_w"].get())
            sh = int(self.vars["spec_h"].get())
            margin = int(self.vars["bottom_margin"].get())
            font_size = int(self.vars["font_size"].get())
        except Exception:
            return

        cw, ch = self._preview_canvas_dimensions()
        header_h = 22
        preview_h = max(40, ch - header_h)
        scale = max(0.01, min((cw - 20) / max(1, w), (preview_h - 20) / max(1, h)))
        ox = (cw - w * scale) / 2
        oy = header_h + (preview_h - h * scale) / 2
        dw = max(2, int(w * scale))
        dh = max(2, int(h * scale))
        c.create_text(8, 6, text=self._preview_info_text(w, h), fill="#ffffff", anchor="nw")

        # Background image preview. This is a UI-only preview and uses the same
        # cover/crop idea as the FFmpeg background filter.
        bg_path = self.vars["background"].get().strip()
        active_scene = None
        if bool(self.vars["slideshow_enabled"].get()):
            try:
                preview_ms = int(float(self.vars["preview_time"].get()) * 1000)
            except Exception:
                preview_ms = 0
            active_scene = active_slideshow_scene(self._settings(), preview_ms)
            if active_scene is not None and active_scene.path:
                bg_path = active_scene.path
        bg_drawn = False
        if bg_path and Path(bg_path).exists() and Image is not None and ImageTk is not None:
            try:
                im = Image.open(bg_path).convert("RGB")
                iw, ih = im.size
                if self.vars["resolution_preset"].get() == BACKGROUND_SIZE_PRESET:
                    # Native-size mode: show the original image mapped directly to the preview rectangle.
                    im = im.resize((dw, dh), Image.LANCZOS)
                else:
                    cover_scale = max(w / max(1, iw), h / max(1, ih))
                    rw, rh = max(1, int(iw * cover_scale)), max(1, int(ih * cover_scale))
                    im = im.resize((rw, rh), Image.LANCZOS)
                    left = max(0, (rw - w) // 2)
                    top = max(0, (rh - h) // 2)
                    im = im.crop((left, top, left + w, top + h))
                    im = im.resize((dw, dh), Image.LANCZOS)
                self.preview_bg_photo = ImageTk.PhotoImage(im)
                c.create_image(int(ox), int(oy), image=self.preview_bg_photo, anchor="nw")
                bg_drawn = True
            except Exception:
                bg_drawn = False
        if not bg_drawn:
            c.create_rectangle(ox, oy, ox + dw, oy + dh, fill="#303030", outline="#777")
            if bg_path and Image is None:
                c.create_text(ox + 8, oy + 28, text="Pillow未導入のため背景表示不可", fill="#dddddd", anchor="nw")

        c.create_rectangle(ox, oy, ox + dw, oy + dh, outline="#777")

        # Spectrum rectangle preview. Show it only when a spectrum file is specified.
        if self.vars["spectrum_color"].get().strip():
            x1 = ox + sx * scale
            y1 = oy + sy * scale
            x2 = ox + (sx + sw) * scale
            y2 = oy + (sy + sh) * scale
            c.create_rectangle(x1, y1, x2, y2, outline="#00ccff", width=2)
            c.create_rectangle(x1, y1, x2, y2, outline="#003344")
            c.create_text((x1 + x2) / 2, (y1 + y2) / 2, text="Spectrum", fill="#00ccff")

        # Title preview. This is approximate, but follows the same anchor idea as ASS.
        title_preview_text = self.vars["title_text"].get().strip()
        if active_scene is not None and active_scene.title.strip():
            title_preview_text = active_scene.title.strip()
        if bool(self.vars["title_enabled"].get()) and title_preview_text:
            title_text = title_preview_text
            t_align = self.vars["title_alignment_label"].get()
            t_size = int(self.vars["title_font_size"].get())
            margin_x = int(self.vars["title_margin_x"].get())
            margin_y = int(self.vars["title_margin_y"].get())
            if t_align == "自由XY":
                t_x = int(self.vars["title_custom_x"].get())
                t_y = int(self.vars["title_custom_y"].get())
                anchor = "center"
            elif t_align in ("左上", "左中央", "左下"):
                t_x = margin_x
                anchor = "nw" if t_align == "左上" else ("w" if t_align == "左中央" else "sw")
            elif t_align in ("右上", "右中央", "右下"):
                t_x = w - margin_x
                anchor = "ne" if t_align == "右上" else ("e" if t_align == "右中央" else "se")
            else:
                t_x = w // 2
                anchor = "n" if t_align == "上中央" else ("center" if t_align == "中央" else "s")
            if t_align in ("左上", "上中央", "右上"):
                t_y = margin_y
            elif t_align in ("左下", "下中央", "右下"):
                t_y = h - margin_y
            elif t_align != "自由XY":
                t_y = h // 2
            title_font = self._canvas_font("title_font_name", max(8, int(t_size * scale)), "title_bold", "title_italic")
            tpx = ox + t_x * scale
            tpy = oy + t_y * scale
            title_outline = self.vars["title_outline_color"].get() or "#000000"
            title_color = self.vars["title_text_color"].get() or "#FFFFFF"
            c.create_text(tpx + 2, tpy + 2, text=title_text, fill=title_outline, font=title_font, anchor=anchor)
            c.create_text(tpx, tpy, text=title_text, fill=title_color, font=title_font, anchor=anchor)

        align = self.vars["alignment_label"].get()
        if align == "自由XY":
            tx = int(self.vars["custom_x"].get())
            ty = int(self.vars["custom_y"].get())
        elif align == "上中央":
            tx, ty = w // 2, margin + font_size
        elif align == "中央":
            tx, ty = w // 2, h // 2
        else:
            tx, ty = w // 2, h - margin

        text_color = self.vars["text_color"].get() or "#FFFFFF"
        outline_color = self.vars["outline_color"].get() or "#000000"
        preview_text = self._current_preview_text()
        # Canvas text cannot accurately emulate ASS wrapping, but multi-line text
        # is useful enough for a lightweight positional preview.
        display_lines = [line.strip() for line in preview_text.splitlines() if line.strip()]
        if display_lines:
            display_text = "\n".join(display_lines[:3])
            scaled_font = max(8, int(font_size * scale))
            px = ox + tx * scale
            py = oy + ty * scale
            subtitle_font = self._canvas_font("font_name", scaled_font, "bold", "italic")
            c.create_text(px + 2, py + 2, text=display_text, fill=outline_color, font=subtitle_font, justify="center")
            c.create_text(px, py, text=display_text, fill=text_color, font=subtitle_font, justify="center")



    def _preview_base_settings(self) -> AppSettings:
        settings = self._settings()
        # For preview, output path itself is not used, but input validation should still be strict.
        validate_settings(settings)
        self.vars["output"].set(settings.files.output)
        if not self.srt_items and settings.files.srt:
            self._load_srt_items(show_message=False)
        return settings

    def start_preview_png(self) -> None:
        if self.preview_thread and self.preview_thread.is_alive():
            messagebox.showinfo("実行中", "プレビュー生成はすでに実行中です。")
            return
        try:
            settings = self._preview_base_settings()
            preview_sec = max(0.0, float(self.vars["preview_time"].get()))
            selected_index = self._selected_srt_index()
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return
        self.preview_thread = threading.Thread(
            target=self._preview_png_worker,
            args=(settings, preview_sec, selected_index),
            daemon=True,
        )
        self.preview_thread.start()

    def _preview_png_worker(self, settings: AppSettings, preview_sec: float, selected_index: int | None) -> None:
        try:
            ass_path = str(WORK_DIR / "preview_static.ass")
            preview_path = str(WORK_DIR / "preview.png")
            generate_preview_ass_static(
                settings.files.srt,
                ass_path,
                settings.subtitle,
                settings.title,
                settings.output,
                int(preview_sec * 1000),
                selected_index=selected_index,
                background=settings.background,
            )
            cmd = build_preview_png_command(settings, ass_path, preview_path, preview_sec)
            self.append_log("\n=== 静止画プレビュー生成 ===\n")
            self.append_log(subprocess.list2cmdline(cmd) + "\n")
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **no_window_subprocess_kwargs(),
            )
            self.append_log(result.stdout)
            if result.returncode != 0:
                raise RuntimeError(f"FFmpegがエラー終了しました。code={result.returncode}")
            self.after(0, lambda: self._show_preview_image(preview_path))
        except Exception as e:
            self.append_log(f"\nERROR: {e}\n")
            self.after(0, lambda msg=str(e): messagebox.showerror("プレビュー生成エラー", msg))

    def _show_preview_image(self, path: str) -> None:
        c = self.preview
        c.delete("all")
        try:
            out_w = int(self.vars["out_w"].get())
            out_h = int(self.vars["out_h"].get())
        except Exception:
            out_w, out_h = 1920, 1080
        cw, ch = self._preview_canvas_dimensions()
        header_h = 22
        preview_h = max(40, ch - header_h)
        scale = max(0.01, min((cw - 20) / max(1, out_w), (preview_h - 20) / max(1, out_h)))
        dw = max(2, int(out_w * scale))
        dh = max(2, int(out_h * scale))
        ox = (cw - dw) / 2
        oy = header_h + (preview_h - dh) / 2

        if Image is not None and ImageTk is not None:
            im = Image.open(path).convert("RGB")
            im = im.resize((dw, dh), Image.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(im)
            c.create_image(int(ox), int(oy), image=self.preview_photo, anchor="nw")
        else:
            self.preview_photo = PhotoImage(file=path)
            c.create_image(cw // 2, int(oy + dh / 2), image=self.preview_photo, anchor="center")
        c.create_rectangle(ox, oy, ox + dw, oy + dh, outline="#777")
        c.create_text(8, 6, text=f"{self.t('ffmpeg_preview')}  {self._preview_info_text(out_w, out_h)}", fill="#ffffff", anchor="nw")
        self._show_large_preview_dialog(path)

    def _show_large_preview_dialog(self, path: str) -> None:
        if Image is None or ImageTk is None:
            open_in_default_app(path)
            return
        try:
            top = Toplevel(self)
            top.title(self.t("preview_window"))
            max_w = min(1280, max(800, self.winfo_screenwidth() - 160))
            max_h = min(800, max(500, self.winfo_screenheight() - 180))
            im = Image.open(path).convert("RGB")
            iw, ih = im.size
            scale = min(max_w / max(1, iw), max_h / max(1, ih), 1.0)
            dw, dh = max(2, int(iw * scale)), max(2, int(ih * scale))
            im = im.resize((dw, dh), Image.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            lbl = Label(top, image=photo, bg="#202020")
            lbl.image = photo
            lbl.pack(padx=10, pady=10)
            Button(top, text=self.t("close"), command=top.destroy).pack(pady=(0, 10))
        except Exception as e:
            self.append_log(f"静止画プレビューダイアログ表示エラー: {e}\n")
    def start_preview_video(self) -> None:
        if self.preview_thread and self.preview_thread.is_alive():
            messagebox.showinfo("実行中", "プレビュー生成はすでに実行中です。")
            return
        try:
            settings = self._preview_base_settings()
            duration_sec = max(1.0, float(self.vars["preview_duration"].get()))
            center_sec = max(0.0, float(self.vars["preview_time"].get()))
            start_sec = max(0.0, center_sec - duration_sec / 2)
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return
        self.preview_thread = threading.Thread(
            target=self._preview_video_worker,
            args=(settings, start_sec, duration_sec),
            daemon=True,
        )
        self.preview_thread.start()

    def _preview_video_worker(self, settings: AppSettings, start_sec: float, duration_sec: float) -> None:
        try:
            ass_path = str(WORK_DIR / "preview_segment.ass")
            preview_path = str(WORK_DIR / "preview.mp4")
            generate_preview_ass_segment(
                settings.files.srt,
                ass_path,
                settings.subtitle,
                settings.title,
                settings.output,
                int(start_sec * 1000),
                int(duration_sec * 1000),
                background=settings.background,
            )
            cmd = build_preview_video_command(settings, ass_path, preview_path, start_sec, duration_sec)
            self.append_log("\n=== 動画プレビュー生成 ===\n")
            self.append_log(subprocess.list2cmdline(cmd) + "\n")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **no_window_subprocess_kwargs(),
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.append_log(line)
            code = process.wait()
            if code != 0:
                raise RuntimeError(f"FFmpegがエラー終了しました。code={code}")
            self.append_log(f"動画プレビューを作成しました: {preview_path}\n")
            self.after(0, lambda: open_in_default_app(preview_path))
        except Exception as e:
            self.append_log(f"\nERROR: {e}\n")
            self.after(0, lambda msg=str(e): messagebox.showerror("動画プレビュー生成エラー", msg))

    def append_log(self, text: str) -> None:
        # Tkinter widgets must be updated from the main UI thread.
        # FFmpeg workers call this method frequently, so marshal log updates via after().
        if getattr(self, "ui_thread_id", None) != threading.get_ident():
            try:
                self.after(0, lambda t=text: self.append_log(t))
            except Exception:
                pass
            return
        if not hasattr(self, "log"):
            return
        self.log.insert(END, text)
        self.log.see(END)
        self.update_idletasks()

    def show_command(self) -> None:
        try:
            settings = self._settings()
            validate_settings(settings)
            self.vars["output"].set(settings.files.output)
            ass_path = str(WORK_DIR / "subtitle_preview.ass")
            duration_ms = int(round(probe_media_duration(settings.files.audio) * 1000))
            generate_ass(
                settings.files.srt,
                ass_path,
                settings.subtitle,
                settings.title,
                settings.output,
                background=settings.background,
                duration_ms=duration_ms,
            )
            cmd = build_ffmpeg_command(settings, ass_path)
            self.append_log("\n--- FFmpeg command ---\n")
            self.append_log(subprocess.list2cmdline(cmd) + "\n")
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def open_output_dir(self) -> None:
        output = self.vars["output"].get().strip()
        if not output:
            self._auto_fill_output_from_audio(force=True)
            output = self.vars["output"].get().strip()
        if not output:
            messagebox.showerror("エラー", "出力MP4の保存先が未設定です。")
            return
        output = normalize_output_path(output)
        parent = Path(output).expanduser().parent
        if str(parent) == ".":
            parent = APP_DIR
        if not parent.exists():
            messagebox.showerror("エラー", f"出力先フォルダが存在しません:\n{parent}")
            return
        try:
            open_in_default_app(parent)
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def start_render(self) -> None:
        if self.render_thread and self.render_thread.is_alive():
            messagebox.showinfo("実行中", "レンダーはすでに実行中です。")
            return
        try:
            settings = self._settings()
            validate_settings(settings)
            self.vars["output"].set(settings.files.output)
            find_tool("ffmpeg")
            find_tool("ffprobe")
        except Exception as e:
            messagebox.showerror("エラー", str(e))
            return
        self.render_thread = threading.Thread(target=self._render_worker, args=(settings,), daemon=True)
        self.render_thread.start()

    def _render_worker(self, settings: AppSettings) -> None:
        try:
            ass_path = str(WORK_DIR / "subtitle.ass")
            duration_ms = int(round(probe_media_duration(settings.files.audio) * 1000))
            generate_ass(
                settings.files.srt,
                ass_path,
                settings.subtitle,
                settings.title,
                settings.output,
                background=settings.background,
                duration_ms=duration_ms,
            )
            cmd = build_ffmpeg_command(settings, ass_path)
            self.append_log("\n=== レンダー開始 ===\n")
            self.append_log(subprocess.list2cmdline(cmd) + "\n\n")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **no_window_subprocess_kwargs(),
            )
            assert process.stdout is not None
            for line in process.stdout:
                self.append_log(line)
            code = process.wait()
            if code == 0:
                self.append_log("\n=== 完了 ===\n")
                self.after(0, lambda: messagebox.showinfo("完了", "レンダーが完了しました。"))
            else:
                self.append_log(f"\n=== FFmpeg error: code {code} ===\n")
                self.after(0, lambda c=code: messagebox.showerror("FFmpegエラー", f"FFmpegがエラー終了しました。code={c}"))
        except Exception as e:
            self.append_log(f"\nERROR: {e}\n")
            self.after(0, lambda msg=str(e): messagebox.showerror("エラー", msg))


def main(argv: list[str] | None = None) -> None:
    handoff_path = parse_startup_args(sys.argv[1:] if argv is None else argv)
    try:
        app = App(handoff_path=handoff_path)
        app.mainloop()
    except Exception as exc:
        messagebox.showerror("起動エラー", str(exc))

if __name__ == "__main__":
    main()
