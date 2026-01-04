"""
Simple example script demonstrating the Python API for video summarization.

This script shows how to:
1. Initialize the VideoSummarizer
2. Run the complete pipeline
3. Access the results
4. Export outputs
"""

import sys
sys.path.insert(0, '..')

from src.video_summarizer import VideoSummarizer
from src.export_utils import export_all


def main():
    """Main example function."""
    # Configuration
    video_path = 'test_video.mp4'  # Path to your video
    output_dir = './example_output'
    
    # Check if video exists
    import os
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        print("Please run 'python create_test_video.py' first to create a test video.")
        return 1
    
    print("=" * 60)
    print("Video Summarization Example")
    print("=" * 60)
    print()
    
    # Step 1: Initialize the summarizer
    print("Step 1: Initializing VideoSummarizer...")
    summarizer = VideoSummarizer(video_path, sample_rate=1)
    
    # Step 2: Run the complete pipeline
    print("\nStep 2: Running video summarization pipeline...")
    summary_data = summarizer.run_pipeline(
        threshold_percentile=75,
        min_shot_length=10,
        window_size=5,
        keyframe_method='middle'
    )
    
    # Step 3: Access results
    print("\nStep 3: Analyzing results...")
    print(f"\nVideo Summary:")
    print(f"  - Total shots: {summary_data['total_shots']}")
    print(f"  - Total frames sampled: {summary_data['total_frames_sampled']}")
    print(f"  - Sample rate: {summary_data['sample_rate']}")
    
    print(f"\nFirst 3 shots:")
    for shot in summary_data['shots'][:3]:
        print(f"  Shot {shot['shot_id'] + 1}:")
        print(f"    Frames: {shot['start_frame']} - {shot['end_frame']}")
        print(f"    Duration: {shot['duration_frames']} frames")
        print(f"    Keyframe: {shot['keyframe']}")
    
    # Step 4: Export results
    print("\nStep 4: Exporting results...")
    output_files = export_all(
        keyframes=summarizer.keyframes,
        keyframe_indices=summarizer.keyframe_indices,
        summary_data=summary_data,
        distances=summarizer.distances,
        boundaries=summarizer.boundaries,
        output_dir=output_dir,
        base_name='example',
        create_video=True,
        threshold=summarizer.threshold
    )
    
    print(f"\nExported files:")
    for file_type, path in output_files.items():
        print(f"  - {file_type}: {path}")
    
    print("\n" + "=" * 60)
    print("Example complete!")
    print("=" * 60)


if __name__ == '__main__':
    main()
