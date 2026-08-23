# 🎉 Team Engagement Service & Admin Console

> Automated, deterministic birthday and work-anniversary email notifications for growing organizations (100+ employees). Driven by static, reviewed Jinja2 templates, local HRMS data mirroring, and a responsive React Admin Dashboard — with **zero runtime LLM in the send path**.

---

## 📑 Table of Contents
- [Architecture & Data Flow](#-architecture--data-flow)
- [Key Features](#-key-features)
- [Project Layout](#-project-layout)
- [Quick Start with Docker (Recommended)](#-quick-start-with-docker-recommended)
- [Local Development Setup (Without Docker)](#-local-development-setup-without-docker)
  - [Backend Setup (FastAPI)](#1-backend-setup-fastapi)
  - [Frontend Setup (React + Vite)](#2-frontend-dashboard-setup-react--vite)
- [Admin Dashboard Features](#-admin-dashboard-features)
- [Admin API Reference](#-admin-api-reference)
- [Environment Configuration](#-environment-configuration)
- [Idempotency & Reliability Guarantees](#-idempotency--reliability-guarantees)
- [Running Automated Tests](#-running-automated-tests)
- [Production Scaling & Extensions](#-production-scaling--extensions)

---

## 🏗️ Architecture & Data Flow

```
   ┌─────────────────────────────────────────────────────────────┐
   │         HRMS System (Workday / BambooHR / Custom)           │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ (Nightly / On-Demand Sync)
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  EmployeeProfile Table (Local PostgreSQL / SQLite Mirror)   │
   └──────────────────────────────┬──────────────────────────────┘
                                  │ (Daily Cron @ 06:00 Business TZ)
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  1. Scanner (app/services/scanner.py)                       │
   │     • Matches DOB / DOJ with business scan date             │
   │     • Handles leap-year policies & filters 0-yr join day    │
   │     • Idempotent upsert into EventLog (status: pending)     │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                                  ▼
   ┌─────────────────────────────────────────────────────────────┐
   │  2. Renderer (app/services/renderer.py)                     │
   │     • Selects variant (default, 5-year, 10-year)            │
   │     • StrictUndefined Jinja2 auto-escaped rendering         │
   │     • Automatic fallback if milestone template is disabled  │
   │     • Updates EventLog (status: rendered)                   │
   └──────────────────────────────┬──────────────────────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  ▼                               ▼
   ┌──────────────────────────────┐ ┌──────────────────────────────┐
   │ 3. Individual Email Sender   │ │ 4. Team Digest Builder       │
   │    (app/services/mailer.py)  │ │    (app/services/digest.py)  │
   │ • 1:1 Email per employee     │ │ • Aggregates same-day events │
   │ • Linear retry + backoff     │ │ • Merges dual celebrations   │
   │ • EventLog status: sent      │ │ • DigestLog status: sent     │
   └──────────────────────────────┘ └──────────────────────────────┘
```

---

## ✨ Key Features

- **🛡️ 100% Idempotent by Construction**: Re-running the pipeline multiple times in a day never creates duplicate database rows and never double-sends an email that already went out.
- **🎯 Deterministic Template Rendering**: Zero LLM hallucination risk. Every email is generated from pre-approved Jinja2 HTML templates populated directly with verified HRMS attributes.
- **🖥️ React Admin Dashboard**: Modern single-page operations console built with React 18, Vite, TypeScript, and Tailwind CSS.
- **🔒 Sandboxed HTML Previews**: Rendered HTML emails and digests are previewed safely inside sandboxed `<iframe sandbox="allow-same-origin">` viewports (with desktop & mobile toggles).
- **🔁 Self-Healing Retries**: Transient SMTP outages or template deactivations automatically heal on the next run or via the in-place **Resend** button.
- **📅 Leap-Day Handling**: Configurable policies (`feb28`, `mar1`, `leap_only`) for February 29th birthdays in non-leap years.
- **🤝 Collision-Merging Digests**: Employees celebrating both a birthday and a work anniversary on the same day appear once in a dedicated "Double Celebration" block.

---

## 📁 Project Layout

```
team-engagement-app/
├── app/
│   ├── config.py                 # Central configuration loaded from env vars
│   ├── database.py               # SQLAlchemy engine, session_scope, and table init
│   ├── models.py                 # EmployeeProfile, EventTemplate, EventLog, DigestLog
│   ├── schemas.py                # Pydantic validation and API response models
│   ├── seed.py                   # Idempotent seeder for default templates
│   ├── templates/                # Static Jinja2 HTML email templates
│   │   ├── birthday_default.html
│   │   ├── anniversary_default.html
│   │   ├── anniversary_5yr.html
│   │   ├── anniversary_10yr.html
│   │   └── digest.html
│   ├── services/
│   │   ├── scanner.py            # Date-matching & due-event detection
│   │   ├── renderer.py           # Strict Jinja2 rendering & milestone fallback
│   │   ├── mailer.py             # SMTP / Mock mailer adapters with backoff retry
│   │   ├── digest.py             # Same-day multi-event grouping & digest render
│   │   ├── hrms_sync.py          # HRMS synchronization adapter
│   │   ├── pipeline.py           # Master orchestration (Scan -> Render -> Send -> Digest)
│   │   └── scheduler.py          # APScheduler cron job pinned to business timezone
│   ├── routers/
│   │   ├── admin.py              # Admin endpoints (events, employees, templates, stats, scan)
│   │   └── health.py             # Health check endpoint
│   └── main.py                   # FastAPI application & CORS configuration
├── dashboard/                    # React + Vite + TypeScript Admin Dashboard
│   ├── src/
│   │   ├── api/client.ts         # Authenticated API client with sessionStorage key storage
│   │   ├── context/              # AuthContext (401 auto-logout) & ToastContext
│   │   ├── components/           # Accessible modals, drawers, tables, iframe previews
│   │   └── pages/                # Overview, Events Log, Employees, Digests, Templates
│   ├── Dockerfile                # Multi-stage static build with Nginx
│   └── nginx.conf
├── docker-compose.yml            # Orchestrates Postgres, Redis, Backend, and Dashboard
├── requirements.txt              # Python dependencies
└── tests/                        # Full pytest suite (54+ test cases)
```

---

## 🐳 Quick Start with Docker (Recommended)

Docker Compose starts the entire ecosystem with a single command:

### 1. Configure Environment
Create a `.env` file in the project root:
```bash
cp .env.example .env
```
*(Or create `.env` with your settings):*
```env
ADMIN_API_KEY=change-me-in-production
COMPANY_NAME=Acme Corporation
MAIL_PROVIDER=mock
ENABLE_SCHEDULER=true
BUSINESS_TIMEZONE=Asia/Kolkata
```

### 2. Build and Start Services
```bash
docker compose up --build
```

### 3. Access Services
| Service | URL | Notes |
|---|---|---|
| **Admin Dashboard** | `http://localhost:8080` | Login using your `ADMIN_API_KEY` |
| **FastAPI Backend & Swagger** | `http://localhost:8000/docs` | Interactive API documentation |
| **Health Check** | `http://localhost:8000/health` | Service health status |
| **PostgreSQL Database** | `localhost:5432` | User: `engagement`, DB: `engagement` |
| **Redis** | `localhost:6379` | Cache & scheduling lock |

---

## 💻 Local Development Setup (Without Docker)

You can run both the FastAPI backend and the React dashboard locally on your host machine.

### Prerequisites
- **Python**: 3.11 or higher
- **Node.js**: 18 or higher (with npm)
- *(Optional)* Local PostgreSQL & Redis (or use SQLite for standalone testing)

---

### 1. Backend Setup (FastAPI)

```bash
# 1. Navigate to project root
cd team-engagement-app

# 2. Create and activate a Python virtual environment
# Windows (PowerShell):
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS:
python3 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Create your local .env file
# Tip: For quick local testing without PostgreSQL, use SQLite:
```
Create a `.env` file in the root directory:
```env
DATABASE_URL=sqlite:///./engagement.db
ADMIN_API_KEY=test-admin-key
MAIL_PROVIDER=mock
COMPANY_NAME=Acme Corp
BUSINESS_TIMEZONE=Asia/Kolkata
ENABLE_SCHEDULER=true
```

```bash
# 5. Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend will be live at: **`http://localhost:8000`**

---

### 2. Frontend Dashboard Setup (React + Vite)

Open a **separate terminal window**:

```bash
# 1. Navigate to the dashboard directory
cd team-engagement-app/dashboard

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```
Dashboard will be live at: **`http://localhost:5173`**

Log in using the `ADMIN_API_KEY` you configured in your `.env` (e.g. `test-admin-key`).

---

## 🖥️ Admin Dashboard Features

| View | Capabilities |
|---|---|
| **Overview Home** | Real-time KPI cards (Total Staff, Sent Today, Failed Today, 7-Day Upcoming celebrations), 30-day interactive delivery volume chart, and on-demand scan runner. |
| **Celebration Events Log** | Comprehensive table filterable by batch date, status (`pending`, `rendered`, `sent`, `failed`, `skipped`), and employee name. Click row to preview rendered HTML in a sandboxed iframe. Includes in-place **Resend** button for failed dispatches. |
| **Employee Directory** | Searchable, paginated directory with initials avatar fallbacks, Add/Edit employee profile modals, and slide-out celebration history drawer. |
| **Daily Digests** | Historical list of daily team-wide digest posts with event counts and full HTML sandboxed email preview. |
| **Templates Console** | Inspect seeded celebration templates, preview substituted mock data, and toggle active status. Immutability notice reinforces code-review policy for HTML changes. |

---

## 🔌 Admin API Reference

All `/admin/*` routes require the header: `x-api-key: <ADMIN_API_KEY>`.

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Public service health check (`{"status": "ok"}`) |
| `POST` | `/admin/scan/trigger?scan_date=YYYY-MM-DD` | Manually runs or backfills the full 4-step pipeline |
| `GET` | `/admin/stats/summary?days=30` | Aggregate delivery trends, active counts & 7-day upcoming events |
| `GET` | `/admin/events` | List events with optional `?batch_id=`, `?status=`, `?employee_id=` |
| `GET` | `/admin/events/{id}` | Inspect full event details including `rendered_html` |
| `POST` | `/admin/events/{id}/resend` | Safe manual retry for failed/pending events (refuses already sent) |
| `GET` | `/admin/employees` | Paginated employee list (`?search=`, `?is_active=`, `?limit=`, `?offset=`) |
| `GET` | `/admin/employees/{id}` | Single employee profile + recent celebration history |
| `POST` | `/admin/employees` | Manually create employee record |
| `PATCH` | `/admin/employees/{id}` | Update employee record |
| `GET` | `/admin/templates` | List all seeded templates |
| `PATCH` | `/admin/templates/{id}` | Toggle template `is_active` status |
| `GET` | `/admin/digests` | Paginated list of daily batch digests |
| `GET` | `/admin/digests/{batch_id}` | Retrieve specific batch digest log |
| `POST` | `/admin/hrms-sync/trigger` | Trigger employee profile sync from HRMS |

---

## ⚙️ Environment Configuration

| Variable | Default | Description |
|---|---|---|
| `ADMIN_API_KEY` | `change-me-in-production` | Secret API key required on all `/admin/*` endpoints |
| `DATABASE_URL` | `postgresql+psycopg2://...` | Database connection string (PostgreSQL or SQLite) |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis instance connection string |
| `BUSINESS_TIMEZONE` | `Asia/Kolkata` | Business timezone for daily 6:00 AM scan |
| `DAILY_SCAN_HOUR` | `6` | Hour of day (0–23) to run the automated scan |
| `DAILY_SCAN_MINUTE` | `0` | Minute of hour (0–59) to run the automated scan |
| `ENABLE_SCHEDULER` | `true` | Enable/disable in-process APScheduler cron |
| `LEAP_DAY_POLICY` | `feb28` | Feb 29 policy in non-leap years (`feb28`, `mar1`, `leap_only`) |
| `MAIL_PROVIDER` | `smtp` | Mail adapter (`smtp` for real delivery, `mock` for dev/test) |
| `SMTP_HOST` | `smtp.example.com` | Outgoing SMTP server hostname |
| `SMTP_PORT` | `587` | Outgoing SMTP server port |
| `SMTP_USERNAME` | `""` | SMTP authentication username |
| `SMTP_PASSWORD` | `""` | SMTP authentication password |
| `SMTP_FROM_ADDRESS` | `celebrations@example.com` | Sender email address on outgoing messages |
| `MAIL_MAX_RETRIES` | `3` | Maximum attempts for transient delivery failures |
| `MAIL_RETRY_BACKOFF_SECONDS`| `2.0` | Linear backoff multiplier between email send retries |
| `COMPANY_NAME` | `Your Company` | Company name injected into email templates |
| `COMPANY_LOGO_URL` | `https://assets.example.com/logo.png` | Company logo URL for email templates |
| `DEFAULT_AVATAR_URL` | `https://assets.example.com/default-avatar.png` | Fallback avatar for employees without photo |
| `HRMS_API_BASE_URL` | `https://hrms.example.com/api` | Base URL for external HRMS API |
| `HRMS_API_TOKEN` | `""` | Bearer token for HRMS authentication |

---

## 🛡️ Idempotency & Reliability Guarantees

1. **Database-Level Idempotency**:
   - `EventLog` has a composite database unique constraint `UNIQUE(employee_id, event_type, event_date)`.
   - `DigestLog` has a unique constraint `UNIQUE(batch_id)`.
   - Triggering a scan multiple times on the same date will **never insert duplicate rows**.
2. **Exclusion of Sent Events**:
   - The send stage strictly queries `status IN ('rendered', 'failed')`.
   - Records with `status = 'sent'` are completely skipped.
3. **Graceful Milestone Fallback**:
   - If a 10-year milestone template is deactivated, `renderer.py` automatically falls back to `anniversary_default.html` instead of failing the delivery.
4. **Collision Merging**:
   - An employee with both a birthday and a work anniversary on the same day appears once in the digest in a dedicated "Double Celebration" section.

---

## 🧪 Running Automated Tests

The test suite runs against an isolated, in-memory SQLite database and mock mailer.

```bash
# Run all tests
pytest -v

# Run with coverage report
pytest --cov=app --cov-report=term-missing
```

### Key Test Scenarios Covered:
- **Date Matching**: Feb-29 leap year birthdays under `feb28`, `mar1`, and `leap_only` policies; join-day exclusion (0-year anniversary).
- **Idempotency**: Re-running scan twice inserts 0 duplicate rows; re-running pipeline sends 0 duplicate emails.
- **Failures & Self-Healing**: Automated retry on transient SMTP error; graceful handling of missing employee email addresses.
- **Template Safety**: Strict HTML autoescaping (XSS injection prevention) and missing variable detection.
- **Admin API**: Full CRUD, pagination, authentication rejection, and resend refusal for already-sent events.

---

## 🚀 Production Scaling & Extensions

- **Multi-Replica Deployments**:
  If running multiple backend containers, disable the in-process APScheduler (`ENABLE_SCHEDULER=false`) and trigger `POST /admin/scan/trigger` via an external scheduler (Kubernetes `CronJob`, AWS EventBridge, or n8n).
- **Slack / Teams Integration**:
  To post digests or celebration messages to Slack/Teams instead of email, simply swap `app/services/mailer.py`'s `send()` method with an incoming webhook client.

