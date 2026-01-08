"""
Summary manifest generation.

Creates structured JSON output for browsable video summaries.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional
from datetime import datetime


@dataclass
class SegmentInfo:
    """Information about a summary segment."""
    index: int
    start_sec: float
    end_sec: float
    start_hms: str  # Human-readable HH:MM:SS
    end_hms: str
    duration_sec: float
    score: float
    keyframe_path: Optional[str]
    title: Optional[str] = None  # For future transcript-based titles


@dataclass
class SummaryManifest:
    """Complete summary manifest."""
    input_video: str
    input_duration_sec: float
    generated_at: str
    total_segments: int
    summary_duration_sec: float
    compression_ratio: float  # summary_duration / input_duration
    segments: List[SegmentInfo]
    
    # Pipeline parameters used
    params: dict


def seconds_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def generate_summary_manifest(
    input_video: str,
    input_duration_sec: float,
    segments: List[tuple],  # List of (start_sec, end_sec, score, shot_index)
    keyframe_paths: List[str],
    params: dict,
    output_path: Path,
) -> SummaryManifest:
    """
    Generate a structured summary manifest JSON file.
    
    Args:
        input_video: Path to original video
        input_duration_sec: Duration of input video
        segments: List of (start_sec, end_sec, score, shot_index) tuples
        keyframe_paths: List of paths to keyframe images (parallel to segments)
        params: Pipeline parameters used
        output_path: Where to save the JSON file
    
    Returns:
        SummaryManifest object
    """
    segment_infos: List[SegmentInfo] = []
    total_duration = 0.0
    
    for i, (start, end, score, shot_idx) in enumerate(segments):
        duration = end - start
        total_duration += duration
        
        keyframe_path = keyframe_paths[i] if i < len(keyframe_paths) else None
        
        segment_infos.append(SegmentInfo(
            index=i,
            start_sec=round(start, 3),
            end_sec=round(end, 3),
            start_hms=seconds_to_hms(start),
            end_hms=seconds_to_hms(end),
            duration_sec=round(duration, 3),
            score=round(score, 4),
            keyframe_path=keyframe_path,
            title=None,  # Placeholder for future transcript integration
        ))
    
    compression_ratio = total_duration / input_duration_sec if input_duration_sec > 0 else 0.0
    
    manifest = SummaryManifest(
        input_video=str(input_video),
        input_duration_sec=round(input_duration_sec, 3),
        generated_at=datetime.now().isoformat(),
        total_segments=len(segment_infos),
        summary_duration_sec=round(total_duration, 3),
        compression_ratio=round(compression_ratio, 4),
        segments=segment_infos,
        params=params,
    )
    
    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dict for JSON serialization
    manifest_dict = {
        "input_video": manifest.input_video,
        "input_duration_sec": manifest.input_duration_sec,
        "generated_at": manifest.generated_at,
        "total_segments": manifest.total_segments,
        "summary_duration_sec": manifest.summary_duration_sec,
        "compression_ratio": manifest.compression_ratio,
        "params": manifest.params,
        "segments": [asdict(seg) for seg in manifest.segments],
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(manifest_dict, f, indent=2, ensure_ascii=False)
    
    return manifest


def generate_highlights_json(
    segments: List[tuple],  # List of (start_sec, end_sec, score, shot_index)
    keyframe_paths: List[str],
    output_path: Path,
) -> None:
    """
    Generate a simpler highlights.json with just segment info.
    
    Useful for quick browsing without full manifest details.
    """
    highlights = []
    
    for i, (start, end, score, shot_idx) in enumerate(segments):
        keyframe = keyframe_paths[i] if i < len(keyframe_paths) else None
        
        highlights.append({
            "segment_index": i,
            "shot_index": shot_idx,
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "start_hms": seconds_to_hms(start),
            "end_hms": seconds_to_hms(end),
            "duration_sec": round(end - start, 3),
            "score": round(score, 4),
            "keyframe": keyframe,
        })
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(highlights, f, indent=2, ensure_ascii=False)
