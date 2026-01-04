"""
Core video summarization module.

This module provides functionality for automatic video summarization using
shot boundary detection and keyframe extraction.
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict
import json


class VideoSummarizer:
    """
    Automatic video summarization using shot boundary detection.
    
    The pipeline:
    1. Load video and sample frames
    2. Compute HSV color histograms + edge histograms
    3. Calculate frame-to-frame distances
    4. Smooth the distance curve
    5. Apply adaptive threshold for shot boundary detection
    6. Extract one keyframe per shot
    """
    
    def __init__(self, video_path: str, sample_rate: int = 1):
        """
        Initialize the video summarizer.
        
        Args:
            video_path: Path to the input video file
            sample_rate: Sample every Nth frame (1 = every frame)
        """
        self.video_path = video_path
        self.sample_rate = sample_rate
        self.frames = []
        self.frame_indices = []
        self.distances = []
        self.boundaries = []
        self.keyframes = []
        self.keyframe_indices = []
        
    def load_video(self) -> None:
        """Load video and sample frames."""
        cap = cv2.VideoCapture(self.video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {self.video_path}")
        
        frame_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % self.sample_rate == 0:
                self.frames.append(frame)
                self.frame_indices.append(frame_count)
                
            frame_count += 1
        
        cap.release()
        print(f"Loaded {len(self.frames)} frames from video (sampled from {frame_count} total frames)")
    
    def compute_hsv_histogram(self, frame: np.ndarray, bins: Tuple[int, int, int] = (8, 8, 8)) -> np.ndarray:
        """
        Compute HSV color histogram for a frame.
        
        Args:
            frame: Input frame in BGR format
            bins: Number of bins for H, S, V channels
            
        Returns:
            Flattened normalized histogram
        """
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, bins, [0, 180, 0, 256, 0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        return hist
    
    def compute_edge_histogram(self, frame: np.ndarray, bins: int = 16) -> np.ndarray:
        """
        Compute edge histogram for a frame.
        
        Args:
            frame: Input frame in BGR format
            bins: Number of bins for the histogram
            
        Returns:
            Normalized edge histogram
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        hist, _ = np.histogram(edges.flatten(), bins=bins, range=(0, 256))
        hist = hist.astype(float) / (hist.sum() + 1e-7)  # Normalize
        return hist
    
    def compute_frame_distance(self, frame1: np.ndarray, frame2: np.ndarray, 
                               color_weight: float = 0.7, edge_weight: float = 0.3) -> float:
        """
        Compute distance between two frames using color and edge histograms.
        
        Args:
            frame1: First frame
            frame2: Second frame
            color_weight: Weight for color histogram distance
            edge_weight: Weight for edge histogram distance
            
        Returns:
            Combined distance metric
        """
        # Color histogram distance
        hist1_color = self.compute_hsv_histogram(frame1)
        hist2_color = self.compute_hsv_histogram(frame2)
        color_dist = cv2.compareHist(hist1_color, hist2_color, cv2.HISTCMP_CHISQR)
        
        # Edge histogram distance
        hist1_edge = self.compute_edge_histogram(frame1)
        hist2_edge = self.compute_edge_histogram(frame2)
        edge_dist = np.sum((hist1_edge - hist2_edge) ** 2)
        
        # Combined distance
        distance = color_weight * color_dist + edge_weight * edge_dist
        return distance
    
    def compute_distances(self) -> None:
        """Compute frame-to-frame distances for all consecutive frames."""
        if len(self.frames) < 2:
            raise ValueError("Need at least 2 frames to compute distances")
        
        self.distances = []
        for i in range(len(self.frames) - 1):
            dist = self.compute_frame_distance(self.frames[i], self.frames[i + 1])
            self.distances.append(dist)
            
            if (i + 1) % 100 == 0:
                print(f"Computed distances for {i + 1}/{len(self.frames) - 1} frame pairs")
        
        self.distances = np.array(self.distances)
        print(f"Distance curve computed: min={self.distances.min():.3f}, max={self.distances.max():.3f}, mean={self.distances.mean():.3f}")
    
    def smooth_distances(self, window_size: int = 5) -> np.ndarray:
        """
        Smooth the distance curve using a moving average.
        
        Args:
            window_size: Size of the smoothing window
            
        Returns:
            Smoothed distance array
        """
        if window_size < 1:
            return self.distances
        
        # Simple moving average
        kernel = np.ones(window_size) / window_size
        smoothed = np.convolve(self.distances, kernel, mode='same')
        return smoothed
    
    def detect_boundaries(self, threshold_percentile: float = 75, 
                         min_shot_length: int = 10, window_size: int = 5) -> None:
        """
        Detect shot boundaries using adaptive thresholding.
        
        Args:
            threshold_percentile: Percentile for adaptive threshold
            min_shot_length: Minimum number of frames in a shot
            window_size: Window size for smoothing
        """
        if len(self.distances) == 0:
            raise ValueError("Distances not computed. Call compute_distances() first.")
        
        # Smooth the distance curve
        smoothed_distances = self.smooth_distances(window_size)
        
        # Adaptive threshold
        threshold = np.percentile(smoothed_distances, threshold_percentile)
        print(f"Adaptive threshold: {threshold:.3f} (percentile: {threshold_percentile})")
        
        # Find peaks above threshold
        self.boundaries = [0]  # Start of video is always a boundary
        
        for i in range(1, len(smoothed_distances)):
            if smoothed_distances[i] > threshold:
                # Check minimum shot length
                if i - self.boundaries[-1] >= min_shot_length:
                    self.boundaries.append(i)
        
        # Add end boundary
        if self.boundaries[-1] != len(self.frames) - 1:
            self.boundaries.append(len(self.frames) - 1)
        
        print(f"Detected {len(self.boundaries) - 1} shots")
    
    def extract_keyframes(self, method: str = 'middle') -> None:
        """
        Extract one keyframe per shot.
        
        Args:
            method: Method for keyframe selection ('middle', 'first', 'last')
        """
        if len(self.boundaries) < 2:
            raise ValueError("Boundaries not detected. Call detect_boundaries() first.")
        
        self.keyframes = []
        self.keyframe_indices = []
        
        for i in range(len(self.boundaries) - 1):
            start = self.boundaries[i]
            end = self.boundaries[i + 1]
            
            if method == 'middle':
                keyframe_idx = (start + end) // 2
            elif method == 'first':
                keyframe_idx = start
            elif method == 'last':
                keyframe_idx = end - 1
            else:
                keyframe_idx = (start + end) // 2
            
            self.keyframes.append(self.frames[keyframe_idx])
            self.keyframe_indices.append(self.frame_indices[keyframe_idx])
        
        print(f"Extracted {len(self.keyframes)} keyframes")
    
    def get_summary_data(self) -> Dict:
        """
        Get summary data including boundaries and keyframe information.
        
        Returns:
            Dictionary with summary information
        """
        shots = []
        for i in range(len(self.boundaries) - 1):
            start_frame = self.frame_indices[self.boundaries[i]]
            end_frame = self.frame_indices[self.boundaries[i + 1]]
            keyframe = self.keyframe_indices[i] if i < len(self.keyframe_indices) else None
            
            shots.append({
                'shot_id': i,
                'start_frame': int(start_frame),
                'end_frame': int(end_frame),
                'keyframe': int(keyframe) if keyframe is not None else None,
                'duration_frames': int(end_frame - start_frame)
            })
        
        return {
            'video_path': self.video_path,
            'total_shots': len(shots),
            'total_frames_sampled': len(self.frames),
            'sample_rate': self.sample_rate,
            'shots': shots
        }
    
    def run_pipeline(self, threshold_percentile: float = 75, 
                     min_shot_length: int = 10, window_size: int = 5,
                     keyframe_method: str = 'middle') -> Dict:
        """
        Run the complete video summarization pipeline.
        
        Args:
            threshold_percentile: Percentile for adaptive threshold
            min_shot_length: Minimum frames per shot
            window_size: Smoothing window size
            keyframe_method: Method for keyframe extraction
            
        Returns:
            Summary data dictionary
        """
        print(f"\n=== Video Summarization Pipeline ===")
        print(f"Video: {self.video_path}")
        
        print("\n[1/4] Loading video...")
        self.load_video()
        
        print("\n[2/4] Computing frame distances...")
        self.compute_distances()
        
        print("\n[3/4] Detecting shot boundaries...")
        self.detect_boundaries(threshold_percentile, min_shot_length, window_size)
        
        print("\n[4/4] Extracting keyframes...")
        self.extract_keyframes(keyframe_method)
        
        print("\n=== Pipeline Complete ===\n")
        
        return self.get_summary_data()
