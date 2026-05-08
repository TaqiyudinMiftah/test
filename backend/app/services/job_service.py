import subprocess
import json
import os
from typing import Dict, Any

class JobService:
    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_format",
                    "-show_streams",
                    file_path
                ],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
            
            metadata = {
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "format_name": format_info.get("format_name", ""),
                "video_codec": video_stream.get("codec_name", ""),
                "video_width": video_stream.get("width", 0),
                "video_height": video_stream.get("height", 0),
                "video_fps": eval(video_stream.get("r_frame_rate", "0/1")),
                "audio_codec": audio_stream.get("codec_name", ""),
                "audio_sample_rate": audio_stream.get("sample_rate", 0),
            }
            return metadata
        except Exception as e:
            print(f"Error extracting metadata: {e}")
            return {}

job_service = JobService()
