"""Schedule-plan business rules: scopes, save-and-expand, lifecycle, and copy.

Plans are the only source of plan-generated roster entries. Saving a plan
validates its scopes and day shifts, writes the plan with child rows, and runs
a full company-month expansion in the same transaction (spec sections 5.1 and
5.2). Expansion never modifies manual exceptions.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import NoReturn

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select

from app.core.errors import Blocker, DomainError
from app.enums import (
    PlanStatus,
    RosterSource,
    RosterState,
    ScheduleScopeType,
)
from app.models import (
    AttendanceMonth,
    Department,
    Employee,
    Message,
    PlanDay,
    PlanRuleOverride,
    PlanScope,
    Position,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
    get_datetime_utc,
)
from app.schemas_attendance.core import RulePatch
from app.schemas_attendance.scheduling import (
    PlanCopyPreview,
    PlanCopyRequest,
    PlanDayInput,
    PlanDayPublic,
    PlanScopePublic,
    RosterChangeSummary,
    SchedulePlanConflict,
    SchedulePlanCreate,
    SchedulePlanMutationPublic,
    SchedulePlanPreview,
    SchedulePlanPreviewRequest,
    SchedulePlanPublic,
    SchedulePlansPublic,
    SchedulePlanUpdate,
)
from app.services.attendance import expansion
from app.services.attendance.errors import AttendanceErrorCode
from app.services.attendance.month_state import (
    EXPANSION_BLOCKED_MESSAGE,
)
from app.services.attendance.month_state import (
    ensure_month_editable as _ensure_month_editable,
)
from app.services.attendance.month_state import (
    ensure_month_expandable as _ensure_month_expandable,
)
from app.services.attendance.month_state import (
    existing_month as _existing_month,
)
from app.services.attendance.month_state import (
    get_or_create_month as _get_or_create_month,
)
from app.services.attendance.rules import (
    RULE_FIELDS,
    _override_values,
    get_plan_or_404,
)
from app.services.attendance.staleness import (
    EDITABLE_MONTH_STATUSES,
    mark_month_stale,
)
from app.services.common import paginate
from app.services.companies import get_company_or_404

__all__ = [
    "archive_schedule_plan",
    "copy_preview",
    "copy_schedule_plan",
    "create_schedule_plan",
    "delete_schedule_plan",
    "expand_preview",
    "expand_schedule_plan",
    "get_plan_or_404",
    "get_schedule_plan",
    "list_schedule_plans",
    "preview_schedule_plan",
    "unarchive_schedule_plan",
    "update_schedule_plan",
]

PLAN_NOT_FOUND_MESSAGE = "排班方案不存在"
PLAN_ARCHIVED_MESSAGE = "已归档的排班方案不可修改，请先取消归档"
SCHEDULE_CONFLICT_MESSAGE = "同一范围内已存在其他启用方案"
SCOPE_ALL_WITH_CHILDREN_MESSAGE = "全公司方案不能指定具体范围"
SCOPE_EMPTY_MESSAGE = "请至少选择一个排班范围"
SCOPE_DUPLICATE_MESSAGE = "排班范围不能重复"
SCOPE_TYPE_MISMATCH_MESSAGE = "排班范围类型不匹配"
SCOPE_MISSING_MESSAGE = "排班范围不存在"
SCOPE_INACTIVE_MESSAGE = "排班范围已停用"
CROSS_COMPANY_MESSAGE = "不能引用其他公司的数据"
EMPLOYEE_OUT_OF_RANGE_MESSAGE = "员工不在该月份的任职期间内"
DAY_OUT_OF_MONTH_MESSAGE = "排班日期超出当月天数"
DAY_DUPLICATE_SEQ_MESSAGE = "同一天同一序号只能有一个班次"
DAY_DUPLICATE_SHIFT_MESSAGE = "同一天不能重复排同一班次"
SHIFT_MISSING_MESSAGE = "班次不存在"
SHIFT_INACTIVE_MESSAGE = "班次已停用，无法排班"
INACTIVE_COMPANY_MESSAGE = "公司已停用，无法维护排班方案"
ACTIVATION_BLOCKED_MESSAGE = "无法取消归档：方案引用的班次已停用"
REFERENCED_MESSAGE = "无法删除：仍有排班明细引用该方案"
COPY_TARGET_MESSAGE = "只能复制到下一个自然月"
COPY_OVERWRITE_MESSAGE = "目标月份已有排班明细将被覆盖，请确认覆盖后重试"
SAME_PRECISION_MESSAGE = "同精确度范围存在重复方案，请检查排班数据"

COPY_MANUAL_WARNING = "人工例外永不被方案展开覆盖，仅在勾选时复制。"
COPY_NEXT_MONTH_WARNING = "目标月份使用自己的节假日日历与当前公司规则，节假日不复制。"


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------


def _month_start(month: str) -> date:
    return date(int(month[:4]), int(month[5:7]), 1)


def _month_string(month: date) -> str:
    return month.strftime("%Y-%m")


def _next_month(month: date) -> date:
    if month.month == 12:
        return date(month.year + 1, 1, 1)
    return date(month.year, month.month + 1, 1)


def _month_end(month: date) -> date:
    return expansion.month_bounds(month)[1]


def _scopes_by_plan(
    session: Session, plan_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PlanScope]]:
    result: dict[uuid.UUID, list[PlanScope]] = defaultdict(list)
    if not plan_ids:
        return result
    for scope in session.exec(
        select(PlanScope)
        .where(col(PlanScope.plan_id).in_(plan_ids))
        .order_by(col(PlanScope.id).asc())
    ).all():
        result[scope.plan_id].append(scope)
    return result


def _days_by_plan(
    session: Session, plan_ids: list[uuid.UUID]
) -> dict[uuid.UUID, list[PlanDayPublic]]:
    result: dict[uuid.UUID, list[PlanDayPublic]] = defaultdict(list)
    if not plan_ids:
        return result
    for day_row, shift in session.exec(
        select(PlanDay, Shift)
        .join(Shift, col(PlanDay.shift_id) == col(Shift.id))
        .where(col(PlanDay.plan_id).in_(plan_ids))
        .order_by(
            col(PlanDay.plan_id).asc(),
            col(PlanDay.day_of_month).asc(),
            col(PlanDay.seq).asc(),
        )
    ).all():
        result[day_row.plan_id].append(
            PlanDayPublic(
                id=day_row.id,
                day_of_month=day_row.day_of_month,
                seq=day_row.seq,
                shift_id=day_row.shift_id,
                shift_code=shift.shift_code,
                shift_name=shift.shift_name,
                shift_color=shift.color,
                shift_is_active=shift.is_active,
            )
        )
    return result


def _scope_labels(
    session: Session, scopes: list[PlanScope], scope_type: ScheduleScopeType
) -> dict[uuid.UUID, tuple[str, str]]:
    ids = {scope.scope_id for scope in scopes}
    if not ids:
        return {}

    if scope_type == ScheduleScopeType.DEPT:
        rows = session.exec(
            select(Department.id, Department.dept_code, Department.dept_name).where(
                col(Department.id).in_(ids)
            )
        ).all()
    elif scope_type == ScheduleScopeType.POSITION:
        rows = session.exec(
            select(Position.id, Position.position_code, Position.position_name).where(
                col(Position.id).in_(ids)
            )
        ).all()
    elif scope_type == ScheduleScopeType.EMPLOYEE:
        rows = session.exec(
            select(Employee.id, Employee.employee_no, Employee.name).where(
                col(Employee.id).in_(ids)
            )
        ).all()
    else:
        rows = []
    return {row[0]: (row[1], row[2]) for row in rows}


def _scope_publics(
    session: Session,
    plans: list[SchedulePlan],
    scopes_by_plan: dict[uuid.UUID, list[PlanScope]],
) -> dict[uuid.UUID, list[PlanScopePublic]]:
    labels_by_type: dict[ScheduleScopeType, dict[uuid.UUID, tuple[str, str]]] = {}
    for scope_type in (
        ScheduleScopeType.DEPT,
        ScheduleScopeType.POSITION,
        ScheduleScopeType.EMPLOYEE,
    ):
        scopes = [
            scope
            for plan in plans
            if plan.scope_type == scope_type
            for scope in scopes_by_plan.get(plan.id, [])
        ]
        labels_by_type[scope_type] = _scope_labels(session, scopes, scope_type)

    result: dict[uuid.UUID, list[PlanScopePublic]] = defaultdict(list)
    for plan in plans:
        labels = labels_by_type.get(plan.scope_type, {})
        for scope in scopes_by_plan.get(plan.id, []):
            code, name = labels.get(scope.scope_id, (None, None))
            result[plan.id].append(
                PlanScopePublic(
                    id=scope.id,
                    scope_id=scope.scope_id,
                    scope_code=code,
                    scope_name=name,
                )
            )
    return result


def _plan_publics(
    session: Session, plans: list[SchedulePlan]
) -> list[SchedulePlanPublic]:
    plan_ids = [plan.id for plan in plans]
    scopes = _scopes_by_plan(session, plan_ids)
    scope_publics = _scope_publics(session, plans, scopes)
    days = _days_by_plan(session, plan_ids)
    return [
        SchedulePlanPublic(
            id=plan.id,
            company_id=plan.company_id,
            month=_month_string(plan.month),
            plan_name=plan.plan_name,
            scope_type=plan.scope_type,
            status=plan.status,
            copied_from_plan_id=plan.copied_from_plan_id,
            note=plan.note,
            scopes=scope_publics.get(plan.id, []),
            days=days.get(plan.id, []),
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )
        for plan in plans
    ]


def _plan_public(session: Session, plan: SchedulePlan) -> SchedulePlanPublic:
    return _plan_publics(session, [plan])[0]


def list_schedule_plans(
    session: Session,
    *,
    company_id: uuid.UUID,
    month: str | None,
    status: PlanStatus | None,
    scope_type: ScheduleScopeType | None,
    keyword: str | None,
    skip: int,
    limit: int,
) -> SchedulePlansPublic:
    """List plans for one company ordered by month, name, and id."""
    get_company_or_404(session, company_id)

    filters: list[ColumnElement[bool]] = [col(SchedulePlan.company_id) == company_id]
    if month is not None:
        filters.append(col(SchedulePlan.month) == _month_start(month))
    if status is not None:
        filters.append(col(SchedulePlan.status) == status)
    if scope_type is not None:
        filters.append(col(SchedulePlan.scope_type) == scope_type)
    normalized_keyword = keyword.strip() if keyword else ""
    if normalized_keyword:
        filters.append(col(SchedulePlan.plan_name).ilike(f"%{normalized_keyword}%"))

    statement = (
        select(SchedulePlan)
        .where(*filters)
        .order_by(
            col(SchedulePlan.month).desc(),
            col(SchedulePlan.plan_name).asc(),
            col(SchedulePlan.id).asc(),
        )
    )
    count_statement = select(func.count()).select_from(SchedulePlan).where(*filters)
    plans, count = paginate(session, statement, count_statement, skip=skip, limit=limit)
    return SchedulePlansPublic(
        data=_plan_publics(session, list(plans)),
        count=count,
    )


def get_schedule_plan(session: Session, plan_id: uuid.UUID) -> SchedulePlanPublic:
    return _plan_public(session, get_plan_or_404(session, plan_id))


# ---------------------------------------------------------------------------
# Month and validation helpers
# ---------------------------------------------------------------------------


def _ensure_plan_mutable(plan: SchedulePlan, month: AttendanceMonth | None) -> None:
    if plan.status == PlanStatus.ARCHIVED:
        raise DomainError(AttendanceErrorCode.PLAN_ARCHIVED, PLAN_ARCHIVED_MESSAGE)
    if month is not None:
        _ensure_month_editable(month)


def _ensure_plan_expandable(plan: SchedulePlan, month: AttendanceMonth | None) -> None:
    if plan.status == PlanStatus.ARCHIVED:
        raise DomainError(AttendanceErrorCode.PLAN_ARCHIVED, PLAN_ARCHIVED_MESSAGE)
    if month is not None:
        _ensure_month_expandable(month)


def _scope_error(
    code: AttendanceErrorCode, message: str, field: str = "scope_ids"
) -> DomainError:
    return DomainError(code, message, field_errors={field: message})


def _type_mismatch(session: Session, scope_id: uuid.UUID, label: str) -> NoReturn:
    """Raise the right error for a scope id that is not in the expected table."""
    if (
        session.get(Department, scope_id) is not None
        or session.get(Position, scope_id) is not None
        or session.get(Employee, scope_id) is not None
    ):
        raise _scope_error(
            AttendanceErrorCode.INVALID_SCOPE,
            f"{SCOPE_TYPE_MISMATCH_MESSAGE}：{label}",
        )
    raise _scope_error(
        AttendanceErrorCode.INVALID_REFERENCE, f"{SCOPE_MISSING_MESSAGE}：{label}"
    )


def _validate_dept_scope(
    session: Session, company_id: uuid.UUID, scope_id: uuid.UUID
) -> None:
    department = session.get(Department, scope_id)
    if department is None:
        _type_mismatch(session, scope_id, str(scope_id))
    if department.company_id != company_id:
        raise _scope_error(AttendanceErrorCode.CROSS_COMPANY, CROSS_COMPANY_MESSAGE)
    if not department.is_active:
        raise _scope_error(
            AttendanceErrorCode.INACTIVE_REFERENCE, SCOPE_INACTIVE_MESSAGE
        )


def _validate_position_scope(
    session: Session, company_id: uuid.UUID, scope_id: uuid.UUID
) -> None:
    position = session.get(Position, scope_id)
    if position is None:
        _type_mismatch(session, scope_id, str(scope_id))
    if position.company_id != company_id:
        raise _scope_error(AttendanceErrorCode.CROSS_COMPANY, CROSS_COMPANY_MESSAGE)
    if not position.is_active:
        raise _scope_error(
            AttendanceErrorCode.INACTIVE_REFERENCE, SCOPE_INACTIVE_MESSAGE
        )


def _validate_employee_scope(
    session: Session, company_id: uuid.UUID, scope_id: uuid.UUID, month: date
) -> None:
    employee = session.get(Employee, scope_id)
    if employee is None:
        _type_mismatch(session, scope_id, str(scope_id))
    department = session.get(Department, employee.dept_id)
    if department is None or department.company_id != company_id:
        raise _scope_error(AttendanceErrorCode.CROSS_COMPANY, CROSS_COMPANY_MESSAGE)
    month_end = _month_end(month)
    if employee.hire_date > month_end or (
        employee.resign_date is not None and employee.resign_date < month
    ):
        raise _scope_error(
            AttendanceErrorCode.EMPLOYEE_OUT_OF_RANGE,
            EMPLOYEE_OUT_OF_RANGE_MESSAGE,
        )


def _validate_scopes(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    scope_type: ScheduleScopeType,
    scope_ids: list[uuid.UUID],
) -> None:
    if len(set(scope_ids)) != len(scope_ids):
        raise _scope_error(AttendanceErrorCode.INVALID_SCOPE, SCOPE_DUPLICATE_MESSAGE)
    if scope_type == ScheduleScopeType.ALL:
        if scope_ids:
            raise _scope_error(
                AttendanceErrorCode.INVALID_SCOPE, SCOPE_ALL_WITH_CHILDREN_MESSAGE
            )
        return
    if not scope_ids:
        raise _scope_error(AttendanceErrorCode.INVALID_SCOPE, SCOPE_EMPTY_MESSAGE)
    for scope_id in scope_ids:
        if scope_type == ScheduleScopeType.DEPT:
            _validate_dept_scope(session, company_id, scope_id)
        elif scope_type == ScheduleScopeType.POSITION:
            _validate_position_scope(session, company_id, scope_id)
        else:
            _validate_employee_scope(session, company_id, scope_id, month)


def _load_day_shifts(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    days: list[PlanDayInput],
) -> dict[uuid.UUID, Shift]:
    """Validate day rows and return the referenced shifts by id."""
    last_day = expansion.days_in_month(month)
    seen_seq: set[tuple[int, int]] = set()
    seen_shift: set[tuple[int, uuid.UUID]] = set()
    shifts: dict[uuid.UUID, Shift] = {}
    for day in days:
        if day.day_of_month > last_day:
            raise _scope_error(
                AttendanceErrorCode.INVALID_SCOPE, DAY_OUT_OF_MONTH_MESSAGE, "days"
            )
        seq_key = (day.day_of_month, day.seq)
        if seq_key in seen_seq:
            raise _scope_error(
                AttendanceErrorCode.INVALID_SCOPE, DAY_DUPLICATE_SEQ_MESSAGE, "days"
            )
        seen_seq.add(seq_key)
        shift_key = (day.day_of_month, day.shift_id)
        if shift_key in seen_shift:
            raise _scope_error(
                AttendanceErrorCode.INVALID_SCOPE,
                DAY_DUPLICATE_SHIFT_MESSAGE,
                "days",
            )
        seen_shift.add(shift_key)
        shift = shifts.get(day.shift_id)
        if shift is None:
            shift = session.get(Shift, day.shift_id)
            if shift is None:
                raise _scope_error(
                    AttendanceErrorCode.INVALID_REFERENCE,
                    SHIFT_MISSING_MESSAGE,
                    "days",
                )
            shifts[day.shift_id] = shift
        if shift.company_id != company_id:
            raise _scope_error(
                AttendanceErrorCode.CROSS_COMPANY, CROSS_COMPANY_MESSAGE, "days"
            )
        if not shift.is_active:
            raise _scope_error(
                AttendanceErrorCode.INACTIVE_REFERENCE,
                SHIFT_INACTIVE_MESSAGE,
                "days",
            )
    return shifts


def _conflict_rows(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    scope_type: ScheduleScopeType,
    scope_ids: list[uuid.UUID],
    *,
    exclude_plan_id: uuid.UUID | None,
) -> list[SchedulePlanConflict]:
    filters: list[ColumnElement[bool]] = [
        col(SchedulePlan.company_id) == company_id,
        col(SchedulePlan.month) == month,
        col(SchedulePlan.status) == PlanStatus.ENABLED,
        col(SchedulePlan.scope_type) == scope_type,
    ]
    if exclude_plan_id is not None:
        filters.append(col(SchedulePlan.id) != exclude_plan_id)

    plans = session.exec(select(SchedulePlan).where(*filters)).all()
    if not plans:
        return []
    if scope_type == ScheduleScopeType.ALL:
        return sorted(
            (
                SchedulePlanConflict(
                    scope_type=plan.scope_type,
                    scope_id=company_id,
                    plan_id=plan.id,
                    plan_name=plan.plan_name,
                )
                for plan in plans
            ),
            key=lambda conflict: (conflict.plan_name, str(conflict.plan_id)),
        )

    wanted = set(scope_ids)
    if not wanted:
        return []
    plan_by_id = {plan.id: plan for plan in plans}
    scope_rows = session.exec(
        select(PlanScope).where(
            col(PlanScope.plan_id).in_(list(plan_by_id)),
            col(PlanScope.scope_id).in_(list(wanted)),
        )
    ).all()
    conflicts = [
        SchedulePlanConflict(
            scope_type=scope_type,
            scope_id=scope.scope_id,
            plan_id=scope.plan_id,
            plan_name=plan_by_id[scope.plan_id].plan_name,
        )
        for scope in scope_rows
    ]
    return sorted(
        conflicts,
        key=lambda conflict: (
            conflict.plan_name,
            str(conflict.scope_id),
            str(conflict.plan_id),
        ),
    )


def _raise_on_conflict(conflicts: list[SchedulePlanConflict]) -> None:
    if not conflicts:
        return
    blocker_plan_names = "、".join(
        sorted({conflict.plan_name for conflict in conflicts})
    )
    message = f"{SCHEDULE_CONFLICT_MESSAGE}：{blocker_plan_names}"
    raise DomainError(
        AttendanceErrorCode.SCHEDULE_CONFLICT,
        message,
        field_errors={"scope_ids": message},
    )


def _scope_ids_for_plan(session: Session, plan_id: uuid.UUID) -> list[uuid.UUID]:
    return [
        scope.scope_id
        for scope in session.exec(
            select(PlanScope).where(col(PlanScope.plan_id) == plan_id)
        ).all()
    ]


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _replace_scopes(
    session: Session, plan: SchedulePlan, scope_ids: list[uuid.UUID]
) -> None:
    for scope in session.exec(
        select(PlanScope).where(col(PlanScope.plan_id) == plan.id)
    ).all():
        session.delete(scope)
    session.flush()
    for scope_id in scope_ids:
        session.add(PlanScope(plan_id=plan.id, scope_id=scope_id))


def _replace_days(
    session: Session,
    plan: SchedulePlan,
    days: list[PlanDayInput],
    shifts: dict[uuid.UUID, Shift],
) -> None:
    for day_row in session.exec(
        select(PlanDay).where(col(PlanDay.plan_id) == plan.id)
    ).all():
        session.delete(day_row)
    session.flush()
    for day in days:
        session.add(
            PlanDay(
                plan_id=plan.id,
                day_of_month=day.day_of_month,
                seq=day.seq,
                shift_id=shifts[day.shift_id].id,
            )
        )


def _replace_overrides(
    session: Session, plan: SchedulePlan, patch: RulePatch | None
) -> None:
    """Replace the plan override row; an all-null patch clears it."""
    row = session.get(PlanRuleOverride, plan.id)
    if patch is None:
        if row is not None:
            session.delete(row)
        return
    values = {field: getattr(patch, field) for field in RULE_FIELDS}
    if all(value is None for value in values.values()):
        if row is not None:
            session.delete(row)
        return
    if row is None:
        row = PlanRuleOverride(plan_id=plan.id)
    for field, value in values.items():
        setattr(row, field, value)
    session.add(row)


def _change_summary(change: expansion.RosterChange) -> RosterChangeSummary:
    return RosterChangeSummary(
        added=change.added,
        updated=change.updated,
        deleted=change.deleted,
        manual_preserved=change.manual_preserved,
    )


def _run_expansion(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    month_row: AttendanceMonth,
) -> expansion.RosterChange:
    try:
        change = expansion.expand_month(session, company_id, month)
    except expansion.SamePrecisionConflict:
        raise DomainError(AttendanceErrorCode.SCHEDULE_CONFLICT, SAME_PRECISION_MESSAGE)
    mark_month_stale(month_row)
    return change


def _resolve_month_row(
    session: Session,
    plan: SchedulePlan,
    month_row: AttendanceMonth | None,
) -> AttendanceMonth:
    """Use the locked month row, or create the month for factory/legacy plans."""
    if month_row is not None:
        return month_row
    return _get_or_create_month(session, plan.company_id, plan.month)


def _finish_mutation(
    session: Session,
    plan: SchedulePlan,
    month_row: AttendanceMonth | None,
    change: expansion.RosterChange,
) -> SchedulePlanMutationPublic:
    session.commit()
    session.refresh(plan)
    return _mutation_response(session, plan, change, month_row)


def _mutation_response(
    session: Session,
    plan: SchedulePlan,
    change: expansion.RosterChange | None,
    month_row: AttendanceMonth | None,
) -> SchedulePlanMutationPublic:
    return SchedulePlanMutationPublic(
        plan=_plan_public(session, plan),
        roster_change=(
            _change_summary(change) if change is not None else RosterChangeSummary()
        ),
        month_stale=bool(month_row.is_stale) if month_row is not None else False,
    )


# ---------------------------------------------------------------------------
# Create / update
# ---------------------------------------------------------------------------


def create_schedule_plan(
    session: Session, payload: SchedulePlanCreate
) -> SchedulePlanPublic:
    company = get_company_or_404(session, payload.company_id)
    if not company.is_active:
        raise DomainError(
            AttendanceErrorCode.INACTIVE_REFERENCE,
            INACTIVE_COMPANY_MESSAGE,
            field_errors={"company_id": INACTIVE_COMPANY_MESSAGE},
        )
    month = _month_start(payload.month)
    month_row = _get_or_create_month(session, company.id, month)
    _ensure_month_editable(month_row)

    _validate_scopes(session, company.id, month, payload.scope_type, payload.scope_ids)
    shifts = _load_day_shifts(session, company.id, month, payload.days)
    _raise_on_conflict(
        _conflict_rows(
            session,
            company.id,
            month,
            payload.scope_type,
            payload.scope_ids,
            exclude_plan_id=None,
        )
    )

    plan = SchedulePlan(
        company_id=company.id,
        month=month,
        plan_name=payload.plan_name,
        scope_type=payload.scope_type,
        status=PlanStatus.ENABLED,
        note=payload.note,
    )
    session.add(plan)
    session.flush()
    _replace_scopes(session, plan, payload.scope_ids)
    _replace_days(session, plan, payload.days, shifts)
    if payload.rule_overrides is not None:
        _replace_overrides(session, plan, payload.rule_overrides)
    session.flush()

    _run_expansion(session, company.id, month, month_row)
    session.commit()
    session.refresh(plan)
    return _plan_public(session, plan)


def update_schedule_plan(
    session: Session, plan_id: uuid.UUID, payload: SchedulePlanUpdate
) -> SchedulePlanPublic:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month, for_update=True)
    _ensure_plan_mutable(plan, month_row)
    fields = payload.model_fields_set

    scope_type = payload.scope_type if "scope_type" in fields else plan.scope_type
    if scope_type is None:
        raise AssertionError("scope_type is non-nullable")
    scope_ids = (
        list(payload.scope_ids or [])
        if "scope_ids" in fields
        else _scope_ids_for_plan(session, plan.id)
    )
    _validate_scopes(session, plan.company_id, plan.month, scope_type, scope_ids)

    days = payload.days if "days" in fields else None
    shifts = (
        _load_day_shifts(session, plan.company_id, plan.month, days or [])
        if days is not None
        else {}
    )
    _raise_on_conflict(
        _conflict_rows(
            session,
            plan.company_id,
            plan.month,
            scope_type,
            scope_ids,
            exclude_plan_id=plan.id,
        )
    )

    if "plan_name" in fields:
        plan.plan_name = payload.plan_name or plan.plan_name
    if "note" in fields:
        plan.note = payload.note
    plan.scope_type = scope_type
    plan.updated_at = get_datetime_utc()
    session.add(plan)
    if "scope_ids" in fields or "scope_type" in fields:
        _replace_scopes(session, plan, scope_ids)
    if days is not None:
        _replace_days(session, plan, days, shifts)
    if "rule_overrides" in fields:
        _replace_overrides(session, plan, payload.rule_overrides)
    session.flush()

    month = _resolve_month_row(session, plan, month_row)
    _run_expansion(session, plan.company_id, plan.month, month)
    session.commit()
    session.refresh(plan)
    return _plan_public(session, plan)


# ---------------------------------------------------------------------------
# Preview and explicit expansion
# ---------------------------------------------------------------------------


def _warnings_for_days(session: Session, days: list[PlanDayInput]) -> list[str]:
    shifts = {
        shift.id: shift
        for shift in session.exec(
            select(Shift).where(col(Shift.id).in_({day.shift_id for day in days}))
        ).all()
    }
    rows = [
        (day.day_of_month, shifts[day.shift_id])
        for day in sorted(days, key=lambda day: (day.day_of_month, day.seq))
        if day.shift_id in shifts
    ]
    return expansion.shift_overlap_warnings(rows)


def _proposed_candidate(
    plan_id: uuid.UUID,
    plan_name: str,
    scope_type: ScheduleScopeType,
    scope_ids: list[uuid.UUID],
    days: list[PlanDayInput],
    shifts: dict[uuid.UUID, Shift],
) -> expansion.PlanCandidate:
    by_day: dict[int, list[tuple[int, Shift]]] = defaultdict(list)
    for day in days:
        by_day[day.day_of_month].append((day.seq, shifts[day.shift_id]))
    return expansion.PlanCandidate(
        plan_id=plan_id,
        plan_name=plan_name,
        scope_type=scope_type,
        scope_ids=frozenset(scope_ids),
        shifts_by_day={
            day: tuple(shift for _, shift in sorted(rows, key=lambda row: row[0]))
            for day, rows in by_day.items()
        },
    )


def _simulate(
    session: Session,
    company_id: uuid.UUID,
    month: date,
    candidates: list[expansion.PlanCandidate],
) -> expansion.RosterChange:
    try:
        plan = expansion.plan_expansion(session, company_id, month, candidates)
    except expansion.SamePrecisionConflict:
        return expansion.RosterChange()
    return plan.change()


def preview_schedule_plan(
    session: Session, payload: SchedulePlanPreviewRequest
) -> SchedulePlanPreview:
    company = get_company_or_404(session, payload.company_id)
    month = _month_start(payload.month)
    month_row = _existing_month(session, company.id, month)
    if month_row is not None and month_row.status not in EDITABLE_MONTH_STATUSES:
        raise DomainError(
            AttendanceErrorCode.SCHEDULE_EXPANSION_BLOCKED, EXPANSION_BLOCKED_MESSAGE
        )

    existing_plan: SchedulePlan | None = None
    if payload.plan_id is not None:
        existing_plan = get_plan_or_404(session, payload.plan_id)
        if existing_plan.company_id != company.id:
            raise DomainError(AttendanceErrorCode.CROSS_COMPANY, CROSS_COMPANY_MESSAGE)
        if existing_plan.month != month:
            raise DomainError(
                AttendanceErrorCode.INVALID_REFERENCE,
                "排班方案与目标月份不一致",
            )
        if existing_plan.status == PlanStatus.ARCHIVED:
            raise DomainError(AttendanceErrorCode.PLAN_ARCHIVED, PLAN_ARCHIVED_MESSAGE)

    _validate_scopes(session, company.id, month, payload.scope_type, payload.scope_ids)
    shifts = _load_day_shifts(session, company.id, month, payload.days)
    conflicts = _conflict_rows(
        session,
        company.id,
        month,
        payload.scope_type,
        payload.scope_ids,
        exclude_plan_id=payload.plan_id,
    )
    candidate = _proposed_candidate(
        payload.plan_id or uuid.uuid4(),
        existing_plan.plan_name if existing_plan is not None else "预览方案",
        payload.scope_type,
        payload.scope_ids,
        payload.days,
        shifts,
    )
    candidates = expansion.load_candidates(
        session,
        company.id,
        month,
        excluded_plan_ids={payload.plan_id} if payload.plan_id else None,
    )
    warnings = _warnings_for_days(session, payload.days)

    conflicting_plan_ids = {conflict.plan_id for conflict in conflicts}
    effective_candidates = [
        item for item in candidates if item.plan_id not in conflicting_plan_ids
    ] + [candidate]
    change = _simulate(session, company.id, month, effective_candidates)
    return SchedulePlanPreview(
        can_apply=not conflicts,
        affected_employees=len(change.affected_employee_ids),
        added=change.added,
        updated=change.updated,
        deleted=change.deleted,
        manual_preserved=change.manual_preserved,
        conflicts=conflicts,
        warnings=warnings,
    )


def expand_preview(session: Session, plan_id: uuid.UUID) -> SchedulePlanPreview:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month)
    _ensure_plan_expandable(plan, month_row)

    scope_ids = _scope_ids_for_plan(session, plan.id)
    conflicts = _conflict_rows(
        session,
        plan.company_id,
        plan.month,
        plan.scope_type,
        scope_ids,
        exclude_plan_id=plan.id,
    )
    candidates = expansion.load_candidates(session, plan.company_id, plan.month)
    change = _simulate(session, plan.company_id, plan.month, candidates)
    warnings = _warnings_for_plan(session, plan)
    return SchedulePlanPreview(
        can_apply=not conflicts,
        affected_employees=len(change.affected_employee_ids),
        added=change.added,
        updated=change.updated,
        deleted=change.deleted,
        manual_preserved=change.manual_preserved,
        conflicts=conflicts,
        warnings=warnings,
    )


def _warnings_for_plan(session: Session, plan: SchedulePlan) -> list[str]:
    rows = session.exec(
        select(PlanDay, Shift)
        .join(Shift, col(PlanDay.shift_id) == col(Shift.id))
        .where(col(PlanDay.plan_id) == plan.id)
        .order_by(col(PlanDay.day_of_month).asc(), col(PlanDay.seq).asc())
    ).all()
    return expansion.shift_overlap_warnings(
        [(day_row.day_of_month, shift) for day_row, shift in rows]
    )


def expand_schedule_plan(
    session: Session, plan_id: uuid.UUID
) -> SchedulePlanMutationPublic:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month, for_update=True)
    _ensure_plan_expandable(plan, month_row)
    month = _resolve_month_row(session, plan, month_row)
    change = _run_expansion(session, plan.company_id, plan.month, month)
    return _finish_mutation(session, plan, month, change)


# ---------------------------------------------------------------------------
# Archive / unarchive / delete
# ---------------------------------------------------------------------------


def archive_schedule_plan(
    session: Session, plan_id: uuid.UUID
) -> SchedulePlanMutationPublic:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month, for_update=True)
    if month_row is not None:
        _ensure_month_editable(month_row)
    if plan.status == PlanStatus.ARCHIVED:
        return _mutation_response(session, plan, None, month_row)
    plan.status = PlanStatus.ARCHIVED
    plan.updated_at = get_datetime_utc()
    session.add(plan)
    session.flush()
    month = _resolve_month_row(session, plan, month_row)
    change = _run_expansion(session, plan.company_id, plan.month, month)
    return _finish_mutation(session, plan, month, change)


def _inactive_shift_blockers(session: Session, plan: SchedulePlan) -> list[Blocker]:
    rows = session.exec(
        select(Shift)
        .join(PlanDay, col(PlanDay.shift_id) == col(Shift.id))
        .where(col(PlanDay.plan_id) == plan.id, col(Shift.is_active).is_(False))
        .distinct()
        .order_by(col(Shift.shift_code).asc())
    ).all()
    return [
        Blocker(
            type="shift",
            id=shift.id,
            code=shift.shift_code,
            label=shift.shift_name,
        )
        for shift in rows
    ]


def unarchive_schedule_plan(
    session: Session, plan_id: uuid.UUID
) -> SchedulePlanMutationPublic:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month, for_update=True)
    if month_row is not None:
        _ensure_month_editable(month_row)
    if plan.status == PlanStatus.ENABLED:
        return _mutation_response(session, plan, None, month_row)

    scope_ids = _scope_ids_for_plan(session, plan.id)
    _raise_on_conflict(
        _conflict_rows(
            session,
            plan.company_id,
            plan.month,
            plan.scope_type,
            scope_ids,
            exclude_plan_id=plan.id,
        )
    )
    blockers = _inactive_shift_blockers(session, plan)
    if blockers:
        raise DomainError(
            AttendanceErrorCode.ACTIVATION_BLOCKED,
            ACTIVATION_BLOCKED_MESSAGE,
            blockers=blockers[:20],
            blocker_count=len(blockers),
        )

    plan.status = PlanStatus.ENABLED
    plan.updated_at = get_datetime_utc()
    session.add(plan)
    session.flush()
    month = _resolve_month_row(session, plan, month_row)
    change = _run_expansion(session, plan.company_id, plan.month, month)
    return _finish_mutation(session, plan, month, change)


def _plan_reference_blockers(
    session: Session, plan_id: uuid.UUID
) -> tuple[int, list[Blocker]]:
    filters: list[ColumnElement[bool]] = [col(RosterEntry.plan_id) == plan_id]
    total = session.exec(
        select(func.count()).select_from(RosterEntry).where(*filters)
    ).one()
    rows = session.exec(
        select(RosterEntry, Employee)
        .join(Employee, col(RosterEntry.employee_id) == col(Employee.id))
        .where(*filters)
        .order_by(col(Employee.employee_no).asc(), col(RosterEntry.work_date).asc())
        .limit(20)
    ).all()
    blockers = [
        Blocker(
            type="roster_entry",
            id=entry.id,
            code=employee.employee_no,
            label=f"{employee.name} {entry.work_date.isoformat()}",
        )
        for entry, employee in rows
    ]
    return total, blockers


def delete_schedule_plan(session: Session, plan_id: uuid.UUID) -> Message:
    plan = get_plan_or_404(session, plan_id)
    month_row = _existing_month(session, plan.company_id, plan.month, for_update=True)
    if month_row is not None:
        _ensure_month_editable(month_row)
    total, blockers = _plan_reference_blockers(session, plan.id)
    if total:
        raise DomainError(
            AttendanceErrorCode.REFERENCED,
            REFERENCED_MESSAGE,
            blockers=blockers,
            blocker_count=total,
        )
    session.delete(plan)
    session.commit()
    return Message(message="排班方案删除成功")


# ---------------------------------------------------------------------------
# Copy to next month
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _CopiedManualEntry:
    employee_id: uuid.UUID
    work_date: date
    state: RosterState
    shifts: list[RosterEntryShift]


@dataclass
class _CopyPlan:
    target: date
    days: list[PlanDayInput]
    shifts: dict[uuid.UUID, Shift]
    conflicts: list[SchedulePlanConflict]
    warnings: list[str]
    change: expansion.RosterChange
    copied_manual: dict[tuple[uuid.UUID, date], _CopiedManualEntry]


def _copied_manual_entries(
    session: Session, source_plan: SchedulePlan, target_month: date
) -> tuple[dict[tuple[uuid.UUID, date], _CopiedManualEntry], int, int]:
    """Map source-month manual exceptions onto target-month dates.

    Returns the entries to copy, the count skipped because the target date does
    not exist or the employee is out of range, and the count skipped because
    the target date already has a manual exception (never overwritten).
    """
    start, end = expansion.month_bounds(source_plan.month)
    target_end = _month_end(target_month)
    entries = session.exec(
        select(RosterEntry).where(
            col(RosterEntry.company_id) == source_plan.company_id,
            col(RosterEntry.work_date) >= start,
            col(RosterEntry.work_date) <= end,
            col(RosterEntry.source) == RosterSource.MANUAL,
        )
    ).all()
    shifts_by_entry: dict[uuid.UUID, list[RosterEntryShift]] = defaultdict(list)
    if entries:
        for shift in session.exec(
            select(RosterEntryShift)
            .where(col(RosterEntryShift.roster_entry_id).in_([e.id for e in entries]))
            .order_by(col(RosterEntryShift.seq).asc())
        ).all():
            shifts_by_entry[shift.roster_entry_id].append(shift)

    target_entries = {
        (entry.employee_id, entry.work_date): entry
        for entry in session.exec(
            select(RosterEntry).where(
                col(RosterEntry.company_id) == source_plan.company_id,
                col(RosterEntry.work_date) >= target_month,
                col(RosterEntry.work_date) <= target_end,
            )
        ).all()
    }

    copied: dict[tuple[uuid.UUID, date], _CopiedManualEntry] = {}
    skipped = 0
    preserved = 0
    for entry in entries:
        if entry.work_date.day > target_end.day:
            skipped += 1
            continue
        target_date = date(target_month.year, target_month.month, entry.work_date.day)
        employee = session.get(Employee, entry.employee_id)
        if employee is None:
            skipped += 1
            continue
        if target_date < employee.hire_date or (
            employee.resign_date is not None and target_date > employee.resign_date
        ):
            skipped += 1
            continue
        existing = target_entries.get((entry.employee_id, target_date))
        if existing is not None and existing.source == RosterSource.MANUAL:
            preserved += 1
            continue
        copied[(entry.employee_id, target_date)] = _CopiedManualEntry(
            employee_id=entry.employee_id,
            work_date=target_date,
            state=entry.state,
            shifts=shifts_by_entry.get(entry.id, []),
        )
    return copied, skipped, preserved


def _copy_warnings(
    source_plan: SchedulePlan,
    target_month: date,
    copied_count: int,
    skipped: int,
    preserved: int,
    change: expansion.RosterChange,
) -> list[str]:
    warnings: list[str] = []
    source_days = expansion.days_in_month(source_plan.month)
    target_days = expansion.days_in_month(target_month)
    if target_days > source_days:
        warnings.append(
            f"目标月份比源月份多 {target_days - source_days} 天，"
            f"第 {source_days + 1} 天起没有对应日期号，按休息处理，请补充排班。"
        )
    elif source_days > target_days:
        warnings.append(
            f"目标月份比源月份少 {source_days - target_days} 天，"
            "源月末尾的排班日期号将被丢弃。"
        )
    if copied_count:
        warnings.append(f"将复制 {copied_count} 条人工例外（仅目标月存在的日期号）。")
    if skipped:
        warnings.append(f"{skipped} 条人工例外因目标月没有对应日期或员工不在职而跳过。")
    if preserved:
        warnings.append(f"{preserved} 条目标月已有的人工例外保持不变。")
    if change.manual_preserved:
        warnings.append(
            f"目标月份有 {change.manual_preserved} 条人工例外，方案展开不会覆盖。"
        )
    if change.updated or change.deleted:
        warnings.append(
            f"目标月份已有 {change.updated + change.deleted} 条方案排班明细将被覆盖，"
            "复制时需要确认覆盖。"
        )
    warnings.append(COPY_MANUAL_WARNING)
    warnings.append(COPY_NEXT_MONTH_WARNING)
    return warnings


def _copy_payload(
    session: Session, source_plan: SchedulePlan, payload: PlanCopyRequest
) -> _CopyPlan:
    target = _month_start(payload.target_month)
    if target != _next_month(source_plan.month):
        raise DomainError(AttendanceErrorCode.INVALID_SCOPE, COPY_TARGET_MESSAGE)
    target_row = _existing_month(session, source_plan.company_id, target)
    if target_row is not None and target_row.status not in EDITABLE_MONTH_STATUSES:
        raise DomainError(
            AttendanceErrorCode.SCHEDULE_EXPANSION_BLOCKED, EXPANSION_BLOCKED_MESSAGE
        )

    source_days = session.exec(
        select(PlanDay).where(col(PlanDay.plan_id) == source_plan.id)
    ).all()
    target_days_count = expansion.days_in_month(target)
    mapped_days = sorted(
        (
            PlanDayInput(
                day_of_month=day_row.day_of_month,
                seq=day_row.seq,
                shift_id=day_row.shift_id,
            )
            for day_row in source_days
            if day_row.day_of_month <= target_days_count
        ),
        key=lambda day: (day.day_of_month, day.seq),
    )
    shifts = _load_day_shifts(session, source_plan.company_id, target, mapped_days)

    scope_ids = _scope_ids_for_plan(session, source_plan.id)
    conflicts = _conflict_rows(
        session,
        source_plan.company_id,
        target,
        source_plan.scope_type,
        scope_ids,
        exclude_plan_id=None,
    )

    copied_manual: dict[tuple[uuid.UUID, date], _CopiedManualEntry] = {}
    skipped = preserved = 0
    if payload.include_manual_exceptions:
        copied_manual, skipped, preserved = _copied_manual_entries(
            session, source_plan, target
        )

    candidate = _proposed_candidate(
        uuid.uuid4(),
        source_plan.plan_name,
        source_plan.scope_type,
        scope_ids,
        mapped_days,
        shifts,
    )
    candidates = expansion.load_candidates(session, source_plan.company_id, target)
    conflicting_plan_ids = {conflict.plan_id for conflict in conflicts}
    effective = [
        item for item in candidates if item.plan_id not in conflicting_plan_ids
    ] + [candidate]
    try:
        simulation = expansion.plan_expansion(
            session,
            source_plan.company_id,
            target,
            effective,
            reserved_keys=set(copied_manual),
        )
        change = simulation.change()
    except expansion.SamePrecisionConflict:
        change = expansion.RosterChange()
    return _CopyPlan(
        target=target,
        days=mapped_days,
        shifts=shifts,
        conflicts=conflicts,
        warnings=_copy_warnings(
            source_plan, target, len(copied_manual), skipped, preserved, change
        ),
        change=change,
        copied_manual=copied_manual,
    )


def copy_preview(
    session: Session, plan_id: uuid.UUID, payload: PlanCopyRequest
) -> PlanCopyPreview:
    source_plan = get_plan_or_404(session, plan_id)
    copy_plan = _copy_payload(session, source_plan, payload)
    return PlanCopyPreview(
        target_month=_month_string(copy_plan.target),
        can_apply=not copy_plan.conflicts,
        added=copy_plan.change.added,
        updated=copy_plan.change.updated,
        deleted=copy_plan.change.deleted,
        manual_preserved=copy_plan.change.manual_preserved,
        conflicts=copy_plan.conflicts,
        warnings=copy_plan.warnings,
    )


def copy_schedule_plan(
    session: Session, plan_id: uuid.UUID, payload: PlanCopyRequest
) -> SchedulePlanPublic:
    source_plan = get_plan_or_404(session, plan_id)
    copy_plan = _copy_payload(session, source_plan, payload)
    _raise_on_conflict(copy_plan.conflicts)
    if (
        copy_plan.change.updated or copy_plan.change.deleted
    ) and not payload.confirm_overwrite:
        raise DomainError(AttendanceErrorCode.SCHEDULE_CONFLICT, COPY_OVERWRITE_MESSAGE)

    target_row = _get_or_create_month(session, source_plan.company_id, copy_plan.target)
    _ensure_month_expandable(target_row)

    new_plan = SchedulePlan(
        company_id=source_plan.company_id,
        month=copy_plan.target,
        plan_name=source_plan.plan_name,
        scope_type=source_plan.scope_type,
        status=PlanStatus.ENABLED,
        copied_from_plan_id=source_plan.id,
        note=source_plan.note,
    )
    session.add(new_plan)
    session.flush()
    _replace_scopes(session, new_plan, _scope_ids_for_plan(session, source_plan.id))
    _replace_days(session, new_plan, copy_plan.days, copy_plan.shifts)
    source_overrides = session.get(PlanRuleOverride, source_plan.id)
    if source_overrides is not None:
        session.add(
            PlanRuleOverride(plan_id=new_plan.id, **_override_values(source_overrides))
        )
    session.flush()

    _insert_copied_manuals(session, new_plan, copy_plan.copied_manual)
    _run_expansion(session, source_plan.company_id, copy_plan.target, target_row)
    session.commit()
    session.refresh(new_plan)
    return _plan_public(session, new_plan)


def _insert_copied_manuals(
    session: Session,
    new_plan: SchedulePlan,
    copied: dict[tuple[uuid.UUID, date], _CopiedManualEntry],
) -> None:
    if not copied:
        return
    candidates = expansion.load_candidates(session, new_plan.company_id, new_plan.month)
    employees = {
        employee.id: employee
        for employee in session.exec(
            select(Employee).where(col(Employee.id).in_({key[0] for key in copied}))
        ).all()
    }
    for key in sorted(copied, key=lambda item: (str(item[0]), item[1])):
        copied_entry = copied[key]
        employee = employees.get(copied_entry.employee_id)
        if employee is None:
            continue
        try:
            winner = expansion.resolve_winner(candidates, employee)
        except expansion.SamePrecisionConflict:
            raise DomainError(
                AttendanceErrorCode.SCHEDULE_CONFLICT, SAME_PRECISION_MESSAGE
            )
        existing = session.exec(
            select(RosterEntry).where(
                col(RosterEntry.employee_id) == copied_entry.employee_id,
                col(RosterEntry.work_date) == copied_entry.work_date,
            )
        ).first()
        if existing is not None:
            session.delete(existing)
            session.flush()
        entry = RosterEntry(
            company_id=new_plan.company_id,
            employee_id=copied_entry.employee_id,
            work_date=copied_entry.work_date,
            state=copied_entry.state,
            source=RosterSource.MANUAL,
            plan_id=winner.plan_id if winner is not None else None,
        )
        session.add(entry)
        session.flush()
        for seq, shift in enumerate(copied_entry.shifts):
            session.add(
                RosterEntryShift(
                    roster_entry_id=entry.id,
                    seq=seq,
                    shift_id=shift.shift_id,
                    shift_code=shift.shift_code,
                    shift_name=shift.shift_name,
                    start_time=shift.start_time,
                    end_time=shift.end_time,
                    cross_day=shift.cross_day,
                    break_start=shift.break_start,
                    break_end=shift.break_end,
                    rest_minutes=shift.rest_minutes,
                )
            )
    session.flush()
