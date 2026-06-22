# -*- coding: utf-8 -*-
"""Motion-shaping layer for spectrum data.

This layer turns raw per-frame/per-band dB values into display-friendly 0..1
motion values.  The qualitative "generation/motion" controls should map here
so future visual styles can share the same perceived motion.
"""
from __future__ import annotations

import numpy as np

from spectrum_types import MotionSettings

def map_db_to_dynamic_values(
    db: np.ndarray,
    motion: MotionSettings,
) -> np.ndarray:
    """Map per-frame/per-band dB values to 0..1 Dynamic bar values.

    This is the public-name equivalent of the stable v0.9 Filmora-like mode:
    per-frame relative peak normalization + temporal pulse/baseline emphasis.
    """
    rng = max(6.0, float(motion.relative_range_db))
    pct = float(np.clip(motion.peak_percentile, 50.0, 99.5))
    peak = np.percentile(db, pct, axis=1, keepdims=True)
    floor = peak - rng
    rel = np.clip((db - floor) / rng, 0.0, 1.0)

    cut = float(np.clip(motion.base_cut, 0.0, 0.80))
    if cut > 0:
        rel = np.clip((rel - cut) / (1.0 - cut), 0.0, 1.0)

    # Absolute energy gate.
    #
    # Relative peak normalization alone is not enough for silence: when all FFT
    # bands are near the noise floor, the "relative" values can still become
    # high because every band is close to the frame peak.  Earlier versions kept
    # a minimum gate of 0.18, which left small bars visible in near-silent parts.
    # Here the gate reaches true zero below min_db, while still fading in
    # smoothly for quiet musical passages.
    denom = max(1.0e-6, float(motion.max_db - motion.min_db))
    energy = np.clip((peak - motion.min_db) / denom, 0.0, 1.0)
    gate = energy * energy * (3.0 - 2.0 * energy)  # smoothstep, 0..1
    values = np.clip(rel * gate, 0.0, 1.0).astype(np.float32)

    # Temporal trough/pulse emphasis.
    pulse_amount = float(np.clip(motion.pulse_amount, 0.0, 1.0))
    pulse_speed = float(np.clip(motion.pulse_speed, 0.01, 0.95))
    if pulse_amount > 0:
        frame_count, bars = values.shape
        pulsed = np.zeros_like(values)
        baseline = np.zeros((bars,), dtype=np.float32)
        for i in range(frame_count):
            v = values[i]
            baseline = baseline + (v - baseline) * pulse_speed
            diff = np.maximum(v - baseline, 0.0)
            denom = np.maximum(1.0 - baseline, 1.0e-4)
            p = np.clip(diff / denom, 0.0, 1.0)
            pulsed[i] = (1.0 - pulse_amount) * v + pulse_amount * p
        values = pulsed

    return smooth_values(values, motion.attack, motion.release)

def smooth_values(values: np.ndarray, attack: float, release: float) -> np.ndarray:
    attack = float(np.clip(attack, 0.01, 1.0))
    release = float(np.clip(release, 0.01, 1.0))
    smoothed = np.zeros_like(values)
    current = np.zeros((values.shape[1],), dtype=np.float32)
    for i in range(values.shape[0]):
        target = values[i]
        coeff = np.where(target >= current, attack, release).astype(np.float32)
        current = current + (target - current) * coeff
        smoothed[i] = current
    return smoothed

