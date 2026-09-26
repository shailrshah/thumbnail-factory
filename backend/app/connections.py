from redis import Redis

from app.config import settings

QUEUE_NAME = "thumbnails"


def app_redis() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def rq_redis() -> Redis:
    # RQ pickles job payloads and breaks on a client that decodes responses to str,
    # so it needs its own connection separate from the job store's.
    return Redis.from_url(settings.redis_url)
