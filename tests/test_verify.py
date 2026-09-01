from __future__ import annotations

import zipfile

import pytest
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


def test_verify_pdf_detects_page_annotations(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        TextStringObject,
    )

    src = tmp_path / "annotated.pdf"
    standard = tmp_path / "standard.pdf"
    aggressive = tmp_path / "aggressive.pdf"

    writer = PdfWriter()
    writer.metadata = None
    page = writer.add_blank_page(width=72, height=72)
    annotation = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Text"),
            NameObject("/Rect"): ArrayObject(
                [FloatObject(10), FloatObject(10), FloatObject(20), FloatObject(20)]
            ),
            NameObject("/Contents"): TextStringObject("Reviewer note"),
        }
    )
    page[NameObject("/Annots")] = ArrayObject([annotation])
    with open(src, "wb") as f:
        writer.write(f)

    result = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))

    assert result.details["page_annots_count"] == 1
    assert result.status == VerifyStatus.METADATA_FOUND

    PdfScrubber().scrub(src, standard, options=ScrubOptions(pdf_aggressive=False))
    standard_result = verify_file(
        standard, options=VerifyOptions(recursive=False, show_values=False)
    )
    assert standard_result.details["page_annots_count"] == 1
    assert standard_result.status == VerifyStatus.METADATA_FOUND

    PdfScrubber().scrub(src, aggressive, options=ScrubOptions(pdf_aggressive=True))
    aggressive_result = verify_file(
        aggressive, options=VerifyOptions(recursive=False, show_values=False)
    )
    assert aggressive_result.details["page_annots_count"] == 0
    assert aggressive_result.status == VerifyStatus.CLEAN


def test_verify_pdf_ignores_empty_page_annotation_array(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, NameObject

    src = tmp_path / "empty-annotations.pdf"

    writer = PdfWriter()
    writer.metadata = None
    page = writer.add_blank_page(width=72, height=72)
    page[NameObject("/Annots")] = ArrayObject()
    with open(src, "wb") as f:
        writer.write(f)

    result = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))

    assert result.details["page_annots_count"] == 0
    assert result.status == VerifyStatus.CLEAN


def test_verify_pdf_reports_unreadable_page_annotations_as_error(tmp_path):
    from pypdf import PdfWriter
    from pypdf.generic import NameObject, NullObject

    src = tmp_path / "invalid-annotations.pdf"

    writer = PdfWriter()
    writer.metadata = None
    page = writer.add_blank_page(width=72, height=72)
    page[NameObject("/Annots")] = NullObject()
    with open(src, "wb") as f:
        writer.write(f)

    result = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))

    assert result.status == VerifyStatus.ERROR
    assert result.message == "Unable to inspect PDF page annotations"


@pytest.mark.parametrize("wrong_type", ["dictionary", "text", "stream"])
def test_verify_pdf_reports_wrong_annotation_container_type_as_error(
    tmp_path, wrong_type
):
    from pypdf import PdfWriter
    from pypdf.generic import (
        DecodedStreamObject,
        DictionaryObject,
        NameObject,
        TextStringObject,
    )

    src = tmp_path / f"invalid-annotations-{wrong_type}.pdf"
    wrong_annots = {
        "dictionary": DictionaryObject(
            {NameObject("/Contents"): TextStringObject("Reviewer note")}
        ),
        "text": TextStringObject("Reviewer note"),
        "stream": DecodedStreamObject(),
    }[wrong_type]
    if isinstance(wrong_annots, DecodedStreamObject):
        wrong_annots.set_data(b"Author: Alice\nComment: Reviewer note")

    writer = PdfWriter()
    writer.metadata = None
    page = writer.add_blank_page(width=72, height=72)
    page[NameObject("/Annots")] = wrong_annots
    with open(src, "wb") as f:
        writer.write(f)

    result = verify_file(src, options=VerifyOptions(recursive=False, show_values=False))

    assert result.status == VerifyStatus.ERROR
    assert result.message == "Unable to inspect PDF page annotations"
