from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageOps

from .base import ScrubOptions, Scrubber


class ImageScrubber(Scrubber):
    name = "images"

    _exts = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self._exts

    def scrub(self, src: Path, dst: Path, *, options: ScrubOptions) -> None:  # noqa: ARG002
        ext = src.suffix.lower()

        with Image.open(src) as img:
            # If we remove EXIF, we should also bake in its orientation.
            img = ImageOps.exif_transpose(img)

            # Drop any sidecar info dict to avoid accidental propagation.
            img_clean = img.copy()
            img_clean.info = {}

            save_kwargs: dict[str, object] = {}
            if ext in {".jpg", ".jpeg"}:
                if img_clean.mode in {"RGBA", "LA"}:
                    img_clean = img_clean.convert("RGB")
                save_kwargs.update({"format": "JPEG", "quality": 95, "optimize": True})
            elif ext == ".png":
                save_kwargs.update({"format": "PNG", "optimize": True})
            elif ext in {".tif", ".tiff"}:
                save_kwargs.update({"format": "TIFF"})
            elif ext == ".webp":
                save_kwargs.update({"format": "WEBP", "quality": 95, "method": 6})
            else:
                # Shouldn't happen due to can_handle, but keep it safe.
                save_kwargs.update({"format": img_clean.format or "PNG"})

            img_clean.save(dst, **save_kwargs)
