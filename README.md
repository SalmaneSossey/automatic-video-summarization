# 🎬 Automatic Video Summarization

**Transform long videos into concise, browsable summaries in seconds.**

A production-ready tool that automatically detects scene changes, extracts representative keyframes, and generates condensed summary videos with structured metadata for UI integration.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Scene Detection** | AI-powered detection of visual changes using color and edge analysis |
| 🖼️ **Keyframe Extraction** | Automatically selects the most representative frame from each scene |
| 📊 **Structured Output** | JSON manifest with timestamps, durations, and quality scores |
| 🎥 **Summary Video** | Condensed video preserving the essence of the original |
| 📋 **Storyboard** | Visual overview grid of all detected scenes |

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install opencv-python numpy matplotlib

# Run summarization
python summarize.py --input your_video.mp4 --output results/
```

**Output (15-min video → 48s summary, 95% compression):**
```
📁 results/
├── summary.mp4      # Condensed video
├── summary.json     # Structured metadata (for UI)
├── storyboard.png   # Visual overview
├── analysis.png     # Scene detection chart
└── keyframes/       # Representative frames
```

---

## 📖 Usage

### Basic Usage
```bash
python summarize.py --input lecture.mp4 --output results/
```

### Advanced Options
```bash
python summarize.py \
    --input meeting.mp4 \
    --output results/ \
    --threshold 95        # Scene sensitivity (50-99, higher = fewer scenes)
    --min-duration 5      # Minimum scene duration in seconds
    --secs-per-shot 3     # Seconds per scene in summary
```

### Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--input, -i` | required | Input video path |
| `--output, -o` | `outputs/summary` | Output directory |
| `--fps` | 4.0 | Analysis sampling rate |
| `--threshold` | 92 | Scene detection sensitivity (50-99) |
| `--min-duration` | 3.0 | Minimum scene duration (seconds) |
| `--secs-per-shot` | 2.5 | Seconds per scene in summary |

---

## 📊 Output Format

### summary.json
```json
{
  "input": {
    "path": "lecture.mp4",
    "duration_sec": 900.4,
    "duration_hms": "00:15:00"
  },
  "summary": {
    "duration_sec": 48.05,
    "compression_percent": 95
  },
  "scenes": [
    {
      "index": 1,
      "start_sec": 0.0,
      "end_sec": 45.2,
      "start_hms": "00:00:00",
      "end_hms": "00:00:45",
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
│ Shot Detection  │  → Smoothing + Threshold + NMS
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
├── summarize.py          # Main entry point
├── src/
│   ├── frame_sampling.py # Video frame extraction
│   ├── features.py       # Visual feature computation
│   ├── distances.py      # Frame similarity metrics
│   ├── shot_detection.py # Scene boundary detection
│   ├── keyframes.py      # Keyframe selection
│   ├── storyboard.py     # Storyboard generation
│   ├── summary_video.py  # Video compilation
│   └── io_outputs.py     # File I/O utilities
├── scripts/
│   ├── inspect_video.py  # Video metadata inspector
│   └── run_demo.py       # Advanced demo script
└── data/
    └── demo.mp4          # Sample video
```

---

## 🎯 Use Cases

| Use Case | Settings |
|----------|----------|
| **Lectures** | `--threshold 95 --min-duration 10 --secs-per-shot 5` |
| **Meetings** | `--threshold 93 --min-duration 5 --secs-per-shot 3` |
| **Vlogs/YouTube** | `--threshold 90 --min-duration 2 --secs-per-shot 2` |
| **Surveillance** | `--threshold 98 --min-duration 30 --secs-per-shot 5` |

---

## 🔮 Roadmap

- [x] **M0**: Core summarization pipeline
- [x] **M0**: Structured JSON output
- [ ] **M1**: Audio preservation (ffmpeg integration)
- [ ] **M2**: Transcript-based chapter titles (Whisper)
- [ ] **M3**: REST API + Web UI

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

**Made with ❤️ for turning hours into minutes.**
