FROM public.ecr.aws/docker/library/python:3.12-alpine

WORKDIR /app

RUN pip install uv

# Dependencies are installed before the source is copied so code edits
# don't invalidate the (slow) dependency layer.
COPY pyproject.toml uv.lock .python-version ./
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-dev --no-install-project

COPY app ./app

ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
