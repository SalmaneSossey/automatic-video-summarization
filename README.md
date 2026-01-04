# Automatic Video Summarization

Turn a long video (lecture / meeting / interview) into a structured summary you can browse in seconds.

This tool automatically detects shot boundaries in videos and extracts representative keyframes to create visual summaries, making it easy to quickly understand video content without watching the entire video.

## Features

- 🎬 **Shot Boundary Detection**: Automatically detect scene changes using color and edge histogram analysis
- 🖼️ **Keyframe Extraction**: Extract one representative frame per shot
- 📊 **Visual Storyboard**: Generate a grid layout of all keyframes
- 📈 **Distance Curve Analysis**: Visualize frame-to-frame differences over time
- 📄 **JSON Export**: Export shot boundaries and metadata in structured format
- 🎥 **Summary Video**: Optional creation of a condensed summary video
- 💻 **CLI & Python API**: Use via command line or integrate into your Python projects
- 📓 **Jupyter Notebook**: Interactive demo notebook included

## Installation

### Prerequisites

- Python 3.10 or higher
- pip

### Setup

1. Clone the repository:
```bash
git clone https://github.com/SalmaneSossey/automatic-video-summarization.git
cd automatic-video-summarization
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command Line Interface

Basic usage:
```bash
python -m src.cli --input video.mp4
```

With custom parameters:
```bash
python -m src.cli --input video.mp4 \
  --output ./results \
  --sample-rate 2 \
  --threshold 80 \
  --create-video
```

#### CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--input, -i` | Path to input video file | (required) |
| `--output, -o` | Output directory for results | `./output` |
| `--base-name` | Base name for output files | `summary` |
| `--sample-rate` | Sample every Nth frame | `1` |
| `--threshold` | Percentile threshold for shot detection | `75` |
| `--min-shot-length` | Minimum frames per shot | `10` |
| `--window-size` | Smoothing window size | `5` |
| `--keyframe-method` | Keyframe selection (`middle`, `first`, `last`) | `middle` |
| `--create-video` | Create summary video (MP4) | `False` |

### Python API

```python
from src.video_summarizer import VideoSummarizer
from src.export_utils import export_all

# Initialize summarizer
summarizer = VideoSummarizer('video.mp4', sample_rate=1)

# Run the complete pipeline
summary_data = summarizer.run_pipeline(
    threshold_percentile=75,
    min_shot_length=10,
    window_size=5,
    keyframe_method='middle'
)

# Export results
output_files = export_all(
    keyframes=summarizer.keyframes,
    keyframe_indices=summarizer.keyframe_indices,
    summary_data=summary_data,
    distances=summarizer.distances,
    boundaries=summarizer.boundaries,
    output_dir='./output',
    create_video=True
)

print(f"Detected {summary_data['total_shots']} shots")
print(f"Output files: {output_files}")
```

### Jupyter Notebook Demo

Launch the interactive demo notebook:
```bash
jupyter notebook examples/demo.ipynb
```

The notebook provides step-by-step visualization of the entire pipeline.

## Pipeline Overview

The video summarization pipeline consists of the following steps:

1. **Video Loading**: Load video and sample frames at specified intervals
2. **Feature Extraction**: 
   - Compute HSV color histograms for each frame
   - Compute edge histograms using Canny edge detection
3. **Distance Calculation**: Calculate frame-to-frame distances using histogram comparison
4. **Smoothing**: Apply moving average filter to reduce noise in distance curve
5. **Boundary Detection**: Detect shot boundaries using adaptive percentile-based thresholding
6. **Keyframe Extraction**: Extract one representative frame from each shot (middle, first, or last)
7. **Export**: Generate outputs:
   - `storyboard.png`: Grid visualization of all keyframes
   - `boundaries.json`: Shot boundary metadata
   - `distance_curve.png`: Plot of frame distances with boundaries
   - `summary.mp4` (optional): Video summary with concatenated keyframes

## Output Files

After processing, the following files are generated in the output directory:

- **`{name}_storyboard.png`**: Visual grid of all keyframes
- **`{name}_boundaries.json`**: JSON file with shot boundaries and metadata
- **`{name}_distance_curve.png`**: Plot showing the distance curve and detected boundaries
- **`{name}_summary.mp4`** (optional): Summary video with keyframes

### Example JSON Output

```json
{
  "video_path": "video.mp4",
  "total_shots": 15,
  "total_frames_sampled": 1500,
  "sample_rate": 1,
  "shots": [
    {
      "shot_id": 0,
      "start_frame": 0,
      "end_frame": 120,
      "keyframe": 60,
      "duration_frames": 120
    },
    ...
  ]
}
```

## Technical Details

### Algorithm

The shot boundary detection algorithm uses:

- **Color Features**: HSV color histograms (8×8×8 bins) for robust color representation
- **Edge Features**: Canny edge detection histograms for structural information
- **Distance Metric**: Chi-square distance for color histograms + L2 distance for edge histograms
- **Smoothing**: Moving average filter to reduce false positives
- **Adaptive Thresholding**: Percentile-based threshold adapts to video characteristics

### Performance

- Processing speed depends on video resolution and frame rate
- Use `--sample-rate` parameter to speed up processing on long videos
- Typical processing time: 30-60 seconds per minute of video (at 30 fps)

## Examples

### Example 1: Quick Summary
```bash
python -m src.cli --input lecture.mp4 --sample-rate 5
```
Fast processing by sampling every 5th frame.

### Example 2: High Precision
```bash
python -m src.cli --input movie.mp4 --threshold 85 --min-shot-length 30
```
More selective boundary detection for content with subtle transitions.

### Example 3: Complete Export
```bash
python -m src.cli --input interview.mp4 --create-video --output ./interview_summary
```
Generate all outputs including summary video.

## Customization

### Adjusting Parameters

- **Threshold**: Higher values (80-90) detect fewer, more significant boundaries
- **Min Shot Length**: Prevent detection of very short shots (useful for noisy videos)
- **Window Size**: Larger windows provide more smoothing but may miss quick transitions
- **Sample Rate**: Higher values speed up processing but may miss brief shots

### Extending the Code

The modular design allows easy customization:

- Add new feature extractors in `video_summarizer.py`
- Implement custom distance metrics
- Create alternative export formats in `export_utils.py`
- Add visualization tools

## Documentation

- **[Report Template](docs/report.md)**: Template for documenting results and analysis
- **[Pipeline Diagram](docs/pipeline.png)**: Visual representation of the processing pipeline
- **[Notebook Demo](examples/demo.ipynb)**: Interactive tutorial with visualizations

## Requirements

- opencv-python >= 4.8.0
- numpy >= 1.24.0
- matplotlib >= 3.7.0

See `requirements.txt` for complete list.

## Troubleshooting

### Video won't load
- Ensure the video file path is correct
- Check that OpenCV supports the video codec (try converting to MP4 with H.264)

### Too many/few shots detected
- Adjust `--threshold` parameter (increase to detect fewer boundaries)
- Modify `--min-shot-length` to filter out very short shots
- Try different `--window-size` values for smoothing

### Memory issues
- Use `--sample-rate` to reduce memory usage
- Process shorter video segments

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

See LICENSE file for details.

## Citation

If you use this tool in your research, please cite:

```
@software{automatic_video_summarization,
  author = {SalmaneSossey},
  title = {Automatic Video Summarization},
  year = {2024},
  url = {https://github.com/SalmaneSossey/automatic-video-summarization}
}
```

## Acknowledgments

This project uses:
- OpenCV for video processing and computer vision
- NumPy for numerical computations
- Matplotlib for visualizations
