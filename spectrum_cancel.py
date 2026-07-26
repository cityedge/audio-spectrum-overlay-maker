# -*- coding: utf-8 -*-
"""Cooperative cancellation for spectrum rendering workers."""
from __future__ import annotations

import subprocess
import threading


class RenderCancelled(RuntimeError):
    """Raised when the user cancels an active render."""

    def __init__(self, message: str = "Render cancelled by user.", *, keep_partial_videos: bool = False) -> None:
        super().__init__(message)
        self.keep_partial_videos = bool(keep_partial_videos)


def _terminate_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass


class RenderCancelToken:
    """Shares one cancellation request across decoding and parallel encoders."""

    def __init__(self, *, keep_partial_videos: bool = False) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._processes: set[subprocess.Popen[bytes]] = set()
        self.keep_partial_videos = bool(keep_partial_videos)

    @property
    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise RenderCancelled(keep_partial_videos=self.keep_partial_videos)

    def register_process(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            self._processes.add(process)
            cancelled = self._event.is_set()
        if cancelled and not self.keep_partial_videos:
            _terminate_process(process)

    def unregister_process(self, process: subprocess.Popen[bytes]) -> None:
        with self._lock:
            self._processes.discard(process)

    def cancel(self) -> None:
        self._event.set()
        if self.keep_partial_videos:
            return
        with self._lock:
            processes = list(self._processes)
        for process in processes:
            _terminate_process(process)
