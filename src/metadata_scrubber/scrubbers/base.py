from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScrubOptions:
    normalize_zip_timestamps: bool = True
    pdf_aggressive: bool = False


class Scrubber(ABC):
    name: str

    @abstractmethod
    def can_handle(self, path: Path) -> bool:
        raise NotImplementedError

    @abstractmethod
    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:
        """Write a scrubbed version of src to dst."""
        raise NotImplementedError
