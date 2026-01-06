from src.frame_sampling import sample_frames

if __name__ == "__main__":
    frames = sample_frames("data/demo.mp4", fps_sample=8.0)
    print(f"Sampled frames: {len(frames)}")
    print("First 5 timestamps:", [round(f.timestamp_sec, 2) for f in frames[:5]])
    print("Last timestamp:", round(frames[-1].timestamp_sec, 2))
