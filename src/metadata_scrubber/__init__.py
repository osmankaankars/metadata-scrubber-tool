"""Metadata Scrubber Tool.

Public API is intentionally small; prefer the CLI entrypoint.
"""

from .core import scrub_paths

__all__ = ["scrub_paths"]
