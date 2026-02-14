from __future__ import annotations

from pypdf import PdfReader, PdfWriter

from metadata_scrubber.scrubbers.base import ScrubOptions
from metadata_scrubber.scrubbers.pdf import PdfScrubber


def test_pdf_scrub_removes_docinfo_and_xmp(tmp_path):
    src = tmp_path / "in.pdf"
    dst = tmp_path / "out.pdf"

    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_metadata({"/Author": "Alice", "/Title": "Secret", "/Subject": "X"})
    with open(src, "wb") as f:
        w.write(f)

    scrubber = PdfScrubber()
    scrubber.scrub(src, dst, options=ScrubOptions())

    r = PdfReader(str(dst))
    md = dict(r.metadata or {})

    assert "/Author" not in md
    assert "/Title" not in md
    assert "/Subject" not in md

    root = r.trailer["/Root"]
    assert "/Metadata" not in root
