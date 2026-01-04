"""
Generate a simple test video for testing the video summarization pipeline.
Creates a video with distinct colored sections to simulate different shots.
"""

import cv2
import numpy as np
import os

def create_test_video(output_path='test_video.mp4', fps=30, duration_seconds=10):
    """
    Create a test video with distinct colored sections.
    
    Args:
        output_path: Path to save the test video
        fps: Frames per second
        duration_seconds: Duration of the video in seconds
    """
    # Video properties
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise ValueError(f"Cannot create video writer for: {output_path}")
    
    total_frames = fps * duration_seconds
    
    # Define color sections (BGR format)
    colors = [
        (255, 0, 0),     # Blue
        (0, 255, 0),     # Green
        (0, 0, 255),     # Red
        (255, 255, 0),   # Cyan
        (255, 0, 255),   # Magenta
        (0, 255, 255),   # Yellow
    ]
    
    frames_per_color = total_frames // len(colors)
    
    print(f"Creating test video: {output_path}")
    print(f"  Resolution: {width}x{height}")
    print(f"  FPS: {fps}")
    print(f"  Duration: {duration_seconds} seconds")
    print(f"  Total frames: {total_frames}")
    print(f"  Frames per color section: {frames_per_color}")
    
    frame_count = 0
    for color_idx, color in enumerate(colors):
        for _ in range(frames_per_color):
            # Create solid color frame
            frame = np.full((height, width, 3), color, dtype=np.uint8)
            
            # Add some variation (text overlay)
            text = f"Section {color_idx + 1} - Frame {frame_count}"
            cv2.putText(frame, text, (20, height // 2),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
            out.write(frame)
            frame_count += 1
    
    out.release()
    print(f"Test video created successfully: {output_path}")
    print(f"Total frames written: {frame_count}")
    return output_path

if __name__ == '__main__':
    # Create test video in the current directory
    video_path = create_test_video('test_video.mp4', fps=30, duration_seconds=6)
    print(f"\nTest video ready at: {video_path}")
