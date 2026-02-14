from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter

from .base import ScrubOptions, Scrubber


class PdfScrubber(Scrubber):
    name = "pdf"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:  # noqa: ARG002
        reader = PdfReader(str(src))
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        # Best-effort: remove document info (/Info) and XMP metadata stream.
        try:
            writer._info = None  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            root = writer._root_object  # type: ignore[attr-defined]
            for k in ("/Metadata", "/PieceInfo"):
                if k in root:
                    del root[k]
        except Exception:
            pass

        with open(dst, "wb") as f:
            writer.write(f)
