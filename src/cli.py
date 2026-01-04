"""
Command-line interface for automatic video summarization.

Usage:
    python -m src.cli --input video.mp4 --output ./results
"""

import argparse
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.video_summarizer import VideoSummarizer
from src.export_utils import export_all


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Automatic Video Summarization using Shot Boundary Detection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python -m src.cli --input video.mp4
  
  # Custom output directory and parameters
  python -m src.cli --input video.mp4 --output ./results --sample-rate 2 --threshold 80
  
  # Create summary video
  python -m src.cli --input video.mp4 --create-video
        """
    )
    
    # Input/Output arguments
    parser.add_argument('--input', '-i', required=True,
                       help='Path to input video file')
    parser.add_argument('--output', '-o', default='./output',
                       help='Output directory for results (default: ./output)')
    parser.add_argument('--base-name', default='summary',
                       help='Base name for output files (default: summary)')
    
    # Pipeline parameters
    parser.add_argument('--sample-rate', type=int, default=1,
                       help='Sample every Nth frame (default: 1, use every frame)')
    parser.add_argument('--threshold', type=float, default=75,
                       help='Percentile threshold for shot detection (default: 75)')
    parser.add_argument('--min-shot-length', type=int, default=10,
                       help='Minimum frames per shot (default: 10)')
    parser.add_argument('--window-size', type=int, default=5,
                       help='Smoothing window size (default: 5)')
    parser.add_argument('--keyframe-method', choices=['middle', 'first', 'last'],
                       default='middle',
                       help='Keyframe selection method (default: middle)')
    
    # Export options
    parser.add_argument('--create-video', action='store_true',
                       help='Create summary video (MP4)')
    parser.add_argument('--no-storyboard', action='store_true',
                       help='Skip storyboard creation')
    parser.add_argument('--no-json', action='store_true',
                       help='Skip JSON export')
    
    args = parser.parse_args()
    
    # Validate input
    if not os.path.exists(args.input):
        print(f"Error: Input video not found: {args.input}")
        return 1
    
    try:
        # Initialize summarizer
        print(f"\n{'='*60}")
        print(f"Automatic Video Summarization")
        print(f"{'='*60}\n")
        print(f"Input: {args.input}")
        print(f"Output: {args.output}")
        print(f"Sample rate: {args.sample_rate}")
        print(f"Threshold percentile: {args.threshold}")
        print(f"Min shot length: {args.min_shot_length}")
        print(f"Smoothing window: {args.window_size}")
        print(f"Keyframe method: {args.keyframe_method}")
        
        summarizer = VideoSummarizer(args.input, sample_rate=args.sample_rate)
        
        # Run pipeline
        summary_data = summarizer.run_pipeline(
            threshold_percentile=args.threshold,
            min_shot_length=args.min_shot_length,
            window_size=args.window_size,
            keyframe_method=args.keyframe_method
        )
        
        # Export results
        print(f"\n{'='*60}")
        print("Exporting results...")
        print(f"{'='*60}\n")
        
        output_files = export_all(
            keyframes=summarizer.keyframes,
            keyframe_indices=summarizer.keyframe_indices,
            summary_data=summary_data,
            distances=summarizer.distances,
            boundaries=summarizer.boundaries,
            output_dir=args.output,
            base_name=args.base_name,
            create_video=args.create_video,
            threshold=summarizer.threshold
        )
        
        # Print summary
        print(f"\n{'='*60}")
        print("Summary")
        print(f"{'='*60}\n")
        print(f"Total shots detected: {summary_data['total_shots']}")
        print(f"Total keyframes extracted: {len(summarizer.keyframes)}")
        print(f"\nOutput files:")
        for output_type, path in output_files.items():
            print(f"  - {output_type}: {path}")
        
        print(f"\n{'='*60}")
        print("Done!")
        print(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
