"""
Automatic Video Summarization - Web UI
======================================
A Gradio-based web interface for the video summarization pipeline.

Run with:
    python app.py

Then open http://localhost:7860 in your browser.
"""
import os
import time
import shutil
from pathlib import Path

import gradio as gr

from summarize import summarize, get_video_info, format_time

# Use a stable output directory inside the project (avoids Windows temp file locking)
PROJECT_DIR = Path(__file__).parent
UI_OUTPUT_DIR = PROJECT_DIR / "outputs" / "_ui_workspace"


def _ensure_ffmpeg_path():
    """Ensure ffmpeg is on PATH (Windows-specific fix)."""
    if shutil.which("ffmpeg"):
        return True
    
    # Try common Windows locations
    possible_paths = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Links",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages",
        Path("C:/ffmpeg/bin"),
        Path("C:/Program Files/ffmpeg/bin"),
    ]
    
    for p in possible_paths:
        if p.exists():
            # Search for ffmpeg.exe recursively
            for ffmpeg in p.rglob("ffmpeg.exe"):
                os.environ["PATH"] = str(ffmpeg.parent) + os.pathsep + os.environ.get("PATH", "")
                return True
    return False


def process_video(
    video_file,
    fps_sample: float,
    threshold_percentile: float,
    min_shot_duration: float,
    max_summary_duration: float,
    secs_per_shot: float,
    keep_audio: bool,
    clean_input: bool,
    best_keyframes: bool,
    progress=gr.Progress(track_tqdm=True),
):
    """
    Process uploaded video and return summarization outputs.
    """
    if video_file is None:
        raise gr.Error("Please upload a video file first.")
    
    # Use stable output directory (avoids Windows temp file locking issues)
    run_id = f"run_{int(time.time())}"
    output_dir = UI_OUTPUT_DIR / run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy input to our workspace
    local_input = output_dir / "input.mp4"
    try:
        shutil.copyfile(video_file, local_input)
        video_file = str(local_input)
    except Exception as e:
        print(f"[UI] Warning: Could not copy input file: {e}")
        # Continue with original path
    
    # Ensure ffmpeg is available
    ffmpeg_found = _ensure_ffmpeg_path()
    ffmpeg_in_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")

    # If audio requested but ffmpeg unavailable, fall back to video-only
    audio_enabled = keep_audio and ffmpeg_found
    print(f"[UI] ffmpeg_found={ffmpeg_found} ffmpeg_in_path={ffmpeg_in_path} audio_enabled={audio_enabled}")
    fallback_note = ""
    if keep_audio and not ffmpeg_found:
        fallback_note = "(Audio disabled: ffmpeg not found in PATH)"

    try:
        progress(0.1, desc="Starting summarization...")
        
        result = summarize(
            input_path=video_file,
            output_dir=str(output_dir),
            fps_sample=fps_sample,
            threshold_percentile=threshold_percentile,
            min_shot_duration=min_shot_duration,
            secs_per_shot=secs_per_shot,
            max_summary_duration=max_summary_duration,
            keep_audio=audio_enabled,
            clean_input=clean_input,
            best_keyframes=best_keyframes,
        )
        
        progress(0.95, desc="Preparing outputs...")
        
        # Get output paths (use absolute paths for Gradio)
        summary_video = output_dir / "summary.mp4"
        storyboard = output_dir / "storyboard.png"
        analysis = output_dir / "analysis.png"
        manifest = result["manifest"]
        
        # Format summary stats
        stats_md = f"""
## ✅ Summarization Complete {fallback_note}

| Metric | Value |
|--------|-------|
| **Input Duration** | {manifest['input']['duration_hms']} ({manifest['input']['duration_sec']}s) |
| **Summary Duration** | {manifest['summary']['duration_hms']} ({manifest['summary']['duration_sec']}s) |
| **Compression** | {manifest['summary']['compression_percent']:.0f}% |
| **Scenes Detected** | {manifest['analysis']['scenes_detected']} |
| **Processing Time** | {result['elapsed_sec']:.1f}s |
| **Audio** | {"Preserved" if audio_enabled else "Video-only"} |

### Scene Breakdown
"""
        for scene in manifest["scenes"]:
            stats_md += f"- **Scene {scene['index']}**: {scene['start_hms']} → {scene['end_hms']} ({scene['duration_sec']}s) - Quality: {scene['quality_score']:.2f}\n"
        
        progress(1.0, desc="Done!")
        
        # Return absolute paths (Gradio handles serving)
        return (
            str(summary_video.absolute()) if summary_video.exists() else None,
            str(storyboard.absolute()) if storyboard.exists() else None,
            str(analysis.absolute()) if analysis.exists() else None,
            stats_md,
        )
        
    except Exception as e:
        # If ffmpeg failure occurred mid-run, retry without audio for resilience
        if keep_audio and "ffmpeg not found" in str(e).lower():
            try:
                result = summarize(
                    input_path=video_file,
                    output_dir=str(output_dir),
                    fps_sample=fps_sample,
                    threshold_percentile=threshold_percentile,
                    min_shot_duration=min_shot_duration,
                    secs_per_shot=secs_per_shot,
                    max_summary_duration=max_summary_duration,
                    keep_audio=False,
                    clean_input=clean_input,
                    best_keyframes=best_keyframes,
                )

                manifest = result["manifest"]
                summary_video = output_dir / "summary.mp4"
                storyboard = output_dir / "storyboard.png"
                analysis = output_dir / "analysis.png"

                stats_md = f"""
## ✅ Summarization Complete (Audio disabled: ffmpeg missing)

| Metric | Value |
|--------|-------|
| **Input Duration** | {manifest['input']['duration_hms']} ({manifest['input']['duration_sec']}s) |
| **Summary Duration** | {manifest['summary']['duration_hms']} ({manifest['summary']['duration_sec']}s) |
| **Compression** | {manifest['summary']['compression_percent']:.0f}% |
| **Scenes Detected** | {manifest['analysis']['scenes_detected']} |
| **Processing Time** | {result['elapsed_sec']:.1f}s |
| **Audio** | Video-only |
"""
                for scene in manifest["scenes"]:
                    stats_md += f"- **Scene {scene['index']}**: {scene['start_hms']} → {scene['end_hms']} ({scene['duration_sec']}s) - Quality: {scene['quality_score']:.2f}\n"

                return (
                    str(summary_video.absolute()) if summary_video.exists() else None,
                    str(storyboard.absolute()) if storyboard.exists() else None,
                    str(analysis.absolute()) if analysis.exists() else None,
                    stats_md,
                )
            except Exception as inner:
                raise gr.Error(f"Summarization failed after retry without audio: {inner}")

        raise gr.Error(f"Summarization failed: {str(e)}")


def get_video_preview(video_file):
    """Get video info for preview."""
    if video_file is None:
        return "Upload a video to see its details."
    
    try:
        info = get_video_info(video_file)
        return f"""
**Video Details:**
- Duration: {format_time(info['duration_sec'])} ({info['duration_sec']:.1f}s)
- Resolution: {info['width']}x{info['height']}
- Frame Rate: {info['fps']:.1f} fps
- Total Frames: {info['frame_count']:,}
"""
    except Exception as e:
        return f"Could not read video: {e}"


# Custom CSS for better styling
custom_css = """
.gradio-container {
    max-width: 1200px !important;
}
.output-video {
    max-height: 480px;
}
#title {
    text-align: center;
    margin-bottom: 0.5em;
}
#subtitle {
    text-align: center;
    color: #666;
    margin-bottom: 1.5em;
}
"""

# Build the Gradio interface
with gr.Blocks(title="Automatic Video Summarization") as app:
    
    gr.Markdown("# 🎬 Automatic Video Summarization", elem_id="title")
    gr.Markdown("Transform long videos into concise, meaningful summaries", elem_id="subtitle")
    
    with gr.Row():
        # Left column - Input
        with gr.Column(scale=1):
            gr.Markdown("### 📤 Input")
            
            video_input = gr.Video(
                label="Upload Video",
                sources=["upload"],
            )
            
            video_info = gr.Markdown("Upload a video to see its details.")
            
            video_input.change(
                fn=get_video_preview,
                inputs=[video_input],
                outputs=[video_info],
            )
            
            gr.Markdown("### ⚙️ Parameters")
            
            with gr.Accordion("Detection Settings", open=True):
                fps_slider = gr.Slider(
                    minimum=1, maximum=10, value=3, step=0.5,
                    label="Analysis FPS",
                    info="Higher = more accurate but slower (recommended: 2-4)",
                )
                threshold_slider = gr.Slider(
                    minimum=50, maximum=99, value=92, step=1,
                    label="Scene Threshold",
                    info="Higher = fewer scenes detected (recommended: 88-96)",
                )
                min_duration_slider = gr.Slider(
                    minimum=1, maximum=15, value=3, step=0.5,
                    label="Min Scene Duration (sec)",
                    info="Minimum duration for a valid scene",
                )
            
            with gr.Accordion("Output Settings", open=True):
                max_duration_slider = gr.Slider(
                    minimum=15, maximum=300, value=60, step=5,
                    label="Max Summary Duration (sec)",
                    info="Maximum length of output video (60s for Shorts, 90s max)",
                )
                secs_per_shot_slider = gr.Slider(
                    minimum=1, maximum=10, value=2.5, step=0.5,
                    label="Seconds per Scene",
                    info="How much of each scene to include in summary",
                )
                keep_audio_checkbox = gr.Checkbox(
                    value=True,
                    label="Keep Audio",
                    info="Preserve original audio (requires ffmpeg)",
                )
                best_keyframes_checkbox = gr.Checkbox(
                    value=True,
                    label="Best Keyframes",
                    info="Select sharpest frames instead of midpoint",
                )
                clean_input_checkbox = gr.Checkbox(
                    value=False,
                    label="Clean Input",
                    info="Re-encode input to fix codec issues (slower)",
                )
            
            summarize_btn = gr.Button(
                "🚀 Summarize Video",
                variant="primary",
                size="lg",
            )
        
        # Right column - Output
        with gr.Column(scale=1):
            gr.Markdown("### 📥 Results")
            
            with gr.Tabs():
                with gr.Tab("Summary Video"):
                    output_video = gr.Video(
                        label="Summary",
                        elem_classes=["output-video"],
                    )
                
                with gr.Tab("Storyboard"):
                    output_storyboard = gr.Image(
                        label="Storyboard",
                    )
                
                with gr.Tab("Analysis"):
                    output_analysis = gr.Image(
                        label="Scene Detection Chart",
                    )
                
                with gr.Tab("Statistics"):
                    output_stats = gr.Markdown("Results will appear here after processing.")
    
    # Wire up the summarize button
    summarize_btn.click(
        fn=process_video,
        inputs=[
            video_input,
            fps_slider,
            threshold_slider,
            min_duration_slider,
            max_duration_slider,
            secs_per_shot_slider,
            keep_audio_checkbox,
            clean_input_checkbox,
            best_keyframes_checkbox,
        ],
        outputs=[
            output_video,
            output_storyboard,
            output_analysis,
            output_stats,
        ],
    )
    
    # Examples section
    gr.Markdown("---")
    gr.Markdown("### 💡 Tips")
    gr.Markdown("""
    - **Fast processing**: Use lower FPS (2-3) for quicker results
    - **More scenes**: Lower the threshold (85-90)
    - **Fewer scenes**: Raise the threshold (94-98)
    - **Shorter summary**: Reduce seconds per scene
    - **Codec errors**: Enable "Clean Input" option
    - **No audio**: Ensure ffmpeg is installed and "Keep Audio" is checked
    """)


def main():
    """Launch the Gradio app."""
    print("\n" + "="*60)
    print("   AUTOMATIC VIDEO SUMMARIZATION - WEB UI")
    print("="*60)
    print("\n🌐 Starting web server...")
    print("   Open http://localhost:7860 in your browser\n")
    
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
