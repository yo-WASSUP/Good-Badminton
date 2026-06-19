import json
import os
import shutil
import subprocess
import time

import cv2
from moviepy.editor import VideoFileClip


def has_audio_track(video_path):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                video_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            data = json.loads(result.stdout)
            return any(stream.get("codec_type") == "audio" for stream in data.get("streams", []))

        try:
            video = VideoFileClip(video_path)
            has_audio = video.audio is not None
            video.close()
            return has_audio
        except Exception:
            return False
    except Exception as exc:
        print(f"Error checking audio track: {exc}")
        return True


def process_video_with_audio(video_path, temp_video_path, output_path, save_dir):
    try:
        print("\nProcessing video audio...")

        if not has_audio_track(video_path):
            print("No audio track detected; exporting video without audio.")
            return process_video_without_audio(temp_video_path, output_path)

        if not os.path.exists(temp_video_path):
            raise FileNotFoundError(f"Temporary video not found: {temp_video_path}")

        fixed_temp_path = os.path.join(save_dir, "fixed_temp_video.mp4")
        temp_for_audio = temp_video_path

        try:
            subprocess.call(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    temp_video_path,
                    "-c:v",
                    "copy",
                    "-movflags",
                    "faststart",
                    fixed_temp_path,
                ],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
            if os.path.exists(fixed_temp_path) and os.path.getsize(fixed_temp_path) > 0:
                temp_for_audio = fixed_temp_path
        except Exception:
            temp_for_audio = temp_video_path

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                temp_for_audio,
                "-i",
                video_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-map",
                "0:v",
                "-map",
                "1:a",
                "-shortest",
                output_path,
            ],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            timeout=120,
        )

        if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("ffmpeg failed to merge audio")

        print(f"Video with audio saved to: {output_path}")
        cleanup_temp_files([temp_video_path, fixed_temp_path])
        return True

    except Exception as exc:
        print(f"Audio merge failed: {exc}")
        print("Falling back to video without audio.")
        return process_video_without_audio(temp_video_path, output_path)


def process_video_without_audio(temp_video_path, output_path):
    try:
        print("\nProcessing video without audio...")
        if not os.path.exists(temp_video_path):
            raise FileNotFoundError(f"Temporary video not found: {temp_video_path}")

        shutil.copy2(temp_video_path, output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError("Output video was not created")

        print(f"Video saved to: {output_path}")
        cleanup_temp_files([temp_video_path])
        return True
    except Exception as exc:
        print(f"Video processing failed: {exc}")
        return False


def setup_video_writer(frame_width, frame_height, fps, temp_output_path):
    os.makedirs(os.path.dirname(temp_output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(temp_output_path, fourcc, fps, (frame_width, frame_height))
    if not writer.isOpened():
        raise RuntimeError(f"Unable to create video writer: {temp_output_path}")
    return writer


def cleanup_temp_files(file_list, keep_temp_video=False):
    for file_path in file_list:
        if keep_temp_video and file_path and "temp_detect_" in os.path.basename(file_path):
            continue
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as exc:
            print(f"Failed to remove temporary file {file_path}: {exc}")

    time.sleep(0.1)
