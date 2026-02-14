from __future__ import annotations

from .images import ImageScrubber
from .openxml import OpenXmlScrubber
from .pdf import PdfScrubber


def default_scrubbers():
    scrubbers = [ImageScrubber(), PdfScrubber(), OpenXmlScrubber()]

    # Optional scrubbers
    try:
        from .audio import AudioScrubber  # noqa: PLC0415

        scrubbers.append(AudioScrubber())
    except Exception:
        pass

    return scrubbers
