"""
Automatic Video Summarization Package

This package provides tools for automatic video summarization using
shot boundary detection and keyframe extraction.
"""

from src.video_summarizer import VideoSummarizer
from src.export_utils import (
    create_storyboard,
    save_boundaries_json,
    create_summary_video,
    export_all
)

__version__ = '1.0.0'
__all__ = [
    'VideoSummarizer',
    'create_storyboard',
    'save_boundaries_json',
    'create_summary_video',
    'export_all'
]
