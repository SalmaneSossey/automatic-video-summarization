import json
from pathlib import Path

from src.frame_sampling import sample_frames
from src.keyframes import build_shots
from src.summary_video import make_summary_video


if __name__ == "__main__":
    outdir = Path("outputs")
    outdir.mkdir(exist_ok=True)

    boundaries = json.loads(Path("outputs/boundaries.json").read_text(encoding="utf-8"))["boundaries_sec"]

    # use your known duration from inspect_video.py
    video_duration_sec = 26.64
    shots = build_shots(boundaries, video_duration_sec)

    out_path = outdir / "summary.mp4"
    fps, nframes = make_summary_video(
        video_path="data/demo.mp4",
        shots=shots,
        out_path=out_path,
        secs_per_shot=1.5,
        out_width=1280,
    )

    print(f"Summary written: {nframes} frames at {fps:.2f} fps")
    print(f"Saved summary to: {out_path} (or .avi fallback if mp4 failed)")
