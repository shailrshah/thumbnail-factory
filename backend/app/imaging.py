from pathlib import Path

from PIL import Image, ImageOps


def make_thumbnails(src: Path, dest_dir: Path, widths: tuple[int, ...]) -> list[dict]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        # Phone cameras store rotation as an EXIF flag rather than rotating pixels.
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA" if _has_alpha(img) else "RGB")

        results = []
        for width in widths:
            thumb = img.copy()
            # thumbnail() never upscales; the height bound is effectively unlimited
            # so width is the only constraint.
            thumb.thumbnail((width, img.height * width))
            path = dest_dir / f"{width}.webp"
            thumb.save(path, "WEBP", quality=80)
            results.append({"width": width, "path": path})
        return results


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
