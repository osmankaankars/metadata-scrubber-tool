# Metadata Scrubber Tool

[![CI](https://github.com/osmankaankars/metadata-scrubber-tool/actions/workflows/ci.yml/badge.svg)](https://github.com/osmankaankars/metadata-scrubber-tool/actions/workflows/ci.yml)

A small CLI tool that removes metadata from common file types before you share them.

## Supported Formats

- Images: `.jpg/.jpeg`, `.png`, `.tif/.tiff`, `.webp`
  - Re-encodes the image without EXIF and other attached metadata
  - Applies EXIF orientation (so the pixels keep the correct orientation after EXIF is removed)
- PDF: `.pdf`
  - Best-effort removal of document info and XMP metadata
  - Optional: more aggressive mode with `--pdf-aggressive`
- Office OpenXML: `.docx`, `.xlsx`, `.pptx`
  - Removes `docProps/*` parts (core/app/custom properties)
  - Normalizes timestamps inside the ZIP container to reduce timestamp-based metadata
- Video (requires `ffmpeg`): `.mp4`, `.mov`, `.m4v`, `.mkv`, `.avi`, `.webm`
  - Stream-copy without re-encoding, while dropping container/stream metadata (best-effort)
- Optional audio (requires `mutagen`): `.mp3`, `.flac`, `.m4a`, `.ogg`
  - Removes all tags

Also (macOS/Linux): the tool attempts to strip extended attributes (xattr) from output files.

## Install

From source (recommended for development):

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

Optional (audio tag removal):

```bash
pip install -e '.[audio]'
```

From GitHub:

```bash
pip install 'git+https://github.com/osmankaankars/metadata-scrubber-tool.git'
```

Video scrubbing and video verification require `ffmpeg`/`ffprobe`.

## Usage

Default mode is copy-mode: it writes scrubbed copies into an output directory and does not modify your originals.

```bash
metadata-scrubber ./PATH_TO_FILES --out ./scrubbed
```

In-place mode (risky): modifies files in place. By default it creates a backup next to each file.

```bash
metadata-scrubber ./secret.pdf --in-place --backup-suffix .bak
```

More aggressive PDF sanitization:

```bash
metadata-scrubber ./file.pdf --out ./scrubbed --pdf-aggressive
```

Dry run:

```bash
metadata-scrubber ./PATH_TO_FILES --out ./scrubbed --dry-run
```

Copy unsupported file types as-is (no scrubbing):

```bash
metadata-scrubber ./PATH_TO_FILES --out ./scrubbed --copy-unknown
```

Examples folder:

```bash
metadata-scrubber ./examples --out ./scrubbed
```

Verify/report remaining metadata (best-effort):

```bash
metadata-verify ./PATH_TO_FILES
metadata-verify ./PATH_TO_FILES --fail-on-metadata
metadata-verify ./PATH_TO_FILES --json
```

## Notes / Limitations

- Metadata removal is best-effort and format-specific. There is no guarantee that *all* metadata is removed for every file.
- Content-level data (for example names inside a document body, revision history, embedded attachments, etc.) may still exist.
- Always validate your output using the tools you trust for your target format.

## Roadmap

Potential next upgrades: more file types (for example HEIC), stronger PDF sanitization options, and richer verification output (including per-format summaries and stricter failure modes).

## License

MIT. See `LICENSE`.
