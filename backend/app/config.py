import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    redis_url: str
    media_root: Path
    max_upload_bytes: int
    worker_delay_seconds: float
    thumbnail_widths: tuple[int, ...]

    @property
    def originals_dir(self) -> Path:
        return self.media_root / "originals"

    @property
    def thumbs_dir(self) -> Path:
        return self.media_root / "thumbs"


def load_settings() -> Settings:
    return Settings(
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        media_root=Path(os.environ.get("MEDIA_ROOT", "/data")),
        max_upload_bytes=int(os.environ.get("MAX_UPLOAD_MB", "10")) * 1024 * 1024,
        worker_delay_seconds=float(os.environ.get("WORKER_DELAY_SECONDS", "2")),
        thumbnail_widths=tuple(
            int(w) for w in os.environ.get("THUMBNAIL_WIDTHS", "128,256,512").split(",")
        ),
    )


settings = load_settings()
