from __future__ import annotations

import zipfile

from metadata_scrubber.scrubbers.openxml import OpenXmlScrubber
from metadata_scrubber.scrubbers.base import ScrubOptions


def _make_openxml(path):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr(
            "[Content_Types].xml",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\">
  <Override PartName=\"/docProps/core.xml\" ContentType=\"application/vnd.openxmlformats-package.core-properties+xml\"/>
  <Override PartName=\"/docProps/app.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.extended-properties+xml\"/>
</Types>""",
        )
        z.writestr(
            "_rels/.rels",
            """<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\">
  <Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties\" Target=\"docProps/core.xml\"/>
  <Relationship Id=\"rId2\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties\" Target=\"docProps/app.xml\"/>
</Relationships>""",
        )
        z.writestr("docProps/core.xml", "<coreProperties><dc:creator>Alice</dc:creator></coreProperties>")
        z.writestr("docProps/app.xml", "<Properties><Application>Word</Application></Properties>")
        z.writestr("word/document.xml", "<w:document/>")


def test_openxml_removes_docprops_and_refs(tmp_path):
    src = tmp_path / "sample.docx"
    dst = tmp_path / "out.docx"
    _make_openxml(src)

    scrubber = OpenXmlScrubber()
    scrubber.scrub(src, dst, options=ScrubOptions(normalize_zip_timestamps=True))

    with zipfile.ZipFile(dst, "r") as z:
        names = set(z.namelist())
        assert "docProps/core.xml" not in names
        assert "docProps/app.xml" not in names

        rels = z.read("_rels/.rels").decode("utf-8")
        assert "docProps/core.xml" not in rels
        assert "docProps/app.xml" not in rels

        ct = z.read("[Content_Types].xml").decode("utf-8")
        assert "/docProps/core.xml" not in ct
        assert "/docProps/app.xml" not in ct

        # Normalized timestamps
        zi = z.getinfo("word/document.xml")
        assert zi.date_time == (1980, 1, 1, 0, 0, 0)
