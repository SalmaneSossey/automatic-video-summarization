from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class ShotDetectionParams:
    smooth_win: int = 7            # odd number recommended (5, 7, 9...)
    threshold_percentile: float = 95.0
    min_shot_len_sec: float = 1.0  # avoid cuts too close to each other


def moving_average(x: np.ndarray, win: int) -> np.ndarray:
    """
    Simple moving average smoothing.
    """
    if win <= 1:
        return x.copy()
    kernel = np.ones(win, dtype=np.float32) / float(win)
    # same length output
    return np.convolve(x, kernel, mode="same")


def auto_threshold(x: np.ndarray, percentile: float = 95.0) -> float:
    """
    Automatic threshold based on percentile of the (smoothed) distance curve.
    Example: 95th percentile => only top 5% peaks are considered.
    """
    percentile = float(np.clip(percentile, 50.0, 99.9))
    return float(np.percentile(x, percentile))


def find_local_maxima(x: np.ndarray, thr: float) -> List[int]:
    """
    Return indices i where x[i] is a local maximum and x[i] >= thr.
    """
    idx = []
    for i in range(1, len(x) - 1):
        if x[i] >= thr and x[i] > x[i - 1] and x[i] >= x[i + 1]:
            idx.append(i)
    return idx


def non_max_suppression(indices: List[int], scores: np.ndarray, min_gap: int) -> List[int]:
    """
    If multiple peaks occur within min_gap, keep only the strongest.
    """
    if not indices:
        return []

    # sort candidates by score descending
    sorted_idx = sorted(indices, key=lambda i: scores[i], reverse=True)

    selected: List[int] = []
    for i in sorted_idx:
        if all(abs(i - j) > min_gap for j in selected):
            selected.append(i)

    return sorted(selected)


def detect_shot_boundaries(
    dist_times: List[float],
    distances: np.ndarray,
    params: ShotDetectionParams
) -> Tuple[np.ndarray, float, List[float]]:
    """
    Returns:
      - smoothed distances
      - threshold value
      - boundary times (seconds), including 0.0
    """
    if len(dist_times) != len(distances):
        raise ValueError("dist_times and distances must have same length.")

    smoothed = moving_average(distances, params.smooth_win)
    thr = auto_threshold(smoothed, params.threshold_percentile)

    candidates = find_local_maxima(smoothed, thr)

    # convert min_shot_len_sec to min_gap in samples
    dt = np.median(np.diff(np.array(dist_times))) if len(dist_times) > 2 else 0.1
    min_gap = int(round(params.min_shot_len_sec / max(dt, 1e-6)))

    peaks = non_max_suppression(candidates, smoothed, min_gap=min_gap)

    boundary_times = [0.0] + [dist_times[i] for i in peaks]
    boundary_times = sorted(set(boundary_times))

    return smoothed, thr, boundary_times
