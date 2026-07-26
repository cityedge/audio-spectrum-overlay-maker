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

from spectrum_types import EncodeSettings, LogFn, PostTransformSettings, RenderStyle, TransformSettings
from spectrum_utils import log, no_window_subprocess_kwargs, resolve_external_tool
from spectrum_draw import draw_spectrum_frame, compute_band_color_offset
from spectrum_post_transform import PostTransformApplier
from spectrum_cancel import RenderCancelToken, RenderCancelled

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
    return subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE, **no_window_subprocess_kwargs())

def render_video(
    bar_values: np.ndarray,
    output_path: Path,
    style: RenderStyle,
    encode: EncodeSettings,
    log_callback: LogFn = None,
    transform: TransformSettings | None = None,
    post_transform: PostTransformSettings | None = None,
    peak_values: np.ndarray | None = None,
    audio_values: np.ndarray | None = None,
    cancel_token: RenderCancelToken | None = None,
) -> None:
    frame_count, bars = bar_values.shape
    if bars != style.bars:
        raise RuntimeError("Internal error: bar_values does not match style.bars.")
    if peak_values is not None and peak_values.shape != bar_values.shape:
        raise RuntimeError("Internal error: peak_values does not match bar_values.")
    if audio_values is not None and audio_values.shape != bar_values.shape:
        raise RuntimeError("Internal error: audio_values does not match bar_values.")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    log(f"Writing video: {output_path}", log_callback)
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    proc = open_ffmpeg_encoder(output_path, style.width, style.height, style.fps, encode)
    if cancel_token is not None:
        cancel_token.register_process(proc)
    if proc.stdin is None:
        raise RuntimeError("Could not open ffmpeg input pipe.")
    progress_step = max(1, frame_count // 20)
    post_applier = PostTransformApplier(post_transform, style.width, style.height, style.fps, style.background_color)
    cancelled = False
    keep_partial = False
    failed = False
    written_frames = 0
    try:
        for i in range(frame_count):
            if cancel_token is not None:
                if cancel_token.is_cancelled and cancel_token.keep_partial_videos:
                    keep_partial = True
                    break
                cancel_token.raise_if_cancelled()
            band_offset = compute_band_color_offset(i, transform.scroll_mode, transform.scroll_step_frames) if transform is not None else 0
            peaks = peak_values[i] if peak_values is not None else None
            frame = draw_spectrum_frame(bar_values[i], style, band_color_offset=band_offset, peak_values=peaks)
            frame = post_applier.apply(frame, i, audio_values[i] if audio_values is not None else bar_values[i])
            proc.stdin.write(frame.tobytes())
            written_frames += 1
            if frame_count >= 300 and ((i + 1) % progress_step == 0 or i + 1 == frame_count):
                log(f"Writing: {100.0 * (i + 1) / frame_count:5.1f}%", log_callback)
    except BrokenPipeError:
        failed = True
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        if cancel_token is not None and cancel_token.is_cancelled and not cancel_token.keep_partial_videos:
            cancelled = True
            raise RenderCancelled("Render cancelled by user.")
        raise RuntimeError("ffmpeg stopped unexpectedly.\n" + stderr)
    except OSError:
        failed = True
        if cancel_token is not None and cancel_token.is_cancelled and not cancel_token.keep_partial_videos:
            cancelled = True
            raise RenderCancelled("Render cancelled by user.")
        raise
    except RenderCancelled:
        cancelled = True
        raise
    finally:
        try:
            proc.stdin.close()
        except Exception:
            pass
        if cancelled or failed or (cancel_token is not None and cancel_token.is_cancelled and not cancel_token.keep_partial_videos):
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    proc.kill()
                except OSError:
                    pass
                proc.wait()
        if cancel_token is not None and (cancelled or failed or (cancel_token.is_cancelled and not cancel_token.keep_partial_videos)):
            cancel_token.unregister_process(proc)
    if cancel_token is not None and cancel_token.is_cancelled and cancel_token.keep_partial_videos:
        keep_partial = True
    try:
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        return_code = proc.wait()
    finally:
        if cancel_token is not None:
            cancel_token.unregister_process(proc)
    if return_code != 0:
        raise RuntimeError("Video encoding failed with ffmpeg.\n" + stderr)
    if keep_partial:
        seconds = written_frames / max(1, style.fps)
        log(f"Cancelled output finalized: {output_path} ({written_frames:,} frames / {seconds:.2f}s)", log_callback)
        raise RenderCancelled(keep_partial_videos=True)
