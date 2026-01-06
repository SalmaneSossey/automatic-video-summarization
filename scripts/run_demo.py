import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

from src.frame_sampling import sample_frames
from src.features import preprocess_frame, hsv_histogram, edge_histogram
from src.distances import combined_distance
from src.shot_detection import ShotDetectionParams, detect_shot_boundaries
from src.keyframes import build_shots, pick_keyframes_middle
from src.io_outputs import save_image_bgr
from src.storyboard import save_storyboard
from src.summary_video import make_summary_video


def main():
    parser = argparse.ArgumentParser(description="Automatic video summarization demo")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--outdir", default="outputs/demo_run", help="Output directory")
    parser.add_argument("--fps_sample", type=float, default=8.0, help="Sampling fps for analysis")
    parser.add_argument("--resize_width", type=int, default=640, help="Resize width for feature extraction")
    parser.add_argument("--smooth_win", type=int, default=7, help="Smoothing window")
    parser.add_argument("--percentile", type=float, default=95.0, help="Threshold percentile")
    parser.add_argument("--min_shot_len", type=float, default=1.0, help="Minimum shot length (sec)")
    parser.add_argument("--secs_per_shot", type=float, default=1.5, help="Seconds to keep per shot in summary")
    parser.add_argument("--summary_width", type=int, default=1280, help="Width of summary video")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 1) Sample frames
    frames = sample_frames(args.input, fps_sample=args.fps_sample)

    # 2) Compute features
    hsv_feats = []
    edge_feats = []
    times = []

    for f in frames:
        img = preprocess_frame(f.image_bgr, width=args.resize_width)
        hsv_feats.append(hsv_histogram(img))
        edge_feats.append(edge_histogram(img))
        times.append(f.timestamp_sec)

    # 3) Distance curve
    dist_times = []
    distances = []
    for i in range(1, len(frames)):
        d = combined_distance(hsv_feats[i-1], hsv_feats[i], edge_feats[i-1], edge_feats[i])
        distances.append(d)
        dist_times.append(times[i])

    distances = np.array(distances, dtype=np.float32)

    # 4) Shot detection
    params = ShotDetectionParams(
        smooth_win=args.smooth_win,
        threshold_percentile=args.percentile,
        min_shot_len_sec=args.min_shot_len
    )
    smoothed, thr, boundaries = detect_shot_boundaries(dist_times, distances, params)

    # Save boundaries.json
    boundaries_path = outdir / "boundaries.json"
    boundaries_path.write_text(
        json.dumps(
            {"threshold": thr, "params": params.__dict__, "boundaries_sec": boundaries},
            indent=2
        ),
        encoding="utf-8"
    )

    # Plot shot detection curve
    plt.figure()
    plt.plot(dist_times, distances, label="raw")
    plt.plot(dist_times, smoothed, label="smoothed")
    plt.axhline(thr, linestyle="--", label=f"thr={thr:.6f}")
    for t in boundaries[1:]:
        plt.axvline(t, linestyle=":")
    plt.xlabel("Time (s)")
    plt.ylabel("Frame-to-frame distance")
    plt.title("Shot boundary detection")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "shot_detection.png", dpi=150)
    plt.close()

    # 5) Keyframes + storyboard
    # estimate duration from last sampled frame + one step (good enough for demo)
    video_duration_sec = times[-1] if times else 0.0
    # make sure last boundary shot has some end; add a small buffer
    video_duration_sec = max(video_duration_sec, boundaries[-1]) + 0.5

    shots = build_shots(boundaries, video_duration_sec)
    keyframes = pick_keyframes_middle(shots, frames)

    keyframe_dir = outdir / "keyframes"
    for i, kf in enumerate(keyframes, start=1):
        save_image_bgr(keyframe_dir / f"shot_{i:03d}.jpg", kf.image_bgr)

    save_storyboard(keyframes, outdir / "storyboard.png")

    # 6) Summary video
    make_summary_video(
        video_path=args.input,
        shots=shots,
        out_path=outdir / "summary.mp4",
        secs_per_shot=args.secs_per_shot,
        out_width=args.summary_width
    )

    print("=== DONE ===")
    print(f"Shots detected: {len(shots)}")
    print(f"Boundaries (sec): {[round(x, 2) for x in boundaries]}")
    print(f"Outputs saved to: {outdir}")


if __name__ == "__main__":
    main()
