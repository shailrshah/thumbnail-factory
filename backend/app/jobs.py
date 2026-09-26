import json
import time
from datetime import UTC, datetime

from redis import Redis

RECENT_KEY = "jobs:recent"
RECENT_MAX = 500

_FIELDS = (
    "id",
    "status",
    "filename",
    "content_type",
    "created_at",
    "started_at",
    "finished_at",
    "worker",
    "error",
)


def _key(job_id: str) -> str:
    return f"job:{job_id}"


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def create(r: Redis, job_id: str, filename: str, content_type: str) -> dict:
    fields = {
        "id": job_id,
        "status": "queued",
        "filename": filename,
        "content_type": content_type,
        "created_at": now_iso(),
        "thumbnails": "[]",
    }
    with r.pipeline() as p:
        p.hset(_key(job_id), mapping=fields)
        p.zadd(RECENT_KEY, {job_id: time.time()})
        p.zremrangebyrank(RECENT_KEY, 0, -RECENT_MAX - 1)
        p.execute()
    return get(r, job_id)


def update(r: Redis, job_id: str, **fields) -> None:
    if "thumbnails" in fields:
        fields["thumbnails"] = json.dumps(fields["thumbnails"])
    r.hset(_key(job_id), mapping=fields)


def get(r: Redis, job_id: str) -> dict | None:
    raw = r.hgetall(_key(job_id))
    return _decode(raw) if raw else None


def list_recent(r: Redis, limit: int = 50) -> list[dict]:
    ids = r.zrevrange(RECENT_KEY, 0, limit - 1)
    with r.pipeline() as p:
        for job_id in ids:
            p.hgetall(_key(job_id))
        rows = p.execute()
    return [_decode(row) for row in rows if row]


def _decode(raw: dict) -> dict:
    job = {f: raw.get(f) or None for f in _FIELDS}
    job["thumbnails"] = json.loads(raw.get("thumbnails") or "[]")
    return job
