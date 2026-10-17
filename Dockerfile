FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy dependency files and install
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY app ./app

# uv instala en /app/.venv; sin esto "uvicorn" a secas no existe (railway.json lo invoca asi).
ENV PATH="/app/.venv/bin:$PATH"

# Railway inyecta el puerto en $PORT
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
