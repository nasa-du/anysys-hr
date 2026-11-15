"""Golden-case API smoke: DB factories -> calculate -> persisted results.

The pure kernel is already covered by all 26 cases. These three smoke cases
verify the DB-to-contract adapter and persistence layer end to end without
duplicating the full golden suite (spec section 14.4).
"""

import json
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, col, select

from app.core.config import settings
from app.enums import (
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    LeaveKind,
    RosterState,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSummary,
    CalcRun,
    Employee,
)
from tests.utils.attendance_factories import (
    create_attendance_rule,
    create_holiday,
    create_import_batch,
    create_oa_leave,
    create_oa_overtime,
    create_oa_trip,
    create_punch_record,
    create_roster_entry,
    create_shift,
)
from tests.utils.factories import (
    create_company,
    create_department,
    create_employee,
    create_position,
)
from tests.utils.user import create_random_user

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_CASES_DIR = REPO_ROOT / "docs" / "specs" / "attendance-golden-cases"
BASE_DIR = GOLDEN_CASES_DIR / "base"
CASES_DIR = GOLDEN_CASES_DIR / "cases"

SMOKE_CASES = (
    "case-01-normal",
    "case-05-cross-day-night",
    "case-13-comp-offset",
)

DAY_DECIMAL_FIELDS = (
    "attendance_fraction",
    "leave_days",
    "paid_leave_days",
    "unpaid_leave_days",
    "comp_leave_days",
    "trip_fraction",
)
DAY_INT_FIELDS = (
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
DAY_AMOUNT_FIELDS = (
    "absent_deduct_amount",
    "late_deduct_amount",
    "early_deduct_amount",
    "missing_punch_deduct_amount",
    "deduction_total",
)
SHIFT_INT_FIELDS = (
    "rest_minutes",
    "scheduled_minutes",
    "worked_minutes",
    "late_minutes",
    "early_minutes",
    "missing_punch_count",
    "ot_minutes",
    "comp_offset_minutes",
)
SHIFT_TIME_FIELDS = ("punch_in_at", "punch_out_at", "break_out_at", "break_in_at")
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
SUMMARY_INT_FIELDS = (
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
RUN_SUMMARY_INT_FIELDS = (
    "employees_total",
    "employees_calculated",
    "employees_skipped",
    "days_total",
    "late_count",
    "late_minutes",
    "early_count",
    "early_minutes",
    "missing_punch_count",
    "absent_days",
    "ot_weekday_minutes",
    "ot_weekend_minutes",
    "ot_holiday_minutes",
    "comp_offset_unused_minutes",
)


def _load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _time(value: str) -> time:
    return time.fromisoformat(value)


def _datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _month_days(year: int, month: int) -> list[date]:
    start = date(year, month, 1)
    end = date(year + (month == 12), month % 12 + 1, 1)
    return [
        date.fromordinal(ordinal)
        for ordinal in range(start.toordinal(), end.toordinal())
    ]


class _Fixture:
    """Database graph built from one golden case's input."""

    def __init__(self, db: Session, case: dict[str, Any]) -> None:
        self.db = db
        self.case = case
        self.year, self.month = (int(part) for part in case["month"].split("-"))
        self.month_start = date(self.year, self.month, 1)
        self.employee_ids: dict[str, uuid.UUID] = {}

        self.company = create_company(
            db, company_code="C4", company_name="荣新考勤演示"
        )
        self.operator = create_random_user(db)
        self._departments: dict[str, Any] = {}
        self._positions: dict[str, Any] = {}
        self.shifts = self._create_shifts()
        self._create_employees()
        self._create_holidays()
        self._create_rule()
        self._create_roster()
        self._create_imports()

    def _department(self, name: str) -> Any:
        if name not in self._departments:
            self._departments[name] = create_department(
                self.db, company=self.company, dept_name=name
            )
        return self._departments[name]

    def _position(self, name: str) -> Any:
        if name not in self._positions:
            department = self._department(name)
            self._positions[name] = create_position(
                self.db, company=self.company, dept=department
            )
        return self._positions[name]

    def _create_shifts(self) -> dict[str, Any]:
        shifts = {}
        for raw in _load_json(BASE_DIR / "shifts.json"):
            shifts[raw["shift_code"]] = create_shift(
                self.db,
                company_id=self.company.id,
                shift_code=raw["shift_code"],
                shift_name=raw["shift_name"],
                start_time=_time(raw["start_time"]),
                end_time=_time(raw["end_time"]),
                cross_day=raw["cross_day"],
                break_start=_time(raw["break_start"]) if raw["break_start"] else None,
                break_end=_time(raw["break_end"]) if raw["break_end"] else None,
                rest_minutes=raw["rest_minutes"],
            )
        return shifts

    def _create_employees(self) -> None:
        base = {
            employee["employee_id"]: employee
            for employee in _load_json(BASE_DIR / "employees.json")
        }
        for employee_id in self.case["input"]["employee_ids"]:
            raw = base[employee_id]
            department = self._department(raw["department"])
            employee = create_employee(
                self.db,
                dept=department,
                position=self._position(raw["department"]),
                employee_no=raw["employee_no"],
                name=raw["name"],
                hire_date=date.fromisoformat(raw["hire_date"]),
                resign_date=(
                    date.fromisoformat(raw["resign_date"])
                    if raw["resign_date"]
                    else None
                ),
            )
            self.employee_ids[employee_id] = employee.id

    def _create_holidays(self) -> None:
        for raw in self.case["input"]["holidays"]:
            create_holiday(
                self.db,
                company_id=self.company.id,
                holiday_date=date.fromisoformat(raw["date"]),
                name=raw["name"],
                day_type=HolidayDayType(raw["day_type"]),
            )

    def _create_rule(self) -> None:
        create_attendance_rule(
            self.db, company_id=self.company.id, **self.case["input"]["rules"]
        )

    def _create_roster(self) -> None:
        raw = self.case["input"]
        overrides = {
            (entry["employee_id"], entry["work_date"]): entry
            for entry in raw["roster_overrides"]
        }
        for employee_id in raw["employee_ids"]:
            for work_date in _month_days(self.year, self.month):
                override = overrides.get((employee_id, work_date.isoformat()))
                if override is None:
                    create_roster_entry(
                        self.db,
                        company_id=self.company.id,
                        employee_id=self.employee_ids[employee_id],
                        work_date=work_date,
                        state=RosterState.REST,
                    )
                else:
                    create_roster_entry(
                        self.db,
                        company_id=self.company.id,
                        employee_id=self.employee_ids[employee_id],
                        work_date=work_date,
                        state=RosterState.WORK,
                        shifts=[self.shifts[code] for code in override["shifts"]],
                    )
        for entry in raw["adjacent_roster_overrides"]:
            create_roster_entry(
                self.db,
                company_id=self.company.id,
                employee_id=self.employee_ids[entry["employee_id"]],
                work_date=date.fromisoformat(entry["work_date"]),
                state=RosterState(entry["state"]),
                shifts=[self.shifts[code] for code in entry["shifts"]],
            )

    def _batch(self, data_type: ImportDataType) -> Any:
        return create_import_batch(
            self.db,
            company_id=self.company.id,
            operator_id=self.operator.id,
            data_type=data_type,
            month=self.month_start,
            status=ImportBatchStatus.COMMITTED,
        )

    def _create_imports(self) -> None:
        raw = self.case["input"]
        if raw["punches"]:
            batch = self._batch(ImportDataType.PUNCH)
            for punch in raw["punches"]:
                create_punch_record(
                    self.db,
                    company_id=self.company.id,
                    batch_id=batch.id,
                    employee_id=self.employee_ids[punch["employee_id"]],
                    attendance_date=date.fromisoformat(punch["attendance_date"]),
                    punch_time=datetime.fromisoformat(punch["punch_time"]),
                    source_row_number=punch["source_row"],
                    punch_result_raw=punch["punch_result"],
                )
        if raw["oa_trips"]:
            batch = self._batch(ImportDataType.TRIP)
            for index, trip in enumerate(raw["oa_trips"], start=2):
                create_oa_trip(
                    self.db,
                    company_id=self.company.id,
                    batch_id=batch.id,
                    employee_id=self.employee_ids[trip["employee_id"]],
                    source_row_number=index,
                    approval_no=trip["approval_no"],
                    application_type_raw=(
                        "出差" if trip["kind"] == "business" else "外出"
                    ),
                    start_at=datetime.fromisoformat(trip["start_at"]),
                    end_at=datetime.fromisoformat(trip["end_at"]),
                )
        if raw["oa_overtime_days"]:
            batch = self._batch(ImportDataType.OT)
            by_approval: dict[str, list[tuple[date, int]]] = {}
            for overtime in raw["oa_overtime_days"]:
                by_approval.setdefault(overtime["approval_no"], []).append(
                    (date.fromisoformat(overtime["work_date"]), overtime["minutes"])
                )
            for index, (approval_no, days) in enumerate(by_approval.items(), start=2):
                employee_id = next(
                    overtime["employee_id"]
                    for overtime in raw["oa_overtime_days"]
                    if overtime["approval_no"] == approval_no
                )
                create_oa_overtime(
                    self.db,
                    company_id=self.company.id,
                    batch_id=batch.id,
                    employee_id=self.employee_ids[employee_id],
                    source_row_number=index,
                    approval_no=approval_no,
                    days=days,
                )
        if raw["oa_leaves"]:
            batch = self._batch(ImportDataType.LEAVE)
            for index, leave in enumerate(raw["oa_leaves"], start=2):
                create_oa_leave(
                    self.db,
                    company_id=self.company.id,
                    batch_id=batch.id,
                    employee_id=self.employee_ids[leave["employee_id"]],
                    source_row_number=index,
                    approval_no=leave["approval_no"],
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


def _assert_day(
    actual: AttendanceDayResult,
    expected: dict[str, Any],
    shifts_by_day: dict[uuid.UUID, list[AttendanceDayShiftResult]],
) -> None:
    for field in ("day_type", "roster_state", "day_status"):
        assert getattr(actual, field).value == expected[field]
    assert sorted(actual.day_flags) == sorted(expected["day_flags"])
    for field in DAY_DECIMAL_FIELDS:
        assert getattr(actual, field) == _decimal(expected[field])
    for field in DAY_INT_FIELDS:
        assert getattr(actual, field) == expected[field]
    for field in DAY_AMOUNT_FIELDS:
        assert getattr(actual, field) == _decimal(expected[field])
    assert (
        actual.leave_kind.value if actual.leave_kind is not None else None
    ) == expected["leave_kind"]
    assert (
        actual.trip_kind.value if actual.trip_kind is not None else None
    ) == expected["trip_kind"]

    shift_results = sorted(shifts_by_day.get(actual.id, []), key=lambda row: row.seq)
    expected_shifts = sorted(expected["shift_results"], key=lambda row: row["seq"])
    assert len(shift_results) == len(expected_shifts)
    for actual_shift, expected_shift in zip(
        shift_results, expected_shifts, strict=True
    ):
        assert actual_shift.seq == expected_shift["seq"]
        for field in ("shift_code", "shift_name", "cross_day"):
            assert getattr(actual_shift, field) == expected_shift[field]
        assert actual_shift.start_time == _time(expected_shift["start_time"])
        assert actual_shift.end_time == _time(expected_shift["end_time"])
        assert actual_shift.break_start == (
            _time(expected_shift["break_start"])
            if expected_shift["break_start"]
            else None
        )
        assert actual_shift.break_end == (
            _time(expected_shift["break_end"]) if expected_shift["break_end"] else None
        )
        assert actual_shift.shift_status.value == expected_shift["shift_status"]
        assert sorted(actual_shift.shift_flags) == sorted(expected_shift["shift_flags"])
        for field in SHIFT_INT_FIELDS:
            assert getattr(actual_shift, field) == expected_shift[field]
        assert actual_shift.leave_days == _decimal(expected_shift["leave_days"])
        for field in SHIFT_TIME_FIELDS:
            actual_value = getattr(actual_shift, field)
            expected_value = _datetime(expected_shift[field])
            assert (actual_value is None) == (expected_value is None)
            if actual_value is not None:
                assert actual_value == expected_value


def _assert_summary(actual: AttendanceMonthSummary, expected: dict[str, Any]) -> None:
    for field in SUMMARY_ONE_DECIMAL_FIELDS + SUMMARY_TWO_DECIMAL_FIELDS:
        assert getattr(actual, field) == _decimal(expected[field])
    for field in SUMMARY_INT_FIELDS:
        assert getattr(actual, field) == expected[field]
    assert actual.is_adjusted == expected["is_adjusted"]
    assert actual.calc_version == expected["calc_version"]


def _assert_run_summary(actual: dict[str, Any], expected: dict[str, Any]) -> None:
    for field in RUN_SUMMARY_INT_FIELDS:
        assert actual[field] == expected[field], field
    assert actual["skipped_reasons"] == expected["skipped_reasons"]
    assert actual["days_by_status"] == expected["days_by_status"]
    assert actual["flag_counts"] == expected["flag_counts"]
    assert _decimal(actual["attendance_deduct"]) == _decimal(
        expected["attendance_deduct"]
    )


@pytest.mark.parametrize("case_name", SMOKE_CASES)
def test_golden_case_through_api(
    client: TestClient,
    superuser_token_headers: dict[str, str],
    db: Session,
    case_name: str,
) -> None:
    case = _load_json(CASES_DIR / f"{case_name}.json")
    fixture = _Fixture(db, case)
    expected = case["expected"]

    response = client.post(
        f"{settings.API_V1_STR}/attendance/months/{case['month']}/calculate",
        headers=superuser_token_headers,
        params={"company_id": str(fixture.company.id)},
    )

    assert response.status_code == 200, response.text
    db.expire_all()

    month = db.exec(
        select(AttendanceMonth).where(
            col(AttendanceMonth.company_id) == fixture.company.id
        )
    ).one()
    calc_run = db.exec(
        select(CalcRun).where(col(CalcRun.attendance_month_id) == month.id)
    ).one()
    _assert_run_summary(calc_run.summary or {}, expected["calc_run_summary"])

    employees = {
        employee.employee_no: employee.id
        for employee in db.exec(
            select(Employee).where(col(Employee.id).in_(fixture.employee_ids.values()))
        ).all()
    }
    day_rows = db.exec(
        select(AttendanceDayResult).where(
            col(AttendanceDayResult.attendance_month_id) == month.id
        )
    ).all()
    shifts_by_day: dict[uuid.UUID, list[AttendanceDayShiftResult]] = {}
    for shift_row in db.exec(
        select(AttendanceDayShiftResult).where(
            col(AttendanceDayShiftResult.calc_run_id) == calc_run.id
        )
    ).all():
        shifts_by_day.setdefault(shift_row.day_result_id, []).append(shift_row)
    days = {(row.employee_id, row.work_date): row for row in day_rows}
    for expected_day in expected["day_results"]:
        key = (
            employees[expected_day["employee_id"]],
            date.fromisoformat(expected_day["work_date"]),
        )
        assert key in days, f"missing day result {key}"
        _assert_day(days[key], expected_day, shifts_by_day)

    summaries = {
        row.employee_id: row
        for row in db.exec(
            select(AttendanceMonthSummary).where(
                col(AttendanceMonthSummary.attendance_month_id) == month.id
            )
        ).all()
    }
    for expected_summary in expected["month_summaries"]:
        employee_id = employees[expected_summary["employee_id"]]
        assert employee_id in summaries, f"missing summary {employee_id}"
        _assert_summary(summaries[employee_id], expected_summary)

    assert month.status.value == "calculated"
    assert month.is_stale is False
    assert calc_run.status.value == "success"
