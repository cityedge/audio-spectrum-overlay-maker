# -*- coding: utf-8 -*-
"""Audio/ffmpeg input helpers.

This layer is responsible for checking the external ffmpeg environment,
probing duration, and decoding input audio into float32 mono samples.  It does
not know anything about spectrum display styles.
"""
from __future__ import annotations

import math
import subprocess
from pathlib import Path

import numpy as np

from spectrum_types import LogFn
from spectrum_utils import find_external_tool, log, no_window_subprocess_kwargs, resolve_external_tool
from spectrum_cancel import RenderCancelToken

def check_environment() -> tuple[bool, str]:
    missing = []
    if find_external_tool("ffmpeg") is None:
        missing.append("ffmpeg")
    if find_external_tool("ffprobe") is None:
        missing.append("ffprobe")
    if missing:
        return False, (
            "Missing external tool(s): "
            + ", ".join(missing)
            + "\nPlace ffmpeg/ffprobe in the app's bin folder, or add them to PATH."
        )
    return True, "OK"

def run_ffprobe_duration(path: Path) -> float | None:
    cmd = [
        resolve_external_tool("ffprobe"), "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True, **no_window_subprocess_kwargs())
        value = proc.stdout.strip()
        if not value:
            return None
        duration = float(value)
        if math.isfinite(duration) and duration > 0:
            return duration
    except Exception:
        return None
    return None

def decode_audio_to_float32_mono(
    path: Path,
    sample_rate: int,
    start: float,
    duration: float | None,
    log_callback: LogFn = None,
    cancel_token: RenderCancelToken | None = None,
) -> np.ndarray:
    cmd = [resolve_external_tool("ffmpeg"), "-hide_banner", "-loglevel", "error"]
    if start > 0:
        cmd += ["-ss", f"{start:.6f}"]
    cmd += ["-i", str(path)]
    if duration is not None and duration > 0:
        cmd += ["-t", f"{duration:.6f}"]
    cmd += [
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-f", "f32le", "-acodec", "pcm_f32le", "pipe:1",
    ]
    log("Loading audio...", log_callback)
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **no_window_subprocess_kwargs())
    if cancel_token is not None:
        cancel_token.register_process(proc)
    try:
        while True:
            try:
                stdout, stderr = proc.communicate(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if cancel_token is not None:
                    cancel_token.raise_if_cancelled()
    finally:
        if cancel_token is not None:
            if cancel_token.is_cancelled and proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
            if cancel_token.is_cancelled:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except OSError:
                        pass
                    proc.wait()
            cancel_token.unregister_process(proc)
    if cancel_token is not None:
        cancel_token.raise_if_cancelled()
    if proc.returncode != 0:
        stderr_text = stderr.decode("utf-8", errors="replace")
        raise RuntimeError("Failed to load audio with ffmpeg.\n" + stderr_text)
    if not stdout:
        raise RuntimeError("No audio data was loaded.")
    audio = np.frombuffer(stdout, dtype=np.float32).copy()
    audio = np.nan_to_num(audio, nan=0.0, posinf=0.0, neginf=0.0)
    audio = np.clip(audio, -1.0, 1.0)
    if audio.size == 0:
        raise RuntimeError("No audio samples were found.")
    return audio
