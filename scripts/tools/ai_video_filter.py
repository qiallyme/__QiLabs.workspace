#!/usr/bin/env python3
"""
AI Video Content Filter
Detects faces, people, body parts, and movement in videos using computer vision.
Only processes videos that contain human content.
"""

import cv2
import numpy as np
import subprocess
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional
import json
import os

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("MediaPipe not available. Install with: pip install mediapipe")

class AIVideoFilter:
    def __init__(self, confidence_threshold: float = 0.5, sample_count: int = 5):
        self.confidence_threshold = confidence_threshold
        self.sample_count = sample_count
        
        # Initialize face detection
        self.face_cascade = None
        self.body_cascade = None
        self.mp_face_detection = None
        self.mp_pose = None
        
        self._init_opencv_detectors()
        self._init_mediapipe_detectors()
    
    def _init_opencv_detectors(self):
        """Initialize OpenCV cascade classifiers"""
        try:
            # Try to load face cascade
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            if os.path.exists(face_cascade_path):
                self.face_cascade = cv2.CascadeClassifier(face_cascade_path)
            
            # Try to load body cascade
            body_cascade_path = cv2.data.haarcascades + 'haarcascade_fullbody.xml'
            if os.path.exists(body_cascade_path):
                self.body_cascade = cv2.CascadeClassifier(body_cascade_path)
                
        except Exception as e:
            print(f"Warning: Could not initialize OpenCV cascades: {e}")
    
    def _init_mediapipe_detectors(self):
        """Initialize MediaPipe detectors"""
        if not MEDIAPIPE_AVAILABLE:
            return
            
        try:
            # Face detection
            self.mp_face_detection = mp.solutions.face_detection.FaceDetection(
                model_selection=0, min_detection_confidence=self.confidence_threshold
            )
            
            # Pose detection
            self.mp_pose = mp.solutions.pose.Pose(
                static_image_mode=True,
                model_complexity=1,
                enable_segmentation=False,
                min_detection_confidence=self.confidence_threshold
            )
        except Exception as e:
            print(f"Warning: Could not initialize MediaPipe: {e}")
    
    def extract_frames(self, video_path: Path, num_frames: int = 5) -> List[np.ndarray]:
        """Extract frames from video at different positions"""
        frames = []
        
        try:
            cap = cv2.VideoCapture(str(video_path))
            if not cap.isOpened():
                return frames
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                return frames
            
            # Calculate frame positions (start, 25%, 50%, 75%, end)
            positions = []
            if num_frames == 1:
                positions = [total_frames // 2]
            else:
                step = max(1, total_frames // (num_frames + 1))
                positions = [step * (i + 1) for i in range(num_frames)]
            
            for pos in positions:
                cap.set(cv2.CAP_PROP_POS_FRAMES, min(pos, total_frames - 1))
                ret, frame = cap.read()
                if ret and frame is not None:
                    frames.append(frame)
                
                if len(frames) >= num_frames:
                    break
            
            cap.release()
            
        except Exception as e:
            print(f"Error extracting frames from {video_path}: {e}")
        
        return frames
    
    def detect_faces_opencv(self, frame: np.ndarray) -> bool:
        """Detect faces using OpenCV Haar cascades"""
        if self.face_cascade is None:
            return False
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            return len(faces) > 0
        except Exception:
            return False
    
    def detect_bodies_opencv(self, frame: np.ndarray) -> bool:
        """Detect bodies using OpenCV Haar cascades"""
        if self.body_cascade is None:
            return False
        
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            bodies = self.body_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=3, minSize=(50, 100)
            )
            return len(bodies) > 0
        except Exception:
            return False
    
    def detect_faces_mediapipe(self, frame: np.ndarray) -> bool:
        """Detect faces using MediaPipe"""
        if self.mp_face_detection is None:
            return False
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_face_detection.process(rgb_frame)
            return results.detections is not None and len(results.detections) > 0
        except Exception:
            return False
    
    def detect_pose_mediapipe(self, frame: np.ndarray) -> bool:
        """Detect human pose using MediaPipe"""
        if self.mp_pose is None:
            return False
        
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.mp_pose.process(rgb_frame)
            
            if results.pose_landmarks:
                landmarks = results.pose_landmarks.landmark
                
                key_points = [
                    landmarks[mp.solutions.pose.PoseLandmark.NOSE.value],
                    landmarks[mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value],
                    landmarks[mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value],
                    landmarks[mp.solutions.pose.PoseLandmark.LEFT_HIP.value],
                    landmarks[mp.solutions.pose.PoseLandmark.RIGHT_HIP.value]
                ]
                
                visible_count = sum(1 for point in key_points if point.visibility > self.confidence_threshold)
                return visible_count >= 2
            
            return False
        except Exception:
            return False
    
    def detect_movement(self, frames: List[np.ndarray]) -> bool:
        """Detect significant movement between frames"""
        if len(frames) < 2:
            return False
        
        try:
            movement_scores = []
            
            for i in range(len(frames) - 1):
                frame1 = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
                frame2 = cv2.cvtColor(frames[i + 1], cv2.COLOR_BGR2GRAY)
                
                diff = cv2.absdiff(frame1, frame2)
                _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
                
                changed_pixels = np.sum(thresh > 0)
                total_pixels = thresh.shape[0] * thresh.shape[1]
                movement_score = changed_pixels / total_pixels
                
                movement_scores.append(movement_score)
            
            max_movement = max(movement_scores) if movement_scores else 0
            return max_movement > 0.05
            
        except Exception:
            return False
    
    def detect_edges_and_shapes(self, frame: np.ndarray) -> bool:
        """Detect human-like shapes using edge detection"""
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edges = cv2.Canny(blurred, 50, 150)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for contour in contours:
                area = cv2.contourArea(contour)
                if area > 1000:
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = h / w if w > 0 else 0
                    
                    if 1.5 < aspect_ratio < 4.0:
                        return True
            
            return False
            
        except Exception:
            return False
    
    def analyze_video(self, video_path: Path) -> Tuple[bool, dict]:
        """
        Analyze video for human content
        Returns (has_human_content, detection_details)
        """
        detection_results = {
            'faces_opencv': False,
            'faces_mediapipe': False,
            'bodies_opencv': False,
            'pose_mediapipe': False,
            'movement': False,
            'shapes': False,
            'frames_analyzed': 0
        }
        
        frames = self.extract_frames(video_path, self.sample_count)
        detection_results['frames_analyzed'] = len(frames)
        
        if not frames:
            return False, detection_results
        
        for frame in frames:
            if not detection_results['faces_opencv']:
                detection_results['faces_opencv'] = self.detect_faces_opencv(frame)
            
            if not detection_results['faces_mediapipe']:
                detection_results['faces_mediapipe'] = self.detect_faces_mediapipe(frame)
            
            if not detection_results['bodies_opencv']:
                detection_results['bodies_opencv'] = self.detect_bodies_opencv(frame)
            
            if not detection_results['pose_mediapipe']:
                detection_results['pose_mediapipe'] = self.detect_pose_mediapipe(frame)
            
            if not detection_results['shapes']:
                detection_results['shapes'] = self.detect_edges_and_shapes(frame)
        
        detection_results['movement'] = self.detect_movement(frames)
        
        has_human_content = any([
            detection_results['faces_opencv'],
            detection_results['faces_mediapipe'],
            detection_results['bodies_opencv'],
            detection_results['pose_mediapipe'],
            detection_results['shapes']
        ])
        
        return has_human_content, detection_results

