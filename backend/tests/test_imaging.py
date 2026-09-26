from PIL import Image

from app.imaging import make_thumbnails

WIDTHS = (128, 256, 512)


def _save(tmp_path, size, mode="RGB", fmt="JPEG", name="src.jpg", exif=None):
    path = tmp_path / name
    img = Image.new(mode, size, "red" if mode == "RGB" else (255, 0, 0, 128))
    kwargs = {"exif": exif} if exif is not None else {}
    img.save(path, fmt, **kwargs)
    return path


def test_generates_one_webp_per_width(tmp_path):
    src = _save(tmp_path, (1000, 500))
    results = make_thumbnails(src, tmp_path / "out", WIDTHS)

    assert [r["width"] for r in results] == list(WIDTHS)
    for r in results:
        with Image.open(r["path"]) as thumb:
            assert thumb.format == "WEBP"
            assert thumb.size == (r["width"], r["width"] // 2)


def test_never_upscales(tmp_path):
    src = _save(tmp_path, (200, 100))
    results = make_thumbnails(src, tmp_path / "out", WIDTHS)

    sizes = {r["width"]: Image.open(r["path"]).size for r in results}
    assert sizes[128] == (128, 64)
    assert sizes[256] == (200, 100)
    assert sizes[512] == (200, 100)


def test_applies_exif_orientation(tmp_path):
    exif = Image.Exif()
    exif[0x0112] = 6  # Orientation: rotate 90° clockwise for display
    src = _save(tmp_path, (800, 400), exif=exif)
    results = make_thumbnails(src, tmp_path / "out", (128,))

    with Image.open(results[0]["path"]) as thumb:
        assert thumb.size == (128, 256)


def test_preserves_transparency(tmp_path):
    src = _save(tmp_path, (400, 400), mode="RGBA", fmt="PNG", name="src.png")
    results = make_thumbnails(src, tmp_path / "out", (128,))

    with Image.open(results[0]["path"]) as thumb:
        assert thumb.mode == "RGBA"
        assert thumb.getpixel((0, 0))[3] == 128
