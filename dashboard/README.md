# Team Engagement Service — Admin Dashboard

A lightweight, high-reliability operations console for HR and marketing administrators managing 100+ employees. Built with **React 18**, **Vite**, **TypeScript**, and **Tailwind CSS**.

---

## Features

- **🔐 Secure Session Authentication**:
  - API key is stored strictly in `sessionStorage` for the active tab (never persisted to `localStorage` or leaked in URL query parameters).
  - Any `401 Unauthorized` response immediately clears session memory and redirects to login with an informative error.

- **📊 Operations Overview & Metrics**:
  - Real-time KPI cards: Total employees (active vs. inactive), celebration emails sent today, failed dispatches today, upcoming celebrations in the next 7 days.
  - Interactive 7/14/30-day delivery volume trend chart (Sent vs. Failed) powered by Recharts.
  - "Run scan now" button with a date picker supporting manual execution and backfilling with toast feedback.

- **📅 Celebration Events Log**:
  - Filterable by date batch, status (`pending`, `rendered`, `sent`, `failed`, `skipped`), and employee name/subject search.
  - Click any event to open a slide-out drawer with full metadata.
  - **Sandboxed `<iframe>` Email Preview**: Safely renders `rendered_html` in a separate iframe context with desktop and mobile viewport toggles without injecting into host DOM.
  - **In-place Resend**: Retry failed/pending items with linear backoff, updating table rows without full page refreshes.

- **👥 Employee Directory**:
  - Searchable, paginated directory of all employee profiles with avatar fallback to initials.
  - Detailed profile drawer showing employment attributes and recent celebration history.
  - "Add Employee" and "Edit Employee" modals with client-side & backend validation.

- **📬 Daily Digest Logs**:
  - Inspect daily summary posts generated for company-wide channels (merging same-day collisions into single entries).
  - Preview full digest email HTML in sandboxed iframe.

- **📑 Seeded Templates & Immutability**:
  - Toggle `is_active` status for all 5 seeded celebration templates (Birthday, Anniversary Default/5yr/10yr, Digest).
  - Preview static templates with substituted placeholder mock data.
  - Enforces codebase-level immutability policy (template copy/HTML edits must go through code review).

- **🔄 On-Demand HRMS Sync**:
  - Trigger synchronization from external HRMS APIs into the local `employee_profile` database mirror.

---

## Running Standalone (Local Development)

### Prerequisites
- Node.js (v18+) and npm
- Team Engagement FastAPI backend running on `http://localhost:8000`

### Steps

```bash
# 1. Navigate to the dashboard directory
cd dashboard

# 2. Install dependencies
npm install

# 3. Start Vite dev server
npm run dev
```

The dashboard will be available at: **`http://localhost:5173`**

*(Optional)* To target a backend running on a different port or host, create `.env` in `dashboard/`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## Running with Docker Compose

The dashboard is integrated into the root `docker-compose.yml` with multi-stage static build and Nginx:

```bash
# From the project root directory
docker compose up --build
```

This starts:
- **FastAPI Backend**: `http://localhost:8000`
- **Admin Dashboard**: `http://localhost:8080`
- **PostgreSQL Database**: `localhost:5432`
- **Redis**: `localhost:6379`

---

## Architecture & Security Highlights

1. **Sandboxed Iframe Rendering**:
   Every rendered email or digest body is rendered inside `<iframe sandbox="allow-same-origin" srcDoc={...}>` to prevent script execution or style bleed into the application.
2. **Zero Storage of Credentials on Disk**:
   Closing the browser tab automatically flushes the admin API key.
3. **Empty States as Normal Outcomes**:
   Days with no events (e.g. `EMPTY_SKIPPED` digest status) are treated as standard operational states rather than error conditions.
