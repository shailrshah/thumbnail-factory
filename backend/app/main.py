import io
import uuid

from fastapi import APIRouter, FastAPI, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from redis.exceptions import RedisError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job, JobStatus
from rq.registry import StartedJobRegistry

from app import connections, jobs
from app.config import settings

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}

app = FastAPI(title="Thumbnail Factory")
api = APIRouter(prefix="/api")


@api.post("/jobs", status_code=202)
async def create_job(file: UploadFile) -> dict:
    ext = EXTENSIONS.get(file.content_type or "")
    if ext is None:
        raise HTTPException(400, "Unsupported file type; use JPEG, PNG, or WebP")

    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_bytes // (1024 * 1024)} MB")

    try:
        Image.open(io.BytesIO(data)).verify()
    except Exception as exc:
        raise HTTPException(400, "File is not a valid image") from exc

    job_id = uuid.uuid4().hex
    settings.originals_dir.mkdir(parents=True, exist_ok=True)
    (settings.originals_dir / f"{job_id}.{ext}").write_bytes(data)

    job = jobs.create(connections.app_redis(), job_id, file.filename or "upload", file.content_type)
    Queue(connections.QUEUE_NAME, connection=connections.rq_redis()).enqueue(
        "app.tasks.make_thumbnails", job_id, job_id=job_id
    )
    return job


@api.get("/jobs")
def list_jobs() -> dict:
    return {"jobs": _reconcile(jobs.list_recent(connections.app_redis()))}


@api.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = jobs.get(connections.app_redis(), job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return _reconcile([job])[0]


@api.get("/health")
def health():
    try:
        connections.app_redis().ping()
    except RedisError:
        return JSONResponse({"status": "unhealthy", "redis": "unreachable"}, status_code=503)
    return {"status": "ok"}


def _reconcile(job_list: list[dict]) -> list[dict]:
    """Report jobs whose worker died mid-run as failed.

    A killed worker leaves our record at `processing` forever. RQ only notices once the worker's
    heartbeat expires (~90 s) and a registry cleanup runs, which live workers do just every
    10 minutes, so run the cleanup here whenever we're about to report a processing job.
    """
    processing = [j for j in job_list if j["status"] == "processing"]
    if not processing:
        return job_list

    rq = connections.rq_redis()
    StartedJobRegistry(connections.QUEUE_NAME, connection=rq).cleanup()
    for job in processing:
        try:
            status = Job.fetch(job["id"], connection=rq).get_status()
        except NoSuchJobError:
            status = None
        if status in (None, JobStatus.FAILED, JobStatus.STOPPED, JobStatus.CANCELED):
            job["status"] = "failed"
            job["error"] = "worker lost"
    return job_list


app.include_router(api)
