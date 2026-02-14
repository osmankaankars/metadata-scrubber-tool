from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .core import RunOptions, scrub_paths
from .models import ScrubStatus


def main(
    paths: list[Path] = typer.Argument(..., exists=True, readable=True, resolve_path=True),
    out: Path | None = typer.Option(
        None,
        "--out",
        help="Output directory (copy mode). Default: ./scrubbed",
    ),
    in_place: bool = typer.Option(False, "--in-place", help="Modify files in place"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would happen"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite existing output files"),
    copy_unknown: bool = typer.Option(
        False,
        "--copy-unknown",
        help="Copy unsupported file types as-is (no scrubbing)",
    ),
    no_recursive: bool = typer.Option(False, "--no-recursive", help="Do not traverse directories"),
    preserve_times: bool = typer.Option(True, "--preserve-times/--no-preserve-times"),
    preserve_perms: bool = typer.Option(True, "--preserve-perms/--no-preserve-perms"),
    strip_xattrs: bool = typer.Option(True, "--strip-xattrs/--no-strip-xattrs"),
    normalize_zip_timestamps: bool = typer.Option(
        True,
        "--normalize-zip-timestamps/--no-normalize-zip-timestamps",
        help="Normalize timestamps inside Office (OpenXML) zip packages",
    ),
    backup_suffix: str = typer.Option(
        ".bak",
        "--backup-suffix",
        help="Backup suffix for in-place mode (empty string disables backups)",
    ),
) -> None:
    console = Console()

    if in_place and out is not None:
        raise typer.BadParameter("--out cannot be used with --in-place")

    if not in_place and out is None:
        out = Path("scrubbed")

    opts = RunOptions(
        out_dir=out,
        in_place=in_place,
        dry_run=dry_run,
        overwrite=overwrite,
        copy_unknown=copy_unknown,
        recursive=not no_recursive,
        preserve_times=preserve_times,
        preserve_perms=preserve_perms,
        strip_xattrs=strip_xattrs,
        normalize_zip_timestamps=normalize_zip_timestamps,
        backup_suffix=backup_suffix,
    )

    results = scrub_paths(paths, opts)

    counts: dict[ScrubStatus, int] = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    table = Table(title="Metadata Scrubber Results")
    table.add_column("Status")
    table.add_column("Count", justify="right")
    for st in ScrubStatus:
        if st in counts:
            table.add_row(st.value, str(counts[st]))

    console.print(table)

    errors = [r for r in results if r.status == ScrubStatus.ERROR]
    if errors:
        err_table = Table(title="Errors", show_lines=False)
        err_table.add_column("Source")
        err_table.add_column("Scrubber")
        err_table.add_column("Message")
        for r in errors[:50]:
            err_table.add_row(str(r.src), str(r.scrubber or "-"), str(r.message or ""))
        console.print(err_table)
        raise typer.Exit(code=1)


def app() -> None:
    """Console script entrypoint."""

    typer.run(main)


if __name__ == "__main__":
    app()
