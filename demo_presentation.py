"""
Presentation Demo Script - AI Engineering Multimedia Processing

Run this to generate presentation-ready outputs.

Usage:
    python demo_presentation.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from summarize import summarize, get_video_info, format_time


def print_header(text: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_metric(label: str, value: str, indent: int = 3) -> None:
    print(" " * indent + f"• {label}: {value}")


def run_demo() -> None:
    print_header("🎬 AUTOMATIC VIDEO SUMMARIZATION")
    print("   AI Engineering - Multimedia Processing")

    input_video = Path("data/vlog_snow.mp4")
    output_dir = Path("outputs/presentation_demo")

    if not input_video.exists():
        print(f"\n❌ Demo video not found: {input_video}")
        print("   Please place vlog_snow.mp4 in the data/ folder")
        return

    info = get_video_info(str(input_video))
    print_header("📹 INPUT VIDEO")
    print_metric("File", input_video.name)
    print_metric("Duration", f"{format_time(info['duration_sec'])} ({info['duration_sec']:.1f}s)")
    print_metric("Resolution", f"{info['width']}x{info['height']} @ {info['fps']:.1f}fps")
    print_metric("Frames", f"{info['frame_count']:,}")

    print_header("⚙️ PROCESSING PIPELINE")
    print("   Running 5-stage pipeline (expected 5-8 min on CPU)\n")

    start_time = time.time()
    result = summarize(
        input_path=str(input_video),
        output_dir=str(output_dir),
        fps_sample=4.0,
        threshold_percentile=92.0,
        min_shot_duration=3.0,
        secs_per_shot=2.5,
        max_summary_duration=60.0,
        keep_audio=True,
        clean_input=False,
        best_keyframes=True,
        transcribe=False,  # Set True to include Whisper transcript
    )
    elapsed = time.time() - start_time

    manifest = result["manifest"]
    compression_ratio = manifest["input"]["duration_sec"] / max(manifest["summary"]["duration_sec"], 1e-6)

    print_header("📊 RESULTS")
    print_metric("Input", f"{manifest['input']['duration_hms']} ({manifest['input']['duration_sec']}s)")
    print_metric("Output", f"{manifest['summary']['duration_hms']} ({manifest['summary']['duration_sec']}s)")
    print_metric("Compression", f"{compression_ratio:.1f}:1 ({manifest['summary']['compression_percent']:.0f}% reduction)")
    print_metric("Scenes", str(manifest['analysis']['scenes_detected']))
    if "evaluation" in manifest:
        print_metric("Quality", f"{manifest['evaluation']['summary_score']['overall']:.2f}/1.00")
    print_metric("Processing Time", f"{elapsed:.1f}s ({manifest['input']['duration_sec']/elapsed:.1f}x realtime)")

    print_header("📁 OUTPUTS")
    print(f"   Location: {output_dir}/\n")
    files = [
        ("summary.mp4", "Condensed video (60s)", True),
        ("summary.json", "Metadata & metrics", True),
        ("evaluation.txt", "Evaluation report", True),
        ("storyboard.png", "Scene overview", True),
        ("analysis.png", "Scene detection chart", True),
        ("keyframes/", "Representative frames", False),
    ]
    for name, desc, is_file in files:
        path = output_dir / name
        if path.exists():
            if is_file:
                size_kb = path.stat().st_size / 1024
                print(f"   ✅ {name:<15} {desc} ({size_kb:.0f} KB)")
            else:
                count = len(list(path.glob('*.jpg')))
                print(f"   ✅ {name:<15} {desc} ({count} images)")
        else:
            print(f"   ❌ {name:<15} {desc}")

    print_header("🎯 PRESENTATION TALKING POINTS")
    print("""
   • 20-minute vlog → 60-second summary (YouTube Shorts ready)
   • 5-stage pipeline: Sampling → Features → Shot detection → Keyframes → Video
   • AI: Whisper transcription (optional), quality scoring, evaluation metrics
   • Metrics: Compression ratio, distribution uniformity, quality score
   • Outputs: summary.mp4, storyboard.png, analysis.png, evaluation.txt, summary.json
""")

    print_header("✅ DEMO COMPLETE")
    print(f"   Open summary video: {output_dir.absolute() / 'summary.mp4'}")
    print()


if __name__ == "__main__":
    run_demo()