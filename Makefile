dev:
	uv run fastapi run app/main.py --host 0.0.0.0 --port 8000

worker:
	uv run celery -A app.modules.tasks.celery_app.celery_app worker --loglevel=INFO --concurrency=1

beat:
	uv run celery -A app.modules.tasks.beat_schedule.celery_app beat --loglevel=INFO

docker-up:
	docker compose up --build

docker-worker:
	docker compose up worker

frontend-dev:
	cd frontend && npm run dev -- --host 0.0.0.0

frontend-build:
	cd frontend && npm run build

frontend-lint:
	cd frontend && npm run lint
