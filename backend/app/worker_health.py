"""Container healthcheck for the RQ worker: `python -m app.worker_health`.

Healthy when this container has a worker registered in Redis whose process is still alive. The PID
check matters in dev mode, where watchfiles is PID 1 and keeps the container "Up" after rq crashes.
Heartbeat age isn't used: an idle worker only refreshes it every ~7 minutes while blocked
on the queue.
"""

import os
import socket
import sys
from pathlib import Path

from rq import Worker

from app import connections


def is_healthy() -> bool:
    hostname = socket.gethostname()
    try:
        workers = Worker.all(connection=connections.rq_redis())
    except Exception:
        return False
    return any(w.hostname == hostname and _alive(w.pid) for w in workers)


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    proc = Path("/proc")
    if proc.is_dir():
        # A crashed rq that watchfiles hasn't reaped yet is a zombie: still in the process
        # table (so kill(pid, 0) succeeds) but dead. /proc exposes the real state.
        try:
            state = (proc / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[0]
        except FileNotFoundError:
            return False
        return state not in ("Z", "X")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


if __name__ == "__main__":
    sys.exit(0 if is_healthy() else 1)
