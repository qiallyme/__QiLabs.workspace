#!/usr/bin/env python3
"""
Check Processed Videos - Check if videos in source folders have already been processed
Determines if videos are already converted/enhanced but just not moved to trash
"""

from pathlib import Path
from collections import defaultdict

CONVERTER_DIR = Path(__file__).parent.parent.resolve()

def find_videos(directory: Path):
    """Find all video files in a directory"""
    videos = []
    if not directory.exists():
        return videos
    
    extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v', '.media']
    for ext in extensions:
        for video in directory.rglob(f'*{ext}'):
            if video.is_file():
                videos.append(video)
    
    return sorted(videos)

def check_step1_processed(source_video: Path):
    """Check if video from 1-combine/ has been processed by Step 1"""
    # Step 1 outputs to 2-combine/
    # Output filename is based on group, so we need to check if any file in 2-combine/ 
    # was created from this source
    
    # For now, just check if 2-combine/ exists and has files
    output_dir = CONVERTER_DIR / "2-combine"
    if output_dir.exists():
        # Check if there are any output files (Step 1 combines videos, so exact match is hard)
        output_files = list(output_dir.rglob('*.mp4')) + list(output_dir.rglob('*.mkv'))
        return len(output_files) > 0
    return False

def check_step2_processed(source_video: Path):
    """Check if video from 2-combine/ has been processed by Step 2"""
    # Step 2 outputs to 2-convert/ with same name but .mp4 extension
    output_dir = CONVERTER_DIR / "2-convert"
    output_file = output_dir / f"{source_video.stem}.mp4"
    
    # Also check subdirectories
    if output_file.exists():
        return True
    
    # Check in subdirectories
    for subdir in output_dir.iterdir():
        if subdir.is_dir():
            output_file = subdir / f"{source_video.stem}.mp4"
            if output_file.exists():
                return True
    
    return False

def check_step3_processed(source_video: Path):
    """Check if video from 2-5-flip/ or 2-convert/ has been processed by Step 3"""
    # Step 3 outputs to 3-enhance/ with same name
    output_dir = CONVERTER_DIR / "3-enhance"
    output_file = output_dir / source_video.name
    
    # Also check subdirectories
    if output_file.exists():
        return True
    
    # Check in subdirectories
    for subdir in output_dir.iterdir():
        if subdir.is_dir():
            output_file = subdir / source_video.name
            if output_file.exists():
                return True
    
    return False

def main():
    print("="*80)
    print("CHECK PROCESSED VIDEOS")
    print("="*80)
    print()
    print("Checking if videos in source folders have already been processed...")
    print()
    
    results = defaultdict(lambda: {'processed': [], 'not_processed': []})
    
    # Check 1-combine/ (Step 1 source)
    step1_source = CONVERTER_DIR / "1-combine"
    if step1_source.exists():
        step1_videos = find_videos(step1_source)
        print(f"Checking 1-combine/ ({len(step1_videos)} videos)...")
        
        for video in step1_videos:
            if check_step1_processed(video):
                results['1-combine']['processed'].append(video)
            else:
                results['1-combine']['not_processed'].append(video)
        
        print(f"  Processed (output exists): {len(results['1-combine']['processed'])}")
        print(f"  Not processed: {len(results['1-combine']['not_processed'])}")
        print()
    
    # Check 2-combine/ (Step 2 source)
    step2_source = CONVERTER_DIR / "2-combine"
    if step2_source.exists():
        step2_videos = find_videos(step2_source)
        print(f"Checking 2-combine/ ({len(step2_videos)} videos)...")
        
        for video in step2_videos:
            if check_step2_processed(video):
                results['2-combine']['processed'].append(video)
            else:
                results['2-combine']['not_processed'].append(video)
        
        print(f"  Processed (output exists in 2-convert/): {len(results['2-combine']['processed'])}")
        print(f"  Not processed: {len(results['2-combine']['not_processed'])}")
        print()
    
    # Check 2-5-flip/ and 2-convert/ (Step 3 source)
    step3_sources = [
        (CONVERTER_DIR / "2-5-flip", "2-5-flip"),
        (CONVERTER_DIR / "2-convert", "2-convert")
    ]
    
    for step3_source, name in step3_sources:
        if step3_source.exists():
            step3_videos = find_videos(step3_source)
            print(f"Checking {name}/ ({len(step3_videos)} videos)...")
            
            for video in step3_videos:
                if check_step3_processed(video):
                    results[name]['processed'].append(video)
                else:
                    results[name]['not_processed'].append(video)
            
            print(f"  Processed (output exists in 3-enhance/): {len(results[name]['processed'])}")
            print(f"  Not processed: {len(results[name]['not_processed'])}")
            print()
    
    # Summary
    print("="*80)
    print("SUMMARY")
    print("="*80)
    
    total_processed = 0
    total_not_processed = 0
    
    for folder, data in results.items():
        processed_count = len(data['processed'])
        not_processed_count = len(data['not_processed'])
        total_processed += processed_count
        total_not_processed += not_processed_count
        
        if processed_count > 0:
            print(f"\n{folder}/: {processed_count} videos already processed (can be moved to trash)")
            if processed_count <= 10:
                for video in data['processed']:
                    rel_path = video.relative_to(CONVERTER_DIR / folder)
                    print(f"  - {rel_path}")
            else:
                for video in data['processed'][:10]:
                    rel_path = video.relative_to(CONVERTER_DIR / folder)
                    print(f"  - {rel_path}")
                print(f"  ... and {processed_count - 10} more")
        
        if not_processed_count > 0:
            print(f"\n{folder}/: {not_processed_count} videos NOT processed yet")
            if not_processed_count <= 10:
                for video in data['not_processed']:
                    rel_path = video.relative_to(CONVERTER_DIR / folder)
                    print(f"  - {rel_path}")
            else:
                for video in data['not_processed'][:10]:
                    rel_path = video.relative_to(CONVERTER_DIR / folder)
                    print(f"  - {rel_path}")
                print(f"  ... and {not_processed_count - 10} more")
    
    print()
    print(f"Total: {total_processed} already processed, {total_not_processed} not processed")
    print()
    print("Note: Videos that are 'already processed' can be safely moved to trash")
    print("      since their output files already exist in the next step's directory")
    print()

if __name__ == "__main__":
    main()

