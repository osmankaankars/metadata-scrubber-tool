from __future__ import annotations

import json
import os
import shutil
import subprocess
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

from defusedxml import ElementTree as DefusedET
from PIL import ExifTags, Image
from pypdf import PdfReader


class VerifyStatus(str, Enum):
    CLEAN = "clean"
    METADATA_FOUND = "metadata_found"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


@dataclass(frozen=True)
class VerifyResult:
    path: Path
    status: VerifyStatus
    kind: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    message: str | None = None


@dataclass(frozen=True)
class VerifyOptions:
    recursive: bool = True
    show_values: bool = False


def verify_paths(paths: Iterable[Path], options: VerifyOptions) -> list[VerifyResult]:
    results: list[VerifyResult] = []

    for root in paths:
        root = root.expanduser()
        for p in _iter_files(root, recursive=options.recursive):
            results.append(verify_file(p, options=options))

    return results


def verify_file(path: Path, *, options: VerifyOptions) -> VerifyResult:
    ext = path.suffix.lower()

    try:
        if ext in {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}:
            return _verify_image(path, options=options)

        if ext == ".pdf":
            return _verify_pdf(path)

        if ext in {".docx", ".xlsx", ".pptx"}:
            return _verify_openxml(path, options=options)

        if ext in {".mp3", ".flac", ".m4a", ".ogg"}:
            return _verify_audio(path)

        if ext in {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}:
            return _verify_video(path)

        return VerifyResult(path=path, status=VerifyStatus.UNSUPPORTED)

    except Exception as e:  # noqa: BLE001
        return VerifyResult(path=path, status=VerifyStatus.ERROR, message=str(e))


def _iter_files(root: Path, *, recursive: bool) -> Iterable[Path]:
    if root.is_file():
        if not root.is_symlink():
            yield root
        return

    if not root.is_dir():
        return

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in {".git", ".venv", "__pycache__"}]
            base = Path(dirpath)
            for fn in filenames:
                p = base / fn
                if p.is_symlink():
                    continue
                if p.is_file():
                    yield p
    else:
        for p in root.iterdir():
            if p.is_symlink():
                continue
            if p.is_file():
                yield p


def _verify_image(path: Path, *, options: VerifyOptions) -> VerifyResult:
    with Image.open(path) as img:
        exif = img.getexif()
        exif_tags: dict[str, Any] = {}
        for tag_id, value in exif.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
            if options.show_values:
                exif_tags[tag_name] = _safe_str(value)
            else:
                exif_tags[tag_name] = None

        info_keys = sorted({k for k in img.info.keys()})

        # Consider only keys that are likely metadata payloads.
        interesting_info_keys = [
            k
            for k in info_keys
            if k.lower() in {"exif", "xmp", "icc_profile", "comment", "xml", "author", "description"}
            or k.lower().startswith("text")
        ]

        found = (len(exif_tags) > 0) or (len(interesting_info_keys) > 0)
        status = VerifyStatus.METADATA_FOUND if found else VerifyStatus.CLEAN

        details: dict[str, Any] = {
            "exif_tag_count": len(exif_tags),
            "exif_tags": sorted(exif_tags.keys()),
            "info_keys": info_keys,
            "interesting_info_keys": interesting_info_keys,
        }
        if options.show_values and exif_tags:
            details["exif_values"] = exif_tags

        return VerifyResult(path=path, kind="image", status=status, details=details)


def _verify_pdf(path: Path) -> VerifyResult:
    r = PdfReader(str(path))

    md = dict(r.metadata or {})
    md_keys = sorted(md.keys())

    root = r.trailer.get("/Root")
    has_root_metadata = False
    names_keys: list[str] = []
    try:
        if root is not None:
            for k in ("/Metadata", "/PieceInfo", "/OpenAction", "/AA"):
                if k in root:
                    has_root_metadata = True

            if "/Names" in root:
                names = root["/Names"]
                if hasattr(names, "keys"):
                    names_keys = sorted(list(names.keys()))
                    if "/EmbeddedFiles" in names or "/JavaScript" in names:
                        has_root_metadata = True
    except Exception:
        pass

    page_pieceinfo = 0
    page_annots = 0
    try:
        for page in r.pages:
            if "/PieceInfo" in page:
                page_pieceinfo += 1
            if "/Annots" in page:
                page_annots += 1
    except Exception:
        pass

    found = bool(md_keys) or has_root_metadata or page_pieceinfo > 0
    status = VerifyStatus.METADATA_FOUND if found else VerifyStatus.CLEAN

    details = {
        "metadata_keys": md_keys,
        "has_root_metadata": has_root_metadata,
        "names_keys": names_keys,
        "page_pieceinfo_count": page_pieceinfo,
        "page_annots_count": page_annots,
    }

    return VerifyResult(path=path, kind="pdf", status=status, details=details)


def _verify_openxml(path: Path, *, options: VerifyOptions) -> VerifyResult:
    with zipfile.ZipFile(path, "r") as z:
        names = set(z.namelist())

        docprops = [
            p
            for p in ["docProps/core.xml", "docProps/app.xml", "docProps/custom.xml"]
            if p in names
        ]

        core_fields: list[str] = []
        if "docProps/core.xml" in names:
            try:
                raw = z.read("docProps/core.xml")
                root = DefusedET.fromstring(raw)
                for el in root.iter():
                    # Element tags are namespaced: {ns}local
                    if "}" in el.tag:
                        local = el.tag.split("}", 1)[1]
                    else:
                        local = el.tag
                    if (el.text or "").strip() == "":
                        continue
                    core_fields.append(local)
                core_fields = sorted(set(core_fields))
            except Exception:
                core_fields = ["<unreadable>"]

        # ZIP entry timestamps can carry metadata; most scrubbers normalize them.
        ts = {info.date_time for info in z.infolist()}
        normalized_ts = (1980, 1, 1, 0, 0, 0)
        non_normalized_ts_count = sum(1 for t in ts if t != normalized_ts)

        found = bool(docprops) or non_normalized_ts_count > 0
        status = VerifyStatus.METADATA_FOUND if found else VerifyStatus.CLEAN

        details: dict[str, Any] = {
            "docprops_present": docprops,
            "core_fields": core_fields,
            "unique_zip_timestamps": len(ts),
            "non_normalized_zip_timestamps": non_normalized_ts_count,
        }

        return VerifyResult(path=path, kind="openxml", status=status, details=details)


def _verify_audio(path: Path) -> VerifyResult:
    try:
        from mutagen import File as MutagenFile  # type: ignore
    except Exception:
        return VerifyResult(
            path=path,
            kind="audio",
            status=VerifyStatus.UNSUPPORTED,
            message="mutagen not installed (pip install -e '.[audio]')",
        )

    audio = MutagenFile(str(path))
    if audio is None:
        return VerifyResult(path=path, kind="audio", status=VerifyStatus.UNSUPPORTED)

    tags = getattr(audio, "tags", None)
    keys: list[str] = []
    if tags is not None and hasattr(tags, "keys"):
        try:
            keys = sorted(list(tags.keys()))
        except Exception:
            keys = []

    status = VerifyStatus.METADATA_FOUND if keys else VerifyStatus.CLEAN
    return VerifyResult(path=path, kind="audio", status=status, details={"tag_keys": keys})


def _verify_video(path: Path) -> VerifyResult:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return VerifyResult(
            path=path,
            kind="video",
            status=VerifyStatus.UNSUPPORTED,
            message="ffprobe not found (install ffmpeg/ffprobe)",
        )

    cmd = [
        ffprobe,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    out = subprocess.check_output(cmd)
    data = json.loads(out.decode("utf-8", errors="replace"))

    format_tags = data.get("format", {}).get("tags") or {}
    stream_tags: dict[str, list[str]] = {}
    for idx, s in enumerate(data.get("streams", []) or []):
        tags = s.get("tags") or {}
        if tags:
            stream_tags[str(idx)] = sorted(tags.keys())

    found = bool(format_tags) or bool(stream_tags)
    status = VerifyStatus.METADATA_FOUND if found else VerifyStatus.CLEAN

    return VerifyResult(
        path=path,
        kind="video",
        status=status,
        details={
            "format_tag_keys": sorted(list(format_tags.keys())),
            "stream_tag_keys": stream_tags,
        },
    )


def _safe_str(value: Any) -> str:
    s = str(value)
    if len(s) > 200:
        return s[:200] + "..."
    return s
