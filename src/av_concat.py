"""
Audio-preserving video segment concatenation using ffmpeg.

This module provides functions to cut and concatenate video segments
while preserving both audio and video tracks.
"""
from __future__ import annotations

import subprocess
import tempfile
import shutil
import os
from pathlib import Path
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


def _find_ffmpeg_windows() -> Optional[str]:
    """Search common Windows locations for ffmpeg."""
    possible_paths = [
        # WinGet installation
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
        # Common manual installations
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
        Path(os.environ.get("USERPROFILE", "")) / "ffmpeg" / "bin",
    ]
    
    for base_path in possible_paths:
        if not base_path.exists():
            continue
        # Search for ffmpeg.exe recursively (for WinGet nested structure)
        for ffmpeg in base_path.rglob("ffmpeg.exe"):
            ffmpeg_dir = str(ffmpeg.parent)
            # Add to PATH for this session
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            logger.info(f"Found ffmpeg at: {ffmpeg_dir}")
            return str(ffmpeg)
    return None


def _check_ffmpeg() -> str:
    """Check if ffmpeg is available and return its path."""
    ffmpeg = shutil.which("ffmpeg")
    
    # If not found, try Windows-specific locations
    if ffmpeg is None and os.name == 'nt':
        ffmpeg = _find_ffmpeg_windows()
    
    if ffmpeg is None:
        raise RuntimeError(
            "ffmpeg not found. Please install ffmpeg and add it to PATH.\n"
            "Windows: winget install ffmpeg  OR  choco install ffmpeg\n"
            "Linux: sudo apt install ffmpeg\n"
            "macOS: brew install ffmpeg"
        )
    return ffmpeg


def cut_segment(
    input_path: Path,
    start_sec: float,
    end_sec: float,
    output_path: Path,
    stream_copy: bool = True,
) -> bool:
    """
    Cut a segment from input video using ffmpeg.
    
    Args:
        input_path: Source video file
        start_sec: Start time in seconds
        end_sec: End time in seconds
        output_path: Output segment file
        stream_copy: If True, use stream copy (fast, no re-encode).
                     If False, re-encode (slower, more compatible).
    
    Returns:
        True if successful, False otherwise.
    """
    ffmpeg = _check_ffmpeg()
    duration = end_sec - start_sec
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    if stream_copy:
        # Fast path: stream copy with accurate seeking
        # Use -ss after -i for accuracy (slightly slower but precise)
        cmd = [
            ffmpeg, "-y",
            "-i", str(input_path),
            "-ss", f"{start_sec:.3f}",
            "-t", f"{duration:.3f}",
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ]
    else:
        # Slow path: re-encode for compatibility
        cmd = [
            ffmpeg, "-y",
            "-i", str(input_path),
            "-ss", f"{start_sec:.3f}",
            "-t", f"{duration:.3f}",
            "-c:v", "libx264", "-crf", "18", "-preset", "fast",
            "-c:a", "aac", "-b:a", "160k",
            "-pix_fmt", "yuv420p",
            "-avoid_negative_ts", "make_zero",
            str(output_path)
        ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 min timeout per segment
        )
        if result.returncode != 0:
            logger.warning(f"ffmpeg cut failed: {result.stderr[:500]}")
            return False
        return output_path.exists()
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg cut timed out")
        return False
    except Exception as e:
        logger.error(f"ffmpeg cut error: {e}")
        return False


def concat_segments(
    segment_paths: List[Path],
    output_path: Path,
    stream_copy: bool = True,
) -> bool:
    """
    Concatenate multiple video segments using ffmpeg concat demuxer.
    
    Args:
        segment_paths: List of segment files to concatenate
        output_path: Output concatenated file
        stream_copy: If True, use stream copy. If False, re-encode.
    
    Returns:
        True if successful, False otherwise.
    """
    if not segment_paths:
        logger.error("No segments to concatenate")
        return False
    
    ffmpeg = _check_ffmpeg()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create concat list file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        concat_list_path = Path(f.name)
        for seg_path in segment_paths:
            # Use forward slashes and escape single quotes
            safe_path = str(seg_path.absolute()).replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
    
    try:
        if stream_copy:
            cmd = [
                ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c", "copy",
                str(output_path)
            ]
        else:
            cmd = [
                ffmpeg, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list_path),
                "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                "-c:a", "aac", "-b:a", "160k",
                "-pix_fmt", "yuv420p",
                str(output_path)
            ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 min timeout for concat
        )
        
        if result.returncode != 0:
            logger.warning(f"ffmpeg concat failed: {result.stderr[:500]}")
            return False
        
        return output_path.exists()
    
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg concat timed out")
        return False
    except Exception as e:
        logger.error(f"ffmpeg concat error: {e}")
        return False
    finally:
        # Cleanup concat list file
        try:
            concat_list_path.unlink()
        except:
            pass


def make_summary_with_audio(
    input_path: Path,
    segments: List[Tuple[float, float]],
    output_path: Path,
    cleanup_temp: bool = True,
) -> Tuple[bool, str]:
    """
    Create a summary video with audio by cutting and concatenating segments.
    
    Args:
        input_path: Source video file
        segments: List of (start_sec, end_sec) tuples
        output_path: Output summary file
        cleanup_temp: If True, remove temporary segment files after concat
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    if not segments:
        return False, "No segments provided"
    
    input_path = Path(input_path)
    output_path = Path(output_path)
    
    if not input_path.exists():
        return False, f"Input video not found: {input_path}"
    
    # Create temp directory for segments
    temp_dir = output_path.parent / "_temp_segments"
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    segment_paths: List[Path] = []
    failed_segments: List[int] = []
    
    try:
        # Step 1: Cut each segment (try stream copy first)
        for i, (start, end) in enumerate(segments):
            seg_path = temp_dir / f"seg_{i:04d}.mp4"
            
            # Try stream copy first (fast)
            success = cut_segment(input_path, start, end, seg_path, stream_copy=True)
            
            if not success:
                # Fallback to re-encode (slower but more compatible)
                logger.info(f"Segment {i}: stream copy failed, trying re-encode...")
                success = cut_segment(input_path, start, end, seg_path, stream_copy=False)
            
            if success:
                segment_paths.append(seg_path)
            else:
                failed_segments.append(i)
                logger.warning(f"Failed to cut segment {i}: {start:.2f}s - {end:.2f}s")
        
        if not segment_paths:
            return False, "All segment cuts failed"
        
        # Step 2: Concatenate segments (try stream copy first)
        success = concat_segments(segment_paths, output_path, stream_copy=True)
        
        if not success:
            # Fallback to re-encode concat
            logger.info("Stream copy concat failed, trying re-encode...")
            success = concat_segments(segment_paths, output_path, stream_copy=False)
        
        if not success:
            return False, "Concatenation failed"
        
        msg = f"Created summary with {len(segment_paths)} segments"
        if failed_segments:
            msg += f" ({len(failed_segments)} segments failed: {failed_segments})"
        
        return True, msg
    
    finally:
        # Cleanup temp files
        if cleanup_temp:
            try:
                for seg_path in segment_paths:
                    if seg_path.exists():
                        seg_path.unlink()
                if temp_dir.exists():
                    temp_dir.rmdir()
            except Exception as e:
                logger.warning(f"Cleanup failed: {e}")


def get_video_duration(video_path: Path) -> Optional[float]:
    """
    Get video duration in seconds using ffprobe.
    
    Returns None if duration cannot be determined.
    """
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    
    cmd = [
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    
    return None
