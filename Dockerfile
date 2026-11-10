# backend image: python + our code, runs the migrations then the api
FROM python:3.12-slim

# uv binary from its official image
COPY --from=ghcr.io/astral-sh/uv:0.12.21 /uv /bin/uv

# no .pyc files, print logs straight away, use the python of this image
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy
WORKDIR /app

# packages first, so docker can reuse this layer when only the code changes
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-cache
ENV PATH="/app/.venv/bin:$PATH"

COPY alembic.ini .
COPY backend backend
COPY scripts scripts
COPY data data

# don't run as root inside the container
RUN useradd --create-home app
USER app

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
