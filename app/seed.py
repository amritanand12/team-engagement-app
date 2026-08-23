"""Seeds the four default templates. Safe to run repeatedly (idempotent by variant_key)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import EventTemplate, EventType
from app.services.renderer import load_seed_template_file

DEFAULT_TEMPLATES = [
    dict(
        event_type=EventType.BIRTHDAY,
        variant_key="default",
        subject_line="🎉 Happy Birthday, {{ name }}!",
        filename="birthday_default.html",
    ),
    dict(
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_default",
        subject_line="🎊 Congrats on {{ years }} year{{ 's' if years != 1 else '' }}, {{ name }}!",
        filename="anniversary_default.html",
    ),
    dict(
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_5yr",
        subject_line="🏅 {{ name }}, 5 years at {{ company_name }}!",
        filename="anniversary_5yr.html",
    ),
    dict(
        event_type=EventType.WORK_ANNIVERSARY,
        variant_key="anniversary_10yr",
        subject_line="👑 {{ name }}, a decade at {{ company_name }}!",
        filename="anniversary_10yr.html",
    ),
]


def seed_default_templates(db: Session) -> int:
    created = 0
    for tpl in DEFAULT_TEMPLATES:
        existing = (
            db.query(EventTemplate)
            .filter(
                EventTemplate.event_type == tpl["event_type"],
                EventTemplate.variant_key == tpl["variant_key"],
                EventTemplate.is_active.is_(True),
            )
            .first()
        )
        if existing:
            continue
        html_body = load_seed_template_file(tpl["filename"])
        db.add(
            EventTemplate(
                event_type=tpl["event_type"],
                variant_key=tpl["variant_key"],
                subject_line=tpl["subject_line"],
                html_body=html_body,
                is_active=True,
            )
        )
        created += 1
    db.commit()
    return created
