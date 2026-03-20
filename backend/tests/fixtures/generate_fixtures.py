"""Generate test fixtures for ML service testing.

Run this script to create test audio and video files:
    python tests/fixtures/generate_fixtures.py

Requirements:
    - numpy
    - scipy (for WAV generation)
    - opencv-python (for video generation)
"""

import os
import wave
import struct
import math
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent


def generate_sine_wave_audio(
    output_path: str,
    duration_sec: float = 5.0,
    frequency: int = 440,
    sample_rate: int = 44100,
) -> str:
    """Generate a simple sine wave audio file.
    
    Args:
        output_path: Path to output WAV file
        duration_sec: Duration in seconds
        frequency: Frequency in Hz (A4 = 440)
        sample_rate: Sample rate in Hz
    
    Returns:
        Path to generated file
    """
    n_samples = int(duration_sec * sample_rate)
    
    samples = []
    for i in range(n_samples):
        t = i / sample_rate
        value = math.sin(2 * math.pi * frequency * t)
        value = int(value * 32767 * 0.5)
        samples.append(value)
    
    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    print(f"Generated audio: {output_path} ({duration_sec}s, {frequency}Hz)")
    return output_path


def generate_silent_audio(
    output_path: str,
    duration_sec: float = 5.0,
    sample_rate: int = 44100,
) -> str:
    """Generate a silent audio file.
    
    Args:
        output_path: Path to output WAV file
        duration_sec: Duration in seconds
        sample_rate: Sample rate in Hz
    
    Returns:
        Path to generated file
    """
    n_samples = int(duration_sec * sample_rate)
    samples = [0] * n_samples
    
    with wave.open(output_path, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    
    print(f"Generated silent audio: {output_path} ({duration_sec}s)")
    return output_path


def generate_test_video(
    output_path: str,
    duration_sec: float = 5.0,
    fps: int = 30,
    width: int = 640,
    height: int = 480,
) -> str:
    """Generate a test video with solid color frames.
    
    Note: This creates a video without a face. For face detection tests,
    you'll need to provide a real video with a face.
    
    Args:
        output_path: Path to output MP4 file
        duration_sec: Duration in seconds
        fps: Frames per second
        width: Video width
        height: Video height
    
    Returns:
        Path to generated file
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("OpenCV not installed. Skipping video generation.")
        print("Install with: pip install opencv-python")
        return None
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    n_frames = int(duration_sec * fps)
    
    for i in range(n_frames):
        color = (
            int(128 + 50 * math.sin(i * 0.1)),
            int(128 + 50 * math.sin(i * 0.1 + 2)),
            int(128 + 50 * math.sin(i * 0.1 + 4)),
        )
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        
        cv2.putText(
            frame,
            f"Test Frame {i+1}/{n_frames}",
            (width // 4, height // 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (255, 255, 255),
            2,
        )
        
        out.write(frame)
    
    out.release()
    print(f"Generated video: {output_path} ({duration_sec}s, {fps}fps, no face)")
    return output_path


def generate_all_fixtures():
    """Generate all test fixtures."""
    print("=" * 50)
    print("Generating test fixtures...")
    print("=" * 50)
    
    generate_sine_wave_audio(
        str(FIXTURES_DIR / "sample.wav"),
        duration_sec=5.0,
        frequency=440,
    )
    
    generate_silent_audio(
        str(FIXTURES_DIR / "silent.wav"),
        duration_sec=5.0,
    )
    
    generate_sine_wave_audio(
        str(FIXTURES_DIR / "short.wav"),
        duration_sec=1.0,
        frequency=440,
    )
    
    generate_test_video(
        str(FIXTURES_DIR / "no_face.mp4"),
        duration_sec=5.0,
    )
    
    print("\n" + "=" * 50)
    print("Note: For face detection tests, provide a real video with a face.")
    print("Save it as: tests/fixtures/sample_with_face.mp4")
    print("=" * 50)
    
    print("\nGenerated fixtures:")
    for f in FIXTURES_DIR.iterdir():
        if f.is_file() and not f.name.endswith('.py'):
            size_kb = f.stat().st_size / 1024
            print(f"  - {f.name} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    generate_all_fixtures()
