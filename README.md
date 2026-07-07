# Instagram Article Automation

Backend v1 untuk memantau post Instagram sekolah, mengubah post menjadi draft artikel,
menjalankan SEO + compliance check, lalu mengirim draft ke admin untuk direview sebelum
dipublikasikan.

Prinsip utama sistem:

- Tidak ada artikel yang dipublish tanpa approval admin.
- Semua boundary I/O divalidasi dengan Pydantic/SQLModel.
- Celery task harus idempotent dan tidak membuat duplikat post/artikel.
- Semua agent run dicatat di `agent_runs`.
- Semua endpoint `/admin/*` wajib memakai API key.

## Stack

- Python 3.13
- FastAPI
- SQLModel + SQLAlchemy
- Alembic
- SQLite v1, dengan WAL
- Celery + Redis
- Pydantic v2
- Ruff, mypy, pytest

## Quick Start Dengan Docker

1. Buat file env:

```bash
cp .env.example .env
```

2. Ubah minimal:

```env
ADMIN_API_KEY=change-this
```

3. Jalankan stack:

```bash
docker compose up --build
```

Service yang berjalan:

- API: `http://localhost:8000`
- Redis: `localhost:6379`
- Celery worker
- Celery beat
- SQLite volume: `sqlite-data`

Container API menjalankan migration otomatis sebelum FastAPI start:

```bash
uv run alembic upgrade head
```

Docker memakai virtualenv internal di `/opt/venv`. Jangan bind-mount atau copy `.venv`
host ke container, karena permission dan symlink Python host/container berbeda.

## Quick Start Lokal

1. Install dependency:

```bash
uv sync
```

2. Buat `.env`:

```bash
cp .env.example .env
```

Untuk local non-Docker, gunakan Redis lokal:

```env
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./data/ig_automation.db
```

Di Docker Compose, `REDIS_URL` otomatis di-override menjadi `redis://redis:6379/0`
karena hostname `redis` hanya valid di network Compose.

3. Apply migration:

```bash
uv run alembic upgrade head
```

4. Jalankan API:

```bash
uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
```

5. Jalankan worker:

```bash
uv run celery -A app.modules.tasks.celery_app.celery_app worker --loglevel=INFO --concurrency=1
```

6. Jalankan beat:

```bash
uv run celery -A app.modules.tasks.beat_schedule.celery_app beat --loglevel=INFO
```

Shortcut Makefile:

```bash
make dev
make worker
make beat
make docker-up
make docker-worker
```

## Environment Variables

| Variable | Fungsi |
|---|---|
| `DATABASE_URL` | URL database SQLAlchemy. Default SQLite. |
| `REDIS_URL` | Broker/backend Celery dan Redis health check. |
| `ADMIN_API_KEY` | Secret untuk header `X-Admin-API-Key`. |
| `INSTAGRAM_ACCESS_TOKEN` | Token Instagram Graph API untuk mode real. |
| `INSTAGRAM_ACCOUNT_ID` | ID akun Instagram yang dipantau. |
| `INSTAGRAM_LIMIT` | Jumlah post yang di-fetch per sync. |
| `USE_FAKE_INSTAGRAM` | Set `true` hanya untuk local demo tanpa credential. Default `false`. |
| `TELEGRAM_BOT_TOKEN` | Token Telegram Bot. Jika kosong, notification adapter mode mock. |
| `TELEGRAM_ADMIN_CHAT_ID` | Chat ID admin penerima notifikasi. |
| `OPENAI_API_KEY` | API key LLM provider. |
| `OPENAI_API_BASE` | Base URL LLM gateway/OpenAI-compatible endpoint. |
| `MODEL` | Model LLM yang dipakai adapter. |
| `PUBLISH_ADAPTER` | `mock` untuk v1. Adapter lain belum diaktifkan. |
| `PUBLIC_BASE_URL` | Base URL untuk link review/publish mock. |
| `WORKER_CONCURRENCY` | Concurrency worker. V1 disarankan `1` sampai `2`. |
| `TASK_MAX_RETRIES` | Batas retry task gagal. |

## Admin API

Semua request `/admin/*` wajib membawa header:

```bash
X-Admin-API-Key: <ADMIN_API_KEY>
```

Endpoint utama:

```text
POST /admin/sync-instagram
POST /admin/sync-instagram/task
GET  /admin/instagram-posts
GET  /admin/articles/drafts
GET  /admin/articles/drafts/{id}
POST /admin/articles/drafts/{id}/approve
POST /admin/articles/drafts/{id}/reject
POST /admin/articles/drafts/{id}/revise
POST /admin/articles/drafts/{id}/edit
POST /admin/articles/drafts/{id}/publish
```

Trigger sync manual:

```bash
curl -X POST http://localhost:8000/admin/sync-instagram \
  -H "X-Admin-API-Key: change-this"
```

List draft:

```bash
curl http://localhost:8000/admin/articles/drafts \
  -H "X-Admin-API-Key: change-this"
```

Approve draft:

```bash
curl -X POST http://localhost:8000/admin/articles/drafts/1/approve \
  -H "X-Admin-API-Key: change-this"
```

Publish draft yang sudah approved:

```bash
curl -X POST http://localhost:8000/admin/articles/drafts/1/publish \
  -H "X-Admin-API-Key: change-this"
```

## Observability

```text
GET /health
GET /worker/status
```

`/health` mengecek database dan Redis.

`/worker/status` mengecek Redis, ping Celery worker, jumlah draft gagal, dan notifikasi pending.

## Workflow

Flow v1:

```text
instagram_collected
  -> asset_downloaded
  -> draft_generating
  -> draft_generated
  -> waiting_review
  -> approved
  -> publishing
  -> published
```

Cabang review:

```text
waiting_review -> rejected
waiting_review -> needs_revision -> draft_generating
```

Status gagal:

```text
fetch_failed
generation_failed
notification_failed
publish_failed
```

`retry_failed_jobs` berjalan berkala setiap 15 menit dan hanya me-retry row existing.
Retry tidak boleh membuat `instagram_posts` atau `article_drafts` baru untuk item yang sama.

## Database & Migration

Apply migration:

```bash
uv run alembic upgrade head
```

Buat migration baru:

```bash
uv run alembic revision --autogenerate -m "deskripsi singkat"
```

Rollback satu revision:

```bash
uv run alembic downgrade -1
```

Jangan ubah schema database tanpa migration.

## Testing & Quality Gates

Jalankan sebelum PR:

```bash
uv run pytest
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
```

Test saat ini mencakup:

- Manual sync membuat post baru dan draft reviewable.
- Duplicate `instagram_media_id` tidak diproses ulang.
- Approve lalu publish mencatat review dan publish log.
- Publish sebelum approval ditolak.
- `/admin/*` tanpa API key ditolak.
- Output LLM invalid menjadi `generation_failed`.
- Notification failure menjadi `notification_failed`.
- Retry memakai row ID existing dan menghormati `max_retries`.

## Mode Mock v1

Untuk memudahkan development tanpa credential eksternal, fake Instagram harus diaktifkan
eksplisit:

```env
USE_FAKE_INSTAGRAM=true
```

- Jika `USE_FAKE_INSTAGRAM=true`, sync memakai fake Instagram post.
- Jika `USE_FAKE_INSTAGRAM=false`, credential Instagram wajib valid.
- Jika `TELEGRAM_BOT_TOKEN` kosong, notifikasi dianggap terkirim dalam mode mock.
- `PUBLISH_ADAPTER=mock` menghasilkan URL publish lokal tanpa memanggil CMS eksternal.

Mode ini cocok untuk regression test dan local smoke test. Integrasi production tetap perlu
credential Instagram, Telegram, dan adapter publish target website yang sebenarnya.

## Troubleshooting

Jika muncul error seperti ini setelah menjalankan Docker:

```text
warning: Ignoring existing virtual environment linked to non-existent Python interpreter
error: failed to remove directory `.venv/include`: Permission denied
```

Artinya `.venv` host pernah tersentuh container dan ownership/isi virtualenv tidak cocok
dengan Python lokal. Fix config di repo ini mencegah hal itu terulang dengan memakai
`UV_PROJECT_ENVIRONMENT=/opt/venv` di container dan `.dockerignore` untuk exclude `.venv`.

Untuk memperbaiki `.venv` host yang sudah rusak, restore ownership lalu recreate env:

```bash
sudo chown -R "$USER":"$USER" .venv
rm -rf .venv
uv sync
```

Jika tidak ingin menghapus `.venv`, cukup jalankan `sudo chown -R "$USER":"$USER" .venv`
lalu ulangi `uv run ...`.

## Struktur Penting

```text
app/api/v1/              FastAPI routers
app/core/settings.py     Environment settings
app/models/              SQLModel tables dan enum
app/modules/adapters/    Boundary eksternal: IG, LLM, Telegram, publish
app/modules/services/    Business logic dan state transition
app/modules/tasks/       Celery task
app/modules/schemas/     Pydantic schemas
alembic/                 Migration
tests/                   Regression tests
```

## Definition of Done

Sebuah perubahan dianggap selesai jika:

- State machine tetap sesuai `PLANS.md`.
- Tidak ada publish tanpa approval admin.
- Semua endpoint admin tetap protected.
- Task baru idempotent dan punya test happy path + edge case.
- LLM/tool output divalidasi schema.
- Agent call tercatat di `agent_runs`.
- Migration disertakan untuk perubahan schema.
- `pytest`, coverage, `ruff`, dan `mypy` hijau.
