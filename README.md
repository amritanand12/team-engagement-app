# Team Engagement Service

Automated birthday & work-anniversary notifications for IT companies (100+ employees).
Static templates + dynamic placeholders, driven entirely by data — no per-recipient
text generation, no LLM in the send path.

## Architecture at a glance

```
HRMS  --(nightly sync)-->  employee_profile  (local read-only mirror)
                                   |
                          daily cron (06:00, business TZ)
                                   v
                          scanner: match DOB/DOJ to today
                                   v
                          event_log (status=pending)  [idempotent: UNIQUE(employee_id, event_type, event_date)]
                                   v
                          renderer: Jinja2 template + placeholders  ->  status=rendered
                                   v
                     ------------------------------
                     |                            |
        individual email (1:1)          same-day digest (1 message, grouped)
              status=sent                     digest_log.status=sent
```

Everything is idempotent by design: re-running the pipeline for a date that
already ran never creates duplicate rows and never double-sends an email that
already went out. It *does* retry anything left in a `failed` state, so a
transient SMTP outage or a briefly-deactivated template self-heals on the
next run without manual intervention.

## Project layout

```
app/
  config.py              # every tunable setting, env-driven
  database.py             # SQLAlchemy engine/session
  models.py               # EmployeeProfile, EventTemplate, EventLog, DigestLog
  schemas.py               # Pydantic API models
  seed.py                  # seeds the 4 default templates
  templates/                # static HTML/Jinja2 email templates
    birthday_default.html
    anniversary_default.html
    anniversary_5yr.html
    anniversary_10yr.html
    digest.html
  services/
    hrms_sync.py            # HRMS -> local mirror (swap in your real HRMS client)
    scanner.py                # date-matching / due-event detection
    renderer.py                # Jinja2 rendering, milestone variant selection
    digest.py                   # same-day multi-event grouping for the digest
    mailer.py                    # SMTP + mock adapters, retry/backoff
    pipeline.py                   # orchestrates scan -> render -> send -> digest
    scheduler.py                   # APScheduler cron wiring
  routers/
    admin.py                        # manual trigger, event/digest lookup, resend
    health.py
  main.py                            # FastAPI app + lifespan (init db, seed, start scheduler)
tests/                                # 54 tests, edge cases below
```

## Running it

```bash
cp .env.example .env        # edit COMPANY_NAME, SMTP_*, HRMS_*, ADMIN_API_KEY etc.
docker compose up --build
```

This starts Postgres, Redis, and the app on `http://localhost:8000`. On
startup the app creates tables and seeds the four default templates
automatically (idempotent — safe to restart).

### Manually triggering a run (also useful for backfilling a missed day)

```bash
curl -X POST "http://localhost:8000/admin/scan/trigger?scan_date=2026-08-22" \
  -H "x-api-key: <ADMIN_API_KEY>"
```

### Wiring up real HRMS data

`app/services/hrms_sync.py` has a stub `fetch_hrms_employees()` — replace it
with your actual HRMS API/export call. Everything downstream only depends on
the local `employee_profile` table, so the daily scan never depends on HRMS
uptime at 6am.

### Scheduling in production

The bundled APScheduler works fine for a **single app instance**. If you run
multiple replicas, move triggering out of the process — call
`POST /admin/scan/trigger` from an external scheduler (n8n Cron node, Celery
beat, a Kubernetes CronJob) instead, so only one instance ever fires the job
per day.

## Design decisions worth knowing about

- **No free-text generation.** Templates are static HTML with Jinja2
  placeholders (`{{ name }}`, `{{ years }}`, `{{ photo_url }}`, ...). Nothing
  is generated per-recipient — every field comes straight from HRMS data, so
  output is 100% predictable and can be reviewed/approved once, up front.
- **`StrictUndefined`** on the Jinja2 environment: a template referencing an
  undefined placeholder raises immediately instead of silently rendering the
  literal `{{ typo }}` into a live email.
- **Idempotency via a DB constraint, not application logic.** `event_log` has
  `UNIQUE(employee_id, event_type, event_date)`. Retries, cron misfires, and
  manual re-triggers are all safe by construction.
- **Milestone templates fall back gracefully.** If the 10-year template is
  deactivated, rendering falls back to the generic anniversary template
  rather than failing the send outright.
- **Digest merges collisions.** An employee with both a birthday and a
  work anniversary on the same day appears once in the digest, in a
  dedicated "Double Celebration" section — never as two separate entries.
- **Leap-year birthdays** are configurable (`LEAP_DAY_POLICY=feb28|mar1|leap_only`)
  rather than hardcoded, since this is a genuine product decision, not a bug.

## Edge cases covered by tests

| Area | Cases |
|---|---|
| Date logic | Feb-29 birthdays under all three policies, in leap and non-leap years; join-day itself excluded from "0-year anniversary"; years-of-service computed correctly |
| Multi-event days | Two different employees same day; one employee with birthday + anniversary same day (merged in digest, still 2 individual emails); 15-person batch |
| Idempotency | Re-running scan twice inserts no duplicates; re-running full pipeline twice sends no duplicate emails; digest never sent twice for the same batch |
| Failure recovery | Send failure followed by pipeline rerun retries and succeeds, without creating duplicate `event_log` rows; retry/backoff on transient mailer failures; permanent failure after max retries |
| Data quality | Missing photo → default avatar; inactive employees excluded and never emailed; employee with no email address fails gracefully instead of crashing the batch |
| Rendering safety | HTML/script injection in a name is autoescaped; missing template raises and is caught; milestone template deactivated falls back to default |
| Digest truncation | >10 events in one section truncate with an "...and N more" summary |
| API | Missing/invalid admin API key rejected; 404s for unknown events/digests; resend refuses to re-send an already-sent event |
| Integration | Full run against a synthetic HRMS fixture (5 employees covering all the above) from sync through send |

Run them with:

```bash
pip install -r requirements.txt
pytest -q                      # 54 tests
pytest --cov=app --cov-report=term-missing   # coverage report
```

## Extending

- **New event types** (work-from-anniversary, promotions, etc.): add an
  `EventType`, a template + seed entry, and a detection clause in
  `scanner.find_due_events`. Everything else (idempotency, rendering,
  digesting) is generic.
- **Slack/Teams instead of email**: swap `mailer.py`'s `send()` for a
  webhook call — the rest of the pipeline is delivery-channel agnostic.
- **n8n**: if you'd rather orchestrate scheduling/dispatch outside this
  service, point an n8n Cron node at `POST /admin/scan/trigger` and use its
  HTTP Request nodes to hit `/admin/events` for monitoring/alerting on
  `failed` rows.
