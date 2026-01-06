from __future__ import annotations

import cv2
import numpy as np
from dataclasses import dataclass
from typing import List


@dataclass
class SampledFrame:
    frame_index: int         # original frame index in the video
    timestamp_sec: float     # time in seconds
    image_bgr: np.ndarray    # OpenCV frame (BGR)


def sample_frames(video_path: str, fps_sample: float = 8.0) -> List[SampledFrame]:
    """
    Sample frames from a video at approximately fps_sample frames per second.

    Returns a list of SampledFrame with original frame indices and timestamps.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Invalid FPS reported by OpenCV.")

    step = max(1, int(round(fps / fps_sample)))  # e.g., 25/8 ≈ 3 => take every 3rd frame

    frames: List[SampledFrame] = []
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % step == 0:
            t = frame_idx / fps
            frames.append(SampledFrame(frame_index=frame_idx, timestamp_sec=t, image_bgr=frame))

        frame_idx += 1

    cap.release()
    return frames
