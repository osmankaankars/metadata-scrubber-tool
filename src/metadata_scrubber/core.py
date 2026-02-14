from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .models import ScrubResult, ScrubStatus
from .scrubbers import default_scrubbers
from .scrubbers.base import ScrubOptions
from .utils import TempPath, atomic_replace, copy_bytes, preserve_stat, strip_xattrs


@dataclass(frozen=True)
class RunOptions:
    out_dir: Path | None
    in_place: bool = False
    dry_run: bool = False
    overwrite: bool = False
    copy_unknown: bool = False
    recursive: bool = True

    preserve_times: bool = True
    preserve_perms: bool = True
    strip_xattrs: bool = True

    normalize_zip_timestamps: bool = True

    backup_suffix: str = ".bak"


def scrub_paths(paths: Iterable[Path], options: RunOptions) -> list[ScrubResult]:
    scrubbers = default_scrubbers()
    scrubber_opts = ScrubOptions(normalize_zip_timestamps=options.normalize_zip_timestamps)

    out_dir_resolved = None
    if options.out_dir is not None:
        out_dir_resolved = options.out_dir.resolve()

    tasks: list[tuple[Path, Path | None]] = []
    for root in paths:
        root = root.expanduser()
        for src in _iter_files(root, recursive=options.recursive):
            if out_dir_resolved is not None:
                try:
                    if src.resolve().is_relative_to(out_dir_resolved):
                        # Avoid re-scrubbing our own output directory.
                        continue
                except Exception:
                    pass

            if options.in_place:
                tasks.append((src, src))
            else:
                if options.out_dir is None:
                    raise ValueError("out_dir is required when not running in-place")
                dst = _map_output_path(src, root, options.out_dir)
                tasks.append((src, dst))

    results: list[ScrubResult] = []
    for (src, dst) in tasks:
        results.append(
            _scrub_one(
                src,
                dst,
                scrubbers=scrubbers,
                scrubber_options=scrubber_opts,
                options=options,
            )
        )

    return results


def _iter_files(root: Path, *, recursive: bool) -> Iterable[Path]:
    if root.is_file():
        if root.is_symlink():
            return
        yield root
        return

    if not root.is_dir():
        return

    if recursive:
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip hidden directories like .git by default?
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


def _map_output_path(src: Path, root: Path, out_dir: Path) -> Path:
    # Put each input root under out_dir/<root_name>/... to avoid collisions.
    if root.is_dir():
        rel = src.relative_to(root)
        return out_dir / root.name / rel

    # root is a file: namespace it by its parent directory name.
    return out_dir / root.parent.name / src.name


def _pick_scrubber(path: Path, scrubbers) -> object | None:
    for s in scrubbers:
        try:
            if s.can_handle(path):
                return s
        except Exception:
            continue
    return None


def _scrub_one(
    src: Path,
    dst: Path | None,
    *,
    scrubbers,
    scrubber_options: ScrubOptions,
    options: RunOptions,
) -> ScrubResult:
    if not src.is_file():
        return ScrubResult(src=src, dst=dst, status=ScrubStatus.SKIPPED_NOT_A_FILE)

    scrubber = _pick_scrubber(src, scrubbers)

    if scrubber is None:
        if options.copy_unknown and not options.in_place and dst is not None:
            if dst.exists() and not options.overwrite:
                return ScrubResult(src=src, dst=dst, status=ScrubStatus.SKIPPED_EXISTS)
            if options.dry_run:
                return ScrubResult(src=src, dst=dst, status=ScrubStatus.DRY_RUN, message="copy unknown")

            with TempPath(dst) as tmp:
                copy_bytes(src, tmp)
                atomic_replace(tmp, dst)

            preserve_stat(src, dst, preserve_times=options.preserve_times, preserve_perms=options.preserve_perms)
            removed = strip_xattrs(dst) if options.strip_xattrs else ()
            return ScrubResult(
                src=src,
                dst=dst,
                status=ScrubStatus.COPIED_UNKNOWN,
                removed_xattrs=removed,
                message="copied without scrubbing (unsupported type)",
            )

        return ScrubResult(src=src, dst=dst, status=ScrubStatus.SKIPPED_UNSUPPORTED)

    # We have a scrubber.
    if dst is None:
        raise ValueError("dst is required")

    if (not options.in_place) and dst.exists() and not options.overwrite:
        return ScrubResult(src=src, dst=dst, status=ScrubStatus.SKIPPED_EXISTS, scrubber=scrubber.name)

    if options.dry_run:
        return ScrubResult(src=src, dst=dst, status=ScrubStatus.DRY_RUN, scrubber=scrubber.name)

    src_stat = src.stat()

    try:
        if options.in_place:
            # Optional backup.
            if options.backup_suffix:
                backup = src.with_name(src.name + options.backup_suffix)
                if backup.exists() and not options.overwrite:
                    return ScrubResult(
                        src=src,
                        dst=dst,
                        status=ScrubStatus.ERROR,
                        scrubber=scrubber.name,
                        message=f"backup exists: {backup}",
                    )
                copy_bytes(src, backup)

            with TempPath(src) as tmp:
                scrubber.scrub(src, tmp, options=scrubber_options)
                atomic_replace(tmp, src)

            # Restore mode/times if requested.
            if options.preserve_perms:
                os.chmod(src, src_stat.st_mode)
            if options.preserve_times:
                os.utime(src, (src_stat.st_atime, src_stat.st_mtime))

            removed = strip_xattrs(src) if options.strip_xattrs else ()
            return ScrubResult(src=src, dst=src, status=ScrubStatus.SCRUBBED, scrubber=scrubber.name, removed_xattrs=removed)

        # Copy mode
        with TempPath(dst) as tmp:
            scrubber.scrub(src, tmp, options=scrubber_options)
            atomic_replace(tmp, dst)

        preserve_stat(src, dst, preserve_times=options.preserve_times, preserve_perms=options.preserve_perms)
        removed = strip_xattrs(dst) if options.strip_xattrs else ()
        return ScrubResult(src=src, dst=dst, status=ScrubStatus.SCRUBBED, scrubber=scrubber.name, removed_xattrs=removed)

    except Exception as e:  # noqa: BLE001
        return ScrubResult(
            src=src,
            dst=dst,
            status=ScrubStatus.ERROR,
            scrubber=getattr(scrubber, "name", None),
            message=str(e),
        )
