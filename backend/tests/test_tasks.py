import pytest
from PIL import Image, UnidentifiedImageError

from app import jobs, tasks


def test_success_marks_done_with_thumbnail_urls(r, media):
    jobs.create(r, "abc", "cat.jpg", "image/jpeg")
    Image.new("RGB", (600, 300)).save(media.originals_dir / "abc.jpg")

    tasks.make_thumbnails("abc")

    job = jobs.get(r, "abc")
    assert job["status"] == "done"
    assert job["worker"]
    assert job["started_at"] and job["finished_at"]
    assert job["thumbnails"] == [
        {"width": w, "url": f"/media/thumbs/abc/{w}.webp"} for w in (128, 256, 512)
    ]
    assert (media.thumbs_dir / "abc" / "256.webp").exists()


def test_corrupt_image_marks_failed_and_reraises(r, media):
    jobs.create(r, "bad", "bad.jpg", "image/jpeg")
    (media.originals_dir / "bad.jpg").write_bytes(b"not an image")

    with pytest.raises(UnidentifiedImageError):
        tasks.make_thumbnails("bad")

    job = jobs.get(r, "bad")
    assert job["status"] == "failed"
    assert job["error"]
