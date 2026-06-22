# -*- coding: utf-8 -*-
"""Video encoding layer.

This layer owns the ffmpeg rawvideo pipe and frame-writing loop.  It receives
already transformed display values and delegates frame drawing to the drawing
layer.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np

from spectrum_types import EncodeSettings, LogFn, RenderStyle, TransformSettings
from spectrum_utils import log, resolve_external_tool
from spectrum_draw import draw_spectrum_frame, compute_band_color_offset

def open_ffmpeg_encoder(output_path: Path, width: int, height: int, fps: int, encode: EncodeSettings) -> subprocess.Popen:
    cmd = [
        resolve_external_tool("ffmpeg"), "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{width}x{height}", "-r", str(fps),
        "-i", "pipe:0", "-an", "-c:v", encode.encoder,
    ]
    if encode.encoder in {"libx264", "libx265"}:
        cmd += ["-preset", encode.preset, "-crf", str(encode.crf)]
    elif "nvenc" in encode.encoder:
        cmd += ["-preset", "p4", "-cq", str(encode.crf)]
    cmd += ["-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)]
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)

def render_video(bar_values: np.ndarray, output_path: Path, style: RenderStyle, encode: EncodeSettings, log_callback: LogFn = None, transform: TransformSettings | None = None) -> None:
    frame_count, bars = bar_values.shape
    if bars != style.bars:
        raise RuntimeError("Internal error: bar_values does not match style.bars.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"Writing video: {output_path}", log_callback)
    proc = open_ffmpeg_encoder(output_path, style.width, style.height, style.fps, encode)
    if proc.stdin is None:
        raise RuntimeError("Could not open ffmpeg input pipe.")
    progress_step = max(1, frame_count // 20)
    try:
        for i in range(frame_count):
            band_offset = compute_band_color_offset(i, transform.scroll_mode, transform.scroll_step_frames) if transform is not None else 0
            frame = draw_spectrum_frame(bar_values[i], style, band_color_offset=band_offset)
            proc.stdin.write(frame.tobytes())
            if frame_count >= 300 and ((i + 1) % progress_step == 0 or i + 1 == frame_count):
                log(f"Writing: {100.0 * (i + 1) / frame_count:5.1f}%", log_callback)
    except BrokenPipeError:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        raise RuntimeError("ffmpeg stopped unexpectedly.\n" + stderr)
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
    stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
    return_code = proc.wait()
    if return_code != 0:
        raise RuntimeError("Video encoding failed with ffmpeg.\n" + stderr)

