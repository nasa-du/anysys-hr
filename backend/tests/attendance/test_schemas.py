"""Attendance schema package: shared conventions and export helpers."""

import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from app.enums import DayStatus
from app.schemas_attendance.common import MonthString
from app.schemas_attendance.core import (
    AttendanceRulePublic,
    AttendanceRuleUpdate,
    CalcRunSummary,
    HolidayUpdate,
    PlanRuleOverrideSnapshot,
    ShiftCreate,
    ShiftUpdate,
)
from app.schemas_attendance.exports import (
    DETAIL_RECORD_TYPES,
    PAYROLL_COLUMNS,
    escape_csv_cell,
)
from app.schemas_attendance.imports import ImportBatchPublic, ImportRecordPublic
from app.schemas_attendance.results import (
    AttendanceAdjustmentValues,
    derive_is_abnormal,
)
from app.schemas_attendance.scheduling import (
    RosterEntryUpdate,
    SchedulePlanCreate,
    SchedulePlanUpdate,
)


def test_shift_create_forbids_unknown_fields() -> None:
    with pytest.raises(ValidationError) as error:
        ShiftCreate(
            company_id="00000000-0000-0000-0000-000000000000",
            shift_code="ADM",
            shift_name="行政班",
            start_time="08:30:00",
            end_time="17:30:00",
            company_name="不允许",
        )

    assert error.value.errors()[0]["type"] == "extra_forbidden"


def test_shift_code_pattern_and_time_shape() -> None:
    shift = ShiftCreate(
        company_id="00000000-0000-0000-0000-000000000000",
        shift_code="adm",
        shift_name="行政班",
        start_time="08:30:00",
        end_time="17:30:00",
    )

    assert shift.shift_code == "ADM"
    with pytest.raises(ValidationError):
        ShiftCreate(
            company_id="00000000-0000-0000-0000-000000000000",
            shift_code="行政 班",
            shift_name="行政班",
            start_time="08:30:00",
            end_time="17:30:00",
        )


@pytest.mark.parametrize(
    "invalid_time",
    ["08:30:00+08:00", "08:30:00.500"],
)
def test_shift_times_must_be_naive_whole_seconds(invalid_time: str) -> None:
    with pytest.raises(ValidationError):
        ShiftCreate(
            company_id="00000000-0000-0000-0000-000000000000",
            shift_code="ADM",
            shift_name="行政班",
            start_time=invalid_time,
            end_time="17:30:00",
        )


def test_month_string_accepts_stored_first_of_month_dates() -> None:
    adapter = TypeAdapter(MonthString)

    assert adapter.validate_python(date(2026, 9, 1)) == "2026-09"
    assert adapter.validate_python("2026-10") == "2026-10"


@pytest.mark.parametrize("invalid_month", ["2026-13", "0000-01", "２０２６-０９"])
def test_month_string_rejects_invalid_month(invalid_month: str) -> None:
    with pytest.raises(ValidationError):
        SchedulePlanCreate(
            company_id="00000000-0000-0000-0000-000000000000",
            month=invalid_month,
            plan_name="行政班",
            scope_type="all",
        )


def test_historical_rule_override_snapshots_allow_unknown_fields() -> None:
    snapshot = PlanRuleOverrideSnapshot(
        plan_id=uuid.uuid4(),
        overrides={"ot_threshold_min": 15, "field_removed_later": True},
    )

    assert snapshot.overrides.ot_threshold_min == 15


def test_decimal_fields_serialize_as_strings() -> None:
    summary = CalcRunSummary(attendance_deduct=Decimal("-20.00"))

    assert summary.model_dump(mode="json")["attendance_deduct"] == "-20.00"


def test_rule_update_rejects_explicit_null_and_unknown_fields() -> None:
    update = AttendanceRuleUpdate(late_grace_min=10)

    assert update.late_grace_min == 10
    with pytest.raises(ValidationError, match="该字段不能为空"):
        AttendanceRuleUpdate(punch_window_min=None)
    with pytest.raises(ValidationError):
        AttendanceRuleUpdate(company_id="00000000-0000-0000-0000-000000000000")


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ShiftUpdate(cross_day=None),
        lambda: HolidayUpdate(day_type=None),
        lambda: SchedulePlanUpdate(days=None),
        lambda: RosterEntryUpdate(state=None),
    ],
)
def test_update_schemas_reject_explicit_null_for_required_fields(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValidationError, match="该字段不能为空"):
        factory()


def test_attendance_rule_public_allows_a_synthetic_default_row() -> None:
    rule = AttendanceRulePublic(
        id=None,
        company_id="00000000-0000-0000-0000-000000000000",
        is_default=True,
        punch_window_min=120,
        late_cap_min=240,
        early_cap_min=240,
        ot_max_min=600,
        late_grace_min=5,
        early_grace_min=5,
        ot_threshold_min=30,
        absent_if_no_punch=True,
        break_punch_required=True,
        break_punch_tolerance_min=60,
        absent_deduct_per_day=Decimal("100"),
        late_deduct_per_occurrence=Decimal("20"),
        early_deduct_per_occurrence=Decimal("20"),
        missing_punch_deduct_per_occurrence=Decimal("10"),
    )

    assert rule.id is None
    assert rule.is_default is True


def test_adjustment_values_only_accept_adjustable_fields() -> None:
    values = AttendanceAdjustmentValues(
        day_status="normal",
        worked_minutes=480,
        leave_days=Decimal("0.5"),
    )

    assert values.worked_minutes == 480
    with pytest.raises(ValidationError):
        AttendanceAdjustmentValues(scheduled_minutes=480)


@pytest.mark.parametrize(
    ("day_status", "day_flags", "expected"),
    [
        (DayStatus.NORMAL, [], False),
        (DayStatus.REST, [], False),
        (DayStatus.LATE, [], True),
        (DayStatus.EARLY, [], True),
        (DayStatus.MISSING_PUNCH, [], True),
        (DayStatus.ABSENT, [], True),
        (DayStatus.UNSCHEDULED_ATTENDANCE, [], True),
        (DayStatus.NORMAL, ["leave_trip_conflict"], True),
        (DayStatus.NORMAL, ["punch_during_leave"], True),
        (DayStatus.NORMAL, ["late"], False),
    ],
)
def test_is_abnormal_derivation(
    day_status: DayStatus, day_flags: list[str], expected: bool
) -> None:
    assert derive_is_abnormal(day_status, day_flags) is expected


def test_import_models_are_importable_and_rebuildable() -> None:
    assert ImportRecordPublic is not None
    assert ImportBatchPublic.model_json_schema()


def test_payroll_columns_are_the_fixed_fourteen() -> None:
    assert len(PAYROLL_COLUMNS) == 14
    assert PAYROLL_COLUMNS[0] == "attendance_month"
    assert PAYROLL_COLUMNS[-1] == "attendance_deduct"
    assert DETAIL_RECORD_TYPES == ("month_summary", "day_result", "shift_result")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, ""),
        (True, "true"),
        (False, "false"),
        (Decimal("-20.00"), "-20.00"),
        (-20, "-20"),
        (date(2026, 9, 25), "2026-09-25"),
        (
            datetime(2026, 9, 25, 8, 30, tzinfo=UTC),
            "2026-09-25T08:30:00+00:00",
        ),
        ("正常", "正常"),
        ("=SUM(A1)", "'=SUM(A1)"),
        ("+8613800000000", "'+8613800000000"),
        ("-危险", "'-危险"),
        ("@cmd", "'@cmd"),
        ("\tvalue", "'\tvalue"),
        ("\rvalue", "'\rvalue"),
    ],
)
def test_csv_cell_escaping(value: object, expected: str) -> None:
    assert escape_csv_cell(value) == expected
