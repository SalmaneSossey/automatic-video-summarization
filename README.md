# 🎬 Automatic Video Summarization

**Transform long videos into concise, browsable summaries in seconds.**

A production-ready tool that automatically detects scene changes, extracts representative keyframes, and generates condensed summary videos **with audio** and structured metadata for UI integration.

---

## 🎥 Demo Output

### Storyboard (Visual Overview)
![Storyboard](docs/demo/storyboard.png)

### Scene Detection Analysis
![Analysis](docs/demo/analysis.png)

### Summary Video
📹 **15 min video → 64 seconds with audio!** (93% compression, 16 scenes detected)

> Run the demo yourself: `python summarize.py --input data/demo.mp4 --output outputs/result --keep-audio`

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Scene Detection** | Visual change detection using color (HSV) and edge analysis |
| 🖼️ **Keyframe Extraction** | Automatically selects the most representative frame from each scene |
| 🔊 **Audio Preservation** | Summary video keeps original audio (requires ffmpeg) |
| 📊 **Structured Output** | JSON manifest with timestamps, durations, and quality scores |
| 🎥 **Summary Video** | Condensed MP4 preserving the essence of the original |
| 📋 **Storyboard** | Visual grid overview of all detected scenes |
| 🧹 **Input Cleaning** | Optional re-encoding to fix codec issues (H.264 mmco errors) |
| ⚡ **Quality Keyframes** | Optional sharpness-based keyframe selection |

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install opencv-python numpy matplotlib
```

For audio support, install ffmpeg:
- **Windows**: `winget install --id Gyan.FFmpeg -e --source winget`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### 2. Run Summarization

```bash
# Basic (no audio)
python summarize.py --input your_video.mp4 --output results/

# With audio preservation
python summarize.py --input your_video.mp4 --output results/ --keep-audio
```

---

## 📊 Example Run

**Command:**
```bash
python summarize.py \
    --input data/demo.mp4 \
    --output outputs/result_audio \
    --threshold 97 \
    --min-duration 5 \
    --secs-per-shot 3 \
    --keep-audio
```

**Console Output:**
```
============================================================
   AUTOMATIC VIDEO SUMMARIZATION
   Transform long videos into concise summaries
============================================================

📹 Input: demo.mp4
   Duration: 00:15:00 (900.4s)
   Resolution: 1280x720 @ 30.0 fps

[1/5] Sampling frames...
   Sampled 3855 frames at 4.0 fps
[2/5] Extracting visual features...
[3/5] Computing frame distances...
[4/5] Detecting scene changes...
   Found 16 distinct scenes
[5/5] Generating outputs...

============================================================
✅ SUMMARIZATION COMPLETE
============================================================
   Input:    00:15:00 (900.4s)
   Summary:  00:01:04 (64.0s)
   Compression: 93%
   Scenes:   16
   Time:     1216.9s

📁 Outputs: outputs/result_audio/
   ├── summary.mp4      (condensed video with audio)
   ├── summary.json     (structured metadata)
   ├── storyboard.png   (visual overview)
   ├── analysis.png     (detection chart)
   └── keyframes/       (representative frames)
```

**Generated Files:**
| File | Description |
|------|-------------|
| `summary.mp4` | 64s condensed video with audio (H.264 + AAC) |
| `summary.json` | Structured metadata with timestamps and scores |
| `storyboard.png` | Grid of 16 keyframes |
| `analysis.png` | Scene detection curve with boundaries |
| `keyframes/` | 16 JPEG keyframes (one per scene) |

---

## 📖 Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input, -i` | required | Input video path |
| `--output, -o` | `outputs/summary` | Output directory |
| `--fps` | 4.0 | Analysis sampling rate |
| `--threshold` | 92 | Scene detection sensitivity (50-99, higher = fewer scenes) |
| `--min-duration` | 3.0 | Minimum scene duration (seconds) |
| `--secs-per-shot` | 2.5 | Seconds per scene in summary |
| `--keep-audio` | false | Preserve audio using ffmpeg |
| `--clean-input` | false | Re-encode input to fix codec issues |
| `--best-keyframes` | false | Pick sharpest keyframes instead of midpoint |

---

## 📄 Output Format

### summary.json
```json
{
  "generated_at": "2026-01-09T14:30:00",
  "input": {
    "path": "data/demo.mp4",
    "duration_sec": 900.4,
    "duration_hms": "00:15:00",
    "resolution": "1280x720",
    "fps": 30.0
  },
  "summary": {
    "path": "summary.mp4",
    "duration_sec": 64.0,
    "duration_hms": "00:01:04",
    "compression_percent": 93
  },
  "analysis": {
    "scenes_detected": 16,
    "threshold_used": 0.001234,
    "params": {
      "fps_sample": 4.0,
      "threshold_percentile": 97,
      "min_shot_duration": 5,
      "secs_per_shot": 3,
      "keep_audio": true
    }
  },
  "scenes": [
    {
      "index": 1,
      "start_sec": 0.0,
      "end_sec": 45.2,
      "start_hms": "00:00:00",
      "end_hms": "00:00:45",
      "duration_sec": 45.2,
      "keyframe": "keyframes/scene_01.jpg",
      "quality_score": 0.87
    }
  ]
}
```

---

## 🏗️ Architecture

```
Input Video
    │
    ▼
┌─────────────────┐
│ Frame Sampling  │  → Sample at N fps (default: 4)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Feature Extract │  → HSV histogram + Edge histogram
└────────┬────────┘
         ▼
┌─────────────────┐
│ Distance Curve  │  → Chi-square distance between frames
└────────┬────────┘
         ▼
┌─────────────────┐
│ Shot Detection  │  → Smoothing + Threshold + NMS + Merging
└────────┬────────┘
         ▼
┌─────────────────┐
│ Output Gen      │  → Keyframes, Storyboard, Summary Video, JSON
└─────────────────┘
```

---

## 📁 Project Structure

```
automatic-video-summarization/
├── summarize.py           # 🎯 Main entry point
├── requirements.txt       # Dependencies
├── README.md
├── LICENSE
├── data/
│   └── demo.mp4           # Sample input video
├── outputs/
│   └── result_audio/      # Generated outputs
│       ├── summary.mp4
│       ├── summary.json
│       ├── storyboard.png
│       ├── analysis.png
│       └── keyframes/
├── scripts/
│   ├── inspect_video.py   # Video metadata inspector
│   └── run_demo.py        # Advanced demo script
└── src/
    ├── __init__.py
    ├── frame_sampling.py  # Video frame extraction
    ├── features.py        # Visual feature computation
    ├── distances.py       # Frame similarity metrics
    ├── shot_detection.py  # Scene boundary detection
    ├── keyframes.py       # Keyframe selection + scoring
    ├── storyboard.py      # Storyboard generation
    ├── summary_video.py   # Video compilation (OpenCV)
    ├── av_concat.py       # Audio-preserving summary (ffmpeg)
    ├── preprocessing.py   # Video cleaning/re-encoding
    ├── summary_manifest.py# JSON manifest generation
    └── io_outputs.py      # File I/O utilities
```

---

## 🎯 Use Cases & Recommended Settings

| Use Case | Command |
|----------|---------|
| **Lectures** | `--threshold 95 --min-duration 10 --secs-per-shot 5` |
| **Meetings** | `--threshold 93 --min-duration 5 --secs-per-shot 3 --keep-audio` |
| **Vlogs/YouTube** | `--threshold 90 --min-duration 2 --secs-per-shot 2` |
| **Surveillance** | `--threshold 98 --min-duration 30 --secs-per-shot 5` |
| **Quick Preview** | `--fps 2 --threshold 90 --secs-per-shot 1` |

---

## 🔮 Roadmap

- [x] **M0**: Core summarization pipeline
- [x] **M0**: Structured JSON output
- [x] **M1**: Audio preservation (ffmpeg integration)
- [x] **M1**: Quality-based keyframe selection
- [x] **M1**: Input video cleaning/re-encoding
- [ ] **M2**: Transcript-based chapter titles (Whisper)
- [ ] **M3**: REST API + Web UI

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `ffmpeg not found` | Install ffmpeg and restart terminal |
| `H.264 mmco errors` | Use `--clean-input` to re-encode |
| Too many scenes | Increase `--threshold` (e.g., 95-98) |
| Too few scenes | Decrease `--threshold` (e.g., 85-90) |
| Summary too long | Decrease `--secs-per-shot` |
| Blurry keyframes | Use `--best-keyframes` |

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Please read the contributing guidelines first.

---

**Made with ❤️ for turning hours into minutes.**
