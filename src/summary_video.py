from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import cv2
import numpy as np

from src.keyframes import Shot


def _resize_keep_aspect(frame_bgr: np.ndarray, out_width: int) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    if w == out_width:
        return frame_bgr
    scale = out_width / float(w)
    out_h = int(round(h * scale))
    return cv2.resize(frame_bgr, (out_width, out_h), interpolation=cv2.INTER_AREA)


def make_summary_video(
    video_path: str,
    shots: List[Shot],
    out_path: Path,
    secs_per_shot: float = 1.5,
    out_width: int = 1280,
    max_duration: float = 0.0,
) -> Tuple[float, int]:
    """
    Create a summary video by concatenating secs_per_shot seconds from the start of each shot.
    
    Args:
        video_path: Input video file path
        shots: List of Shot objects to include
        out_path: Output video path
        secs_per_shot: Seconds to include from each shot
        out_width: Output video width
        max_duration: Maximum total duration (0 = no limit)
        
    Returns (fps, total_written_frames).
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        raise RuntimeError("Invalid FPS from OpenCV.")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    max_frames = int(max_duration * fps) if max_duration > 0 else float('inf')

    # Prepare writer after reading the first frame (so we know output height)
    writer = None
    written = 0

    def open_writer(sample_frame: np.ndarray, path: Path) -> cv2.VideoWriter:
        frame_out = _resize_keep_aspect(sample_frame, out_width)
        h, w = frame_out.shape[:2]
        path.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        vw = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
        if not vw.isOpened():
            # Fallback to AVI if mp4 codec fails on some machines
            fallback = path.with_suffix(".avi")
            fourcc2 = cv2.VideoWriter_fourcc(*"XVID")
            vw = cv2.VideoWriter(str(fallback), fourcc2, fps, (w, h))
            if not vw.isOpened():
                raise RuntimeError("Could not open VideoWriter (mp4v and XVID failed).")
            return vw
        return vw

    for shot in shots:
        # Check if we've reached max duration
        if written >= max_frames:
            break
            
        start_frame = int(round(shot.start_sec * fps))
        seg_frames = int(round(secs_per_shot * fps))
        
        # Limit segment frames to not exceed max_duration
        remaining_frames = max_frames - written if max_duration > 0 else seg_frames
        seg_frames = min(seg_frames, remaining_frames)

        # Make sure we don't exceed the shot end or video end
        end_frame_by_secs = start_frame + seg_frames
        end_frame_by_shot = int(round(shot.end_sec * fps))
        end_frame = min(end_frame_by_secs, end_frame_by_shot, total_frames - 1)

        if end_frame <= start_frame:
            continue

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        for _ in range(end_frame - start_frame):
            if written >= max_frames:
                break
            ret, frame = cap.read()
            if not ret:
                break

            if writer is None:
                writer = open_writer(frame, out_path)

            frame_out = _resize_keep_aspect(frame, out_width)
            writer.write(frame_out)
            written += 1

    cap.release()
    if writer is not None:
        writer.release()

    return float(fps), int(written)
