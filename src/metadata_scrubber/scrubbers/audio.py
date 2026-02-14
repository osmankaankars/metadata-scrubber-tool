from __future__ import annotations

import shutil
from pathlib import Path

from .base import ScrubOptions, Scrubber


class AudioScrubber(Scrubber):
    name = "audio"

    _exts = {".mp3", ".flac", ".m4a", ".mp4", ".ogg"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self._exts

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:  # noqa: ARG002
        # Mutagen works in-place, so we copy first when dst != src.
        shutil.copyfile(src, dst)

        from mutagen import File as MutagenFile  # type: ignore

        audio = MutagenFile(str(dst))
        if audio is None:
            raise ValueError("Unsupported or unreadable audio file")

        # Remove all tags.
        if hasattr(audio, "delete"):
            audio.delete()
        if hasattr(audio, "save"):
            audio.save()
