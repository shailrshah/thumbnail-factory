import dataclasses

import fakeredis
import pytest

from app import config


@pytest.fixture
def server():
    return fakeredis.FakeServer()


@pytest.fixture
def r(server):
    return fakeredis.FakeRedis(server=server, decode_responses=True)


@pytest.fixture
def media(tmp_path, monkeypatch):
    patched = dataclasses.replace(config.settings, media_root=tmp_path, worker_delay_seconds=0)
    for module in ("app.config", "app.tasks", "app.connections"):
        monkeypatch.setattr(f"{module}.settings", patched, raising=False)
    patched.originals_dir.mkdir(parents=True)
    return patched


@pytest.fixture(autouse=True)
def fake_connections(server, monkeypatch):
    monkeypatch.setattr(
        "app.connections.app_redis",
        lambda: fakeredis.FakeRedis(server=server, decode_responses=True),
    )
    monkeypatch.setattr("app.connections.rq_redis", lambda: fakeredis.FakeRedis(server=server))
    monkeypatch.setattr(
        "app.tasks.app_redis",
        lambda: fakeredis.FakeRedis(server=server, decode_responses=True),
    )
