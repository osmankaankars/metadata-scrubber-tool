from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, IndirectObject

from .base import ScrubOptions, Scrubber


class PdfScrubber(Scrubber):
    name = "pdf"

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".pdf"

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:
        reader = PdfReader(str(src))
        writer = PdfWriter()

        for page in reader.pages:
            _sanitize_page(page, aggressive=options.pdf_aggressive)
            writer.add_page(page)

        _sanitize_writer(writer, aggressive=options.pdf_aggressive)

        with open(dst, "wb") as f:
            writer.write(f)


def _sanitize_page(page, *, aggressive: bool) -> None:
    # Remove per-page structures that may include creator/tooling data.
    for k in ("/PieceInfo", "/AA"):
        try:
            if k in page:
                del page[k]
        except Exception:
            pass

    if aggressive:
        # Annotations can contain author names, comments, timestamps, etc.
        for k in ("/Annots",):
            try:
                if k in page:
                    del page[k]
            except Exception:
                pass


def _sanitize_writer(writer: PdfWriter, *, aggressive: bool) -> None:
    # Best-effort removal of document info (/Info), XMP metadata streams, and
    # other root-level structures that often contain identifying information.
    try:
        writer._info = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Some libraries include a trailer /ID by default. It's optional; remove it
    # in aggressive mode.
    if aggressive:
        try:
            writer._ID = None  # type: ignore[attr-defined]
        except Exception:
            pass

    drop_root_keys = {"/Metadata", "/PieceInfo", "/OpenAction", "/AA"}
    if aggressive:
        drop_root_keys |= {
            "/AcroForm",
            "/Outlines",
            "/StructTreeRoot",
            "/PageLabels",
            "/ViewerPreferences",
            "/Threads",
            "/Dests",
        }

    try:
        root = writer._root_object  # type: ignore[attr-defined]
        for k in drop_root_keys:
            try:
                if k in root:
                    del root[k]
            except Exception:
                pass

        # Remove common name-tree entries that can carry scripts or attachments.
        if "/Names" in root:
            try:
                names = root["/Names"]
                if isinstance(names, DictionaryObject):
                    for k in ("/EmbeddedFiles", "/JavaScript"):
                        if k in names:
                            del names[k]
                    if aggressive and len(names) == 0:
                        del root["/Names"]
            except Exception:
                pass
    except Exception:
        pass

    # Deep scrub: traverse copied objects and delete any lingering metadata keys.
    keys_to_delete = {"/Metadata", "/PieceInfo", "/LastModified"}
    if aggressive:
        keys_to_delete |= {"/CreationDate", "/ModDate", "/Creator", "/Producer"}

    try:
        _deep_delete_keys(writer._root_object, keys_to_delete, aggressive=aggressive)  # type: ignore[attr-defined]
    except Exception:
        pass


def _deep_delete_keys(obj, keys_to_delete: set[str], *, aggressive: bool, _seen: set[int] | None = None) -> None:
    if _seen is None:
        _seen = set()

    try:
        if isinstance(obj, IndirectObject):
            real = obj.get_object()
            oid = id(real)
            if oid in _seen:
                return
            _seen.add(oid)
            _deep_delete_keys(real, keys_to_delete, aggressive=aggressive, _seen=_seen)
            return

        if isinstance(obj, DictionaryObject):
            for k in list(obj.keys()):
                if k in keys_to_delete:
                    try:
                        del obj[k]
                    except Exception:
                        pass

            # Aggressive: drop annotation arrays and form actions anywhere they appear.
            if aggressive:
                for k in ("/Annots", "/AA", "/OpenAction"):
                    if k in obj:
                        try:
                            del obj[k]
                        except Exception:
                            pass

            for v in list(obj.values()):
                _deep_delete_keys(v, keys_to_delete, aggressive=aggressive, _seen=_seen)
            return

        if isinstance(obj, ArrayObject):
            for item in list(obj):
                _deep_delete_keys(item, keys_to_delete, aggressive=aggressive, _seen=_seen)
            return
    except Exception:
        return
