#!/usr/bin/env python3
"""
Find Failed Videos - Locate videos that failed processing
Checks log files and source directories to find videos that didn't complete successfully
"""

import re
from pathlib import Path
from datetime import datetime

CONVERTER_DIR = Path(__file__).parent.parent.resolve()

def find_failed_in_logs():
    """Find failed videos by checking log files"""
    failed_videos = {
        'step2': [],
        'step3': []
    }
    
    # Find all log files
    log_files = list(CONVERTER_DIR.glob('step*_log_*.txt'))
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)  # Most recent first
    
    # Check most recent log files
    for log_file in log_files[:5]:  # Check last 5 log files
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Find failed conversions (Step 2)
            if 'step2' in log_file.name.lower():
                failed_matches = re.findall(r'\[FAIL\].*?Failed:?\s+([^\s:]+)', content, re.IGNORECASE)
                failed_videos['step2'].extend(failed_matches)
            
            # Find failed enhancements (Step 3)
            if 'step3' in log_file.name.lower():
                failed_matches = re.findall(r'\[FAIL\].*?Failed:?\s+([^\s:]+)', content, re.IGNORECASE)
                failed_videos['step3'].extend(failed_matches)
        except Exception as e:
            print(f"Error reading {log_file.name}: {e}")
    
    return failed_videos

def find_videos_in_directory(directory: Path, pattern: str = None):
    """Find video files in a directory"""
    videos = []
    if not directory.exists():
        return videos
    
    extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.media']
    for ext in extensions:
        for video in directory.rglob(f'*{ext}'):
            if video.is_file():
                if pattern is None or pattern.lower() in video.name.lower():
                    videos.append(video)
    
    return sorted(videos)

def main():
    print("="*80)
    print("FIND FAILED VIDEOS")
    print("="*80)
    print()
    
    # Check source directories for videos that might have failed
    print("Checking source directories for videos that may have failed...")
    print()
    
    # Step 2 source (2-combine/)
    step2_source = CONVERTER_DIR / "2-combine"
    step2_videos = find_videos_in_directory(step2_source)
    if step2_videos:
        print(f"Step 2 (Convert) - Videos still in 2-combine/ ({len(step2_videos)} videos):")
        print(f"  Location: {step2_source}")
        for video in step2_videos[:10]:  # Show first 10
            rel_path = video.relative_to(step2_source)
            size_mb = video.stat().st_size / (1024 * 1024)
            print(f"    - {rel_path} ({size_mb:.1f} MB)")
        if len(step2_videos) > 10:
            print(f"    ... and {len(step2_videos) - 10} more")
        print()
    
    # Step 3 source (2-5-flip/ or 2-convert/)
    step3_sources = [
        CONVERTER_DIR / "2-5-flip",
        CONVERTER_DIR / "2-convert"
    ]
    
    step3_videos = []
    for source_dir in step3_sources:
        videos = find_videos_in_directory(source_dir)
        step3_videos.extend([(v, source_dir.name) for v in videos])
    
    if step3_videos:
        print(f"Step 3 (Enhance) - Videos still in source directories ({len(step3_videos)} videos):")
        for source_dir in step3_sources:
            videos_in_dir = [v for v, d in step3_videos if d == source_dir.name]
            if videos_in_dir:
                print(f"  Location: {source_dir.name}/ ({len(videos_in_dir)} videos)")
                for video, _ in videos_in_dir[:10]:  # Show first 10
                    rel_path = video.relative_to(CONVERTER_DIR / source_dir.name)
                    size_mb = video.stat().st_size / (1024 * 1024)
                    print(f"    - {rel_path} ({size_mb:.1f} MB)")
                if len(videos_in_dir) > 10:
                    print(f"    ... and {len(videos_in_dir) - 10} more")
        print()
    
    # Check log files for explicit failures
    print("Checking log files for explicit failures...")
    failed_in_logs = find_failed_in_logs()
    
    if failed_in_logs['step2']:
        print(f"Step 2 failures found in logs: {len(set(failed_in_logs['step2']))} unique videos")
        for video_name in set(failed_in_logs['step2'])[:10]:
            print(f"    - {video_name}")
        print()
    
    if failed_in_logs['step3']:
        print(f"Step 3 failures found in logs: {len(set(failed_in_logs['step3']))} unique videos")
        for video_name in set(failed_in_logs['step3'])[:10]:
            print(f"    - {video_name}")
        print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Videos in 2-combine/ (may have failed Step 2): {len(step2_videos)}")
    print(f"Videos in 2-5-flip/ or 2-convert/ (may have failed Step 3): {len(step3_videos)}")
    print()
    print("To retry failed videos:")
    print(f"  Step 2: python step2_convert_to_mp4.py 2-combine")
    print(f"  Step 3: python step3_enhance.py 2-5-flip")
    print()

if __name__ == "__main__":
    main()

