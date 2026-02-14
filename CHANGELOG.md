# Changelog

All notable changes to this project will be documented in this file.

## 0.2.0 - 2026-02-14

More file types and verification tooling.

- New: `metadata-verify` command to report remaining metadata (best-effort)
- New: Video scrubber (MP4/MOV/M4V/MKV/AVI/WebM) via `ffmpeg` stream copy with metadata removal
- Improved: PDF scrubber supports a more aggressive mode (`--pdf-aggressive`) and deeper metadata removal

## 0.1.0 - 2026-02-14

Initial public release.

- CLI tool: `metadata-scrubber`
- Scrubbers:
  - Images (JPEG/PNG/TIFF/WebP): re-encode without EXIF; apply orientation
  - PDF: best-effort removal of document info and XMP metadata
  - Office OpenXML (DOCX/XLSX/PPTX): remove `docProps/*`; normalize ZIP timestamps
  - Optional audio (MP3/FLAC/M4A/MP4/OGG): remove tags (via `mutagen`)
- Best-effort removal of extended attributes (xattr) on macOS/Linux
