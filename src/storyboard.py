from __future__ import annotations

from pathlib import Path
from typing import List
import math
import matplotlib.pyplot as plt
import cv2

from src.frame_sampling import SampledFrame


def save_storyboard(keyframes: List[SampledFrame], out_path: Path, max_frames: int = 30) -> None:
    """
    Save a grid image storyboard from keyframes.
    If too many keyframes, sample uniformly.
    """
    if not keyframes:
        raise ValueError("No keyframes provided.")

    # limit number displayed
    if len(keyframes) > max_frames:
        idxs = [round(i) for i in list(_linspace(0, len(keyframes) - 1, max_frames))]
        keyframes = [keyframes[i] for i in idxs]

    n = len(keyframes)
    cols = min(5, n)
    rows = math.ceil(n / cols)

    plt.figure(figsize=(cols * 3, rows * 3))

    for i, kf in enumerate(keyframes):
        img_rgb = cv2.cvtColor(kf.image_bgr, cv2.COLOR_BGR2RGB)
        ax = plt.subplot(rows, cols, i + 1)
        ax.imshow(img_rgb)
        ax.set_title(f"t={kf.timestamp_sec:.2f}s")
        ax.axis("off")

    plt.suptitle("Storyboard (keyframes per shot)", y=0.98)
    plt.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()


def _linspace(a: float, b: float, n: int):
    if n == 1:
        return [a]
    step = (b - a) / (n - 1)
    return [a + i * step for i in range(n)]
