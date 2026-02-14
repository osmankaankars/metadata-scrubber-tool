from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from defusedxml import ElementTree as DefusedET

from .base import ScrubOptions, Scrubber


class OpenXmlScrubber(Scrubber):
    name = "openxml"

    _exts = {".docx", ".xlsx", ".pptx"}

    _remove_parts = {
        "docProps/core.xml",
        "docProps/app.xml",
        "docProps/custom.xml",
        "docProps/thumbnail.jpeg",
        "docProps/thumbnail.png",
    }

    _rels_path = "_rels/.rels"
    _content_types_path = "[Content_Types].xml"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self._exts

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:
        with zipfile.ZipFile(src, "r") as zin:
            with zipfile.ZipFile(dst, "w", compression=zipfile.ZIP_DEFLATED) as zout:
                for info in zin.infolist():
                    name = info.filename

                    if name in self._remove_parts:
                        continue

                    data = zin.read(name)

                    if name == self._rels_path:
                        data = _scrub_rels_xml(data)
                    elif name == self._content_types_path:
                        data = _scrub_content_types_xml(data)

                    zi = zipfile.ZipInfo(filename=name)
                    if options.normalize_zip_timestamps:
                        zi.date_time = (1980, 1, 1, 0, 0, 0)
                    else:
                        zi.date_time = info.date_time

                    zi.compress_type = zipfile.ZIP_DEFLATED
                    zi.external_attr = info.external_attr
                    zout.writestr(zi, data)


def _scrub_rels_xml(raw: bytes) -> bytes:
    try:
        root = DefusedET.fromstring(raw)
    except Exception:
        return raw

    # Relationship types we want to remove.
    drop_types = {
        "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties",
    }
    drop_targets = {"docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"}

    to_remove = []
    for rel in list(root):
        typ = rel.attrib.get("Type")
        target = rel.attrib.get("Target")
        if typ in drop_types or target in drop_targets:
            to_remove.append(rel)

    for rel in to_remove:
        root.remove(rel)

    return _etree_to_bytes(root)


def _scrub_content_types_xml(raw: bytes) -> bytes:
    try:
        root = DefusedET.fromstring(raw)
    except Exception:
        return raw

    drop_parts = {"/docProps/core.xml", "/docProps/app.xml", "/docProps/custom.xml"}

    to_remove = []
    for child in list(root):
        part = child.attrib.get("PartName")
        if part in drop_parts:
            to_remove.append(child)

    for child in to_remove:
        root.remove(child)

    return _etree_to_bytes(root)


def _etree_to_bytes(root) -> bytes:
    # Preserve XML declaration if present? Office usually doesn't require it.
    buf = io.BytesIO()
    # defusedxml.ElementTree is a safe parser, but doesn't expose the full
    # xml.etree.ElementTree API surface (like ElementTree()). Use stdlib for
    # serialization.
    ET.ElementTree(root).write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()
