import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import logging

from src.frame_sampling import sample_frames
from src.features import preprocess_frame, hsv_histogram, edge_histogram
from src.distances import combined_distance
from src.shot_detection import ShotDetectionParams, detect_shot_boundaries
from src.keyframes import build_shots, pick_keyframes_middle, pick_keyframes_best, select_highlight_segments
from src.io_outputs import save_image_bgr
from src.storyboard import save_storyboard
from src.summary_video import make_summary_video
from src.av_concat import make_summary_with_audio
from src.preprocessing import ensure_clean_video
from src.summary_manifest import generate_summary_manifest, generate_highlights_json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def main():
    parser = argparse.ArgumentParser(description="Automatic video summarization demo")
    parser.add_argument("--input", required=True, help="Path to input video")
    parser.add_argument("--outdir", default="outputs/demo_run", help="Output directory")
    parser.add_argument("--fps_sample", type=float, default=8.0, help="Sampling fps for analysis")
    parser.add_argument("--resize_width", type=int, default=640, help="Resize width for feature extraction")
    parser.add_argument("--smooth_win", type=int, default=7, help="Smoothing window")
    parser.add_argument("--percentile", type=float, default=95.0, help="Threshold percentile")
    parser.add_argument("--min_shot_len", type=float, default=1.0, help="Minimum shot length (sec)")
    parser.add_argument("--min_gap", type=float, default=1.5, help="Minimum gap between boundaries (sec)")
    parser.add_argument("--min_shot_duration", type=float, default=2.0, help="Minimum shot duration (sec)")
    parser.add_argument("--secs_per_shot", type=float, default=3.0, help="Seconds to keep per shot in summary")
    parser.add_argument("--summary_width", type=int, default=1280, help="Width of summary video")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio in summary (faster, uses OpenCV)")
    parser.add_argument("--clean-input", action="store_true", help="Re-encode input to fix codec issues")
    parser.add_argument("--best-keyframes", action="store_true", help="Use quality-based keyframe selection")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    input_path = Path(args.input)
    
    # 0) Optional: clean/re-encode input video
    if getattr(args, 'clean_input', False):
        logging.info("Checking/cleaning input video...")
        input_path, was_cleaned, clean_msg = ensure_clean_video(
            input_path, outdir, force_clean=True
        )
        logging.info(clean_msg)

    # 1) Sample frames
    frames = sample_frames(str(input_path), fps_sample=args.fps_sample)

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
        min_shot_len_sec=args.min_shot_len,
        min_gap_sec=args.min_gap,
        min_shot_duration_sec=args.min_shot_duration,
    )
    
    # Estimate video duration from last frame
    video_duration_sec = times[-1] if times else 0.0
    video_duration_sec = max(video_duration_sec, 1.0) + 0.5
    
    smoothed, thr, boundaries = detect_shot_boundaries(
        dist_times, distances, params, video_duration_sec=video_duration_sec
    )

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
    # Recalculate video duration (boundaries may have changed)
    video_duration_sec = max(times[-1] if times else 0.0, boundaries[-1] if boundaries else 0.0) + 0.5

    shots = build_shots(boundaries, video_duration_sec)
    
    # Select keyframes (quality-based or middle)
    if getattr(args, 'best_keyframes', False):
        logging.info("Using quality-based keyframe selection...")
        scored_keyframes = pick_keyframes_best(shots, frames)
        keyframes = [sk.frame for sk in scored_keyframes]
    else:
        keyframes = pick_keyframes_middle(shots, frames)

    keyframe_dir = outdir / "keyframes"
    keyframe_paths = []
    for i, kf in enumerate(keyframes):
        kf_path = keyframe_dir / f"shot_{i:03d}.jpg"
        save_image_bgr(kf_path, kf.image_bgr)
        keyframe_paths.append(str(kf_path.relative_to(outdir)))

    save_storyboard(keyframes, outdir / "storyboard.png")
    
    # 6) Select highlight segments for summary
    highlights = select_highlight_segments(
        shots, frames, 
        segment_duration=args.secs_per_shot
    )
    
    # Save highlights.json
    generate_highlights_json(
        highlights,
        keyframe_paths,
        outdir / "highlights.json"
    )

    # 7) Summary video (with or without audio)
    summary_path = outdir / "summary.mp4"
    
    if getattr(args, 'no_audio', False):
        # Use OpenCV (no audio)
        logging.info("Creating summary video (no audio)...")
        make_summary_video(
            video_path=str(input_path),
            shots=shots,
            out_path=summary_path,
            secs_per_shot=args.secs_per_shot,
            out_width=args.summary_width
        )
    else:
        # Use ffmpeg (with audio)
        logging.info("Creating summary video with audio...")
        segments = [(start, end) for start, end, score, idx in highlights]
        success, msg = make_summary_with_audio(
            input_path=input_path,
            segments=segments,
            output_path=summary_path,
        )
        if not success:
            logging.warning(f"Audio summary failed ({msg}), falling back to OpenCV...")
            make_summary_video(
                video_path=str(input_path),
                shots=shots,
                out_path=summary_path,
                secs_per_shot=args.secs_per_shot,
                out_width=args.summary_width
            )
        else:
            logging.info(msg)
    
    # 8) Generate summary manifest
    pipeline_params = {
        "fps_sample": args.fps_sample,
        "resize_width": args.resize_width,
        "smooth_win": args.smooth_win,
        "threshold_percentile": args.percentile,
        "min_shot_len": args.min_shot_len,
        "min_gap": args.min_gap,
        "min_shot_duration": args.min_shot_duration,
        "secs_per_shot": args.secs_per_shot,
    }
    
    generate_summary_manifest(
        input_video=str(args.input),
        input_duration_sec=video_duration_sec,
        segments=highlights,
        keyframe_paths=keyframe_paths,
        params=pipeline_params,
        output_path=outdir / "summary.json",
    )

    print("=== DONE ===")
    print(f"Shots detected: {len(shots)}")
    print(f"Boundaries (sec): {[round(x, 2) for x in boundaries]}")
    print(f"Outputs saved to: {outdir}")


if __name__ == "__main__":
    main()
