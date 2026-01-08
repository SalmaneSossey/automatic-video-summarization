from __future__ import annotations

import numpy as np


def chi_square_distance(p: np.ndarray, q: np.ndarray) -> float:
    """
    Chi-square distance for histograms.
    """
    p = p.astype(np.float32)
    q = q.astype(np.float32)
    num = (p - q) ** 2
    den = (p + q) + 1e-8
    return float(0.5 * np.sum(num / den))


def combined_distance(hsv1: np.ndarray, hsv2: np.ndarray, edge1: np.ndarray, edge2: np.ndarray,
                      w_hsv: float = 0.7, w_edge: float = 0.3) -> float:
    """
    Weighted combination of HSV hist distance and edge hist distance.
    """
    d_hsv = chi_square_distance(hsv1, hsv2)
    d_edge = chi_square_distance(edge1, edge2)
    return float(w_hsv * d_hsv + w_edge * d_edge)
