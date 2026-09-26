import dataclasses
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from redis.exceptions import ConnectionError as RedisConnectionError
from rq import Queue
from rq.job import Job, JobStatus

from app import connections, jobs
from app.main import app


@pytest.fixture
def client(media, monkeypatch):
    monkeypatch.setattr("app.main.settings", media)
    return TestClient(app)


def _jpeg(size=(64, 64)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "blue").save(buf, "JPEG")
    return buf.getvalue()


def _upload(client, data, content_type="image/jpeg", name="cat.jpg"):
    return client.post("/api/jobs", files={"file": (name, data, content_type)})


def test_upload_creates_queued_job_and_enqueues(client, media):
    resp = _upload(client, _jpeg())

    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["filename"] == "cat.jpg"
    assert body["thumbnails"] == []
    assert (media.originals_dir / f"{body['id']}.jpg").exists()

    queue = Queue(connections.QUEUE_NAME, connection=connections.rq_redis())
    assert queue.job_ids == [body["id"]]


def test_rejects_unsupported_type(client):
    resp = _upload(client, b"GIF89a", content_type="image/gif", name="a.gif")
    assert resp.status_code == 400


def test_rejects_oversized_upload(client, media, monkeypatch):
    monkeypatch.setattr("app.main.settings", dataclasses.replace(media, max_upload_bytes=100))
    resp = _upload(client, _jpeg((400, 400)))
    assert resp.status_code == 413


def test_rejects_non_image_bytes_with_image_type(client):
    resp = _upload(client, b"definitely not a jpeg")
    assert resp.status_code == 400


def test_get_unknown_job_is_404(client):
    assert client.get("/api/jobs/nope").status_code == 404


def test_list_jobs_newest_first(client):
    first = _upload(client, _jpeg()).json()["id"]
    second = _upload(client, _jpeg()).json()["id"]

    ids = [j["id"] for j in client.get("/api/jobs").json()["jobs"]]
    assert ids[:2] == [second, first]


def test_processing_job_with_failed_rq_job_reports_worker_lost(client, r):
    job_id = _upload(client, _jpeg()).json()["id"]
    jobs.update(r, job_id, status="processing")
    Job.fetch(job_id, connection=connections.rq_redis()).set_status(JobStatus.FAILED)

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert job["error"] == "worker lost"


def test_processing_job_with_live_rq_job_stays_processing(client, r):
    job_id = _upload(client, _jpeg()).json()["id"]
    jobs.update(r, job_id, status="processing")
    Job.fetch(job_id, connection=connections.rq_redis()).set_status(JobStatus.STARTED)

    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "processing"


def test_health_ok(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_health_503_when_redis_down(client, monkeypatch):
    class Down:
        def ping(self):
            raise RedisConnectionError("down")

    monkeypatch.setattr("app.connections.app_redis", lambda: Down())
    assert client.get("/api/health").status_code == 503
