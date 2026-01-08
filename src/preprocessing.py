"""
Video preprocessing utilities.

Handles cleaning/re-encoding problematic video files before processing.
"""
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


def _check_ffmpeg() -> str:
    """Check if ffmpeg is available and return its path."""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and add it to PATH.\n"
            "Windows: winget install ffmpeg  OR  choco install ffmpeg\n"
            "Linux: sudo apt install ffmpeg\n"
            "macOS: brew install ffmpeg"
        )
    return ffmpeg


def clean_video(
    input_path: Path,
    output_path: Path,
    crf: int = 18,
    preset: str = "veryfast",
    audio_bitrate: str = "160k",
) -> Tuple[bool, str]:
    """
    Re-encode video to fix codec issues (H.264 mmco errors, corrupt frames, etc.)
    
    This creates a clean, standardized H.264/AAC file that OpenCV and ffmpeg
    can handle without warnings.
    
    Args:
        input_path: Source video with potential issues
        output_path: Cleaned output video
        crf: Constant Rate Factor (18 = visually lossless, 23 = default, 28 = smaller)
        preset: Encoding speed/quality tradeoff 
                (ultrafast, veryfast, fast, medium, slow)
        audio_bitrate: Audio bitrate (e.g., "128k", "160k", "192k")
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        return False, f"Input video not found: {input_path}"
    
    ffmpeg = _check_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        ffmpeg, "-y",
        "-i", str(input_path),
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p",  # Maximum compatibility
        "-c:a", "aac",
        "-b:a", audio_bitrate,
        "-movflags", "+faststart",  # Web streaming optimization
        str(output_path)
    ]
    
    try:
        logger.info(f"Cleaning video: {input_path.name} -> {output_path.name}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout for long videos
        )
        
        if result.returncode != 0:
            error_msg = result.stderr[:1000] if result.stderr else "Unknown error"
            return False, f"ffmpeg failed: {error_msg}"
        
        if not output_path.exists():
            return False, "Output file was not created"
        
        # Verify output is valid
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        
        if output_size < input_size * 0.01:  # Output < 1% of input is suspicious
            return False, f"Output file suspiciously small ({output_size} bytes)"
        
        return True, f"Cleaned video saved: {output_path}"
    
    except subprocess.TimeoutExpired:
        return False, "Video cleaning timed out (>1 hour)"
    except Exception as e:
        return False, f"Error during video cleaning: {e}"


def probe_video_issues(video_path: Path) -> Tuple[bool, str]:
    """
    Quick probe to detect potential issues in a video file.
    
    Returns:
        Tuple of (has_issues: bool, description: str)
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return False, "ffprobe not available, cannot check for issues"
    
    cmd = [
        ffprobe,
        "-v", "error",  # Only show errors
        "-i", str(video_path),
        "-f", "null", "-"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        stderr = result.stderr.lower()
        
        issues = []
        if "mmco" in stderr:
            issues.append("H.264 mmco reference errors")
        if "invalid" in stderr:
            issues.append("Invalid data detected")
        if "corrupt" in stderr:
            issues.append("Corruption detected")
        if "error" in stderr and "non-existing" in stderr:
            issues.append("Missing reference frames")
        
        if issues:
            return True, f"Issues found: {', '.join(issues)}"
        
        return False, "No obvious issues detected"
    
    except subprocess.TimeoutExpired:
        return True, "Probe timed out (may indicate issues)"
    except Exception as e:
        return True, f"Probe error: {e}"


def ensure_clean_video(
    input_path: Path,
    output_dir: Path,
    force_clean: bool = False,
) -> Tuple[Path, bool, str]:
    """
    Ensure we have a clean video to process.
    
    If force_clean=True or issues are detected, creates a cleaned copy.
    Otherwise, returns the original path.
    
    Args:
        input_path: Original video path
        output_dir: Directory to store cleaned video if needed
        force_clean: If True, always re-encode
    
    Returns:
        Tuple of (video_path_to_use, was_cleaned, message)
    """
    input_path = Path(input_path)
    
    if not force_clean:
        has_issues, issue_msg = probe_video_issues(input_path)
        if not has_issues:
            return input_path, False, "Original video looks clean"
        logger.info(f"Video issues detected: {issue_msg}")
    
    # Need to clean
    clean_path = output_dir / f"{input_path.stem}_clean.mp4"
    success, msg = clean_video(input_path, clean_path)
    
    if success:
        return clean_path, True, msg
    else:
        # Cleaning failed, use original anyway
        logger.warning(f"Cleaning failed ({msg}), using original video")
        return input_path, False, f"Cleaning failed: {msg}"
