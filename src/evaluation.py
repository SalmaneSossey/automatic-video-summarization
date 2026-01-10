"""
Evaluation metrics for video summarization.
============================================================
Provides quantitative metrics to assess summary quality.

Metrics included:
- Compression ratio and reduction percentage
- Timeline coverage and distribution analysis
- Scene quality statistics
- Uniformity score (how well distributed across video)

Usage:
    from src.evaluation import generate_evaluation_report
    
    report = generate_evaluation_report(
        original_duration=900.0,
        summary_duration=60.0,
        scenes=scenes_list
    )
"""
from typing import List, Tuple, Dict
import numpy as np


def calculate_coverage(
    summary_segments: List[Tuple[float, float]],
    video_duration: float,
) -> float:
    """
    Calculate what percentage of video timeline is covered by summary.
    
    Note: This measures total duration of selected segments relative to
    the full video, not whether every part is represented.
    
    Args:
        summary_segments: List of (start, end) tuples
        video_duration: Total video duration in seconds
        
    Returns:
        Coverage percentage (0-100)
    """
    if video_duration <= 0:
        return 0.0
    
    total_covered = sum(end - start for start, end in summary_segments)
    return (total_covered / video_duration) * 100


def calculate_compression_ratio(
    original_duration: float,
    summary_duration: float,
) -> float:
    """
    Calculate compression ratio.
    
    Example: 15 min video → 1 min summary = 15:1 ratio
    
    Args:
        original_duration: Original video duration in seconds
        summary_duration: Summary video duration in seconds
        
    Returns:
        Compression ratio (higher = more compression)
    """
    if summary_duration <= 0:
        return float('inf')
    return original_duration / summary_duration


def calculate_scene_distribution(
    scenes: List[Dict],
    video_duration: float,
    num_bins: int = 10,
) -> Dict:
    """
    Analyze how well scenes are distributed across video timeline.
    
    Good summaries should cover different parts of the video,
    not cluster all scenes in one area.
    
    Args:
        scenes: List of scene dicts with start_sec/end_sec
        video_duration: Total video duration
        num_bins: Number of time bins to divide video into
        
    Returns:
        {
            "bins": [2, 1, 3, 0, ...],  # scenes per bin
            "uniformity": 0.85,          # 0=clustered, 1=uniform
            "coverage_gaps": 2,          # bins with 0 scenes
            "temporal_spread": 0.9       # normalized spread
        }
    """
    if video_duration <= 0 or not scenes:
        return {
            "bins": [0] * num_bins,
            "uniformity": 0.0,
            "coverage_gaps": num_bins,
            "temporal_spread": 0.0,
        }
    
    bin_size = video_duration / num_bins
    bins = [0] * num_bins
    
    # Count scenes in each time bin
    for scene in scenes:
        mid_point = (scene.get("start_sec", 0) + scene.get("end_sec", 0)) / 2
        bin_idx = min(int(mid_point / bin_size), num_bins - 1)
        bins[bin_idx] += 1
    
    # Calculate uniformity (0 = all in one bin, 1 = perfectly uniform)
    total_scenes = len(scenes)
    expected = total_scenes / num_bins
    
    # Use coefficient of variation for uniformity
    variance = sum((b - expected) ** 2 for b in bins) / num_bins
    std_dev = np.sqrt(variance)
    cv = std_dev / expected if expected > 0 else 0
    uniformity = max(0, 1 - cv)
    
    # Calculate temporal spread (first scene to last scene)
    scene_times = [(s.get("start_sec", 0) + s.get("end_sec", 0)) / 2 for s in scenes]
    if len(scene_times) >= 2:
        temporal_spread = (max(scene_times) - min(scene_times)) / video_duration
    else:
        temporal_spread = 0.0
    
    return {
        "bins": bins,
        "uniformity": round(uniformity, 3),
        "coverage_gaps": bins.count(0),
        "temporal_spread": round(temporal_spread, 3),
    }


def calculate_quality_metrics(scenes: List[Dict]) -> Dict:
    """
    Aggregate quality scores from selected scenes.
    
    Args:
        scenes: List of scene dicts with quality_score field
        
    Returns:
        Statistical summary of quality scores
    """
    if not scenes:
        return {
            "mean": 0.0,
            "std": 0.0,
            "min": 0.0,
            "max": 0.0,
            "median": 0.0,
        }
    
    scores = [s.get("quality_score", 0.5) for s in scenes]
    
    return {
        "mean": round(float(np.mean(scores)), 3),
        "std": round(float(np.std(scores)), 3),
        "min": round(float(min(scores)), 3),
        "max": round(float(max(scores)), 3),
        "median": round(float(np.median(scores)), 3),
    }


def calculate_scene_duration_stats(scenes: List[Dict]) -> Dict:
    """
    Analyze scene duration statistics.
    
    Args:
        scenes: List of scene dicts with duration_sec field
        
    Returns:
        Duration statistics
    """
    if not scenes:
        return {
            "mean_sec": 0.0,
            "std_sec": 0.0,
            "min_sec": 0.0,
            "max_sec": 0.0,
            "total_sec": 0.0,
        }
    
    durations = [s.get("duration_sec", 0) for s in scenes]
    
    return {
        "mean_sec": round(float(np.mean(durations)), 2),
        "std_sec": round(float(np.std(durations)), 2),
        "min_sec": round(float(min(durations)), 2),
        "max_sec": round(float(max(durations)), 2),
        "total_sec": round(float(sum(durations)), 2),
    }


def generate_evaluation_report(
    original_duration: float,
    summary_duration: float,
    scenes: List[Dict],
) -> Dict:
    """
    Generate comprehensive evaluation report.
    
    This report provides quantitative metrics for academic evaluation
    of the video summarization quality.
    
    Args:
        original_duration: Original video duration in seconds
        summary_duration: Summary video duration in seconds
        scenes: List of scene dictionaries
        
    Returns:
        Comprehensive evaluation metrics dictionary
    """
    # Extract segments for coverage calculation
    segments = [
        (s.get("start_sec", 0), s.get("end_sec", 0)) 
        for s in scenes
    ]
    
    # Compression metrics
    compression = {
        "original_duration_sec": round(original_duration, 2),
        "summary_duration_sec": round(summary_duration, 2),
        "compression_ratio": round(
            calculate_compression_ratio(original_duration, summary_duration), 2
        ),
        "reduction_percent": round(
            (1 - summary_duration / original_duration) * 100 
            if original_duration > 0 else 0, 1
        ),
    }
    
    # Coverage metrics
    coverage = {
        "timeline_coverage_percent": round(
            calculate_coverage(segments, original_duration), 2
        ),
        "num_scenes": len(scenes),
        "avg_scene_duration_sec": round(
            summary_duration / len(scenes) if scenes else 0, 2
        ),
    }
    
    # Distribution analysis
    distribution = calculate_scene_distribution(scenes, original_duration)
    
    # Quality metrics
    quality = calculate_quality_metrics(scenes)
    
    # Scene duration stats
    duration_stats = calculate_scene_duration_stats(scenes)
    
    return {
        "compression": compression,
        "coverage": coverage,
        "distribution": distribution,
        "quality_scores": quality,
        "scene_durations": duration_stats,
        "summary_score": calculate_overall_score(
            compression, coverage, distribution, quality
        ),
    }


def calculate_overall_score(
    compression: Dict,
    coverage: Dict,
    distribution: Dict,
    quality: Dict,
) -> Dict:
    """
    Calculate an overall summary quality score.
    
    Combines multiple factors:
    - Compression efficiency
    - Timeline coverage
    - Distribution uniformity
    - Scene quality
    
    Returns:
        Overall score and component breakdown
    """
    # Normalize compression (target: 10-20x is ideal)
    ratio = compression.get("compression_ratio", 1)
    if ratio < 5:
        comp_score = 0.5  # Not compressed enough
    elif ratio > 30:
        comp_score = 0.7  # Very compressed (might lose content)
    else:
        comp_score = 1.0  # Good compression range
    
    # Distribution uniformity (higher is better)
    dist_score = distribution.get("uniformity", 0.5)
    
    # Coverage (moderate coverage is good, too high means not summarizing)
    cov_pct = coverage.get("timeline_coverage_percent", 0)
    if cov_pct < 3:
        cov_score = 0.5  # Too little
    elif cov_pct > 20:
        cov_score = 0.7  # Not summarized enough
    else:
        cov_score = 1.0  # Good range
    
    # Quality score
    qual_score = quality.get("mean", 0.5)
    
    # Weighted combination
    weights = {
        "compression": 0.2,
        "distribution": 0.3,
        "coverage": 0.2,
        "quality": 0.3,
    }
    
    overall = (
        weights["compression"] * comp_score +
        weights["distribution"] * dist_score +
        weights["coverage"] * cov_score +
        weights["quality"] * qual_score
    )
    
    return {
        "overall": round(overall, 3),
        "components": {
            "compression_score": round(comp_score, 3),
            "distribution_score": round(dist_score, 3),
            "coverage_score": round(cov_score, 3),
            "quality_score": round(qual_score, 3),
        },
        "weights": weights,
    }


def format_evaluation_report(report: Dict) -> str:
    """
    Format evaluation report as readable text.
    
    Args:
        report: Evaluation report dictionary
        
    Returns:
        Formatted string for display
    """
    lines = [
        "=" * 60,
        "   VIDEO SUMMARIZATION EVALUATION REPORT",
        "=" * 60,
        "",
        "📊 COMPRESSION METRICS",
        f"   Original Duration:  {report['compression']['original_duration_sec']}s",
        f"   Summary Duration:   {report['compression']['summary_duration_sec']}s",
        f"   Compression Ratio:  {report['compression']['compression_ratio']}:1",
        f"   Reduction:          {report['compression']['reduction_percent']}%",
        "",
        "📍 COVERAGE METRICS",
        f"   Timeline Coverage:  {report['coverage']['timeline_coverage_percent']}%",
        f"   Number of Scenes:   {report['coverage']['num_scenes']}",
        f"   Avg Scene Duration: {report['coverage']['avg_scene_duration_sec']}s",
        "",
        "📈 DISTRIBUTION ANALYSIS",
        f"   Uniformity Score:   {report['distribution']['uniformity']} (0-1, higher=better)",
        f"   Coverage Gaps:      {report['distribution']['coverage_gaps']} bins",
        f"   Temporal Spread:    {report['distribution']['temporal_spread']}",
        "",
        "⭐ QUALITY METRICS",
        f"   Mean Quality:       {report['quality_scores']['mean']}",
        f"   Quality Std Dev:    {report['quality_scores']['std']}",
        f"   Quality Range:      [{report['quality_scores']['min']}, {report['quality_scores']['max']}]",
        "",
        "🏆 OVERALL SCORE",
        f"   Score:              {report['summary_score']['overall']:.2f} / 1.00",
        "",
        "=" * 60,
    ]
    
    return "\n".join(lines)
