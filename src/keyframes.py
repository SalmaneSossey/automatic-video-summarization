from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional
import numpy as np
import cv2

from src.frame_sampling import SampledFrame


@dataclass
class Shot:
    start_sec: float
    end_sec: float


@dataclass
class ScoredKeyframe:
    """A keyframe with quality scores."""
    frame: SampledFrame
    sharpness_score: float
    motion_score: float  # Lower = less motion blur
    combined_score: float
    shot_index: int


def score_frame_sharpness(image_bgr: np.ndarray) -> float:
    """
    Compute sharpness score using Laplacian variance.
    Higher value = sharper image.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return float(laplacian.var())


def score_frame_motion(
    prev_frame: Optional[np.ndarray], 
    curr_frame: np.ndarray
) -> float:
    """
    Estimate motion blur by computing frame difference.
    Lower value = less motion (more stable frame).
    Returns 0.0 if no previous frame.
    """
    if prev_frame is None:
        return 0.0
    
    # Convert to grayscale
    gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
    gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
    
    # Compute absolute difference
    diff = cv2.absdiff(gray_prev, gray_curr)
    return float(np.mean(diff))


def score_frame(
    frame: SampledFrame,
    prev_image: Optional[np.ndarray] = None,
    w_sharpness: float = 0.7,
    w_motion: float = 0.3,
) -> Tuple[float, float, float]:
    """
    Compute combined quality score for a frame.
    
    Returns:
        Tuple of (sharpness_score, motion_score, combined_score)
        Higher combined_score = better quality frame.
    """
    sharpness = score_frame_sharpness(frame.image_bgr)
    motion = score_frame_motion(prev_image, frame.image_bgr)
    
    # Normalize sharpness (typical range 0-5000, we cap at 1000 for normalization)
    norm_sharpness = min(sharpness / 1000.0, 1.0)
    
    # Motion: lower is better, so we invert (typical range 0-50)
    norm_motion = max(0.0, 1.0 - motion / 50.0)
    
    combined = w_sharpness * norm_sharpness + w_motion * norm_motion
    
    return sharpness, motion, combined


def build_shots(boundaries_sec: List[float], video_duration_sec: float) -> List[Shot]:
    """
    Convert boundary start times into [start, end] shot intervals.
    """
    b = sorted(boundaries_sec)
    shots: List[Shot] = []
    for i in range(len(b)):
        start = b[i]
        end = b[i + 1] if i + 1 < len(b) else video_duration_sec
        if end > start:
            shots.append(Shot(start_sec=start, end_sec=end))
    return shots


def pick_keyframes_middle(shots: List[Shot], sampled_frames: List[SampledFrame]) -> List[SampledFrame]:
    """
    For each shot, pick the sampled frame closest to the shot midpoint.
    """
    times = np.array([f.timestamp_sec for f in sampled_frames], dtype=np.float32)

    keyframes: List[SampledFrame] = []
    for shot in shots:
        mid = 0.5 * (shot.start_sec + shot.end_sec)
        idx = int(np.argmin(np.abs(times - mid)))
        keyframes.append(sampled_frames[idx])
    return keyframes


def pick_keyframes_best(
    shots: List[Shot], 
    sampled_frames: List[SampledFrame],
    w_sharpness: float = 0.7,
    w_motion: float = 0.3,
) -> List[ScoredKeyframe]:
    """
    For each shot, pick the highest-quality frame based on sharpness and motion.
    
    Returns list of ScoredKeyframe with quality metrics.
    """
    times = np.array([f.timestamp_sec for f in sampled_frames], dtype=np.float32)
    
    scored_keyframes: List[ScoredKeyframe] = []
    
    for shot_idx, shot in enumerate(shots):
        # Find frames within this shot
        mask = (times >= shot.start_sec) & (times < shot.end_sec)
        shot_frame_indices = np.where(mask)[0]
        
        if len(shot_frame_indices) == 0:
            # Fallback: find closest frame to shot midpoint
            mid = 0.5 * (shot.start_sec + shot.end_sec)
            closest_idx = int(np.argmin(np.abs(times - mid)))
            shot_frame_indices = [closest_idx]
        
        # Score each frame in the shot
        best_frame = None
        best_scores = (0.0, 0.0, -1.0)
        
        prev_image = None
        for i, frame_idx in enumerate(shot_frame_indices):
            frame = sampled_frames[frame_idx]
            
            # Get previous frame for motion scoring
            if i > 0:
                prev_image = sampled_frames[shot_frame_indices[i-1]].image_bgr
            
            sharpness, motion, combined = score_frame(
                frame, prev_image, w_sharpness, w_motion
            )
            
            if combined > best_scores[2]:
                best_scores = (sharpness, motion, combined)
                best_frame = frame
        
        if best_frame is not None:
            scored_keyframes.append(ScoredKeyframe(
                frame=best_frame,
                sharpness_score=best_scores[0],
                motion_score=best_scores[1],
                combined_score=best_scores[2],
                shot_index=shot_idx,
            ))
    
    return scored_keyframes


def select_highlight_segments(
    shots: List[Shot],
    sampled_frames: List[SampledFrame],
    segment_duration: float = 3.0,
    w_sharpness: float = 0.7,
    w_motion: float = 0.3,
) -> List[Tuple[float, float, float, int]]:
    """
    Select the best segment from each shot for the summary.
    
    For each shot, finds the highest-quality window of segment_duration seconds.
    
    Returns:
        List of (start_sec, end_sec, score, shot_index) tuples.
    """
    times = np.array([f.timestamp_sec for f in sampled_frames], dtype=np.float32)
    highlights: List[Tuple[float, float, float, int]] = []
    
    for shot_idx, shot in enumerate(shots):
        shot_duration = shot.end_sec - shot.start_sec
        
        # If shot is shorter than segment_duration, use the whole shot
        if shot_duration <= segment_duration:
            # Score the shot
            mask = (times >= shot.start_sec) & (times < shot.end_sec)
            shot_frames = [sampled_frames[i] for i in np.where(mask)[0]]
            
            if shot_frames:
                scores = [score_frame(f)[2] for f in shot_frames]
                avg_score = np.mean(scores)
            else:
                avg_score = 0.5
            
            highlights.append((shot.start_sec, shot.end_sec, float(avg_score), shot_idx))
            continue
        
        # Find frames in this shot
        mask = (times >= shot.start_sec) & (times < shot.end_sec)
        shot_frame_indices = np.where(mask)[0]
        
        if len(shot_frame_indices) < 2:
            highlights.append((shot.start_sec, shot.start_sec + segment_duration, 0.5, shot_idx))
            continue
        
        # Slide window to find best segment
        best_segment = (shot.start_sec, shot.start_sec + segment_duration, 0.0)
        
        # Get all possible window start times
        window_starts = times[shot_frame_indices]
        window_starts = window_starts[window_starts + segment_duration <= shot.end_sec]
        
        if len(window_starts) == 0:
            window_starts = [shot.start_sec]
        
        for win_start in window_starts:
            win_end = win_start + segment_duration
            win_mask = (times >= win_start) & (times < win_end)
            win_frame_indices = np.where(win_mask)[0]
            
            if len(win_frame_indices) == 0:
                continue
            
            # Score frames in this window
            scores = []
            prev_img = None
            for fi in win_frame_indices:
                _, _, combined = score_frame(sampled_frames[fi], prev_img, w_sharpness, w_motion)
                scores.append(combined)
                prev_img = sampled_frames[fi].image_bgr
            
            avg_score = np.mean(scores)
            
            if avg_score > best_segment[2]:
                best_segment = (float(win_start), float(win_end), float(avg_score))
        
        highlights.append((best_segment[0], best_segment[1], best_segment[2], shot_idx))
    
    return highlights
