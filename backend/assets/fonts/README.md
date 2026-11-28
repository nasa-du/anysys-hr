# Static Noto Sans SC for payroll rendering

`NotoSansSC-Regular.ttf` and `NotoSansSC-Bold.ttf` are static TrueType
instances generated from the upstream variable font and vendored so PDF
rendering is offline, version-pinned, and reproducible. `OFL.txt` is the
upstream SIL Open Font License 1.1.

## Upstream

- Repository: `google/fonts`
- Commit: `2894aab31764f10f29c421bdfd2340d3b382d384` (2022-12-09)
- Path: `ofl/notosanssc/NotoSansSC[wght].ttf`
- License path: `ofl/notosanssc/OFL.txt`
- Variable font SHA-256:
  `a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`

## Regenerate

```bash
uv run fonttools varLib.instancer --update-name-table --static \
  -o backend/assets/fonts/NotoSansSC-Regular.ttf \
  'NotoSansSC[wght].ttf' wght=400
uv run fonttools varLib.instancer --update-name-table --static \
  -o backend/assets/fonts/NotoSansSC-Bold.ttf \
  'NotoSansSC[wght].ttf' wght=700
```

Generated with fontTools 4.69.1. The family name stays `Noto Sans SC` with
subfamily `Regular` / `Bold`; WeasyPrint embeds only used glyph subsets and
never sets `full_fonts=True`.

## Checksums

```text
b89e33c2d907845af77514579a355b128d4c526b12c424391e890ca9abb1d22d  NotoSansSC-Bold.ttf
cd7f6bc777318957e6957ce156d03bdf3b040344d3c14821d4cd112f0ca9acdb  NotoSansSC-Regular.ttf
1c05c68c34f9708415aada51f17e1b0092d2cea709bf4a94cd38114f9e73d7d9  OFL.txt
```
