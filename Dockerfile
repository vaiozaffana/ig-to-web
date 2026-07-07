FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_LINK_MODE=copy
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --frozen

COPY . .

EXPOSE 8000
CMD ["sh", "-c", "uv run python -m app.scripts.ensure_migrations && uv run alembic upgrade head && uv run fastapi run app/main.py --host 0.0.0.0 --port 8000"]
