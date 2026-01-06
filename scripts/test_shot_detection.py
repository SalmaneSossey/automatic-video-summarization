import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from src.frame_sampling import sample_frames
from src.features import preprocess_frame, hsv_histogram, edge_histogram
from src.distances import combined_distance
from src.shot_detection import ShotDetectionParams, detect_shot_boundaries


if __name__ == "__main__":
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)

    frames = sample_frames("data/demo.mp4", fps_sample=8.0)

    hsv_feats = []
    edge_feats = []
    times = []

    for f in frames:
        img = preprocess_frame(f.image_bgr, width=640)
        hsv_feats.append(hsv_histogram(img))
        edge_feats.append(edge_histogram(img))
        times.append(f.timestamp_sec)

    dist_times = []
    distances = []

    for i in range(1, len(frames)):
        d = combined_distance(hsv_feats[i-1], hsv_feats[i], edge_feats[i-1], edge_feats[i])
        distances.append(d)
        dist_times.append(times[i])

    distances = np.array(distances, dtype=np.float32)

    params = ShotDetectionParams(
        smooth_win=7,
        threshold_percentile=95.0,
        min_shot_len_sec=1.0
    )

    smoothed, thr, boundaries = detect_shot_boundaries(dist_times, distances, params)

    # Save boundaries
    boundaries_path = outdir / "boundaries.json"
    with open(boundaries_path, "w", encoding="utf-8") as f:
        json.dump(
            {"threshold": thr, "params": params.__dict__, "boundaries_sec": boundaries},
            f,
            indent=2
        )

    # Plot
    plt.figure()
    plt.plot(dist_times, distances, label="raw")
    plt.plot(dist_times, smoothed, label="smoothed")
    plt.axhline(thr, linestyle="--", label=f"thr={thr:.6f}")

    for t in boundaries[1:]:  # skip 0.0 line
        plt.axvline(t, linestyle=":")

    plt.xlabel("Time (s)")
    plt.ylabel("Frame-to-frame distance")
    plt.title("Shot boundary detection")
    plt.legend()
    plt.tight_layout()

    plot_path = outdir / "shot_detection.png"
    plt.savefig(plot_path, dpi=150)

    print(f"Threshold: {thr:.6f}")
    print(f"Detected boundaries: {len(boundaries)} (including 0.0)")
    print("Boundaries (sec):", [round(x, 2) for x in boundaries])
    print(f"Saved: {boundaries_path}")
    print(f"Saved: {plot_path}")
