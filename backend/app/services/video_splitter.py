"""Video splitter utility for processing large videos."""

import subprocess
import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CHUNK_DURATION_SEC = 300  # 5 minutes
MAX_FILE_SIZE_MB = 500
MIN_CHUNK_DURATION_SEC = 30


def get_video_info(video_path: str) -> Dict[str, Any]:
    """
    Get video metadata using FFprobe.
    
    Args:
        video_path: Path to video file
    
    Returns:
        Dict with duration, size, fps, resolution
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format', '-show_streams',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        import json
        data = json.loads(result.stdout)
        
        format_info = data.get('format', {})
        video_stream = next(
            (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
            {}
        )
        
        duration = float(format_info.get('duration', 0))
        size_bytes = int(format_info.get('size', 0))
        fps = 0
        width = 0
        height = 0
        
        if video_stream:
            width = int(video_stream.get('width', 0))
            height = int(video_stream.get('height', 0))
            
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) > 0 else 0
        
        return {
            'duration': duration,
            'size_mb': size_bytes / (1024 * 1024),
            'size_bytes': size_bytes,
            'fps': fps,
            'width': width,
            'height': height,
            'resolution': f"{width}x{height}",
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info: {e}")
        return {
            'duration': 0,
            'size_mb': 0,
            'size_bytes': 0,
            'fps': 0,
            'width': 0,
            'height': 0,
            'resolution': 'unknown',
        }


def should_split_video(video_path: str) -> bool:
    """
    Determine if video should be split.
    
    Args:
        video_path: Path to video file
    
    Returns:
        True if video should be split
    """
    info = get_video_info(video_path)
    
    if info['duration'] > MAX_CHUNK_DURATION_SEC * 2:
        return True
    
    if info['size_mb'] > MAX_FILE_SIZE_MB:
        return True
    
    return False


def calculate_chunk_times(
    total_duration: float,
    chunk_duration: float = MAX_CHUNK_DURATION_SEC
) -> List[Tuple[float, float]]:
    """
    Calculate chunk start and end times.
    
    Args:
        total_duration: Total video duration in seconds
        chunk_duration: Target duration per chunk
    
    Returns:
        List of (start_time, end_time) tuples
    """
    chunks = []
    start = 0.0
    
    while start < total_duration:
        end = min(start + chunk_duration, total_duration)
        chunks.append((start, end))
        start = end
    
    return chunks


def split_video(
    video_path: str,
    output_dir: str,
    chunk_duration: float = MAX_CHUNK_DURATION_SEC
) -> List[Dict[str, Any]]:
    """
    Split video into chunks using FFmpeg.
    
    Args:
        video_path: Path to video file
        output_dir: Directory for chunk files
        chunk_duration: Duration per chunk in seconds
    
    Returns:
        List of chunk info dicts with path, start, end, duration
    """
    video_path = Path(video_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    info = get_video_info(str(video_path))
    total_duration = info['duration']
    
    if total_duration < MIN_CHUNK_DURATION_SEC:
        logger.info(f"Video too short to split ({total_duration:.1f}s)")
        return [{
            'path': str(video_path),
            'start': 0.0,
            'end': total_duration,
            'duration': total_duration,
            'chunk_index': 0,
            'is_original': True,
        }]
    
    chunk_times = calculate_chunk_times(total_duration, chunk_duration)
    chunks = []
    
    base_name = video_path.stem
    
    for i, (start, end) in enumerate(chunk_times):
        chunk_path = output_dir / f"{base_name}_chunk_{i:03d}.mp4"
        duration = end - start
        
        logger.info(f"Creating chunk {i}: {start:.1f}s - {end:.1f}s ({duration:.1f}s)")
        
        try:
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-ss', str(start),
                '-t', str(duration),
                '-c', 'copy',
                '-avoid_negative_ts', 'make_zero',
                str(chunk_path)
            ]
            
            subprocess.run(cmd, capture_output=True, check=True)
            
            if chunk_path.exists():
                chunks.append({
                    'path': str(chunk_path),
                    'start': start,
                    'end': end,
                    'duration': duration,
                    'chunk_index': i,
                    'is_original': False,
                })
            else:
                logger.warning(f"Chunk {i} was not created")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create chunk {i}: {e}")
            continue
    
    logger.info(f"Created {len(chunks)} chunks from {video_path}")
    return chunks


def merge_chunk_results(
    chunk_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Merge analysis results from video chunks.
    
    Args:
        chunk_results: List of analysis results from each chunk
    
    Returns:
        Merged analysis result
    """
    if not chunk_results:
        return {}
    
    if len(chunk_results) == 1:
        return chunk_results[0]
    
    merged = {
        'emotion_timeline': [],
        'expression_timeline': [],
        'pitch_timeline': [],
        'voice_activity_segments': [],
        'transcript_segments': [],
        'warnings': [],
        'stages_completed': set(),
        'stages_failed': set(),
    }
    
    time_offset = 0.0
    
    for i, result in enumerate(chunk_results):
        chunk_duration = result.get('duration', 0)
        
        if 'emotion_timeline' in result:
            for entry in result['emotion_timeline']:
                adjusted_entry = entry.copy()
                adjusted_entry['timestamp'] = entry['timestamp'] + time_offset
                merged['emotion_timeline'].append(adjusted_entry)
        
        if 'expression_timeline' in result:
            for entry in result['expression_timeline']:
                adjusted_entry = entry.copy()
                adjusted_entry['timestamp'] = entry['timestamp'] + time_offset
                merged['expression_timeline'].append(adjusted_entry)
        
        if 'pitch_timeline' in result:
            for entry in result['pitch_timeline']:
                adjusted_entry = entry.copy()
                adjusted_entry['timestamp'] = entry['timestamp'] + time_offset
                merged['pitch_timeline'].append(adjusted_entry)
        
        if 'voice_activity_segments' in result:
            for entry in result['voice_activity_segments']:
                adjusted_entry = entry.copy()
                adjusted_entry['start'] = entry['start'] + time_offset
                adjusted_entry['end'] = entry['end'] + time_offset
                merged['voice_activity_segments'].append(adjusted_entry)
        
        if 'transcript_segments' in result:
            for entry in result['transcript_segments']:
                adjusted_entry = entry.copy()
                adjusted_entry['start'] = entry['start'] + time_offset
                adjusted_entry['end'] = entry['end'] + time_offset
                merged['transcript_segments'].append(adjusted_entry)
        
        merged['stages_completed'].update(result.get('stages_completed', []))
        merged['stages_failed'].update(result.get('stages_failed', []))
        merged['warnings'].extend(result.get('warnings', []))
        
        time_offset += chunk_duration
    
    merged['stages_completed'] = list(merged['stages_completed'])
    merged['stages_failed'] = list(merged['stages_failed'])
    
    return merged


def cleanup_chunks(chunks: List[Dict[str, Any]]) -> None:
    """
    Remove chunk files after processing.
    
    Args:
        chunks: List of chunk info dicts
    """
    for chunk in chunks:
        if chunk.get('is_original'):
            continue
        
        chunk_path = chunk.get('path')
        if chunk_path and os.path.exists(chunk_path):
            try:
                os.remove(chunk_path)
                logger.debug(f"Removed chunk: {chunk_path}")
            except Exception as e:
                logger.warning(f"Failed to remove chunk {chunk_path}: {e}")
