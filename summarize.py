"""
Automatic Video Summarization - Main Entry Point
================================================
A production-ready video summarization tool that:
- Detects scene changes using visual features
- Extracts representative keyframes
- Generates a condensed summary video
- Outputs structured JSON for UI integration

Usage:
    python summarize.py --input video.mp4 --output results/

Author: Automatic Video Summarization Project
"""
import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import cv2

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.frame_sampling import sample_frames
from src.features import preprocess_frame, hsv_histogram, edge_histogram
from src.distances import combined_distance
from src.shot_detection import ShotDetectionParams, detect_shot_boundaries
from src.keyframes import build_shots, pick_keyframes_middle, select_highlight_segments
from src.io_outputs import save_image_bgr
from src.storyboard import save_storyboard
from src.summary_video import make_summary_video


def print_banner():
    print("\n" + "="*60)
    print("   AUTOMATIC VIDEO SUMMARIZATION")
    print("   Transform long videos into concise summaries")
    print("="*60 + "\n")


def get_video_info(video_path: str) -> dict:
    """Get video metadata."""
    cap = cv2.VideoCapture(video_path)
    info = {
        "fps": cap.get(cv2.CAP_PROP_FPS),
        "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
        "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
    }
    info["duration_sec"] = info["frame_count"] / info["fps"] if info["fps"] > 0 else 0
    cap.release()
    return info


def format_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def summarize(
    input_path: str,
    output_dir: str,
    fps_sample: float = 4.0,
    threshold_percentile: float = 92.0,
    min_shot_duration: float = 3.0,
    secs_per_shot: float = 2.5,
) -> dict:
    """
    Main summarization pipeline.
    
    Returns dict with results and paths.
    """
    start_time = time.time()
    
    input_path = Path(input_path)
    outdir = Path(output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    
    # Get video info
    print(f"📹 Input: {input_path.name}")
    video_info = get_video_info(str(input_path))
    print(f"   Duration: {format_time(video_info['duration_sec'])} ({video_info['duration_sec']:.1f}s)")
    print(f"   Resolution: {video_info['width']}x{video_info['height']} @ {video_info['fps']:.1f} fps")
    
    # Step 1: Sample frames
    print("\n[1/5] Sampling frames...")
    frames = sample_frames(str(input_path), fps_sample=fps_sample)
    print(f"   Sampled {len(frames)} frames at {fps_sample} fps")
    
    # Step 2: Extract features
    print("[2/5] Extracting visual features...")
    hsv_feats, edge_feats, times = [], [], []
    for f in frames:
        img = preprocess_frame(f.image_bgr, width=480)
        hsv_feats.append(hsv_histogram(img))
        edge_feats.append(edge_histogram(img))
        times.append(f.timestamp_sec)
    
    # Step 3: Compute distances
    print("[3/5] Computing frame distances...")
    dist_times, distances = [], []
    for i in range(1, len(frames)):
        d = combined_distance(hsv_feats[i-1], hsv_feats[i], edge_feats[i-1], edge_feats[i])
        distances.append(d)
        dist_times.append(times[i])
    distances = np.array(distances, dtype=np.float32)
    
    # Step 4: Detect shots
    print("[4/5] Detecting scene changes...")
    params = ShotDetectionParams(
        smooth_win=5,
        threshold_percentile=threshold_percentile,
        min_shot_len_sec=1.0,
        min_gap_sec=2.0,
        min_shot_duration_sec=min_shot_duration,
    )
    
    video_duration = video_info['duration_sec']
    smoothed, thr, boundaries = detect_shot_boundaries(
        dist_times, distances, params, video_duration_sec=video_duration
    )
    
    shots = build_shots(boundaries, video_duration)
    print(f"   Found {len(shots)} distinct scenes")
    
    # Step 5: Generate outputs
    print("[5/5] Generating outputs...")
    
    # Keyframes
    keyframes = pick_keyframes_middle(shots, frames)
    keyframe_dir = outdir / "keyframes"
    keyframe_paths = []
    for i, kf in enumerate(keyframes):
        kf_path = keyframe_dir / f"scene_{i+1:02d}.jpg"
        save_image_bgr(kf_path, kf.image_bgr)
        keyframe_paths.append(f"keyframes/scene_{i+1:02d}.jpg")
    
    # Storyboard
    save_storyboard(keyframes, outdir / "storyboard.png")
    
    # Shot detection plot
    plt.figure(figsize=(12, 4))
    plt.plot(dist_times, distances, alpha=0.5, label="Raw")
    plt.plot(dist_times, smoothed, linewidth=2, label="Smoothed")
    plt.axhline(thr, color='r', linestyle='--', label=f"Threshold")
    for t in boundaries[1:]:
        plt.axvline(t, color='g', alpha=0.5, linestyle=':')
    plt.xlabel("Time (seconds)")
    plt.ylabel("Visual Change")
    plt.title("Scene Change Detection")
    plt.legend()
    plt.tight_layout()
    plt.savefig(outdir / "analysis.png", dpi=120)
    plt.close()
    
    # Highlight segments
    highlights = select_highlight_segments(shots, frames, segment_duration=secs_per_shot)
    
    # Summary video
    summary_path = outdir / "summary.mp4"
    make_summary_video(
        video_path=str(input_path),
        shots=shots,
        out_path=summary_path,
        secs_per_shot=secs_per_shot,
        out_width=1280,
    )
    
    # Calculate summary duration
    summary_info = get_video_info(str(summary_path))
    compression = (1 - summary_info['duration_sec'] / video_duration) * 100 if video_duration > 0 else 0
    
    # Generate manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "input": {
            "path": str(input_path),
            "duration_sec": round(video_duration, 2),
            "duration_hms": format_time(video_duration),
            "resolution": f"{video_info['width']}x{video_info['height']}",
            "fps": round(video_info['fps'], 2),
        },
        "summary": {
            "path": "summary.mp4",
            "duration_sec": round(summary_info['duration_sec'], 2),
            "duration_hms": format_time(summary_info['duration_sec']),
            "compression_percent": round(compression, 1),
        },
        "analysis": {
            "scenes_detected": len(shots),
            "threshold_used": round(thr, 6),
            "params": {
                "fps_sample": fps_sample,
                "threshold_percentile": threshold_percentile,
                "min_shot_duration": min_shot_duration,
                "secs_per_shot": secs_per_shot,
            }
        },
        "scenes": [],
    }
    
    for i, (shot, kf_path) in enumerate(zip(shots, keyframe_paths)):
        highlight = highlights[i] if i < len(highlights) else (shot.start_sec, shot.end_sec, 0.5, i)
        manifest["scenes"].append({
            "index": i + 1,
            "start_sec": round(shot.start_sec, 2),
            "end_sec": round(shot.end_sec, 2),
            "start_hms": format_time(shot.start_sec),
            "end_hms": format_time(shot.end_sec),
            "duration_sec": round(shot.end_sec - shot.start_sec, 2),
            "keyframe": kf_path,
            "quality_score": round(highlight[2], 3),
        })
    
    # Save manifest
    with open(outdir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    
    elapsed = time.time() - start_time
    
    return {
        "success": True,
        "elapsed_sec": elapsed,
        "manifest": manifest,
        "output_dir": str(outdir),
    }


def main():
    print_banner()
    
    parser = argparse.ArgumentParser(
        description="Automatic Video Summarization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python summarize.py --input lecture.mp4 --output results/
  python summarize.py --input meeting.mp4 --secs-per-shot 3.0
  python summarize.py --input vlog.mp4 --threshold 90 --min-duration 2.0
        """
    )
    parser.add_argument("--input", "-i", required=True, help="Input video path")
    parser.add_argument("--output", "-o", default="outputs/summary", help="Output directory")
    parser.add_argument("--fps", type=float, default=4.0, help="Analysis sampling rate (default: 4)")
    parser.add_argument("--threshold", type=float, default=92.0, help="Scene detection sensitivity 50-99 (default: 92)")
    parser.add_argument("--min-duration", type=float, default=3.0, help="Minimum scene duration in seconds (default: 3)")
    parser.add_argument("--secs-per-shot", type=float, default=2.5, help="Seconds per scene in summary (default: 2.5)")
    
    args = parser.parse_args()
    
    # Validate input
    if not Path(args.input).exists():
        print(f"❌ Error: Input file not found: {args.input}")
        sys.exit(1)
    
    try:
        result = summarize(
            input_path=args.input,
            output_dir=args.output,
            fps_sample=args.fps,
            threshold_percentile=args.threshold,
            min_shot_duration=args.min_duration,
            secs_per_shot=args.secs_per_shot,
        )
        
        m = result["manifest"]
        print("\n" + "="*60)
        print("✅ SUMMARIZATION COMPLETE")
        print("="*60)
        print(f"   Input:    {m['input']['duration_hms']} ({m['input']['duration_sec']}s)")
        print(f"   Summary:  {m['summary']['duration_hms']} ({m['summary']['duration_sec']}s)")
        print(f"   Compression: {m['summary']['compression_percent']:.0f}%")
        print(f"   Scenes:   {m['analysis']['scenes_detected']}")
        print(f"   Time:     {result['elapsed_sec']:.1f}s")
        print(f"\n📁 Outputs: {result['output_dir']}/")
        print("   ├── summary.mp4      (condensed video)")
        print("   ├── summary.json     (structured metadata)")
        print("   ├── storyboard.png   (visual overview)")
        print("   ├── analysis.png     (detection chart)")
        print("   └── keyframes/       (representative frames)")
        print()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
