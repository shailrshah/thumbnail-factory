import subprocess
import time
from pathlib import Path

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from rq import Worker

from app import connections, worker_health


def _register_worker() -> Worker:
    worker = Worker(["thumbnails"], connection=connections.rq_redis())
    worker.register_birth()
    return worker


def test_healthy_with_live_registered_worker():
    _register_worker()
    assert worker_health.is_healthy()


def test_unhealthy_with_no_registered_worker():
    assert not worker_health.is_healthy()


def test_unhealthy_when_worker_process_is_gone():
    worker = _register_worker()
    connections.rq_redis().hset(worker.key, "pid", 999_999_999)
    assert not worker_health.is_healthy()


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="zombie detection reads Linux /proc")
def test_unhealthy_when_worker_process_is_a_zombie():
    child = subprocess.Popen(["true"])
    time.sleep(0.2)  # exited but not yet reaped (no wait()), so it's a zombie
    worker = _register_worker()
    connections.rq_redis().hset(worker.key, "pid", child.pid)
    try:
        assert not worker_health.is_healthy()
    finally:
        child.wait()


def test_unhealthy_when_worker_belongs_to_another_container(monkeypatch):
    _register_worker()
    monkeypatch.setattr(worker_health.socket, "gethostname", lambda: "some-other-container")
    assert not worker_health.is_healthy()


def test_unhealthy_when_redis_unreachable(monkeypatch):
    def down():
        raise RedisConnectionError("down")

    monkeypatch.setattr("app.connections.rq_redis", down)
    assert not worker_health.is_healthy()
