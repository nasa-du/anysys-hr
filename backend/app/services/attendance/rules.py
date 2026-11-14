"""Attendance rules: company defaults and per-plan overrides.

A company has at most one stored default-rule row. Reading never creates it:
an absent row means the documented system defaults remain in effect. Plan
overrides are nullable fields merged over the company default; ``None`` means
inherit. Rule changes mark editable months stale but never recalculate or
alter confirmed/locked results (spec sections 4.6, 5.6, 8.3.7, and 8.7).
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.core.errors import DomainError
from app.enums import AttendanceMonthStatus, PlanStatus
from app.models import (
    AttendanceMonth,
    AttendanceRule,
    PlanRuleOverride,
    SchedulePlan,
    get_datetime_utc,
)
from app.schemas_attendance.core import (
    AttendanceRulePublic,
    AttendanceRuleUpdate,
    RulePatch,
    RuleValues,
)
from app.schemas_attendance.scheduling import (
    PlanRuleOverridesPublic,
    PlanRuleOverridesUpdate,
)
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.staleness import (
    mark_company_months_stale,
    mark_month_stale,
)
from app.services.companies import get_company_or_404

RULE_FIELDS: tuple[str, ...] = (
    "punch_window_min",
    "late_cap_min",
    "early_cap_min",
    "ot_max_min",
    "late_grace_min",
    "early_grace_min",
    "ot_threshold_min",
    "absent_if_no_punch",
    "break_punch_required",
    "break_punch_tolerance_min",
    "absent_deduct_per_day",
    "late_deduct_per_occurrence",
    "early_deduct_per_occurrence",
    "missing_punch_deduct_per_occurrence",
)

SYSTEM_DEFAULT_RULE_VALUES: dict[str, Any] = {
    "punch_window_min": 120,
    "late_cap_min": 240,
    "early_cap_min": 240,
    "ot_max_min": 600,
    "late_grace_min": 5,
    "early_grace_min": 5,
    "ot_threshold_min": 30,
    "absent_if_no_punch": True,
    "break_punch_required": True,
    "break_punch_tolerance_min": 60,
    "absent_deduct_per_day": Decimal("0.00"),
    "late_deduct_per_occurrence": Decimal("0.00"),
    "early_deduct_per_occurrence": Decimal("0.00"),
    "missing_punch_deduct_per_occurrence": Decimal("0.00"),
}

PLAN_NOT_FOUND_MESSAGE = "排班方案不存在"
PLAN_ARCHIVED_MESSAGE = "已归档的排班方案不可修改，请先取消归档"
MONTH_CONFIRMED_MESSAGE = "考勤月份已确认，请先取消确认"
MONTH_LOCKED_MESSAGE = "考勤月份已锁定，请先解锁"


def _rule_values(rule: AttendanceRule) -> dict[str, Any]:
    return {field: getattr(rule, field) for field in RULE_FIELDS}


def _company_rule_row(session: Session, company_id: uuid.UUID) -> AttendanceRule | None:
    return session.exec(
        select(AttendanceRule).where(col(AttendanceRule.company_id) == company_id)
    ).first()


def company_default_values(session: Session, company_id: uuid.UUID) -> dict[str, Any]:
    """Return the stored company rule or the documented system defaults."""
    rule = _company_rule_row(session, company_id)
    if rule is None:
        return dict(SYSTEM_DEFAULT_RULE_VALUES)
    return _rule_values(rule)


def _rule_public(
    company_id: uuid.UUID,
    values: dict[str, Any],
    *,
    rule_id: uuid.UUID | None,
    is_default: bool,
    created_at: Any = None,
    updated_at: Any = None,
) -> AttendanceRulePublic:
    return AttendanceRulePublic(
        id=rule_id,
        company_id=company_id,
        is_default=is_default,
        created_at=created_at,
        updated_at=updated_at,
        **values,
    )


def get_company_rule(session: Session, company_id: uuid.UUID) -> AttendanceRulePublic:
    """Read the company rule without ever writing a row."""
    get_company_or_404(session, company_id)
    rule = _company_rule_row(session, company_id)
    if rule is None:
        return _rule_public(
            company_id,
            dict(SYSTEM_DEFAULT_RULE_VALUES),
            rule_id=None,
            is_default=True,
        )
    return _rule_public(
        company_id,
        _rule_values(rule),
        rule_id=rule.id,
        is_default=False,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def update_company_rule(
    session: Session,
    company_id: uuid.UUID,
    payload: AttendanceRuleUpdate,
) -> AttendanceRulePublic:
    """Create the first company row or update the supplied fields."""
    get_company_or_404(session, company_id)
    data = payload.model_dump(exclude_unset=True)

    rule = _company_rule_row(session, company_id)
    if rule is None:
        rule = AttendanceRule(
            company_id=company_id,
            **SYSTEM_DEFAULT_RULE_VALUES,
        )
        for field, value in data.items():
            setattr(rule, field, value)
        # Mark before adding the row: stale marking runs a query and would
        # otherwise autoflush the new rule outside the IntegrityError backstop.
        mark_company_months_stale(session, company_id)
        session.add(rule)
    else:
        changed = any(getattr(rule, field) != value for field, value in data.items())
        for field, value in data.items():
            setattr(rule, field, value)
        if changed:
            rule.updated_at = get_datetime_utc()
            mark_company_months_stale(session, company_id)

    try:
        session.commit()
    except IntegrityError:
        # Two first-writes can race on ``uq_attendance_rule_company``. Retry
        # once as an update rather than surfacing database text.
        session.rollback()
        rule = _company_rule_row(session, company_id)
        if rule is None:
            raise
        for field, value in data.items():
            setattr(rule, field, value)
        rule.updated_at = get_datetime_utc()
        mark_company_months_stale(session, company_id)
        session.commit()

    session.refresh(rule)
    return _rule_public(
        company_id,
        _rule_values(rule),
        rule_id=rule.id,
        is_default=False,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def get_plan_or_404(session: Session, plan_id: uuid.UUID) -> SchedulePlan:
    plan = session.get(SchedulePlan, plan_id)
    if plan is None:
        raise DomainError(AttendanceErrorCode.NOT_FOUND, PLAN_NOT_FOUND_MESSAGE)
    return plan


def _month_for_plan(
    session: Session, plan: SchedulePlan, *, for_update: bool = False
) -> AttendanceMonth | None:
    statement = select(AttendanceMonth).where(
        col(AttendanceMonth.company_id) == plan.company_id,
        col(AttendanceMonth.month) == date(plan.month.year, plan.month.month, 1),
    )
    if for_update:
        statement = statement.with_for_update()
    return session.exec(statement).first()


def _ensure_plan_editable(plan: SchedulePlan, month: AttendanceMonth | None) -> None:
    if plan.status == PlanStatus.ARCHIVED:
        raise DomainError(AttendanceErrorCode.PLAN_ARCHIVED, PLAN_ARCHIVED_MESSAGE)
    if month is None:
        return
    if month.status == AttendanceMonthStatus.LOCKED:
        raise DomainError(AttendanceErrorCode.MONTH_LOCKED, MONTH_LOCKED_MESSAGE)
    if month.status == AttendanceMonthStatus.CONFIRMED:
        raise DomainError(AttendanceErrorCode.MONTH_CONFIRMED, MONTH_CONFIRMED_MESSAGE)


def _override_values(row: PlanRuleOverride | None) -> dict[str, Any]:
    if row is None:
        return dict.fromkeys(RULE_FIELDS)
    return {field: getattr(row, field) for field in RULE_FIELDS}


def _effective_values(
    defaults: dict[str, Any], overrides: dict[str, Any]
) -> dict[str, Any]:
    return {
        field: (overrides[field] if overrides[field] is not None else defaults[field])
        for field in RULE_FIELDS
    }


def _plan_overrides_public(
    session: Session,
    plan: SchedulePlan,
    overrides: dict[str, Any],
) -> PlanRuleOverridesPublic:
    defaults = company_default_values(session, plan.company_id)
    return PlanRuleOverridesPublic(
        overrides=RulePatch.model_validate(overrides),
        effective=RuleValues.model_validate(_effective_values(defaults, overrides)),
        company_default=RuleValues.model_validate(defaults),
    )


def get_plan_rule_overrides(
    session: Session, plan_id: uuid.UUID
) -> PlanRuleOverridesPublic:
    plan = get_plan_or_404(session, plan_id)
    row = session.get(PlanRuleOverride, plan_id)
    return _plan_overrides_public(session, plan, _override_values(row))


def update_plan_rule_overrides(
    session: Session,
    plan_id: uuid.UUID,
    payload: PlanRuleOverridesUpdate,
) -> PlanRuleOverridesPublic:
    """Replace the plan override row wholesale and mark its month stale."""
    plan = get_plan_or_404(session, plan_id)
    month = _month_for_plan(session, plan, for_update=True)
    _ensure_plan_editable(plan, month)

    values = {field: getattr(payload.overrides, field) for field in RULE_FIELDS}
    row = session.get(PlanRuleOverride, plan.id)
    if all(value is None for value in values.values()):
        if row is not None:
            session.delete(row)
    else:
        if row is None:
            row = PlanRuleOverride(plan_id=plan.id)
        for field, value in values.items():
            setattr(row, field, value)
        session.add(row)

    if month is not None:
        mark_month_stale(month)

    session.commit()
    return _plan_overrides_public(session, plan, values)
