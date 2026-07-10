# Site Analysis API

A production-grade Django REST Framework platform bundling several website-analysis
tools behind one versioned API, with JWT + API-key auth and a credit/quota system.

| Tool | What it does | Upstream |
|---|---|---|
| **Google Speed** | Performance / accessibility / best-practices / SEO scores + Core Web Vitals | Google PageSpeed Insights |
| **GTmetrix** | Grade, performance & structure scores, load timings, page weight | GTmetrix API 2.0 (paid credits) |
| **Speed Test** | Combined PageSpeed **+** GTmetrix in one request | both of the above |
| **Accessibility** | WCAG errors/alerts/features/structure/contrast + issue breakdown | WAVE API (paid per request) |

## Architecture

```
Client → Nginx → Django REST API (Gunicorn)
                     ├── PostgreSQL   (primary datastore)
                     ├── Redis        (cache + Celery broker)
                     └── Celery worker → Google PageSpeed / GTmetrix APIs
WAVE audits run synchronously (one request returns the full report).
```

Every app follows the same layered pattern:
`models/ → services/ → selectors/ → serializers/ → views/ → tasks.py → tests/`
Views are thin (validate → call service/selector → serialize); services hold all
write/business logic (keyword-only args, transactional); selectors hold reads.

### Apps
| App | Responsibility |
|---|---|
| `apps/common` | `BaseModel` (UUID PK, timestamps, soft delete), global exception handler, pagination, middleware (correlation id + request logging), throttling, validators |
| `apps/users` | JWT auth, email verification, password reset/change, `me`; **username + role**, **per-user API keys** (`X-API-Key`), admin user listing |
| `apps/analysis` | Google PageSpeed (`/google_speed/`) — async via Celery |
| `apps/gtmetrix` | GTmetrix (`/gtmetrix/`) — async, polled, credit-aware retry |
| `apps/speed_test` | Combined PageSpeed + GTmetrix (`/speed_test/`) |
| `apps/audits` | WAVE accessibility audits (`/audits/`) — synchronous |
| `apps/credits` | Credit balance, ledger, purchase; gates paid audits for authenticated users |

## Endpoints — `/api/v1/`

### Auth — `/auth/`
`register/` · `login/` · `logout/` · `token/refresh/` · `password/change/` ·
`password/reset/` · `password/reset/confirm/` · `email/verify/` ·
`email/verify/resend/` · `me/` (GET/PATCH) · `me/api-key/` (GET get / POST rotate) ·
`admin/users/` (GET, admin-only — users + their API keys)

### Google Speed — `/google_speed/`
| Endpoint | Method | Auth |
|---|---|---|
| `analyze/` | POST | public |
| `reports/` · `reports/{id}/` | GET / DELETE | public (detail by id) |
| `history/` | GET | auth |

### GTmetrix — `/gtmetrix/`
`analyze/` (POST) · `reports/` · `reports/{id}/` (GET/DELETE) — all public.

### Speed Test — `/speed_test/`
`analyze/` (POST) · `reports/` · `reports/{id}/` (GET/DELETE) — all public.

### Accessibility (WAVE) — `/audits/`
| Endpoint | Method | Notes |
|---|---|---|
| `run/` | POST | Public. Authenticated → 1 credit; anonymous → no credit. 10/min per user/IP. |
| `` (list) · `{id}/` | GET / DELETE | Detail public by id; list owner-scoped |
| `{id}/issues/` | GET | Filter by `issue_type` |

### Credits — `/credits/` (auth required)
`balance/` (GET) · `purchase/` (POST) · `transactions/` (GET)

### Docs & tooling
- Swagger UI: `/api/docs/` · ReDoc: `/api/redoc/` · schema: `/api/schema/`
- HTML tester (DEBUG only): `/tester/`
- Postman: import `postman/*.json`
- OpenAPI files: `docs/openapi.yaml`, `docs/openapi.json`

## Authentication
- **JWT:** access 15 min, rotating + blacklisted refresh 7 days. `Authorization: Bearer <token>`.
- **API key:** every user gets one; send `X-API-Key: sk_...` instead of a JWT.
- **Roles:** `admin` / `manager` / `user`; superusers are `admin`.
- Most analysis endpoints are **public** (`AllowAny`); account, credits, admin, and
  history endpoints require auth. A bad/expired token still yields 401 even on a
  public endpoint (auth runs before permissions) — omit the header to call anonymously.

## Async processing (Celery)
PageSpeed / GTmetrix / Speed Test submissions return `202 pending` and are
processed by a Celery worker, then polled via `…/reports/{id}/`. Tasks retry
transient errors up to 3× and stop; fatal errors (e.g. out-of-credits) stop
immediately. Set `CELERY_TASK_ALWAYS_EAGER=True` to run inline without a worker
(blocks the request — local testing only). WAVE audits are synchronous.

## Quick start (local, no Docker)

```bash
python -m venv .venv && .venv\Scripts\activate     # Windows
pip install -r requirements.txt
cp .env.example .env        # set SECRET_KEY + the API keys you have

# SQLite (default in .env.example) needs no DB server:
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver          # http://localhost:8000/api/docs/  ·  /tester/
```

For the async tools, in separate terminals (and set `CELERY_TASK_ALWAYS_EAGER=False`):
```bash
redis-server                                   # or docker run -p 6379:6379 redis:7-alpine
celery -A config worker -l info --pool=solo    # --pool=solo is required on Windows
```

## Docker
```bash
cp .env.example .env
make up      # api + postgres + redis + mailpit + celery worker
```
Production image + full stack (api, db, redis, celery_worker, celery_beat) in
`docker/Dockerfile` + `docker-compose.yml`.

## Configuration (`.env`, via python-decouple)
| Var | Purpose |
|---|---|
| `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` | Django core |
| `DB_ENGINE`, `DB_*` | Database (SQLite or PostgreSQL) |
| `REDIS_URL`, `CELERY_*`, `CELERY_TASK_ALWAYS_EAGER` | Redis / Celery |
| `GOOGLE_PAGESPEED_API_KEY` | Google PageSpeed |
| `GTMETRIX_API_KEY`, `GTMETRIX_POLL_*` | GTmetrix (paid) |
| `WAVE_API_KEY`, `WAVE_REPORT_TYPE` | WAVE accessibility (paid) |
| `EMAIL_*`, `FRONTEND_BASE_URL`, `CORS_ALLOWED_ORIGINS` | Email / links / CORS |

Settings are split per environment: `config/settings/{base,development,production,test}.py`.

## Credits (for WAVE audits)
WAVE bills per request, so authenticated audits consume internal credits:
```
POST /api/v1/credits/purchase/   { "amount": 100 }      # simulated top-up
POST /api/v1/audits/run/         { "url": "https://…" } # 1 credit (authed) / free (anon)
GET  /api/v1/credits/balance/
```
Credit ops are atomic with `select_for_update()` so concurrent audits never
double-spend or go negative.

## Testing
```bash
make test                       # pytest (config.settings.test)
make cov                        # with coverage
# against SQLite without Postgres:
DB_ENGINE=django.db.backends.sqlite3 DB_NAME=:memory: pytest
```
Tests mock every external API (Google/GTmetrix/WAVE are never called), run Celery
eagerly, and cover services, selectors, views, tasks, and credit edge cases.

## Make targets
`make help` lists all: `run`, `migrate`, `migrations`, `superuser`, `test`, `cov`,
`lint`, `fmt`, `typecheck`, `celery`, `beat`, `up`, `down`, `logs`.

## Security highlights
- JWT (rotating + blacklisted refresh) and `X-API-Key` auth; role-based admin access.
- Password complexity validator; mandatory email verification for gated resources.
- Per-user throttles (analysis 5/min, audits 10/min) + auth-endpoint throttling.
- Credit gating with row-locked atomic deductions.
- UUID primary keys everywhere; soft delete by default; SSRF guard on target URLs.
- Production security headers (HSTS, SSL redirect, secure cookies, nosniff, frame-deny).

## ⚠️ Paid APIs
- **GTmetrix** (`/gtmetrix/`, `/speed_test/`) and **WAVE** (`/audits/`) cost real money
  per call. `/audits/run/` and the GTmetrix endpoints are currently **public** — anyone
  with the URL can spend your balance (per-IP/user throttle is the only limit). Re-add
  `IsAuthenticated` on those submit views if you want to protect spend.
