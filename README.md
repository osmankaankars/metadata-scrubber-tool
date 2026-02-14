# Metadata Scrubber Tool

Klasor veya dosya listesi uzerinden calisan, yaygin dosya turlerinden (or: JPG/PNG, PDF, DOCX/XLSX/PPTX) metadata temizleyen bir CLI aracidir.

## Desteklenen Turler (MVP)

- Image: `.jpg/.jpeg`, `.png`, `.tif/.tiff`, `.webp` (EXIF dahil metadata'yi dusurup yeniden yazar; orientation uygulanir)
- PDF: doc info + XMP metadata best-effort temizlenir (dosya yeniden yazilir)
- Office OpenXML: `.docx/.xlsx/.pptx` icindeki `docProps/*` parcalari kaldirilir; zip ic timestamp'ler normalize edilir
- (Opsiyonel) Audio: `.mp3/.flac/.m4a/.mp4/.ogg` (butun tag'ler silinir, `mutagen` ile)

Ek olarak (macOS/Linux): cikti dosyalarindaki extended attributes (xattr) best-effort kaldirilir.

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

Opsiyonel (ses dosyalari icin):

```bash
pip install -e '.[audio]'
```

## Kullanim

Bir klasoru ciktiya scrub'layarak kopyalar (varsayilan):

```bash
metadata-scrubber ./DOSYALARIN_OLDUGU_KLASOR --out ./scrubbed
```

Ornek (bu repodaki `ornekler/` klasoru):

```bash
metadata-scrubber ./ornekler --out ./scrubbed
```

Yerinde (in-place) scrub (riskli):

```bash
metadata-scrubber ./ornek.pdf --in-place --backup-suffix .bak
```

Dry-run:

```bash
metadata-scrubber ./ornekler --out ./scrubbed --dry-run
```

## Notlar

- Varsayilan davranis: orijinal dosyalara dokunmaz, cikti klasorune temizlenmis kopyalar yazar.
- Desteklenmeyen dosya turleri varsayilan olarak atlanir (kopyalanmaz).
- Desteklenmeyen dosyalari da kopyalamak icin: `--copy-unknown`
