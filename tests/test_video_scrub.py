from __future__ import annotations

import json
import shutil
import subprocess

import pytest

from metadata_scrubber.scrubbers.base import ScrubOptions
from metadata_scrubber.scrubbers.video import VideoScrubber


def _probe_tags(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        pytest.skip("ffprobe not installed")

    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    data = json.loads(subprocess.check_output(cmd).decode("utf-8", errors="replace"))

    fmt_tags = (data.get("format") or {}).get("tags") or {}
    stream_tags = [(s.get("tags") or {}) for s in (data.get("streams") or [])]
    return fmt_tags, stream_tags


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_video_scrub_removes_common_tags(tmp_path):
    src = tmp_path / "in.mp4"
    dst = tmp_path / "out.mp4"

    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg

    # Create a tiny MP4 with obvious metadata tags.
    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=64x64:rate=1",
        "-t",
        "1",
        "-metadata",
        "title=SecretTitle",
        "-metadata",
        "comment=SecretComment",
        "-c:v",
        "mpeg4",
        str(src),
    ]
    subprocess.run(cmd, check=True)

    in_fmt, _in_streams = _probe_tags(src)
    assert ("title" in in_fmt) or ("comment" in in_fmt)

    scrubber = VideoScrubber()
    scrubber.scrub(src, dst, options=ScrubOptions())

    out_fmt, out_streams = _probe_tags(dst)

    for key in ["title", "comment", "artist", "album", "date", "creation_time", "encoder"]:
        assert key not in out_fmt
        for st in out_streams:
            assert key not in st
