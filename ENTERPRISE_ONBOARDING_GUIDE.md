# 🚀 Enterprise Onboarding Playbook & Sales Demo Guide

> A step-by-step implementation guide for enterprise IT/HR administrators and a 15-minute winning demonstration script for Account Executives selling **Team Engagement App**.

---

## 🛠️ Part 1: Enterprise Onboarding Playbook (6-Step Deployment)

```
  Step 1               Step 2               Step 3               Step 4               Step 5               Step 6
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Tenant      │ ──► │  Database    │ ──► │  SMTP Email  │ ──► │  HRMS Data   │ ──► │  Branding &  │ ──► │  Dry-Run     │
│  Creation    │     │  (BYODB)     │     │  Verification│     │  Sync / CSV  │     │  Templates   │     │  Pipeline    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
```

### Step 1: Tenant Organization Provisioning
1. Log into the SuperAdmin Console (`/superadmin`).
2. Click **Create New Tenant Organization**.
3. Enter Company Name (e.g., `Acme Corporation`), URL slug (`acme`), and assign a Tenant Admin email address.
4. System automatically generates a secure tenant API key (`x-api-key`).

### Step 2: Database Connection & Infrastructure Setup
1. Log into the Tenant Admin Console using the generated credentials.
2. Navigate to **Organization Settings -> Database Configuration**.
3. *Option A (Standard)*: Use Managed Shared Database infrastructure.
4. *Option B (Enterprise BYODB)*: Enter private PostgreSQL parameters:
   - Host: `db.internal.acme.com`
   - Port: `5432`
   - Database Name: `acme_engagement_prod`
   - Username: `engagement_app`
   - Password: `[ENCRYPTED]`
   - SSL Mode: `require`
5. Click **Test Database Connection**. Upon success (green latency badge), click **Save Database Credentials**. System automatically provisions required schema tables.

### Step 3: Enterprise SMTP Mailer Verification
1. In Settings, navigate to **SMTP Configuration**.
2. Input Corporate SMTP details:
   - SMTP Host: `smtp.sendgrid.net` (or internal relay `mail.acme.com`)
   - Port: `587`
   - Username / Password: `[ENCRYPTED]`
   - From Address: `celebrations@acme.com`
   - TLS: Enabled
3. Click **Send Test Email**. Verify reception in admin inbox. Click **Activate SMTP Settings**.

### Step 4: HRMS Data Mirroring & Employee Import
1. Navigate to **Employee Directory**.
2. Click **Import Employees via CSV** (or click **Sync with HRMS** if BambooHR API token is connected).
3. Upload HRMS export containing: `employee_code`, `full_name`, `email`, `date_of_birth`, `date_of_joining`, `department`, `manager_id`.
4. System validates date formats (`YYYY-MM-DD`), screens out invalid entries, and upserts profiles into the database.

### Step 5: Branding & Custom Milestone Templates
1. Under **Settings**, upload Company Logo URL (`https://assets.acme.com/logo.png`) and select **Business Timezone** (e.g., `America/New_York`).
2. Set Feb-29 Leap Day policy (`feb28` or `mar1`).
3. Under **Templates Console**, inspect seeded templates (`birthday_default`, `anniversary_5yr`, `anniversary_10yr`). Customize Jinja2 HTML placeholders as desired.

### Step 6: Dry-Run Scan & Pipeline Validation
1. Go to **Overview Home**.
2. Click **Run Manual Scan**.
3. System executes 4-step pipeline (Scan -> Render -> Send -> Digest).
4. Inspect output in **Celebration Events Log** and preview rendered email output inside sandboxed iframe.

---

## 🎬 Part 2: Executive Sales Demo Script (15-Minute AE Walkthrough)

### 00:00 - 03:00 | Executive Overview & Delivery Telemetry
- **Action**: Open Dashboard Overview page (`http://localhost:5173`).
- **Script**: *"Welcome! What you're seeing here is the executive operational cockpit of Team Engagement App. In a single view, HR leaders get real-time visibility into total active staff, today's dispatched celebrations, any delivery errors, and upcoming events over the next 7 days. Notice the 30-day interactive delivery chart tracking exact email volume over time."*

### 03:00 - 07:00 | Celebration Events Log & Sandboxed Email Previews
- **Action**: Click on **Events Log**, select a `rendered` or `sent` row to open the Sandboxed HTML Preview drawer. Toggle Desktop / Mobile viewports.
- **Script**: *"Here is where our platform truly shines. Every single email is rendered deterministically using pre-approved Jinja2 HTML templates. There is zero runtime LLM risk—no hallucinations, no formatting breaks, no wrong dates. Look at this 5-Year Milestone Anniversary email: notice how employee name, tenure years, company logo, and personalized photo attachment are automatically populated. Admins can preview exact HTML output in a safe iframe viewport and click 'Resend' in case of external mail server drops."*

### 07:00 - 10:00 | Employee Roster, Photo Upload Portal & HRMS Sync
- **Action**: Navigate to **Employee Directory**, click on an employee profile to open their Celebration History drawer. Show **Import CSV** modal and Photo Request link.
- **Script**: *"Our employee roster mirrors your official HRMS database. We support nightly automated syncs with BambooHR, Workday, and HiBob, as well as one-click CSV imports. Notice our automated photo request feature: 7 days before a milestone anniversary, the platform can automatically email the employee a secure upload link so their manager can include a personal team picture in the celebration!"*

### 10:00 - 13:00 | Enterprise BYODB Settings & Security Isolation
- **Action**: Navigate to **Organization Settings**, highlight Database Connection tab and SMTP settings.
- **Script**: *"For your InfoSec and compliance teams, we support Enterprise BYODB (Bring Your Own Database). You can point our service directly to a private PostgreSQL database inside your cloud environment. All credentials are encrypted using AES-256 GCM at rest, and all admin actions generate an immutable audit log."*

### 13:00 - 15:00 | SuperAdmin Multi-Tenant Control Panel & Closing
- **Action**: Switch to SuperAdmin view (`/superadmin`). Show active tenant list, metrics, and global system health.
- **Script**: *"Finally, for organizations operating multiple subsidiaries or managing multi-brand holding companies, our SuperAdmin console gives you centralized telemetry across all tenant organizations while keeping customer data completely isolated. Let's get your 7-day sandbox instance set up today!"*
