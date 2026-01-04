# Examples

This directory contains examples demonstrating how to use the automatic video summarization tool.

## Files

### 1. demo.ipynb
Interactive Jupyter notebook that walks through the entire pipeline with visualizations.

**Usage:**
```bash
jupyter notebook demo.ipynb
```

### 2. simple_example.py
Simple Python script demonstrating the Python API.

**Usage:**
```bash
# First, create a test video
python create_test_video.py

# Then run the example
python simple_example.py
```

### 3. create_test_video.py
Utility script to generate a test video with distinct color sections for testing.

**Usage:**
```bash
python create_test_video.py
```

This creates a `test_video.mp4` file with 6 colored sections, perfect for testing shot boundary detection.

## Quick Start

### Option 1: Command Line
```bash
# Create test video
python create_test_video.py

# Run summarization from parent directory
cd ..
python -m src.cli --input examples/test_video.mp4 --output examples/test_output --create-video
```

### Option 2: Python Script
```bash
# Create test video
python create_test_video.py

# Run example script
python simple_example.py
```

### Option 3: Jupyter Notebook
```bash
# Launch notebook
jupyter notebook demo.ipynb

# Follow the step-by-step instructions in the notebook
```

## Expected Output

After running the examples, you should see:

- **storyboard.png**: Grid of keyframes from each shot
- **boundaries.json**: Shot boundary information and metadata
- **distance_curve.png**: Visualization of frame-to-frame distances
- **summary.mp4**: Optional video summary (if enabled)

## Using Your Own Videos

Replace `test_video.mp4` with the path to your own video file:

**CLI:**
```bash
python -m src.cli --input /path/to/your/video.mp4 --output ./my_results
```

**Python:**
```python
from src.video_summarizer import VideoSummarizer
summarizer = VideoSummarizer('/path/to/your/video.mp4')
summary_data = summarizer.run_pipeline()
```

**Notebook:**
Edit the `VIDEO_PATH` variable in the second cell of `demo.ipynb`.

## Tips

- For faster processing on long videos, use `--sample-rate 2` or higher
- Adjust `--threshold` if detecting too many/few boundaries (higher = fewer shots)
- Use `--min-shot-length` to filter out very short shots
- Try different `--keyframe-method` options: middle, first, or last
