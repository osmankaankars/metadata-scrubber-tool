from __future__ import annotations

from PIL import Image

from metadata_scrubber.scrubbers.base import ScrubOptions
from metadata_scrubber.scrubbers.images import ImageScrubber


def test_image_scrub_removes_exif_and_bakes_orientation(tmp_path):
    src = tmp_path / "in.jpg"
    dst = tmp_path / "out.jpg"

    # JPEG is lossy; use a larger image and assert on channel dominance rather
    # than exact pixel values.
    w, h = 120, 40
    img = Image.new("RGB", (w, h), (255, 0, 0))  # red
    for x in range(w // 2, w):
        for y in range(h):
            img.putpixel((x, y), (0, 0, 255))  # blue

    exif = Image.Exif()
    exif[274] = 3  # Orientation: rotate 180

    img.save(src, exif=exif, quality=95, subsampling=0)

    scrubber = ImageScrubber()
    scrubber.scrub(src, dst, options=ScrubOptions())

    with Image.open(dst) as out:
        out_exif = out.getexif()
        assert len(out_exif) == 0

        # Orientation should have been applied (rotate 180), so the left half of
        # the output corresponds to the original right half (blue).
        left = out.getpixel((w // 4, h // 2))
        right = out.getpixel((3 * w // 4, h // 2))

        assert left[2] > left[0] and left[2] > left[1]  # blue-dominant
        assert right[0] > right[1] and right[0] > right[2]  # red-dominant
