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

## Setup Pertama Kali

1. Buat file env:

```bash
cp .env.example .env
```

2. Isi minimal secret dan credential di `.env`:

```env
ADMIN_API_KEY=change-this
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
WHATSAPP_ACCESS_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=
WHATSAPP_ADMIN_PHONE=
```

3. Pilih mode run:

- Docker: paling praktis untuk menjalankan API, Redis, worker, dan beat sekaligus.
- Lokal: cocok saat debugging Python/frontend dengan proses terpisah.

## Menjalankan Dengan Docker

Gunakan ini saat membuka project yang sudah pernah disetup.

```bash
docker compose up
```

Jika image belum pernah dibuat atau dependency berubah:

```bash
docker compose up --build
```

Jalankan di background:

```bash
docker compose up -d
```

Cek status service:

```bash
docker compose ps
```

Lihat log:

```bash
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat
```

Restart setelah mengubah `.env`:

```bash
docker compose up -d --no-build --force-recreate api worker beat
```

Matikan stack:

```bash
docker compose down
```

Service Docker:

- API: `http://localhost:8000`
- Redis: internal Compose service `redis:6379`
- Celery worker
- Celery beat
- SQLite volume: `sqlite-data`

Container API menjalankan migration otomatis sebelum FastAPI start:

```bash
uv run alembic upgrade head
```

Docker memakai virtualenv internal di `/opt/venv`. Jangan bind-mount atau copy `.venv`
host ke container, karena permission dan symlink Python host/container berbeda.

## Menjalankan Lokal

Gunakan ini jika ingin menjalankan proses backend secara terpisah di host.

Setup dependency sekali:

```bash
uv sync
```

Untuk local non-Docker, pastikan `.env` memakai Redis lokal:

```env
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./data/ig_automation.db
```

Di Docker Compose, `REDIS_URL` otomatis di-override menjadi `redis://redis:6379/0`
karena hostname `redis` hanya valid di network Compose.

Apply migration setelah pull perubahan schema:

```bash
uv run alembic upgrade head
```

Terminal 1, jalankan Redis. Bisa pakai Docker untuk Redis saja:

```bash
docker compose up -d redis
```

Terminal 2, jalankan API:

```bash
make dev
```

atau:

```bash
uv run fastapi run app/main.py --host 0.0.0.0 --port 8000
```

Terminal 3, jalankan worker:

```bash
make worker
```

Terminal 4, jalankan beat:

```bash
make beat
```

## Menjalankan Frontend

Frontend ada di `frontend/` dan memakai proxy `/api` ke backend `http://127.0.0.1:8000`.

Install dependency frontend sekali:

```bash
cd frontend
bun install
```

Jalankan dev server:

```bash
make fe-dev
```

atau:

```bash
cd frontend
bun dev
```

Default URL frontend: `http://localhost:5173`.

Jika backend berjalan di URL lain, set target proxy saat menjalankan frontend:

```bash
cd frontend
VITE_API_TARGET=http://127.0.0.1:8000 bun dev
```

## Smoke Check Setelah Project Dibuka

Setelah Docker atau local process berjalan, cek:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/worker/status
```

Cek credential Instagram:

```bash
curl http://localhost:8000/admin/integrations/instagram/status \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

Trigger sync manual:

```bash
curl -X POST http://localhost:8000/admin/sync-instagram/task \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

## Setup Webhook WhatsApp (Optional)

**NOTE: Webhook hanya diperlukan jika menggunakan Meta WhatsApp Cloud API. Untuk Baileys (default), webhook tidak diperlukan.**

WhatsApp Business API memerlukan webhook untuk menerima status updates (sent, delivered, read, failed). Setup webhook diperlukan untuk production tapi opsional untuk development.

### Prasyarat

1. **Ngrok Account** (gratis): Signup di https://ngrok.com
2. **Ngrok Authtoken**: Dapatkan dari https://dashboard.ngrok.com/get-started/your-authtoken
3. **Verify Token**: Buat string random (bisa pakai `uuidgen` atau generator lain)

### Setup Steps

1. Tambahkan credentials ke `.env`:

```env
WHATSAPP_VERIFY_TOKEN=your-random-verify-token-here
NGROK_AUTHTOKEN=your-ngrok-authtoken-here
```

2. Start semua services termasuk ngrok:

```bash
docker compose up -d
```

3. Dapatkan public webhook URL:

```bash
make ngrok-url
```

Output akan memberikan URL webhook dan instruksi setup lengkap.

4. Setup di Meta for Developers:

- Buka https://developers.facebook.com/
- Pilih app → WhatsApp → Configuration
- Di bagian "Webhook", klik "Edit"
- Masukkan:
  - **Callback URL**: `https://xxxx.ngrok-free.app/api/webhooks/whatsapp` (dari `make ngrok-url`)
  - **Verify token**: Nilai `WHATSAPP_VERIFY_TOKEN` dari `.env` Anda
- Klik "Verify and Save"
- Subscribe ke field: `messages`

5. Monitor webhook requests:

```bash
# Lihat ngrok web interface
open http://localhost:4040

# Atau lihat logs
make ngrok-logs
```

### Verify Webhook

Test webhook verification secara manual:

```bash
curl "http://localhost:8000/api/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=your-token&hub.challenge=test123"
```

Response harus return `test123` jika token cocok.

## Setup WhatsApp dengan Baileys

Sistem menggunakan **Baileys** (WhatsApp Web API) yang tidak memerlukan Meta Business account atau verifikasi. Anda cukup scan QR code seperti WhatsApp Web.

### Keuntungan Baileys vs Meta Cloud API

| Fitur | Baileys | Meta Cloud API |
|---|---|---|
| Setup | Scan QR code saja | Perlu Meta Business, verifikasi, webhook |
| Biaya | Gratis | Gratis untuk volume rendah |
| Batasan | Rate limit WhatsApp Web | Rate limit official API |
| Test recipients | Bisa kirim ke nomor apa saja | Perlu daftar test recipients |

### Langkah Setup

1. **Start semua services:**

```bash
docker compose up -d
```

2. **Cek status WhatsApp:**

```bash
curl http://localhost:8000/admin/whatsapp/status \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

3. **Jika belum connected, dapatkan QR code:**

```bash
curl http://localhost:8000/admin/whatsapp/qr \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"
```

4. **Scan QR code dengan WhatsApp:**
   - Buka WhatsApp di HP
   - Tap menu (⋮) → **Linked Devices**
   - Tap **Link a Device**
   - Scan QR code yang muncul dari response API di atas

5. **Verify connection & test:**

```bash
# Cek status
curl http://localhost:8000/admin/whatsapp/status \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

# Test kirim pesan (via script)
make test-whatsapp-baileys
```

### Troubleshooting Baileys

**Service tidak bisa diakses:**
```bash
# Cek status service
docker compose ps whatsapp

# Cek logs
docker compose logs whatsapp -f

# Restart jika perlu
docker compose restart whatsapp
```

**QR Code tidak muncul:**
- Tunggu 10-30 detik setelah service start
- Jika masih tidak muncul, restart: `docker compose restart whatsapp`

**Connection lost setelah scan:**
- Baileys akan auto-reconnect
- Session disimpan di volume `whatsapp-auth`
- Tidak perlu scan ulang kecuali logout manual

**Pesan tidak terkirim:**
- Pastikan `WHATSAPP_ADMIN_PHONE` benar di `.env`
- Format yang valid: `+628979755323` atau `628979755323`
- **PENTING**: Nomor pengirim (yang scan QR) harus BERBEDA dari `WHATSAPP_ADMIN_PHONE`
- WhatsApp tidak bisa kirim pesan ke diri sendiri!
- Debug: `uv run python scripts/debug_whatsapp.py`
- Cek logs: `docker compose logs whatsapp worker`

### Mode Notifikasi: Private vs Group

Sistem mendukung 2 mode notifikasi:

**Mode 1: Private Chat (Default)**
- Notifikasi dikirim ke nomor WhatsApp personal
- Set `WHATSAPP_NOTIFICATION_MODE=private` di `.env`
- Gunakan `WHATSAPP_ADMIN_PHONE=628979755323`

**Mode 2: Group Chat**
- Notifikasi dikirim ke group WhatsApp
- Set `WHATSAPP_NOTIFICATION_MODE=group` di `.env`
- Gunakan `WHATSAPP_GROUP_ID=120363XXXXX@g.us`

**Cara Mendapatkan Group ID:**

```bash
# 1. List semua group yang terhubung
curl http://localhost:8000/admin/whatsapp/groups \
  -H "X-Admin-API-Key: <ADMIN_API_KEY>"

# Atau via script
make test-whatsapp-groups

# 2. Salin 'id' group yang diinginkan
# Contoh: 120363298126068720@g.us

# 3. Set di .env
WHATSAPP_GROUP_ID=120363298126068720@g.us
WHATSAPP_NOTIFICATION_MODE=group

# 4. Restart services
docker compose restart api worker beat
```

**Tips:**
- Pastikan akun WhatsApp yang di-scan adalah member dari group target
- Group ID format: `120363XXXXX@g.us`
- Bisa switch mode kapan saja dengan update `.env` dan restart services
- Debug: `uv run python scripts/debug_whatsapp.py`
- Cek logs: `docker compose logs whatsapp worker`

## Setup Webhook WhatsApp (Optional)

**NOTE: Webhook hanya diperlukan jika menggunakan Meta WhatsApp Cloud API. Untuk Baileys (default), webhook tidak diperlukan.**

WhatsApp Business API memerlukan webhook untuk menerima status updates (sent, delivered, read, failed). Setup webhook diperlukan untuk production tapi opsional untuk development.

| Variable | Fungsi |
|---|---|
| `DATABASE_URL` | URL database SQLAlchemy. Default SQLite. |
| `REDIS_URL` | Broker/backend Celery dan Redis health check. |
| `ADMIN_API_KEY` | Secret untuk header `X-Admin-API-Key`. |
| `INSTAGRAM_ACCESS_TOKEN` | Token Instagram Graph API untuk mode real. |
| `INSTAGRAM_ACCOUNT_ID` | ID akun Instagram yang dipantau. |
| `INSTAGRAM_LIMIT` | Jumlah post yang di-fetch per sync. |
| `USE_FAKE_INSTAGRAM` | Set `true` hanya untuk local demo tanpa credential. Default `false`. |
| `WHATSAPP_SERVICE_URL` | URL Baileys WhatsApp service. Default `http://localhost:3001`. Di Docker: `http://whatsapp:3001`. |
| `WHATSAPP_ADMIN_PHONE` | Nomor WhatsApp admin penerima. Format: `+628979755323` atau `628979755323`. |
| `TELEGRAM_BOT_TOKEN` | Token Telegram Bot. Dipakai sebagai fallback jika WhatsApp gagal/tidak dikonfigurasi. |
| `TELEGRAM_ADMIN_CHAT_ID` | Chat ID admin penerima notifikasi fallback Telegram. |
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

## Template Notifikasi

Sistem mengirim notifikasi WhatsApp dengan template yang menarik dan persuasif saat artikel siap direview.

### Format Template

Template menggunakan gaya redaksi berita dengan elemen:
- ✨ Emoji menarik (variasi berdasarkan artikel)
- 📰 Judul artikel yang eye-catching
- 📅 Timestamp posting Instagram
- 👤 Username Instagram author
- 📁 Kategori artikel
- 🎬 Call-to-action yang jelas
- ⚡ Aksi review yang tersedia

### Preview Template

Lihat preview template sebelum deploy:

```bash
make preview-notification
```

Atau manual:

```bash
uv run python scripts/preview_notification_template.py
```

### Contoh Output

```
🎯 *ARTIKEL BARU SIAP TAYANG!* 🎯
━━━━━━━━━━━━━━━━━━━━━━━━

📰 *Kegiatan Ekstrakurikuler Robotik Juara 1 Tingkat Nasional*

━━━━━━━━━━━━━━━━━━━━━━━━
📅 13 July 2026, 14:30 WIB
👤 @smkn1jakarta
📁 Prestasi

🎬 *Konten fresh dari Instagram sudah kami olah jadi artikel menarik!*

Yuk, cek dulu sebelum dipublikasikan:
👉 http://localhost:8000/admin/articles/drafts/1

━━━━━━━━━━━━━━━━━━━━━━━━
⚡ *AKSI CEPAT:*
✅ Approve → Publish
✏️ Edit → Revisi konten
❌ Reject → Buang draft

_Konten berkualitas dimulai dari review yang teliti!_ 🎯
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

### WhatsApp Notification Issues

**Error: "Account not registered" (#133010)**

Nomor penerima WhatsApp belum terdaftar sebagai test recipient atau business belum verified.

Solusi untuk development:
1. Buka [Meta for Developers](https://developers.facebook.com/)
2. Pilih app → WhatsApp → API Setup
3. Di bagian "Send and receive messages", klik "Add phone number"
4. Masukkan nomor tujuan (e.g., `+628979755323`) dan verify via OTP

Untuk production: Business account perlu verified oleh Meta untuk mengirim ke nomor arbitrary.

**Error: "Object with ID 'xxx' does not exist" (code 100, subcode 33)**

Phone Number ID tidak valid atau tidak punya permission.

Solusi:
1. Verify Phone Number ID di WhatsApp → API Setup → "From" section
2. Generate new access token jika expired
3. Pastikan token punya permission: `whatsapp_business_messaging` dan `whatsapp_business_management`

**Test WhatsApp Configuration**

Setelah update `.env`, restart services dan test:

```bash
docker compose restart api worker beat
sleep 5
docker compose exec api python scripts/test_whatsapp.py
```

**Fallback Mechanism**

Sistem otomatis fallback ke Telegram jika WhatsApp gagal. Pastikan `TELEGRAM_BOT_TOKEN` dan `TELEGRAM_ADMIN_CHAT_ID` terkonfigurasi dengan benar untuk backup notification channel.

### Docker & Virtualenv Issues

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
