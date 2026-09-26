# Measurements

Numbers recorded while working through [tasks.md](tasks.md), for the learning experiments.

## Backend image size (experiment 5)

Measured on linux/arm64 (Apple Silicon); x86_64 sizes will differ slightly.

- **Unpacked**: sum of layer sizes from `docker history`. This is what the image occupies once pulled.
- **Download**: `CONTENT SIZE` from `docker image ls`, the compressed size transferred on push/pull.
- Don't compare `docker image ls` **DISK USAGE** across machines. With the containerd image store it
  counts both the compressed blobs and the unpacked layers (here 104 + 299 ≈ 403 MB).

| Stage | Build | Unpacked | Download | Notes |
|-------|-------|---------:|---------:|-------|
| Milestone 1 (task 1.6) | single-stage, `-slim` (Debian) | 299 MB | 104 MB | See breakdown below |
| Alpine switch | single-stage, `-alpine` | 200 MB | 84 MB | OS layer 115 MB → 9 MB; the leftover `uv` layer is now 82 MB (41%) |
| Task 5.2 (done early) | multi-stage, `-alpine` | 117 MB | 36 MB | `uv` and pip cache stay in the builder stage |

Tried and not adopted:

| Variant | Unpacked | Download | Why not |
|---------|---------:|---------:|---------|
| multi-stage + plain `uvicorn` (no `[standard]` extras) | 98 MB | 29 MB | Optional; kept the extras for now |
| multi-stage + `RUN rm -rf` pip in the final stage | 117 MB | 36 MB | **No effect.** pip lives in a base-image layer; a later `rm` only adds a whiteout layer. Layers are additive, which is why multi-stage works and deleting doesn't. |

### Milestone 1 breakdown (`-slim`)

| Layer | Size | Needed at runtime? |
|-------|-----:|--------------------|
| Debian trixie base (`python:3.12-slim`) | 115 MB | Partly |
| Python 3.12 | 45 MB | Yes |
| `pip install uv`: uv binary 42 MB, pip cache 20 MB, rest | 75 MB | No, only used at build time |
| `.venv` (largest: uvloop 16 MB, Pillow + libs 22 MB, pydantic-core 4 MB) | 64 MB | Mostly; uvloop and httptools are optional `uvicorn[standard]` extras |
| App code | 37 KB | Yes |

## Non-root and volume ownership (task 5.3)

The backend and worker now run as `app` (UID 10001). Findings:

| Scenario | `/data` owner | Writes |
|----------|---------------|--------|
| Existing volume created while the image ran as root | `0:0` (unchanged) | **Fail**: `PermissionError: [Errno 13]` on upload |
| Fresh volume, image pre-creates `/data` owned by `app` | `10001:10001` | OK |
| Fresh volume, image does **not** pre-create `/data` | `0:0` | **Fail**: `mkdir: can't create directory` |

Docker copies the mount point's ownership (and contents) from the image into a named volume only when
the volume is new and empty. It never changes ownership of an existing volume. Switching an existing
deployment to non-root therefore needs either a fresh volume (`docker compose down -v`, which loses data)
or a one-off `chown -R 10001:10001` on the volume.

Other services: the gateway and frontend already run as `nginx` (UID 101). `docker compose exec redis`
opens a root shell, but `redis-server` itself runs as `redis`, because the image's entrypoint drops
privileges.
