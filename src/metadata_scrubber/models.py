from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ScrubStatus(str, Enum):
    SCRUBBED = "scrubbed"
    COPIED_UNKNOWN = "copied_unknown"
    SKIPPED_UNSUPPORTED = "skipped_unsupported"
    SKIPPED_NOT_A_FILE = "skipped_not_a_file"
    SKIPPED_EXISTS = "skipped_exists"
    DRY_RUN = "dry_run"
    ERROR = "error"


@dataclass(frozen=True)
class ScrubResult:
    src: Path
    dst: Path | None
    status: ScrubStatus
    scrubber: str | None = None
    message: str | None = None
    removed_xattrs: tuple[str, ...] = ()
