"""
Media processing utilities for video/audio manipulation.
"""

import os
import logging
from typing import List, Optional
import subprocess
import tempfile

class MediaProcessor:
    """Handles media processing operations."""
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.config = config_manager.get_config()
        
    def create_slideshow_video(self, image_paths: List[str], audio_path: Optional[str], 
                             output_path: str, duration_per_image: float = 3.0) -> bool:
        """
        Create a video slideshow from images and audio.
        
        Args:
            image_paths: List of image file paths
            audio_path: Path to audio file (optional)
            output_path: Output video file path
            duration_per_image: Duration to show each image in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not image_paths:
                logging.error("No images provided for slideshow")
                return False
                
            # Check if FFmpeg is available
            if not self._check_ffmpeg():
                logging.error("FFmpeg not found. Please install FFmpeg to process slideshows.")
                return False
                
            # Get slideshow duration from config
            duration_per_image = self.config.get('tiktok', {}).get('slideshow_duration_per_image', 3.0)
            
            # Create slideshow video
            if audio_path and os.path.exists(audio_path):
                return self._create_slideshow_with_audio(image_paths, audio_path, output_path, duration_per_image)
            else:
                return self._create_slideshow_without_audio(image_paths, output_path, duration_per_image)
                
        except Exception as e:
            logging.error(f"Error creating slideshow video: {e}")
            return False
            
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False
            
    def _create_slideshow_with_audio(self, image_paths: List[str], audio_path: str, 
                                   output_path: str, duration_per_image: float) -> bool:
        """Create slideshow video with audio."""
        try:
            # Create a temporary file list for FFmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                file_list_path = f.name
                
                for image_path in image_paths:
                    # Escape path for FFmpeg
                    escaped_path = image_path.replace("'", "\\'").replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")
                    f.write(f"duration {duration_per_image}\n")
                    
                # Add the last image again for proper duration
                if image_paths:
                    escaped_path = image_paths[-1].replace("'", "\\'").replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")
                    
            try:
                # Get audio duration
                audio_duration = self._get_audio_duration(audio_path)
                if audio_duration <= 0:
                    audio_duration = len(image_paths) * duration_per_image
                    
                # Build FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', file_list_path,
                    '-i', audio_path,
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-pix_fmt', 'yuv420p',
                    '-shortest',  # Stop when shortest input ends
                    '-y',  # Overwrite output file
                    output_path
                ]
                
                # Execute FFmpeg command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logging.info(f"Successfully created slideshow video: {output_path}")
                    return True
                else:
                    logging.error(f"FFmpeg error: {result.stderr}")
                    return False
                    
            finally:
                # Clean up temporary file
                if os.path.exists(file_list_path):
                    os.unlink(file_list_path)
                    
        except Exception as e:
            logging.error(f"Error creating slideshow with audio: {e}")
            return False
            
    def _create_slideshow_without_audio(self, image_paths: List[str], output_path: str, 
                                      duration_per_image: float) -> bool:
        """Create slideshow video without audio."""
        try:
            # Create a temporary file list for FFmpeg
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                file_list_path = f.name
                
                for image_path in image_paths:
                    # Escape path for FFmpeg
                    escaped_path = image_path.replace("'", "\\'").replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")
                    f.write(f"duration {duration_per_image}\n")
                    
                # Add the last image again for proper duration
                if image_paths:
                    escaped_path = image_paths[-1].replace("'", "\\'").replace("\\", "/")
                    f.write(f"file '{escaped_path}'\n")
                    
            try:
                # Build FFmpeg command
                cmd = [
                    'ffmpeg',
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', file_list_path,
                    '-c:v', 'libx264',
                    '-pix_fmt', 'yuv420p',
                    '-r', '30',  # Frame rate
                    '-y',  # Overwrite output file
                    output_path
                ]
                
                # Execute FFmpeg command
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                
                if result.returncode == 0:
                    logging.info(f"Successfully created slideshow video: {output_path}")
                    return True
                else:
                    logging.error(f"FFmpeg error: {result.stderr}")
                    return False
                    
            finally:
                # Clean up temporary file
                if os.path.exists(file_list_path):
                    os.unlink(file_list_path)
                    
        except Exception as e:
            logging.error(f"Error creating slideshow without audio: {e}")
            return False
            
    def _get_audio_duration(self, audio_path: str) -> float:
        """Get duration of audio file in seconds."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            else:
                logging.warning(f"Could not get audio duration: {result.stderr}")
                return 0.0
                
        except Exception as e:
            logging.warning(f"Error getting audio duration: {e}")
            return 0.0
            
    def convert_audio_format(self, input_path: str, output_path: str, format: str = 'mp3') -> bool:
        """Convert audio to specified format."""
        try:
            if not self._check_ffmpeg():
                logging.error("FFmpeg not found")
                return False
                
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-acodec', 'libmp3lame' if format == 'mp3' else format,
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logging.info(f"Successfully converted audio: {output_path}")
                return True
            else:
                logging.error(f"Audio conversion failed: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error converting audio: {e}")
            return False
            
    def extract_audio_from_video(self, video_path: str, audio_path: str) -> bool:
        """Extract audio from video file."""
        try:
            if not self._check_ffmpeg():
                logging.error("FFmpeg not found")
                return False
                
            cmd = [
                'ffmpeg',
                '-i', video_path,
                '-vn',  # No video
                '-acodec', 'copy',
                '-y',
                audio_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                logging.info(f"Successfully extracted audio: {audio_path}")
                return True
            else:
                logging.error(f"Audio extraction failed: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error extracting audio: {e}")
            return False
            
    def resize_image(self, input_path: str, output_path: str, width: int, height: int) -> bool:
        """Resize image using FFmpeg."""
        try:
            if not self._check_ffmpeg():
                logging.error("FFmpeg not found")
                return False
                
            cmd = [
                'ffmpeg',
                '-i', input_path,
                '-vf', f'scale={width}:{height}',
                '-y',
                output_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logging.info(f"Successfully resized image: {output_path}")
                return True
            else:
                logging.error(f"Image resize failed: {result.stderr}")
                return False
                
        except Exception as e:
            logging.error(f"Error resizing image: {e}")
            return False
