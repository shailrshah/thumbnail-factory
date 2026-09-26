FROM public.ecr.aws/docker/library/python:3.12-alpine AS builder

RUN pip install uv

WORKDIR /app
# Dependencies are installed before the source is copied so code edits
# don't invalidate the (slow) dependency layer.
COPY pyproject.toml uv.lock .python-version ./
RUN UV_PYTHON_DOWNLOADS=never UV_PROJECT_ENVIRONMENT=/opt/venv \
    uv sync --frozen --no-dev --no-install-project


FROM public.ecr.aws/docker/library/python:3.12-alpine

# /data is created here, owned by app, because a new named volume copies the ownership of
# the directory it's mounted over; without it the volume would be root-owned and unwritable.
RUN addgroup -S -g 10001 app \
 && adduser -S -D -H -u 10001 -G app app \
 && mkdir /data && chown app:app /data

# Must match the builder's path: venv entry-point scripts hardcode it in their shebangs.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY app ./app

ENV PATH="/opt/venv/bin:$PATH"
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
