import socket
import time

from app import jobs
from app.config import settings
from app.connections import app_redis
from app.imaging import make_thumbnails as render


def make_thumbnails(job_id: str) -> None:
    r = app_redis()
    jobs.update(
        r, job_id, status="processing", worker=socket.gethostname(), started_at=jobs.now_iso()
    )
    try:
        time.sleep(settings.worker_delay_seconds)
        src = next(settings.originals_dir.glob(f"{job_id}.*"))
        results = render(src, settings.thumbs_dir / job_id, settings.thumbnail_widths)
        thumbnails = [
            {"width": t["width"], "url": f"/media/thumbs/{job_id}/{t['width']}.webp"}
            for t in results
        ]
        jobs.update(r, job_id, status="done", thumbnails=thumbnails, finished_at=jobs.now_iso())
    except Exception as exc:
        jobs.update(r, job_id, status="failed", error=str(exc), finished_at=jobs.now_iso())
        raise
