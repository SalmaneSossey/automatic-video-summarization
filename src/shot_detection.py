from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import numpy as np


@dataclass
class ShotDetectionParams:
    smooth_win: int = 7            # odd number recommended (5, 7, 9...)
    threshold_percentile: float = 95.0
    min_shot_len_sec: float = 1.0  # avoid cuts too close to each other
    min_gap_sec: float = 1.5       # merge boundaries closer than this
    min_shot_duration_sec: float = 2.0  # drop shots shorter than this


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


def merge_close_boundaries(boundaries_sec: List[float], min_gap_sec: float = 1.5) -> List[float]:
    """
    Merge boundaries that are closer than min_gap_sec.
    Keeps the first boundary in each cluster.
    """
    if len(boundaries_sec) <= 1:
        return boundaries_sec
    
    sorted_b = sorted(boundaries_sec)
    merged = [sorted_b[0]]
    
    for b in sorted_b[1:]:
        if b - merged[-1] >= min_gap_sec:
            merged.append(b)
        # else: skip this boundary (too close to previous)
    
    return merged


def filter_short_shots(
    boundaries_sec: List[float], 
    video_duration_sec: float,
    min_duration_sec: float = 2.0
) -> List[float]:
    """
    Remove boundaries that would create shots shorter than min_duration_sec.
    Keeps shot boundaries that result in adequately long shots.
    """
    if len(boundaries_sec) <= 1:
        return boundaries_sec
    
    sorted_b = sorted(boundaries_sec)
    filtered = [sorted_b[0]]  # Always keep the first boundary (0.0)
    
    for i in range(1, len(sorted_b)):
        current = sorted_b[i]
        prev = filtered[-1]
        
        # Check if this shot would be long enough
        shot_duration = current - prev
        
        # Also check the next shot duration (if not last boundary)
        if i < len(sorted_b) - 1:
            next_boundary = sorted_b[i + 1]
            next_shot_duration = next_boundary - current
        else:
            # Last boundary - check remaining duration to video end
            next_shot_duration = video_duration_sec - current
        
        # Keep boundary if both resulting shots are long enough
        if shot_duration >= min_duration_sec and next_shot_duration >= min_duration_sec:
            filtered.append(current)
        elif shot_duration >= min_duration_sec and i == len(sorted_b) - 1:
            # Last boundary, only check current shot duration
            if next_shot_duration >= min_duration_sec * 0.5:  # More lenient for last shot
                filtered.append(current)
    
    return filtered


def detect_shot_boundaries(
    dist_times: List[float],
    distances: np.ndarray,
    params: ShotDetectionParams,
    video_duration_sec: float = None,
) -> Tuple[np.ndarray, float, List[float]]:
    """
    Returns:
      - smoothed distances
      - threshold value
      - boundary times (seconds), including 0.0
    
    Post-processing steps:
      1. Non-max suppression based on min_shot_len_sec
      2. Merge boundaries closer than min_gap_sec
      3. Filter out shots shorter than min_shot_duration_sec
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
    
    # Post-processing: merge close boundaries
    boundary_times = merge_close_boundaries(boundary_times, params.min_gap_sec)
    
    # Post-processing: filter short shots
    if video_duration_sec is not None and video_duration_sec > 0:
        boundary_times = filter_short_shots(
            boundary_times, 
            video_duration_sec, 
            params.min_shot_duration_sec
        )

    return smoothed, thr, boundary_times
