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

# Test commands
test-whatsapp:
	docker compose exec api python scripts/test_whatsapp.py

test-whatsapp-baileys:
	uv run python scripts/test_whatsapp_baileys.py

test-whatsapp-groups:
	uv run python scripts/test_whatsapp_groups.py

test-notification:
	docker compose exec api python scripts/test_notification_fallback.py

test-webhook:
	uv run python scripts/test_webhook.py

debug-whatsapp:
	uv run python scripts/debug_whatsapp.py

preview-notification:
	uv run python scripts/preview_notification_template.py

# Ngrok webhook commands
ngrok-url:
	uv run python scripts/get_ngrok_url.py

ngrok-logs:
	docker compose logs -f ngrok

# Frontend commands
fe-dev:
	cd frontend && bun dev -- --host 0.0.0.0

fe-build:
	cd frontend && bun run build

fe-lint:
	cd frontend && bun run lint
