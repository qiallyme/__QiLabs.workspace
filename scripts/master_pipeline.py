#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Master Video Processing Pipeline
Consolidated interactive pipeline for video processing.

Usage:
    python scripts/master_pipeline.py

Features:
    - Interactive prompts for input folder and step toggles
    - Modular step functions (preserves original logic)
    - Clear logging for each step
    - Error handling with continue/stop options
"""

import argparse
import sys
import io

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent.resolve()
CONVERTER_DIR = SCRIPT_DIR.parent.resolve()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import from organized structure using relative imports
try:
    from core.ffmpeg_utils import find_ffmpeg, check_ffmpeg
    from steps.step1_combine import Step1GroupAndConcat
    from steps.step1_fast_combine import Step1_5FastConcat
    from steps.step2_convert import Step2ConvertToMP4
    from steps.step2_flip import Step2_5FlipVideos
    from steps.step3_enhance import Step3Enhance
    from steps.step3_filter import Step3_5AIFilter
except ImportError as e:
    print(f"Error: Could not import required modules: {e}")
    print("Please ensure all scripts are in 04_scripts/steps/ and 04_scripts/core/ directories.")
    print(f"Current sys.path: {sys.path[:3]}")
    sys.exit(1)

VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp', '.mpg', '.mpeg', '.media'}


class MasterPipeline:
    """Master pipeline orchestrator - runs all video processing steps interactively"""
    
    def __init__(self, input_folder: Path, output_base: Path = None, verbose: bool = True):
        self.input_folder = Path(input_folder).resolve()
        
        # Auto-detect project name if input is in projects/ folder
        project_name = self._detect_project_name()
        
        # Set output base: processed/[project_name]/
        if output_base:
            self.output_base = Path(output_base).resolve()
        else:
            self.output_base = CONVERTER_DIR / "02_processed" / project_name
        
        # Set archive base: archive/[project_name]/
        self.archive_base = CONVERTER_DIR / "03_archive" / project_name
        
        self.verbose = verbose
        
        # Step outputs (will be set during execution)
        self.step_outputs = {}
        
        # Logging
        self.log_file = self.output_base / f"pipeline_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _detect_project_name(self) -> str:
        """Detect project name from input folder path"""
        try:
            # Check if input folder is inside projects/
            projects_dir = CONVERTER_DIR / "01_projects"
            if projects_dir.exists():
                try:
                    # Get relative path from projects/
                    rel_path = self.input_folder.relative_to(projects_dir)
                    # First part is project name
                    project_name = rel_path.parts[0]
                    return project_name
                except ValueError:
                    # Not inside projects/, use folder name
                    pass
            
            # Fallback: use input folder name
            return self.input_folder.name
        except Exception:
            # Ultimate fallback
            return "default"
        
        # Check FFmpeg
        if not check_ffmpeg():
            print("\nError: FFmpeg is required but not found. Please install it first.")
            sys.exit(1)
    
    def log(self, message: str, level: str = "INFO"):
        """Log message to file and optionally print"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
        
        if self.verbose:
            print(log_msg)
    
    def prompt_yes_no(self, question: str, default: bool = False) -> bool:
        """Prompt user for yes/no answer"""
        default_str = "Y/n" if default else "y/N"
        response = input(f"{question} ({default_str}): ").strip().lower()
        if not response:
            return default
        return response in ['y', 'yes']
    
    def prompt_path(self, question: str, default: Path = None) -> Path:
        """Prompt user for path"""
        if default:
            response = input(f"{question} (default: {default}): ").strip()
        else:
            response = input(f"{question}: ").strip()
        
        if not response and default:
            return default
        
        path = Path(response).resolve()
        if not path.exists():
            raise ValueError(f"Path does not exist: {path}")
        return path
    
    def cleanup_previous_step(self, previous_step_key: str):
        """Clean up previous step's output folder after current step completes successfully"""
        if previous_step_key not in self.step_outputs:
            return
        
        previous_dir = self.step_outputs[previous_step_key]
        if not previous_dir or not previous_dir.exists():
            return
        
        try:
            # Count files before deletion
            file_count = sum(1 for _ in previous_dir.rglob('*') if _.is_file())
            
            if file_count > 0:
                self.log(f"Cleaning up previous step folder: {previous_dir} ({file_count} files)", "INFO")
                shutil.rmtree(previous_dir)
                self.log(f"✓ Removed {previous_step_key} folder ({file_count} files freed)", "INFO")
            else:
                # Remove empty folder
                previous_dir.rmdir()
                self.log(f"✓ Removed empty {previous_step_key} folder", "INFO")
        except Exception as e:
            self.log(f"Warning: Could not clean up {previous_step_key} folder: {e}", "WARNING")
    
    def run_step1_combine(self, enable_fast: bool = False) -> Optional[Path]:
        """Step 1: Group and Concatenate Videos"""
        self.log("="*80)
        self.log("STEP 1: Group and Concatenate Videos")
        self.log("="*80)
        
        if enable_fast:
            self.log("Using fast concatenation mode (no re-encoding)")
            output_dir = self.output_base / "01_combined"
            trash_dir = self.archive_base / "01_combined"
            
            try:
                processor = Step1_5FastConcat(
                    self.input_folder,
                    output_dir,
                    trash_dir,
                    parallel=1,
                    verbose=self.verbose,
                    dry_run=False
                )
                processor.run()
                self.step_outputs['step1'] = output_dir
                self.log(f"✓ Step 1.5 completed successfully. Output: {output_dir}", "INFO")
                return output_dir
            except Exception as e:
                self.log(f"Step 1.5 failed: {e}", "ERROR")
                return None
        else:
            self.log("Using standard concatenation mode (with grouping by date/time)")
            output_dir = self.output_base / "01_combined"
            trash_dir = self.archive_base / "01_combined"
            
            try:
                processor = Step1GroupAndConcat(
                    self.input_folder,
                    output_dir,
                    trash_dir,
                    verbose=self.verbose,
                    dry_run=False
                )
                processor.run()
                self.step_outputs['step1'] = output_dir
                self.log(f"✓ Step 1 completed successfully. Output: {output_dir}", "INFO")
                return output_dir
            except Exception as e:
                self.log(f"Step 1 failed: {e}", "ERROR")
                return None
    
    def run_step2_convert(self, source_dir: Path) -> Optional[Path]:
        """Step 2: Convert to MP4"""
        self.log("="*80)
        self.log("STEP 2: Convert to MP4")
        self.log("="*80)
        
        output_dir = self.output_base / "02_converted"
        trash_dir = self.archive_base / "02_converted"
        
        try:
            processor = Step2ConvertToMP4(
                source_dir,
                output_dir,
                trash_dir,
                gpu_enabled=True,
                threads=4,
                verbose=self.verbose,
                dry_run=False
            )
            processor.run()
            self.step_outputs['step2'] = output_dir
            self.log(f"✓ Step 2 completed successfully. Output: {output_dir}", "INFO")
            
            # Clean up Step 1 folder now that Step 2 is confirmed
            self.cleanup_previous_step('step1')
            
            return output_dir
        except Exception as e:
            self.log(f"Step 2 failed: {e}", "ERROR")
            return None
    
    def run_step2_5_flip(self, source_dir: Path) -> Optional[Path]:
        """Step 2.5: Flip Videos (if needed)"""
        self.log("="*80)
        self.log("STEP 2.5: Flip Videos (if needed)")
        self.log("="*80)
        
        output_dir = self.output_base / "03_flipped"
        
        try:
            processor = Step2_5FlipVideos(
                source_dir,
                output_dir,
                verbose=self.verbose
            )
            processor.run()
            self.step_outputs['step2_5'] = output_dir
            self.log(f"✓ Step 2.5 completed successfully. Output: {output_dir}", "INFO")
            
            # Clean up Step 2 folder now that Step 2.5 is confirmed
            self.cleanup_previous_step('step2')
            
            return output_dir
        except Exception as e:
            self.log(f"Step 2.5 failed: {e}", "ERROR")
            return None
    
    def run_step3_enhance(self, source_dir: Path) -> Optional[Path]:
        """Step 3: Enhance Quality"""
        self.log("="*80)
        self.log("STEP 3: Enhance Quality")
        self.log("="*80)
        
        output_dir = self.output_base / "04_enhanced"
        trash_dir = self.archive_base / "04_enhanced"
        
        try:
            processor = Step3Enhance(
                source_dir,
                output_dir,
                trash_dir,
                gpu_enabled=True,
                threads=4,
                verbose=self.verbose,
                dry_run=False
            )
            processor.run()
            self.step_outputs['step3'] = output_dir
            self.log(f"✓ Step 3 completed successfully. Output: {output_dir}", "INFO")
            
            # Clean up previous step folder (either step2_5 or step2)
            if 'step2_5' in self.step_outputs:
                self.cleanup_previous_step('step2_5')
            else:
                self.cleanup_previous_step('step2')
            
            return output_dir
        except Exception as e:
            self.log(f"Step 3 failed: {e}", "ERROR")
            return None
    
    def run_step3_5_filter(self, source_dir: Path) -> Optional[Path]:
        """Step 3.5: AI Content Filter"""
        self.log("="*80)
        self.log("STEP 3.5: AI Content Filter")
        self.log("="*80)
        
        output_dir = self.output_base / "05_final"
        rejected_dir = self.archive_base / "05_filter_rejected"
        
        try:
            processor = Step3_5AIFilter(
                source_dir,
                output_dir,
                rejected_dir,
                confidence=0.4,
                sample_count=5,
                verbose=self.verbose
            )
            processor.run()
            self.step_outputs['step3_5'] = output_dir
            self.log(f"✓ Step 3.5 completed successfully. Output: {output_dir}", "INFO")
            
            # Clean up Step 3 folder now that Step 3.5 is confirmed
            self.cleanup_previous_step('step3')
            
            return output_dir
        except Exception as e:
            self.log(f"Step 3.5 failed: {e}", "ERROR")
            return None
    
    def run(self, 
            enable_combine: bool = True,
            use_fast_combine: bool = False,
            enable_flip: bool = False,
            enable_enhance: bool = False,
            enable_filter: bool = False):
        """Run the complete pipeline with specified step toggles"""
        
        self.log("="*80)
        self.log("MASTER VIDEO PROCESSING PIPELINE")
        self.log("="*80)
        self.log(f"Input folder: {self.input_folder}")
        self.log(f"Output base: {self.output_base}")
        self.log(f"Log file: {self.log_file}")
        self.log("="*80)
        
        # Verify input folder
        if not self.input_folder.exists():
            self.log(f"Error: Input folder does not exist: {self.input_folder}", "ERROR")
            return False
        
        # Check for videos
        videos = []
        for ext in VIDEO_EXTENSIONS:
            videos.extend(list(self.input_folder.rglob(f'*{ext}')))
        
        if not videos:
            self.log(f"Warning: No video files found in {self.input_folder}", "WARNING")
            if not self.prompt_yes_no("Continue anyway?", default=False):
                return False
        
        self.log(f"Found {len(videos)} video file(s)")
        
        # Pipeline execution
        current_input = self.input_folder
        success = True
        
        # Step 1: Combine (optional)
        if enable_combine:
            result = self.run_step1_combine(enable_fast=use_fast_combine)
            if not result:
                self.log("Step 1 failed. Stopping pipeline.", "ERROR")
                return False
            current_input = result
        else:
            self.log("Step 1 (Combine) skipped")
        
        # Step 2: Convert (required)
        result = self.run_step2_convert(current_input)
        if not result:
            self.log("Step 2 failed. Stopping pipeline.", "ERROR")
            return False
        current_input = result
        
        # Step 2.5: Flip (optional)
        if enable_flip:
            result = self.run_step2_5_flip(current_input)
            if not result:
                self.log("Step 2.5 failed. Stopping pipeline.", "ERROR")
                return False
            current_input = result
        else:
            self.log("Step 2.5 (Flip) skipped")
            # If flip is skipped, we still need to clean up step1 after step2 completes
            # (already done in run_step2_convert)
        
        # Step 3: Enhance (optional)
        if enable_enhance:
            result = self.run_step3_enhance(current_input)
            if not result:
                self.log("Step 3 failed. Stopping pipeline.", "ERROR")
                return False
            current_input = result
        else:
            self.log("Step 3 (Enhance) skipped")
            # If enhance is skipped, clean up previous step folder
            if enable_flip and 'step2_5' in self.step_outputs:
                self.cleanup_previous_step('step2_5')
            elif 'step2' in self.step_outputs:
                self.cleanup_previous_step('step2')
        
        # Step 3.5: Filter (optional)
        if enable_filter:
            result = self.run_step3_5_filter(current_input)
            if not result:
                self.log("Step 3.5 failed. Stopping pipeline.", "ERROR")
                return False
            current_input = result
        else:
            self.log("Step 3.5 (Filter) skipped")
            # If filter is skipped, clean up step3 folder if enhance was enabled
            if enable_enhance and 'step3' in self.step_outputs:
                self.cleanup_previous_step('step3')
        
        # Final summary
        self.log("="*80)
        self.log("PIPELINE COMPLETE!")
        self.log("="*80)
        self.log(f"Final output: {current_input}")
        self.log(f"Log file: {self.log_file}")
        self.log("="*80)
        
        return True


def interactive_setup():
    """Interactive setup - prompts user for configuration"""
    print("\n" + "="*80)
    print("MASTER VIDEO PROCESSING PIPELINE")
    print("="*80)
    print("\nThis pipeline will process your videos through multiple steps.")
    print("You'll be prompted to configure each step.\n")
    
    # Get input folder (from projects/)
    projects_dir = CONVERTER_DIR / "01_projects"
    print(f"\nAvailable projects in {projects_dir}:")
    if projects_dir.exists():
        projects = [d.name for d in projects_dir.iterdir() if d.is_dir()]
        for i, proj in enumerate(projects[:10], 1):  # Show first 10
            print(f"  {i}. {proj}")
        if len(projects) > 10:
            print(f"  ... and {len(projects) - 10} more")
    
    input_folder = None
    while not input_folder:
        try:
            input_str = input(f"\nEnter project folder path (from {projects_dir}): ").strip()
            if not input_str:
                print("Error: Please enter a project folder path")
                continue
            input_folder = Path(input_str).resolve()
            # If relative path, assume it's in projects/
            if not input_folder.is_absolute():
                input_folder = projects_dir / input_str
            input_folder = input_folder.resolve()
            if not input_folder.exists():
                print(f"Error: Folder does not exist: {input_folder}")
                input_folder = None
        except Exception as e:
            print(f"Error: {e}")
            input_folder = None
    
    # Output base is auto-detected from project name, but allow override
    output_base = None  # Will be auto-detected in __init__
    
    # Step toggles
    print("\n" + "="*80)
    print("STEP CONFIGURATION")
    print("="*80)
    
    enable_combine = input("\nEnable Step 1: Combine videos? (Y/n): ").strip().lower() != 'n'
    use_fast_combine = False
    if enable_combine:
        use_fast_combine = input("  Use fast combine (no re-encoding, faster)? (y/N): ").strip().lower() == 'y'
    
    enable_flip = input("\nEnable Step 2.5: Flip videos (fix rotation)? (y/N): ").strip().lower() == 'y'
    enable_enhance = input("Enable Step 3: Enhance quality? (y/N): ").strip().lower() == 'y'
    enable_filter = input("Enable Step 3.5: AI content filter? (y/N): ").strip().lower() == 'y'
    
    # Summary
    print("\n" + "="*80)
    print("CONFIGURATION SUMMARY")
    # Auto-detect output base for display
    project_name = "default"
    try:
        projects_dir = CONVERTER_DIR / "01_projects"
        if projects_dir.exists():
            try:
                rel_path = input_folder.resolve().relative_to(projects_dir)
                project_name = rel_path.parts[0]
            except ValueError:
                project_name = input_folder.name
    except:
        project_name = input_folder.name
    
    output_base_display = CONVERTER_DIR / "02_processed" / project_name
    
    print("="*80)
    print(f"Input folder: {input_folder}")
    print(f"Output base: {output_base_display} (auto-detected from project)")
    print(f"Step 1 (Combine): {'Enabled (Fast)' if enable_combine and use_fast_combine else 'Enabled (Standard)' if enable_combine else 'Disabled'}")
    print(f"Step 2 (Convert): Enabled (Required)")
    print(f"Step 2.5 (Flip): {'Enabled' if enable_flip else 'Disabled'}")
    print(f"Step 3 (Enhance): {'Enabled' if enable_enhance else 'Disabled'}")
    print(f"Step 3.5 (Filter): {'Enabled' if enable_filter else 'Disabled'}")
    print("="*80)
    
    confirm = input("\nProceed with this configuration? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("Cancelled.")
        return None
    
    return {
        'input_folder': input_folder,
        'output_base': output_base,
        'enable_combine': enable_combine,
        'use_fast_combine': use_fast_combine,
        'enable_flip': enable_flip,
        'enable_enhance': enable_enhance,
        'enable_filter': enable_filter
    }


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Master Video Processing Pipeline")
    parser.add_argument("--input", "-i", help="Input folder path (from 01_projects/)")
    parser.add_argument("--output", "-o", help="Output base folder (default: 02_processed/[project])")
    parser.add_argument("--combine", action="store_true", help="Enable Step 1: Combine")
    parser.add_argument("--fast-combine", action="store_true", help="Use fast combine (no re-encoding)")
    parser.add_argument("--flip", action="store_true", help="Enable Step 2.5: Flip videos")
    parser.add_argument("--enhance", action="store_true", help="Enable Step 3: Enhance quality")
    parser.add_argument("--filter", action="store_true", help="Enable Step 3.5: AI content filter")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode (less output)")
    
    args = parser.parse_args()
    
    # Interactive mode if no arguments provided
    if not args.input:
        config = interactive_setup()
        if not config:
            return
        input_folder = config['input_folder']
        output_base = config['output_base']
        enable_combine = config['enable_combine']
        use_fast_combine = config['use_fast_combine']
        enable_flip = config['enable_flip']
        enable_enhance = config['enable_enhance']
        enable_filter = config['enable_filter']
    else:
        input_folder = Path(args.input).resolve()
        output_base = Path(args.output).resolve() if args.output else None  # Auto-detect from project
        enable_combine = args.combine
        use_fast_combine = args.fast_combine
        enable_flip = args.flip
        enable_enhance = args.enhance
        enable_filter = args.filter
    
    # Create pipeline
    pipeline = MasterPipeline(input_folder, output_base, verbose=not args.quiet)
    
    # Run pipeline
    success = pipeline.run(
        enable_combine=enable_combine,
        use_fast_combine=use_fast_combine,
        enable_flip=enable_flip,
        enable_enhance=enable_enhance,
        enable_filter=enable_filter
    )
    
    if success:
        print("\n✓ Pipeline completed successfully!")
        final_output = (pipeline.step_outputs.get('step3_5') or 
                       pipeline.step_outputs.get('step3') or 
                       pipeline.step_outputs.get('step2_5') or 
                       pipeline.step_outputs.get('step2') or
                       pipeline.output_base / "05_final")
        print(f"  Final output: {final_output}")
        print(f"  Log file: {pipeline.log_file}")
    else:
        print("\n✗ Pipeline failed. Check log file for details.")
        print(f"  Log file: {pipeline.log_file}")
        sys.exit(1)


if __name__ == "__main__":
    main()

