# Measurements

Numbers recorded while working through [tasks.md](tasks.md), for the learning experiments.

## Backend image size (experiment 5)

Measured with `docker image ls` on linux/arm64 (Apple Silicon); x86_64 sizes will differ slightly.

| Stage | Build | Disk usage | Content size | Notes |
|-------|-------|-----------:|-------------:|-------|
| Milestone 1 (task 1.6) | single-stage | 403 MB | 104 MB | `uv` installed via pip and left in the image; runs as root |
| Milestone 5 (task 5.2) | multi-stage | _tbd_ | _tbd_ | |
