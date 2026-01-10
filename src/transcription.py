"""
Audio transcription using OpenAI Whisper (local, free).
============================================================
Adds AI-powered speech recognition to the video summarization pipeline.

Usage:
    from src.transcription import transcribe_video, generate_scene_titles
    
    transcript = transcribe_video("video.mp4", model_size="base")
    scenes = generate_scene_titles(transcript, scenes)
"""
from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import tempfile
import shutil


def extract_audio(video_path: str, audio_path: str) -> bool:
    """
    Extract audio from video using ffmpeg.
    
    Args:
        video_path: Path to input video
        audio_path: Path to output audio file (WAV format)
        
    Returns:
        True if successful, False otherwise
    """
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        print("[Transcription] ffmpeg not found, cannot extract audio")
        return False
    
    try:
        result = subprocess.run([
            ffmpeg, "-y", "-i", video_path,
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # PCM 16-bit
            "-ar", "16000",  # 16kHz sample rate (Whisper optimal)
            "-ac", "1",  # Mono
            audio_path
        ], check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[Transcription] Audio extraction failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"[Transcription] Audio extraction error: {e}")
        return False


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
) -> Dict:
    """
    Transcribe audio using Whisper.
    
    Args:
        audio_path: Path to audio file (WAV recommended)
        model_size: Whisper model size - tiny, base, small, medium, large
                   (base is good balance of speed/accuracy)
    
    Returns:
        {
            "text": "full transcript",
            "language": "en",
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "Hello world"},
                ...
            ]
        }
    """
    try:
        import whisper
    except ImportError:
        raise ImportError(
            "Whisper not installed. Run: pip install openai-whisper"
        )
    
    print(f"[Whisper] Loading {model_size} model...")
    model = whisper.load_model(model_size)
    
    print(f"[Whisper] Transcribing audio...")
    result = model.transcribe(audio_path, verbose=False)
    
    segments = [
        {
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        }
        for seg in result["segments"]
    ]
    
    print(f"[Whisper] Found {len(segments)} speech segments")
    
    return {
        "text": result["text"].strip(),
        "language": result.get("language", "unknown"),
        "segments": segments,
    }


def transcribe_video(
    video_path: str,
    model_size: str = "base",
) -> Optional[Dict]:
    """
    Full pipeline: extract audio from video and transcribe.
    
    Args:
        video_path: Path to input video
        model_size: Whisper model size (tiny/base/small/medium/large)
        
    Returns:
        Transcript dict or None if failed
    """
    # Create temporary WAV file
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        audio_path = f.name
    
    try:
        print(f"[Transcription] Extracting audio from video...")
        if not extract_audio(video_path, audio_path):
            return None
        
        return transcribe_audio(audio_path, model_size)
    finally:
        # Clean up temp file
        Path(audio_path).unlink(missing_ok=True)


def get_transcript_for_segment(
    transcript: Dict,
    start_sec: float,
    end_sec: float,
) -> str:
    """
    Get transcript text that falls within a time segment.
    
    Args:
        transcript: Full transcript dict from transcribe_video
        start_sec: Segment start time
        end_sec: Segment end time
        
    Returns:
        Concatenated text from overlapping speech segments
    """
    if not transcript or "segments" not in transcript:
        return ""
    
    texts = []
    for seg in transcript["segments"]:
        # Check if segment overlaps with our time range
        if seg["end"] > start_sec and seg["start"] < end_sec:
            texts.append(seg["text"])
    
    return " ".join(texts).strip()


def generate_scene_titles(
    transcript: Dict,
    scenes: List[Dict],
    max_title_length: int = 60,
) -> List[Dict]:
    """
    Add transcript-based titles to each scene.
    
    Args:
        transcript: Full transcript dict
        scenes: List of scene dicts with start_sec/end_sec
        max_title_length: Maximum characters for title
        
    Returns:
        Scenes list with added 'title' and 'transcript' fields
    """
    if not transcript:
        # No transcript available, add placeholder
        for scene in scenes:
            scene["title"] = f"Scene {scene.get('index', '?')}"
            scene["transcript"] = ""
        return scenes
    
    for scene in scenes:
        text = get_transcript_for_segment(
            transcript,
            scene.get("start_sec", 0),
            scene.get("end_sec", 0),
        )
        
        # Generate title from transcript
        if text:
            # Use first N chars as title
            if len(text) > max_title_length:
                title = text[:max_title_length].rsplit(" ", 1)[0] + "..."
            else:
                title = text
        else:
            title = "[No speech]"
        
        scene["title"] = title
        scene["transcript"] = text
    
    return scenes


def get_transcript_summary(transcript: Dict) -> Dict:
    """
    Get summary statistics about the transcript.
    
    Returns:
        {
            "language": "en",
            "total_words": 150,
            "total_segments": 25,
            "speech_duration_sec": 120.5,
            "words_per_minute": 75.0
        }
    """
    if not transcript:
        return {
            "language": "unknown",
            "total_words": 0,
            "total_segments": 0,
            "speech_duration_sec": 0,
            "words_per_minute": 0,
        }
    
    total_words = len(transcript.get("text", "").split())
    segments = transcript.get("segments", [])
    
    # Calculate total speech duration
    speech_duration = sum(
        seg["end"] - seg["start"] 
        for seg in segments
    )
    
    wpm = (total_words / speech_duration * 60) if speech_duration > 0 else 0
    
    return {
        "language": transcript.get("language", "unknown"),
        "total_words": total_words,
        "total_segments": len(segments),
        "speech_duration_sec": round(speech_duration, 2),
        "words_per_minute": round(wpm, 1),
    }
