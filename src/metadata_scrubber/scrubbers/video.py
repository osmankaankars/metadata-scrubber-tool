from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from .base import ScrubOptions, Scrubber


class VideoScrubber(Scrubber):
    name = "video"

    _exts = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self._exts

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:  # noqa: ARG002
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(
                "ffmpeg not found (required to scrub video files). Install ffmpeg and try again."
            )

        # Copy streams without re-encoding, but drop container/stream metadata.
        # -map_metadata -1: drop global metadata
        # -map_chapters -1: drop chapters (often include titles)
        cmd = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            "-map",
            "0",
            "-c",
            "copy",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            # Reduce muxer-generated tags like encoder=Lavf... where possible.
            "-fflags",
            "+bitexact",
            "-flags",
            "+bitexact",
            "-metadata",
            "title=",
            "-metadata",
            "comment=",
            "-metadata",
            "artist=",
            "-metadata",
            "album=",
            "-metadata",
            "date=",
            "-metadata",
            "creation_time=",
            "-metadata",
            "encoder=",
            "-metadata:s",
            "creation_time=",
            "-metadata:s",
            "encoder=",
            str(dst),
        ]

        subprocess.run(cmd, check=True)
