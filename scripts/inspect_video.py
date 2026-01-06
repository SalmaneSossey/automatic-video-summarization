import cv2
from pathlib import Path

def inspect(video_path: str) -> None:
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("OpenCV could not open the video (codec/path issue).")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

    duration_sec = frame_count / fps if fps else 0.0

    print(f"Path: {path}")
    print(f"Resolution: {int(width)}x{int(height)}")
    print(f"FPS: {fps:.3f}")
    print(f"Frames: {int(frame_count)}")
    print(f"Duration (s): {duration_sec:.2f}")

    cap.release()

if __name__ == "__main__":
    # Put a small test video in data/demo.mp4 then run this script
    inspect("data/demo.mp4")
