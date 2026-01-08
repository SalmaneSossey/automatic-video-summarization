from __future__ import annotations

import cv2
import numpy as np


def preprocess_frame(frame_bgr: np.ndarray, width: int = 640) -> np.ndarray:
    """
    Resize a frame to a fixed width (keeping aspect ratio) for faster processing.
    """
    h, w = frame_bgr.shape[:2]
    if w == width:
        return frame_bgr
    scale = width / float(w)
    new_h = int(round(h * scale))
    return cv2.resize(frame_bgr, (width, new_h), interpolation=cv2.INTER_AREA)


def hsv_histogram(frame_bgr: np.ndarray, h_bins: int = 32, s_bins: int = 32) -> np.ndarray:
    """
    Compute a normalized HSV histogram (H,S channels).
    Returns a 1D float vector.
    """
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], channels=[0, 1], mask=None, histSize=[h_bins, s_bins], ranges=[0, 180, 0, 256])
    hist = hist.astype(np.float32)
    hist /= (hist.sum() + 1e-8)
    return hist.flatten()


def edge_histogram(frame_bgr: np.ndarray, bins: int = 32) -> np.ndarray:
    """
    Compute a normalized histogram of edge magnitudes (via Canny edges).
    Returns a 1D float vector.
    """
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    # light blur to reduce noise
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    edges = cv2.Canny(gray, threshold1=80, threshold2=160)
    # edges is 0 or 255, histogram will reflect proportion of edges
    hist, _ = np.histogram(edges, bins=bins, range=(0, 256))
    hist = hist.astype(np.float32)
    hist /= (hist.sum() + 1e-8)
    return hist
