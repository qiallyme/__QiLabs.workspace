#!/usr/bin/env python3
"""
Local Processing Wrapper
Copies files from cloud storage (Google Drive) to local temp folder,
runs the processing step, then copies results back.
This avoids sync issues when processing large video files on cloud storage.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

LOCAL_TEMP_DIR = Path("C:/Users/codyr/.videoconverter/temp")

class LocalProcessor:
    def __init__(self, source_dir: Path, output_dir: Path, trash_dir: Optional[Path] = None):
        self.source_dir = Path(source_dir).resolve()
        self.output_dir = Path(output_dir).resolve()
        self.trash_dir = Path(trash_dir).resolve() if trash_dir else None
        
        # Create local temp directories
        self.local_source = LOCAL_TEMP_DIR / "source"
        self.local_output = LOCAL_TEMP_DIR / "output"
        self.local_trash = LOCAL_TEMP_DIR / "trash" if trash_dir else None
        
        self.local_source.mkdir(parents=True, exist_ok=True)
        self.local_output.mkdir(parents=True, exist_ok=True)
        if self.local_trash:
            self.local_trash.mkdir(parents=True, exist_ok=True)
    
    def copy_to_local(self, source: Path, dest: Path, verbose: bool = False):
        """Copy directory tree from source to local temp"""
        if verbose:
            print(f"Copying {source} to {dest}...")
        
        if not source.exists():
            print(f"Warning: Source directory {source} does not exist")
            return False
        
        # Clear destination first
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True, exist_ok=True)
        
        # Copy directory tree
        try:
            shutil.copytree(source, dest, dirs_exist_ok=True)
            if verbose:
                print(f"✓ Copied to local temp: {dest}")
            return True
        except Exception as e:
            print(f"Error copying to local: {e}")
            return False
    
    def copy_from_local(self, source: Path, dest: Path, verbose: bool = False):
        """Copy directory tree from local temp back to destination"""
        if verbose:
            print(f"Copying {source} to {dest}...")
        
        if not source.exists():
            print(f"Warning: Local source {source} does not exist")
            return False
        
        # Ensure destination exists
        dest.mkdir(parents=True, exist_ok=True)
        
        # Copy files, preserving structure
        try:
            for item in source.rglob('*'):
                if item.is_file():
                    rel_path = item.relative_to(source)
                    dest_file = dest / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
            
            if verbose:
                print(f"✓ Copied from local temp: {dest}")
            return True
        except Exception as e:
            print(f"Error copying from local: {e}")
            return False
    
    def cleanup_local(self):
        """Clean up local temp directories"""
        try:
            if self.local_source.exists():
                shutil.rmtree(self.local_source)
            if self.local_output.exists():
                shutil.rmtree(self.local_output)
            if self.local_trash and self.local_trash.exists():
                shutil.rmtree(self.local_trash)
        except Exception as e:
            print(f"Warning: Error cleaning up local temp: {e}")
    
    def run_step(self, step_script: str, step_args: list, verbose: bool = False):
        """Run processing step with local files"""
        # Copy source to local
        if not self.copy_to_local(self.source_dir, self.local_source, verbose):
            return False
        
        # Build command with local paths
        local_args = [str(self.local_source)]
        
        # Replace output and trash paths with local equivalents
        for i, arg in enumerate(step_args):
            if arg == "--output" or arg == "-o":
                if i + 1 < len(step_args):
                    step_args[i + 1] = str(self.local_output)
                else:
                    local_args.extend(["--output", str(self.local_output)])
            elif arg == "--trash" or arg == "-t":
                if i + 1 < len(step_args):
                    step_args[i + 1] = str(self.local_trash) if self.local_trash else ""
                else:
                    if self.local_trash:
                        local_args.extend(["--trash", str(self.local_trash)])
            elif not arg.startswith("-"):
                # Positional argument (source dir) - already handled
                continue
            else:
                local_args.append(arg)
        
        # Add output if not already specified
        if "--output" not in local_args and "-o" not in local_args:
            local_args.extend(["--output", str(self.local_output)])
        
        # Add trash if specified
        if self.local_trash and "--trash" not in local_args and "-t" not in local_args:
            local_args.extend(["--trash", str(self.local_trash)])
        
        # Run the step script
        script_path = Path(__file__).parent / step_script
        cmd = [sys.executable, str(script_path)] + local_args
        
        if verbose:
            print(f"Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(cmd, cwd=str(script_path.parent))
            
            if result.returncode == 0:
                # Copy results back
                self.copy_from_local(self.local_output, self.output_dir, verbose)
                if self.local_trash and self.local_trash.exists():
                    self.copy_from_local(self.local_trash, self.trash_dir, verbose)
                return True
            else:
                print(f"Step failed with return code {result.returncode}")
                return False
        except Exception as e:
            print(f"Error running step: {e}")
            return False
        finally:
            # Cleanup (optional - comment out if you want to keep temp files for debugging)
            # self.cleanup_local()

def main():
    parser = argparse.ArgumentParser(description="Local Processing Wrapper - Copies files to local temp for processing")
    parser.add_argument("step", choices=["1", "1.5", "2", "2.5", "3", "3.5"], help="Step number to run")
    parser.add_argument("source_dir", help="Source directory (cloud location)")
    parser.add_argument("--output", "-o", help="Output directory (cloud location)")
    parser.add_argument("--trash", "-t", help="Trash directory (cloud location)")
    parser.add_argument("--no-copy-back", action="store_true", help="Don't copy results back (for testing)")
    parser.add_argument("--keep-temp", action="store_true", help="Keep local temp files after processing")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    step_scripts = {
        "1": "step1_group_and_concat.py",
        "1.5": "step1_5_fast_concat.py",
        "2": "step2_convert_to_mp4.py",
        "2.5": "step2_5_flip_videos.py",
        "3": "step3_enhance.py",
        "3.5": "step3_5_ai_filter.py"
    }
    
    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output).resolve() if args.output else None
    trash_dir = Path(args.trash).resolve() if args.trash else None
    
    if not source_dir.exists():
        print(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)
    
    processor = LocalProcessor(source_dir, output_dir, trash_dir)
    
    # Get step-specific args from remaining command line
    step_args = []
    # This would need to be passed through from orchestrator
    
    success = processor.run_step(step_scripts[args.step], step_args, args.verbose)
    
    if not args.keep_temp:
        processor.cleanup_local()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

