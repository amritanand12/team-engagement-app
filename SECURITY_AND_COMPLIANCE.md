# 🔒 Security, Data Privacy & Compliance Whitepaper

> Enterprise Security Architecture, Data Isolation Controls, Encryption Standards, and Compliance Mapping for **Team Engagement Service & Admin Console**.

---

## 📌 Executive Security Summary

Mid-market enterprises require robust security controls, strict role-based access, complete data isolation, and comprehensive auditability before connecting employee HR data to any software application.

The **Team Engagement Service** is engineered with a **defense-in-depth security model**:
- **BYODB Database Isolation**: Support for dedicated enterprise-owned PostgreSQL databases.
- **AES-256 Credential Encryption**: Encryption for all sensitive credentials at rest.
- **Strict Deterministic Rendering**: Zero third-party LLM APIs; zero risk of employee PII leaking into AI model training sets.
- **Granular RBAC**: 4-tier Role-Based Access Control enforcing strict read/write boundaries.
- **Immutable Audit Trail**: Detailed audit logging of all administrative actions, data edits, and authentication events.

---

## 🏗️ 1. Multi-Tenant Architecture & Data Isolation

```
                   ┌─────────────────────────────────────────┐
                   │        Platform Application Engine       │
                   └────────────────────┬────────────────────┘
                                        │
           ┌────────────────────────────┴────────────────────────────┐
           ▼                                                         ▼
┌──────────────────────────────┐                         ┌──────────────────────────────┐
│  Dedicated Enterprise DB A   │                         │  Dedicated Enterprise DB B   │
│   (Customer VPC / BYODB)     │                         │   (Customer VPC / BYODB)     │
├──────────────────────────────┤                         ├──────────────────────────────┤
│ • Employee Profiles          │                         │ • Employee Profiles          │
│ • Celebration Event Logs     │                         │ • Celebration Event Logs     │
│ • Private HTML Templates     │                         │ • Private HTML Templates     │
└──────────────────────────────┘                         └──────────────────────────────┘
```

### Shared Multi-Tenancy vs. BYODB (Bring Your Own Database)
1. **Shared Tenant Mode**: Data is segregated at the database schema level using `organization_id` foreign keys, unique composite indexes, and SQLAlchemy tenant-scoped queries.
2. **Dedicated Enterprise BYODB Mode**: Enterprise customers supply their own PostgreSQL connection endpoint (`db_host`, `db_name`, `db_user`). The platform engine dynamically routes tenant database sessions to the customer's private database engine over SSL/TLS. No customer PII is stored on shared application database storage.

---

## 🔐 2. Authentication, Authorization & RBAC

All administrative API endpoints enforce JWT (JSON Web Token) validation or secure API Key verification (`x-api-key` header).

### Role-Based Access Control (RBAC) Matrix

| User Role | System Scope | Capabilities & Permissions |
|---|---|---|
| **`SUPER_ADMIN`** | Platform-wide | Multi-tenant tenant provisioning, global system stats, tenant database setup review, platform health monitoring. |
| **`TENANT_ADMIN`** | Single Tenant | Full administrative privileges within organization: manage users, configure SMTP/DB, trigger scans, edit templates, import/export employees. |
| **`HR_MANAGER`** | Single Tenant | Operations access: view/add/edit employee profiles, trigger scans, resend failed emails, preview digests. Cannot modify core system credentials. |
| **`VIEWER`** | Single Tenant | **Read-Only Access**: View dashboard stats, inspect celebration logs, view templates. All write/delete endpoints return `403 Forbidden`. |

---

## 🛡️ 3. Cryptography & Data Protection

### Encryption at Rest
All sensitive secrets (PostgreSQL database passwords, custom SMTP passwords, HRMS API tokens) are encrypted prior to persistence using **AES-256 GCM** cryptography (`app/services/crypto.py`). Cleartext passwords are never logged or stored in database tables.

### Encryption In Transit
- All administrative traffic requires **TLS 1.3 / HTTPS**.
- PostgreSQL database connections enforce SSL encryption (`sslmode=require` or `sslmode=verify-full`).
- Outgoing SMTP mail server connections enforce TLS encryption (`smtp_use_tls = True`).

### HTML Sandbox & XSS Protection
Rendered HTML emails and daily team digests present potential cross-site scripting (XSS) attack vectors if unescaped user data (e.g., employee names, job titles) is rendered.
- **Strict Auto-escaping**: Jinja2 renderer operates with auto-escaping enabled and `StrictUndefined` variable checking.
- **Sandboxed Viewport**: Dashboard preview components render HTML inside sandboxed `<iframe sandbox="allow-same-origin">` containers, preventing script execution within the dashboard DOM context.

---

## 📋 4. Audit Logging & Telemetry

The platform maintains an immutable audit record in the `audit_log` database table for every administrative, operational, and configuration action:

```json
{
  "id": "a9b8c7d6-e5f4-4321-8765-123456789abc",
  "organization_id": "org_covalense_01",
  "actor_email": "admin@covalense.com",
  "actor_role": "tenant_admin",
  "action": "TENANT_DATABASE_CONFIGURED",
  "resource_type": "organization",
  "resource_id": "org_covalense_01",
  "details": "Tenant configured private PostgreSQL database (prod_db on db.internal.covalense.com:5432)",
  "ip_address": "192.168.1.105",
  "created_at": "2026-10-06T11:20:00Z"
}
```

### Key Tracked Audit Events:
- `AUTH_LOGIN_SUCCESS` / `AUTH_LOGIN_FAILED`
- `TENANT_DATABASE_CONFIGURED` / `TENANT_SMTP_CONFIGURED`
- `EMPLOYEE_CREATED` / `EMPLOYEE_UPDATED` / `EMPLOYEE_CSV_IMPORTED`
- `SCAN_TRIGGERED` / `EVENT_RESENT`
- `TEMPLATE_CREATED` / `TEMPLATE_UPDATED` / `TEMPLATE_DEACTIVATED`

---

## 📑 5. Enterprise Compliance Mapping

### SOC 2 Type II Alignment

| SOC 2 Trust Principle | Platform Control Implementation |
|---|---|
| **CC6.1 (Logical Access Controls)** | JWT Bearer token auth + API Key verification + 4-tier RBAC (`require_write_permission` guards). |
| **CC6.6 (Boundary Protection)** | TLS encrypted endpoints, dedicated database connections, isolated tenant engines. |
| **CC6.8 (Malicious Code Prevention)** | Deterministic Jinja2 auto-escaping + iframe viewport sandboxing (`allow-same-origin`). |
| **CC7.2 (Infrastructure Monitoring)** | Automated health check endpoint (`/health`), Redis lock monitoring, APScheduler telemetry. |
| **CC8.1 (Change Management)** | Code-reviewed Jinja2 templates; template immutability warnings in admin dashboard. |

### GDPR & CCPA Readiness

1. **Right to Rectification & Erasure**: Admin endpoints allow immediate updating (`PATCH /admin/employees/{id}`) or deactivation/deletion of employee PII.
2. **Data Minimization**: Only essential employment attributes (Full Name, Preferred Name, Email, DOB, DOJ, Department, Manager) are mirrored from HRMS.
3. **Storage Limitation**: Celebration event logs and photo upload tokens enforce explicit lifecycle policies.
