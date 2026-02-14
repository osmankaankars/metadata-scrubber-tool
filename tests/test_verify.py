from __future__ import annotations

import zipfile

from PIL import Image

from metadata_scrubber.scrubbers.base import ScrubOptions
from metadata_scrubber.scrubbers.images import ImageScrubber
from metadata_scrubber.scrubbers.openxml import OpenXmlScrubber
from metadata_scrubber.scrubbers.pdf import PdfScrubber
from metadata_scrubber.verify import VerifyOptions, VerifyStatus, verify_file


def test_verify_image_detects_exif_then_clean_after_scrub(tmp_path):
    src = tmp_path / "in.jpg"
    dst = tmp_path / "out.jpg"

    img = Image.new("RGB", (20, 20), (10, 20, 30))
    exif = Image.Exif()
    exif[274] = 3
    img.save(src, exif=exif, quality=95, subsampling=0)

    r1 = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))
    assert r1.status == VerifyStatus.METADATA_FOUND

    ImageScrubber().scrub(src, dst, options=ScrubOptions())

    r2 = verify_file(dst, options=VerifyOptions(recursive=False, show_values=False))
    assert r2.status == VerifyStatus.CLEAN


def _make_openxml(path):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>
</Relationships>""",
        )
        z.writestr("docProps/core.xml", "<coreProperties><dc:creator>Alice</dc:creator></coreProperties>")
        z.writestr("word/document.xml", "<w:document/>")


def test_verify_openxml_detects_docprops_then_clean_after_scrub(tmp_path):
    src = tmp_path / "sample.docx"
    dst = tmp_path / "out.docx"
    _make_openxml(src)

    r1 = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))
    assert r1.status == VerifyStatus.METADATA_FOUND

    OpenXmlScrubber().scrub(src, dst, options=ScrubOptions(normalize_zip_timestamps=True))

    r2 = verify_file(dst, options=VerifyOptions(recursive=False, show_values=False))
    assert r2.status == VerifyStatus.CLEAN


def test_verify_pdf_detects_docinfo_then_clean_after_scrub(tmp_path):
    from pypdf import PdfWriter

    src = tmp_path / "in.pdf"
    dst = tmp_path / "out.pdf"

    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    w.add_metadata({"/Author": "Alice", "/Title": "Secret"})
    with open(src, "wb") as f:
        w.write(f)

    r1 = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))
    assert r1.status == VerifyStatus.METADATA_FOUND

    PdfScrubber().scrub(src, dst, options=ScrubOptions(pdf_aggressive=False))

    r2 = verify_file(dst, options=VerifyOptions(recursive=False, show_values=False))
    assert r2.status == VerifyStatus.CLEAN
