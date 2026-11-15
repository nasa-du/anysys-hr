"""Golden-case contract tests for the pure attendance calculation kernel.

These tests are the executable form of ``docs/specs/attendance-golden-cases``.
Each case feeds frozen contract dataclasses into ``run_month`` and compares the
returned day results, month summaries, and run summary against the reviewed
expectations. The kernel under test never touches a database.
"""

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]

from app.enums import (
    HolidayDayType,
    LeaveKind,
    ResultRosterState,
    RosterState,
    TripKind,
)
from app.services.attendance.calc import (
    Employee,
    Holiday,
    Leave,
    MonthInputs,
    MonthOutputs,
    OvertimeDay,
    Punch,
    RosterEntry,
    Rules,
    ShiftSnapshot,
    Trip,
    run_month,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_CASES_DIR = REPO_ROOT / "docs" / "specs" / "attendance-golden-cases"
BASE_DIR = GOLDEN_CASES_DIR / "base"
CASES_DIR = GOLDEN_CASES_DIR / "cases"

CASE_PATHS = sorted(CASES_DIR.glob("*.json"))

DAY_ONE_DECIMAL_FIELDS = (
    "attendance_fraction",
    "leave_days",
    "paid_leave_days",
    "unpaid_leave_days",
    "comp_leave_days",
    "trip_fraction",
)
DAY_TWO_DECIMAL_FIELDS = (
    "absent_deduct_amount",
    "late_deduct_amount",
    "early_deduct_amount",
    "missing_punch_deduct_amount",
    "deduction_total",
)
SUMMARY_ONE_DECIMAL_FIELDS = (
    "weekday_full",
    "weekend_full",
    "weekday_attended",
    "weekend_attended",
    "paid_leave_days",
    "unpaid_leave_days",
    "comp_leave_days",
    "trip_days",
)
SUMMARY_TWO_DECIMAL_FIELDS = (
    "ot_weekday_hours",
    "ot_weekend_hours",
    "ot_holiday_hours",
    "comp_leave_used_hours",
    "attendance_deduct",
)
DAY_MINUTE_FIELDS = (
    "scheduled_minutes",
    "worked_minutes",
    "late_minutes",
    "early_minutes",
    "missing_punch_count",
    "ot_weekday_minutes",
    "ot_weekend_minutes",
    "ot_holiday_minutes",
    "comp_offset_minutes",
    "comp_offset_unused_minutes",
    "late_count",
    "early_count",
)
SUMMARY_MINUTE_FIELDS = (
    "ot_weekday_minutes",
    "ot_weekend_minutes",
    "ot_holiday_minutes",
    "comp_offset_unused_minutes",
    "late_count",
    "late_minutes",
    "early_count",
    "early_minutes",
    "missing_punch_count",
    "absent_days",
    "worked_minutes",
)
SHIFT_MINUTE_FIELDS = (
    "scheduled_minutes",
    "worked_minutes",
    "late_minutes",
    "early_minutes",
    "missing_punch_count",
    "ot_minutes",
    "comp_offset_minutes",
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


SCHEMA_VALIDATOR = Draft202012Validator(_load_json(GOLDEN_CASES_DIR / "schema.json"))


def _load_base() -> tuple[list[dict[str, Any]], dict[str, ShiftSnapshot]]:
    employees = _load_json(BASE_DIR / "employees.json")
    shifts = {
        shift["shift_code"]: ShiftSnapshot(
            shift_code=shift["shift_code"],
            shift_name=shift["shift_name"],
            start_time=time.fromisoformat(shift["start_time"]),
            end_time=time.fromisoformat(shift["end_time"]),
            cross_day=shift["cross_day"],
            break_start=(
                time.fromisoformat(shift["break_start"])
                if shift["break_start"]
                else None
            ),
            break_end=(
                time.fromisoformat(shift["break_end"]) if shift["break_end"] else None
            ),
            rest_minutes=shift["rest_minutes"],
        )
        for shift in _load_json(BASE_DIR / "shifts.json")
    }
    return employees, shifts


EMPLOYEES, SHIFTS = _load_base()


def _build_rules(raw: dict[str, Any]) -> Rules:
    return Rules(
        punch_window_min=raw["punch_window_min"],
        late_cap_min=raw["late_cap_min"],
        early_cap_min=raw["early_cap_min"],
        ot_max_min=raw["ot_max_min"],
        late_grace_min=raw["late_grace_min"],
        early_grace_min=raw["early_grace_min"],
        ot_threshold_min=raw["ot_threshold_min"],
        absent_if_no_punch=raw["absent_if_no_punch"],
        break_punch_required=raw["break_punch_required"],
        break_punch_tolerance_min=raw["break_punch_tolerance_min"],
        absent_deduct_per_day=Decimal(str(raw["absent_deduct_per_day"])),
        late_deduct_per_occurrence=Decimal(str(raw["late_deduct_per_occurrence"])),
        early_deduct_per_occurrence=Decimal(str(raw["early_deduct_per_occurrence"])),
        missing_punch_deduct_per_occurrence=Decimal(
            str(raw["missing_punch_deduct_per_occurrence"])
        ),
    )


def _build_roster(raw: list[dict[str, Any]]) -> tuple[RosterEntry, ...]:
    return tuple(
        RosterEntry(
            employee_id=entry["employee_id"],
            work_date=date.fromisoformat(entry["work_date"]),
            state=RosterState(entry["state"]),
            shifts=tuple(SHIFTS[code] for code in entry["shifts"]),
        )
        for entry in raw
    )


def _build_inputs(case: dict[str, Any]) -> MonthInputs:
    raw = case["input"]
    employee_ids = raw["employee_ids"]
    employees_by_id = {employee["employee_id"]: employee for employee in EMPLOYEES}
    employees = tuple(
        Employee(
            employee_id=employees_by_id[employee_id]["employee_id"],
            employee_no=employees_by_id[employee_id]["employee_no"],
            name=employees_by_id[employee_id]["name"],
            department=employees_by_id[employee_id]["department"],
            hire_date=date.fromisoformat(employees_by_id[employee_id]["hire_date"]),
            resign_date=(
                date.fromisoformat(employees_by_id[employee_id]["resign_date"])
                if employees_by_id[employee_id]["resign_date"]
                else None
            ),
        )
        for employee_id in employee_ids
    )

    year, month = (int(part) for part in case["month"].split("-"))
    return MonthInputs(
        month=date(year, month, 1),
        employees=employees,
        roster=_build_roster(raw["roster_overrides"]),
        adjacent_roster=_build_roster(raw["adjacent_roster_overrides"]),
        punches=tuple(
            Punch(
                employee_id=punch["employee_id"],
                attendance_date=date.fromisoformat(punch["attendance_date"]),
                punch_time=datetime.fromisoformat(punch["punch_time"]),
                punch_result=punch["punch_result"],
            )
            for punch in raw["punches"]
        ),
        trips=tuple(
            Trip(
                id=trip["id"],
                approval_no=trip["approval_no"],
                employee_id=trip["employee_id"],
                kind=TripKind(trip["kind"]),
                start_at=datetime.fromisoformat(trip["start_at"]),
                end_at=datetime.fromisoformat(trip["end_at"]),
            )
            for trip in raw["oa_trips"]
        ),
        overtime_days=tuple(
            OvertimeDay(
                id=overtime["id"],
                approval_no=overtime["approval_no"],
                employee_id=overtime["employee_id"],
                work_date=date.fromisoformat(overtime["work_date"]),
                minutes=overtime["minutes"],
            )
            for overtime in raw["oa_overtime_days"]
        ),
        leaves=tuple(
            Leave(
                id=leave["id"],
                approval_no=leave["approval_no"],
                employee_id=leave["employee_id"],
                leave_kind=LeaveKind(leave["leave_kind"]),
                days=Decimal(str(leave["days"])),
                rest_start_at=datetime.fromisoformat(leave["rest_start_at"]),
                rest_end_at=datetime.fromisoformat(leave["rest_end_at"]),
                work_start_at=(
                    datetime.fromisoformat(leave["work_start_at"])
                    if leave["work_start_at"]
                    else None
                ),
                work_end_at=(
                    datetime.fromisoformat(leave["work_end_at"])
                    if leave["work_end_at"]
                    else None
                ),
            )
            for leave in raw["oa_leaves"]
        ),
        holidays=tuple(
            Holiday(
                date=date.fromisoformat(holiday["date"]),
                name=holiday["name"],
                day_type=HolidayDayType(holiday["day_type"]),
            )
            for holiday in raw["holidays"]
        ),
        rules=_build_rules(raw["rules"]),
        roster_default=ResultRosterState(raw["roster_default"]),
    )


def _normalize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, date):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return _normalize(asdict(value))
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _assert_places(
    instance: object, fields: tuple[str, ...], places: int, label: str
) -> None:
    for field in fields:
        value = getattr(instance, field)
        assert isinstance(value, Decimal), f"{label}.{field} must be Decimal"
        assert value.as_tuple().exponent == -places, (
            f"{label}.{field}={value} must have {places} decimal places"
        )


def _assert_minutes(instance: object, fields: tuple[str, ...], label: str) -> None:
    for field in fields:
        value = getattr(instance, field)
        assert isinstance(value, int) and not isinstance(value, bool), (
            f"{label}.{field} must be integer minutes"
        )


def _assert_numeric_conventions(outputs: MonthOutputs) -> None:
    for result in outputs.day_results:
        label = f"day {result.employee_id} {result.work_date}"
        _assert_places(result, DAY_ONE_DECIMAL_FIELDS, 1, label)
        _assert_places(result, DAY_TWO_DECIMAL_FIELDS, 2, label)
        _assert_minutes(result, DAY_MINUTE_FIELDS, label)
        for shift in result.shift_results:
            shift_label = f"{label} shift {shift.seq}"
            _assert_places(shift, ("leave_days",), 1, shift_label)
            _assert_minutes(shift, SHIFT_MINUTE_FIELDS, shift_label)
    for summary in outputs.month_summaries:
        label = f"summary {summary.employee_id}"
        _assert_places(summary, SUMMARY_ONE_DECIMAL_FIELDS, 1, label)
        _assert_places(summary, SUMMARY_TWO_DECIMAL_FIELDS, 2, label)
        _assert_minutes(summary, SUMMARY_MINUTE_FIELDS, label)
    assert outputs.summary.attendance_deduct.as_tuple().exponent == -2


@pytest.mark.parametrize("case_path", CASE_PATHS, ids=lambda path: path.stem)
def test_golden_case(case_path: Path) -> None:
    case = _load_json(case_path)
    SCHEMA_VALIDATOR.validate(case)
    expected = case["expected"]

    outputs = run_month(_build_inputs(case))
    _assert_numeric_conventions(outputs)

    day_results = {
        (result.employee_id, result.work_date.isoformat()): _normalize(result)
        for result in outputs.day_results
    }
    for expected_day in expected["day_results"]:
        key = (expected_day["employee_id"], expected_day["work_date"])
        assert key in day_results, f"{case_path.name}: missing day result {key}"
        assert day_results[key] == expected_day, f"{case_path.name}: day result {key}"

    month_summaries = {
        summary.employee_id: _normalize(summary) for summary in outputs.month_summaries
    }
    for expected_summary in expected["month_summaries"]:
        employee_id = expected_summary["employee_id"]
        assert employee_id in month_summaries, (
            f"{case_path.name}: missing month summary {employee_id}"
        )
        assert month_summaries[employee_id] == expected_summary, (
            f"{case_path.name}: month summary {employee_id}"
        )

    assert _normalize(outputs.summary) == expected["calc_run_summary"]
