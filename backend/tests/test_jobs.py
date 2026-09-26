import fakeredis
import pytest

from app import jobs


@pytest.fixture
def r():
    return fakeredis.FakeRedis(decode_responses=True)


def test_create_returns_queued_job_with_nulls(r):
    job = jobs.create(r, "abc", "cat.jpg", "image/jpeg")

    assert job["id"] == "abc"
    assert job["status"] == "queued"
    assert job["filename"] == "cat.jpg"
    assert job["created_at"].endswith("Z")
    assert job["started_at"] is None
    assert job["worker"] is None
    assert job["error"] is None
    assert job["thumbnails"] == []


def test_get_missing_returns_none(r):
    assert jobs.get(r, "nope") is None


def test_update_round_trips_thumbnails(r):
    jobs.create(r, "abc", "cat.jpg", "image/jpeg")
    thumbs = [{"width": 128, "url": "/media/thumbs/abc/128.webp"}]
    jobs.update(r, "abc", status="done", thumbnails=thumbs)

    job = jobs.get(r, "abc")
    assert job["status"] == "done"
    assert job["thumbnails"] == thumbs


def test_list_recent_is_newest_first_and_limited(r, monkeypatch):
    clock = iter(range(1000, 2000))
    monkeypatch.setattr(jobs.time, "time", lambda: next(clock))
    for i in range(5):
        jobs.create(r, f"j{i}", "x.jpg", "image/jpeg")

    assert [j["id"] for j in jobs.list_recent(r, limit=3)] == ["j4", "j3", "j2"]


def test_recent_index_is_trimmed(r, monkeypatch):
    monkeypatch.setattr(jobs, "RECENT_MAX", 3)
    for i in range(5):
        jobs.create(r, f"j{i}", "x.jpg", "image/jpeg")

    assert r.zcard(jobs.RECENT_KEY) == 3
