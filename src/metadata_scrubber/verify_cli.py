from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .verify import VerifyOptions, VerifyStatus, verify_paths


def main(
    paths: list[Path] = typer.Argument(..., exists=True, readable=True, resolve_path=True),
    json_output: bool = typer.Option(False, "--json", help="Output JSON to stdout"),
    show_values: bool = typer.Option(False, "--show-values", help="Include values (may expose sensitive data)"),
    no_recursive: bool = typer.Option(False, "--no-recursive", help="Do not traverse directories"),
    fail_on_metadata: bool = typer.Option(
        False,
        "--fail-on-metadata",
        help="Exit with a non-zero code if any metadata is found",
    ),
) -> None:
    opts = VerifyOptions(recursive=not no_recursive, show_values=show_values)
    results = verify_paths(paths, opts)

    if json_output:
        payload = [
            {
                "path": str(r.path),
                "status": r.status.value,
                "kind": r.kind,
                "details": r.details,
                "message": r.message,
            }
            for r in results
        ]
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
    else:
        console = Console()

        counts: dict[VerifyStatus, int] = {}
        for r in results:
            counts[r.status] = counts.get(r.status, 0) + 1

        table = Table(title="Metadata Verify Results")
        table.add_column("Status")
        table.add_column("Count", justify="right")
        for st in VerifyStatus:
            if st in counts:
                table.add_row(st.value, str(counts[st]))
        console.print(table)

        findings = [r for r in results if r.status in {VerifyStatus.METADATA_FOUND, VerifyStatus.ERROR}]
        if findings:
            ft = Table(title="Findings (first 200)", show_lines=False)
            ft.add_column("Path")
            ft.add_column("Kind")
            ft.add_column("Status")
            ft.add_column("Summary")
            for r in findings[:200]:
                ft.add_row(str(r.path), str(r.kind or "-"), r.status.value, _summarize(r))
            console.print(ft)

    has_errors = any(r.status == VerifyStatus.ERROR for r in results)
    has_metadata = any(r.status == VerifyStatus.METADATA_FOUND for r in results)

    if has_errors:
        raise typer.Exit(code=2)
    if fail_on_metadata and has_metadata:
        raise typer.Exit(code=1)


def app() -> None:
    typer.run(main)


def _summarize(r) -> str:
    if r.status == VerifyStatus.ERROR:
        return r.message or ""

    if r.kind == "image":
        exif_n = r.details.get("exif_tag_count", 0)
        interesting = r.details.get("interesting_info_keys") or []
        return f"exif_tags={exif_n} interesting_info_keys={len(interesting)}"

    if r.kind == "pdf":
        md_keys = r.details.get("metadata_keys") or []
        pieceinfo = r.details.get("page_pieceinfo_count", 0)
        annots = r.details.get("page_annots_count", 0)
        root_md = bool(r.details.get("has_root_metadata"))
        return f"docinfo_keys={len(md_keys)} root_md={root_md} pieceinfo_pages={pieceinfo} annots_pages={annots}"

    if r.kind == "openxml":
        docprops = r.details.get("docprops_present") or []
        non_norm = r.details.get("non_normalized_zip_timestamps", 0)
        return f"docprops={len(docprops)} non_normalized_zip_timestamps={non_norm}"

    if r.kind == "audio":
        keys = r.details.get("tag_keys") or []
        return f"tag_keys={len(keys)}"

    if r.kind == "video":
        fmt = r.details.get("format_tag_keys") or []
        streams = r.details.get("stream_tag_keys") or {}
        return f"format_tag_keys={len(fmt)} stream_tags={len(streams)}"

    return ""
