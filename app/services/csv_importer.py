"""
Universal CSV importer for employee rosters.
Normalizes arbitrary CSV headers, parses multiple date formats, and bulk upserts
into EmployeeProfile scoped to the tenant organization.
"""
from __future__ import annotations

import csv
import io
import logging
import re
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import EmployeeProfile

logger = logging.getLogger("engagement.csv_importer")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

HEADER_MAPPINGS = {
    "employee_code": [
        "employee_code", "employeecode", "employee_id", "employeeid", "emp_code",
        "emp_id", "empid", "code", "id", "staff_id", "badge_number"
    ],
    "full_name": [
        "full_name", "fullname", "name", "employee_name", "employeename", "first_last"
    ],
    "preferred_name": [
        "preferred_name", "preferredname", "nickname", "display_name", "displayname"
    ],
    "email": [
        "email", "email_address", "emailaddress", "work_email", "workemail", "corporate_email"
    ],
    "photo_url": [
        "photo_url", "photourl", "avatar", "avatar_url", "image_url", "picture"
    ],
    "date_of_birth": [
        "date_of_birth", "dateofbirth", "dob", "birth_date", "birthdate", "birthday"
    ],
    "date_of_joining": [
        "date_of_joining", "dateofjoining", "doj", "joining_date", "joiningdate",
        "hire_date", "hiredate", "start_date", "startdate"
    ],
    "department": [
        "department", "dept", "team", "division", "unit"
    ],
    "team_channel_id": [
        "team_channel_id", "channel_id", "slack_channel", "teams_channel"
    ],
}


def _normalize_key(header: str) -> str:
    cleaned = header.strip().lower().replace(" ", "_").replace("-", "_").replace(".", "")
    for canonical, variations in HEADER_MAPPINGS.items():
        if cleaned in variations:
            return canonical
    return cleaned


DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%m/%d/%Y",
    "%d-%m-%Y",
    "%m-%d-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y%m%d",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
]


def parse_date_lenient(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    val_str = str(value).strip()
    if not val_str:
        return None

    # Strip time part if present (e.g. 1990-05-14T00:00:00)
    val_str = val_str.split("T")[0].split(" ")[0].strip()

    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue

    raise ValueError(f"Unrecognized date format: '{value}'")


def import_employees_from_csv(
    db: Session,
    organization_id: str,
    csv_content: str | bytes,
) -> tuple[int, int, int, list[dict[str, Any]]]:
    """
    Parses CSV content and imports employee records for the given organization.
    Returns: (imported_count, updated_count, failed_count, errors)
    """
    if isinstance(csv_content, bytes):
        try:
            csv_str = csv_content.decode("utf-8-sig")  # handles BOM
        except UnicodeDecodeError:
            csv_str = csv_content.decode("latin-1")
    else:
        csv_str = csv_content

    reader = csv.reader(io.StringIO(csv_str))
    rows = list(reader)
    if not rows:
        return 0, 0, 0, [{"row": 1, "error": "CSV file is empty"}]

    raw_headers = rows[0]
    normalized_headers = [_normalize_key(h) for h in raw_headers]

    imported_count = 0
    updated_count = 0
    errors: list[dict[str, Any]] = []

    for row_idx, row in enumerate(rows[1:], start=2):
        if not row or all(not cell.strip() for cell in row):
            continue  # Skip blank lines

        row_dict = {}
        for col_idx, cell in enumerate(row):
            if col_idx < len(normalized_headers):
                row_dict[normalized_headers[col_idx]] = cell.strip()

        # Validate required fields
        emp_code = row_dict.get("employee_code")
        full_name = row_dict.get("full_name")
        email = row_dict.get("email")

        row_errors = []
        if not emp_code:
            row_errors.append("Missing employee code / ID")
        if not full_name:
            row_errors.append("Missing full name")
        if not email:
            row_errors.append("Missing email address")
        elif not EMAIL_REGEX.match(email):
            row_errors.append(f"Invalid email format: '{email}'")

        dob: date | None = None
        if "date_of_birth" in row_dict and row_dict["date_of_birth"]:
            try:
                dob = parse_date_lenient(row_dict["date_of_birth"])
            except ValueError as e:
                row_errors.append(str(e))

        doj: date | None = None
        if "date_of_joining" in row_dict and row_dict["date_of_joining"]:
            try:
                doj = parse_date_lenient(row_dict["date_of_joining"])
            except ValueError as e:
                row_errors.append(str(e))

        if row_errors:
            errors.append({"row": row_idx, "error": "; ".join(row_errors)})
            continue

        # Look up existing employee in this organization
        existing = (
            db.query(EmployeeProfile)
            .filter(
                EmployeeProfile.organization_id == organization_id,
                EmployeeProfile.employee_code == emp_code,
            )
            .first()
        )

        pref_name = row_dict.get("preferred_name") or None
        photo_url = row_dict.get("photo_url") or None
        dept = row_dict.get("department") or None
        team_channel = row_dict.get("team_channel_id") or None

        if existing:
            existing.full_name = full_name
            existing.preferred_name = pref_name
            existing.email = email
            if photo_url:
                existing.photo_url = photo_url
            if dob:
                existing.date_of_birth = dob
            if doj:
                existing.date_of_joining = doj
            if dept:
                existing.department = dept
            if team_channel:
                existing.team_channel_id = team_channel
            existing.last_synced_at = datetime.utcnow()
            updated_count += 1
        else:
            new_emp = EmployeeProfile(
                organization_id=organization_id,
                employee_code=emp_code,
                full_name=full_name,
                preferred_name=pref_name,
                email=email,
                photo_url=photo_url,
                date_of_birth=dob,
                date_of_joining=doj,
                department=dept,
                team_channel_id=team_channel,
                is_active=True,
                last_synced_at=datetime.utcnow(),
            )
            db.add(new_emp)
            imported_count += 1

    db.flush()
    return imported_count, updated_count, len(errors), errors
