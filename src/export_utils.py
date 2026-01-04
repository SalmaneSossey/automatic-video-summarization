"""
Export utilities for video summarization results.

This module provides functions to export summarization results in various formats:
- Storyboard PNG (grid of keyframes)
- Boundaries JSON (shot boundary data)
- Summary MP4 (optional concatenated video)
"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import json
from typing import List, Dict, Tuple
import math


def create_storyboard(keyframes: List[np.ndarray], output_path: str, 
                     cols: int = None, title: str = "Video Storyboard",
                     frame_labels: List[str] = None) -> None:
    """
    Create a storyboard image with all keyframes in a grid layout.
    
    Args:
        keyframes: List of keyframe images (BGR format)
        output_path: Path to save the storyboard PNG
        cols: Number of columns in the grid (auto-calculated if None)
        title: Title for the storyboard
        frame_labels: Optional labels for each frame
    """
    if not keyframes:
        raise ValueError("No keyframes to create storyboard")
    
    n_frames = len(keyframes)
    
    # Auto-calculate grid dimensions
    if cols is None:
        cols = min(4, n_frames)  # Max 4 columns
    rows = math.ceil(n_frames / cols)
    
    # Create figure
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4, rows * 3))
    fig.suptitle(title, fontsize=16, fontweight='bold')
    
    # Handle single row/column case
    if rows == 1 and cols == 1:
        axes = np.array([[axes]])
    elif rows == 1:
        axes = axes.reshape(1, -1)
    elif cols == 1:
        axes = axes.reshape(-1, 1)
    
    # Plot keyframes
    for idx in range(rows * cols):
        row = idx // cols
        col = idx % cols
        ax = axes[row, col]
        
        if idx < n_frames:
            # Convert BGR to RGB for matplotlib
            frame_rgb = cv2.cvtColor(keyframes[idx], cv2.COLOR_BGR2RGB)
            ax.imshow(frame_rgb)
            
            # Add label
            if frame_labels and idx < len(frame_labels):
                ax.set_title(frame_labels[idx], fontsize=10)
            else:
                ax.set_title(f"Shot {idx + 1}", fontsize=10)
        else:
            ax.axis('off')
        
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Storyboard saved to: {output_path}")


def save_boundaries_json(summary_data: Dict, output_path: str) -> None:
    """
    Save shot boundary data to a JSON file.
    
    Args:
        summary_data: Dictionary containing summary information
        output_path: Path to save the JSON file
    """
    with open(output_path, 'w') as f:
        json.dump(summary_data, f, indent=2)
    
    print(f"Boundaries JSON saved to: {output_path}")


def create_summary_video(keyframes: List[np.ndarray], keyframe_indices: List[int],
                        output_path: str, fps: float = 1.0, 
                        frame_duration: int = 30) -> None:
    """
    Create a summary video by concatenating keyframes.
    
    Args:
        keyframes: List of keyframe images (BGR format)
        keyframe_indices: Original frame indices of keyframes
        output_path: Path to save the summary MP4
        fps: Frames per second for the output video
        frame_duration: Number of frames to show each keyframe
    """
    if not keyframes:
        raise ValueError("No keyframes to create summary video")
    
    # Get frame dimensions
    height, width = keyframes[0].shape[:2]
    
    # Initialize video writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        raise ValueError(f"Cannot create video writer for: {output_path}")
    
    # Write each keyframe multiple times to create duration
    for i, frame in enumerate(keyframes):
        # Add text overlay with shot number
        frame_with_text = frame.copy()
        text = f"Shot {i + 1}"
        if i < len(keyframe_indices):
            text += f" (Frame {keyframe_indices[i]})"
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.0
        thickness = 2
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        
        # Add text background
        text_x = 10
        text_y = height - 20
        cv2.rectangle(frame_with_text, 
                     (text_x - 5, text_y - text_size[1] - 5),
                     (text_x + text_size[0] + 5, text_y + 5),
                     (0, 0, 0), -1)
        
        # Add text
        cv2.putText(frame_with_text, text, (text_x, text_y),
                   font, font_scale, (255, 255, 255), thickness)
        
        # Write frame multiple times
        for _ in range(frame_duration):
            out.write(frame_with_text)
    
    out.release()
    print(f"Summary video saved to: {output_path}")


def plot_distance_curve(distances: np.ndarray, boundaries: List[int], 
                        output_path: str, threshold: float = None) -> None:
    """
    Plot the frame-to-frame distance curve with detected boundaries.
    
    Args:
        distances: Array of frame-to-frame distances
        boundaries: List of boundary indices
        output_path: Path to save the plot
        threshold: Optional threshold value to display
    """
    plt.figure(figsize=(12, 6))
    
    # Plot distance curve
    plt.plot(distances, linewidth=1, label='Frame Distance', color='blue', alpha=0.7)
    
    # Plot threshold line
    if threshold is not None:
        plt.axhline(y=threshold, color='red', linestyle='--', 
                   linewidth=2, label=f'Threshold: {threshold:.3f}')
    
    # Mark boundaries
    for boundary in boundaries:
        if 0 < boundary < len(distances):
            plt.axvline(x=boundary, color='green', linestyle='-', 
                       linewidth=1.5, alpha=0.5)
    
    plt.xlabel('Frame Index', fontsize=12)
    plt.ylabel('Distance', fontsize=12)
    plt.title('Frame-to-Frame Distance Curve with Shot Boundaries', fontsize=14, fontweight='bold')
    plt.legend(loc='upper right')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Distance curve plot saved to: {output_path}")


def export_all(keyframes: List[np.ndarray], keyframe_indices: List[int],
               summary_data: Dict, distances: np.ndarray, boundaries: List[int],
               output_dir: str = '.', base_name: str = 'summary',
               create_video: bool = False, threshold: float = None) -> Dict[str, str]:
    """
    Export all summarization results.
    
    Args:
        keyframes: List of keyframe images
        keyframe_indices: Original frame indices
        summary_data: Summary data dictionary
        distances: Frame distance array
        boundaries: Boundary indices
        output_dir: Output directory
        base_name: Base name for output files
        create_video: Whether to create summary video
        threshold: Optional threshold value used for boundary detection
        
    Returns:
        Dictionary mapping output type to file path
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    output_files = {}
    
    # Storyboard
    storyboard_path = os.path.join(output_dir, f'{base_name}_storyboard.png')
    frame_labels = [f"Shot {i+1}\nFrame {keyframe_indices[i]}" 
                   for i in range(len(keyframes))]
    create_storyboard(keyframes, storyboard_path, frame_labels=frame_labels)
    output_files['storyboard'] = storyboard_path
    
    # JSON boundaries
    json_path = os.path.join(output_dir, f'{base_name}_boundaries.json')
    save_boundaries_json(summary_data, json_path)
    output_files['boundaries'] = json_path
    
    # Distance curve plot
    curve_path = os.path.join(output_dir, f'{base_name}_distance_curve.png')
    # Use provided threshold or calculate from distances
    if threshold is None:
        threshold = np.percentile(distances, 75) if len(distances) > 0 else None
    plot_distance_curve(distances, boundaries, curve_path, threshold)
    output_files['distance_curve'] = curve_path
    
    # Optional summary video
    if create_video:
        video_path = os.path.join(output_dir, f'{base_name}_summary.mp4')
        try:
            create_summary_video(keyframes, keyframe_indices, video_path)
            output_files['summary_video'] = video_path
        except Exception as e:
            print(f"Warning: Could not create summary video: {e}")
    
    return output_files
