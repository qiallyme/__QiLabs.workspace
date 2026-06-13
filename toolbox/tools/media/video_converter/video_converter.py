# file: video_converter.py
# purpose: Toolbox tool module for Video Converter in the media bucket. Provides VideoConverterTool for the QiOne Desktop Tools UI.
# usage: Loaded by the QiOne toolbox build system and launched from main_ui.py.
# inputs: User-selected target directory and tool-specific UI options.
# outputs: Tool-specific logs, generated files, or file operations depending on selected mode.
# safety: Supports scan/dry-run vs live execution through the QiOne toolbox shell when implemented by the tool.
# owner: QiLabs

import os
import subprocess
import tkinter as tk
from tkinter import ttk
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.base_tool import BaseTool

class VideoConverterTool(BaseTool):
    def __init__(self):
        self.cancel_requested = False
        self.supported_exts = {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.m4v', '.mpeg', '.mpg', '.webm', '.media'}
        self.active_processes = []

    def get_name(self):
        return "🎥 Video Converter & Remaster"

    def build_ui(self, parent):
        self.w_mode = tk.StringVar(value="FAST")
        self.w_enhance = tk.BooleanVar(value=True)
        self.w_recursive = tk.BooleanVar(value=True)
        self.w_delete_orig = tk.BooleanVar(value=False)

        ttk.Label(parent, text="PROCESSING MODE", background="#0f0f11", foreground="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(0,5))

        mode_frame = tk.Frame(parent, bg="#0f0f11")
        mode_frame.pack(fill='x', pady=(0, 10))
        ttk.Radiobutton(mode_frame, text="🚀 FAST MODE (3x Concurrent, Max Resources, Hardware Accel)", variable=self.w_mode, value="FAST").pack(anchor='w', pady=2)
        ttk.Radiobutton(mode_frame, text="🐢 PASSIVE MODE (1x Sequential, Idle CPU Priority, Bulletproof Skipping)", variable=self.w_mode, value="PASSIVE").pack(anchor='w', pady=2)

        ttk.Label(parent, text="ENHANCEMENTS & ROUTING", background="#0f0f11", foreground="#a1a1aa", font=("Segoe UI", 9, "bold")).pack(anchor='w', pady=(10,5))
        ttk.Checkbutton(parent, text="✨ Apply Visual Remaster (Fix Dark/Blurry, Reduce Flashes)", variable=self.w_enhance).pack(anchor='w', pady=2)
        ttk.Checkbutton(parent, text="🔄 Recursive (Scan sub-folders)", variable=self.w_recursive).pack(anchor='w', pady=2)
        ttk.Checkbutton(parent, text="🗑️ Delete Original File After Successful Conversion", variable=self.w_delete_orig).pack(anchor='w', pady=2)

    def process_video(self, input_path, target_path, is_live, log):
        if self.cancel_requested: return False

        mode = self.w_mode.get()
        enhance = self.w_enhance.get()
        filename = os.path.basename(input_path)
        name, ext = os.path.splitext(filename)

        out_name = f"{name}_remastered.mkv" if ext.lower() == '.mkv' and enhance else f"{name}.mkv"
        output_path = os.path.join(os.path.dirname(input_path), out_name)

        if not is_live:
            log(f"   [DRY RUN] Would convert: {filename} -> {out_name}")
            return True

        # Base Command
        cmd = ["ffmpeg", "-y"]

        # Mode specific tweaks
        if mode == "FAST":
            cmd.extend(["-hwaccel", "auto"]) # Use GPU if available

        cmd.extend(["-i", input_path, "-c:v", "libx264"])

        if mode == "FAST":
            cmd.extend(["-preset", "superfast", "-crf", "24"])
        else:
            # Passive mode sips CPU, so we can afford a slower preset for better compression
            cmd.extend(["-preset", "slow", "-crf", "24", "-threads", "1"])

        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        if enhance:
            cmd.extend(["-vf", "deflicker,eq=brightness=0.04:contrast=1.05:gamma=1.1,unsharp=5:5:0.8:3:3:0.0"])

        cmd.append(output_path)

        try:
            # CREATE_NO_WINDOW (0x08000000) prevents the CMD popup.
            # IDLE_PRIORITY_CLASS (0x00000040) tells Windows to only process this when the PC is doing nothing else.
            creation_flags = 0x08000000
            if os.name == 'nt' and mode == "PASSIVE":
                creation_flags |= 0x00000040

            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, creationflags=creation_flags)
            self.active_processes.append(process)

            _, stderr = process.communicate()

            if process in self.active_processes:
                self.active_processes.remove(process)

            if process.returncode != 0 and not self.cancel_requested:
                err_msg = stderr.decode('utf-8', errors='ignore')[-150:].replace('\n', ' ')
                log(f"   ⚠️ SKIPPED: {filename} (FFmpeg Error) -> Continuing to next file...")
                # We return False so the final counter knows it failed, but we DO NOT raise an exception.
                return False

            if self.cancel_requested:
                return False

            orig_size = os.path.getsize(input_path) / (1024*1024)
            new_size = os.path.getsize(output_path) / (1024*1024)
            savings = orig_size - new_size

            log(f"   ✅ CONVERTED: {out_name} (Saved {savings:.1f} MB)")

            if self.w_delete_orig.get() and os.path.exists(output_path):
                try:
                    os.remove(input_path)
                except Exception as e:
                    log(f"   ⚠️ Could not delete original {filename}: {e}")

            return True

        except Exception as e:
            # Absolute worst-case scenario catch-all so the queue never dies
            log(f"   ⚠️ FATAL SKIP on {filename}: {str(e)} -> Continuing to next file...")
            return False

    def execute(self, target_path, is_live, log, prog):
        self.cancel_requested = False
        self.active_processes = []
        is_rec = self.w_recursive.get()
        mode = self.w_mode.get()

        log(f"🚀 [VIDEO CONVERTER] {'LIVE MODE' if is_live else 'DRY RUN'}\nTarget: {target_path}\n" + "-"*40)

        videos_to_process = []
        for root, dirs, files in os.walk(target_path):
            if not is_rec and root != target_path:
                dirs[:] = []
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in self.supported_exts:
                    videos_to_process.append(os.path.join(root, f))

        total_videos = len(videos_to_process)
        if total_videos == 0:
            log("❌ No supported video files found in target directory.")
            return

        log(f"Found {total_videos} videos. Mode: {mode}")
        if self.w_enhance.get(): log("✨ Visual Remastering Engine ENGAGED.")
        if mode == "PASSIVE": log("🐢 Background Priority active. This will run silently and safely skip errors.")
        log("-" * 40)

        workers = 3 if mode == "FAST" else 1
        completed = 0
        success_count = 0
        fail_count = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_video = {executor.submit(self.process_video, vp, target_path, is_live, log): vp for vp in videos_to_process}

            for future in as_completed(future_to_video):
                if self.cancel_requested:
                    for p in self.active_processes:
                        p.kill()
                    log("\n🛑 CANCELED BY USER. Killed active FFmpeg processes.")
                    break

                # Check if it returned True (Success) or False (Skipped/Error)
                result = future.result()
                if result:
                    success_count += 1
                else:
                    fail_count += 1

                completed += 1
                prog(int((completed / total_videos) * 100))

        if not self.cancel_requested:
            prog(100)
            log("-" * 40)
            log(f"✅ BATCH COMPLETE.")
            log(f"   Successful: {success_count}")
            log(f"   Skipped/Failed: {fail_count}")
