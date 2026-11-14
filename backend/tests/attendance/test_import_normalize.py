"""Fixture regression for row normalization (spec sections 6.3-6.5).

Seam: ``app.services.attendance.import_normalize.normalize_rows``. Each test
loads the checked-in fixture, normalizes it against the fixture employee seed,
and asserts the documented row-by-row results and aggregate counts.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlmodel import Session, select

from app.enums import ImportDataType, ImportSeverity, LeaveKind
from app.models import Department, Employee
from app.services.attendance import import_normalize, import_parsing
from tests.utils.attendance_imports import parse_fixture, seed_fixture_employees
from tests.utils.factories import create_company

SHANGHAI = ZoneInfo("Asia/Shanghai")
MONTH = date(2026, 9, 1)


def normalize(
    db: Session, data_type: ImportDataType
) -> import_normalize.NormalizationOutcome:
    company = create_company(db)
    seed_fixture_employees(db, company)
    employees = list(company_employees(db, company))
    table = parse_fixture(data_type)
    return import_normalize.normalize_rows(
        table, data_type=data_type, month=MONTH, employees=employees
    )


def company_employees(db: Session, company):
    return db.exec(
        select(Employee)
        .join(Department, Department.id == Employee.dept_id)
        .where(Department.company_id == company.id)
    ).all()


def issues_by_code(
    outcome: import_normalize.NormalizationOutcome, code: str
) -> list[import_normalize.ImportIssue]:
    return [issue for issue in outcome.issues if issue.code == code]


def punch_row(
    outcome: import_normalize.NormalizationOutcome, row_number: int
) -> import_normalize.PunchData:
    matches = [
        record
        for record in outcome.records
        if record.source_row_number == row_number
    ]
    assert len(matches) == 1, row_number
    record = matches[0]
    assert isinstance(record, import_normalize.PunchData)
    return record


def test_punch_fixture_aggregates(db: Session) -> None:
    outcome = normalize(db, ImportDataType.PUNCH)

    assert outcome.source_rows == 37
    assert outcome.valid_records == 27
    assert outcome.skipped_records == 10
    assert outcome.error_records == 4
    assert outcome.warning_records == 5
    assert outcome.skip_counts == {
        "unknown_employee": 1,
        "out_of_employment": 2,
        "missing_punch_time": 1,
        "invalid_punch": 3,
        "not_in_month": 1,
        "duplicate_punch": 2,
    }
    assert outcome.warning_counts == {
        "empty_result": 1,
        "name_mismatch": 1,
        "date_mismatch": 1,
        "result_conflict": 1,
        "unknown_result": 1,
    }
    assert len(outcome.matched_employee_ids) == 11
    assert outcome.unknown_keys == {"E999"}
    assert outcome.duplicate_name_keys == set()
    assert len(outcome.affected_employee_ids) == 9


def test_punch_rows_match_the_fixture_expectations(db: Session) -> None:
    outcome = normalize(db, ImportDataType.PUNCH)

    cross_day = punch_row(outcome, 12)  # data row 11 (header is row 1)
    assert cross_day.attendance_date == date(2026, 9, 30)
    assert cross_day.punch_time.astimezone(SHANGHAI) == datetime(
        2026, 10, 1, 6, 5, tzinfo=SHANGHAI
    )

    time_only = punch_row(outcome, 26)
    assert time_only.punch_time.astimezone(SHANGHAI) == datetime(
        2026, 9, 22, 8, 0, tzinfo=SHANGHAI
    )

    slash_date = punch_row(outcome, 27)
    assert slash_date.attendance_date == date(2026, 9, 22)

    with_seconds = punch_row(outcome, 28)
    assert with_seconds.punch_time.astimezone(SHANGHAI).second == 0

    date_mismatch = punch_row(outcome, 29)
    assert date_mismatch.attendance_date == date(2026, 9, 24)
    assert [
        issue.source_row_number
        for issue in issues_by_code(outcome, "date_mismatch")
    ] == [29]

    name_mismatch = punch_row(outcome, 24)
    assert name_mismatch.employee_name_raw == "错误姓名"
    assert [
        issue.source_row_number
        for issue in issues_by_code(outcome, "name_mismatch")
    ] == [24]

    empty_result = punch_row(outcome, 18)
    assert empty_result.punch_result_raw == ""

    result_conflict = issues_by_code(outcome, "result_conflict")
    assert [issue.source_row_number for issue in result_conflict] == [31]
    assert result_conflict[0].severity is ImportSeverity.WARNING

    unknown_result = issues_by_code(outcome, "unknown_result")
    assert [issue.source_row_number for issue in unknown_result] == [32]

    # Row 18 (`已被更新`) is filtered before dedupe, so row 17 still imports.
    assert outcome.skip_counts["duplicate_punch"] == 2
    assert {record.source_row_number for record in outcome.records}.isdisjoint(
        {10, 31}
    )


def test_punch_never_falls_back_from_number_to_name(db: Session) -> None:
    outcome = normalize(db, ImportDataType.PUNCH)

    unknown = issues_by_code(outcome, "unknown_employee")
    assert len(unknown) == 1
    assert unknown[0].raw_row["工号"] == "E999"
    assert unknown[0].raw_row["姓名"] == "不存在"


def test_punch_missing_time_is_an_error_and_scheduled_time_never_fills_in(
    db: Session,
) -> None:
    outcome = normalize(db, ImportDataType.PUNCH)

    (missing,) = issues_by_code(outcome, "missing_punch_time")
    assert missing.source_row_number == 25
    assert missing.severity is ImportSeverity.ERROR
    assert missing.raw_row["考勤时间"] == "2026-09-21 08:00"


def test_trip_fixture_aggregates_and_split_records(db: Session) -> None:
    outcome = normalize(db, ImportDataType.TRIP)

    assert outcome.source_rows == 15
    assert len(outcome.records) == 8
    assert outcome.valid_records == 8
    assert outcome.skipped_records == 9
    assert outcome.error_records == 5
    assert outcome.warning_records == 0
    assert outcome.skip_counts == {
        "unknown_employee": 2,
        "pending": 1,
        "terminated": 1,
        "rejected": 1,
        "invalid_range": 1,
        "missing_required": 2,
        "duplicate_approval": 1,
    }
    split = [
        record
        for record in outcome.records
        if record.source_row_number == 3
    ]
    assert [record.split_index for record in split if hasattr(record, "split_index")] == [0, 1]
    assert sorted(record.employee_name_raw for record in split) == sorted(
        ["冯芷茵", "刘衍英"]
    )


def test_trip_cross_month_request_keeps_the_full_range(db: Session) -> None:
    outcome = normalize(db, ImportDataType.TRIP)

    cross_month = [
        record
        for record in outcome.records
        if record.source_row_number == 8  # fixture row 7
    ][0]
    assert isinstance(cross_month, import_normalize.OaTripData)
    assert cross_month.start_at.astimezone(SHANGHAI) == datetime(
        2026, 9, 28, 8, 0, tzinfo=SHANGHAI
    )
    assert cross_month.end_at.astimezone(SHANGHAI) == datetime(
        2026, 10, 2, 18, 0, tzinfo=SHANGHAI
    )
    assert cross_month.start_date == date(2026, 9, 28)
    assert cross_month.end_date == date(2026, 10, 2)


def test_overtime_fixture_aggregates_and_daily_minutes(db: Session) -> None:
    outcome = normalize(db, ImportDataType.OT)

    assert outcome.source_rows == 15
    assert outcome.valid_records == 8
    assert outcome.skipped_records == 7
    assert outcome.error_records == 3
    assert outcome.warning_records == 1
    assert outcome.skip_counts == {
        "unknown_employee": 1,
        "pending": 1,
        "terminated": 1,
        "rejected": 1,
        "invalid_range": 1,
        "missing_required": 1,
        "duplicate_approval": 1,
    }
    assert outcome.warning_counts == {"amount_mismatch": 1}

    def days_for(row_number: int) -> dict[date, int]:
        record = [
            record
            for record in outcome.records
            if record.source_row_number == row_number
        ][0]
        assert isinstance(record, import_normalize.OaOvertimeData)
        return dict(record.days)

    assert days_for(2) == {date(2026, 9, 14): 480}
    assert days_for(3) == {date(2026, 9, 15): 480}
    assert days_for(4) == {
        date(2026, 9, 20): 240,
        date(2026, 9, 21): 120,
    }
    assert days_for(5) == {
        date(2026, 9, 28): 480,
        date(2026, 9, 29): 480,
        date(2026, 9, 30): 480,
    }
    # Spec 6.5.3: overlapping minutes per natural day, capped at 480.
    assert days_for(6) == {
        date(2026, 9, 12): 390,
        date(2026, 9, 13): 480,
        date(2026, 9, 14): 480,
    }
    assert days_for(11) == {date(2026, 9, 30): 240}
    assert days_for(14) == {date(2026, 9, 22): 240}
    assert days_for(16) == {date(2026, 9, 23): 240}
    assert sum(len(record.days) for record in outcome.records) == 13


def test_overtime_amount_mismatch_warns_without_blocking(db: Session) -> None:
    outcome = normalize(db, ImportDataType.OT)

    (warning,) = issues_by_code(outcome, "amount_mismatch")
    assert warning.source_row_number == 3
    assert warning.severity is ImportSeverity.WARNING
    assert warning.raw_row["加班时长（天/小时）"] == "6"
    assert any(
        record.source_row_number == 3 for record in outcome.records
    )


def test_leave_fixture_aggregates_and_classification(db: Session) -> None:
    outcome = normalize(db, ImportDataType.LEAVE)

    assert outcome.source_rows == 19
    assert outcome.valid_records == 8
    assert outcome.skipped_records == 11
    assert outcome.error_records == 8
    assert outcome.warning_records == 1
    assert outcome.skip_counts == {
        "invalid_leave_type": 2,
        "pending": 1,
        "rejected": 1,
        "unknown_employee": 1,
        "duplicate_name": 1,
        "out_of_employment": 2,
        "missing_required": 1,
        "invalid_range": 1,
        "duplicate_approval": 1,
    }
    assert outcome.warning_counts == {"missing_work_start": 1}
    kinds = {
        record.source_row_number: record.leave_kind
        for record in outcome.records
    }
    assert kinds == {
        2: LeaveKind.UNPAID,
        3: LeaveKind.PAID,
        4: LeaveKind.COMP,
        5: LeaveKind.COMP,
        6: LeaveKind.COMP,
        8: LeaveKind.UNPAID,
        18: LeaveKind.UNPAID,
        20: LeaveKind.COMP,
    }
    assert outcome.duplicate_name_keys == {"张伟"}
    assert outcome.unknown_keys == {"王小明"}
    assert len(outcome.affected_employee_ids) == 6


def test_leave_cross_month_comp_request_is_attributed_by_work_date(
    db: Session,
) -> None:
    outcome = normalize(db, ImportDataType.LEAVE)

    record = [
        record
        for record in outcome.records
        if record.source_row_number == 4  # fixture row 3
    ][0]
    assert isinstance(record, import_normalize.OaLeaveData)
    assert record.rest_start_date == date(2026, 10, 22)
    assert record.work_start_date == date(2026, 9, 25)


def test_leave_unrecognized_types_are_row_errors(db: Session) -> None:
    outcome = normalize(db, ImportDataType.LEAVE)

    invalid = issues_by_code(outcome, "invalid_leave_type")
    assert [issue.source_row_number for issue in invalid] == [7, 17]
    assert {issue.raw_row["请假类型"] for issue in invalid} == {"婚假", "病假"}
    assert not any(
        record.leave_type_raw in {"婚假", "病假"} for record in outcome.records
    )


def test_xlsx_date_serials_are_parsed(db: Session) -> None:
    company = create_company(db)
    seed_fixture_employees(db, company)
    employees = list(company_employees(db, company))
    table = parse_fixture(ImportDataType.PUNCH)
    serial_table = table.__class__(
        header_columns=table.header_columns,
        header_row_number=table.header_row_number,
        data_rows=[
            import_parsing.SourceRow(
                row_number=2,
                cells=["E101", "冯芷茵", "生产部", "46266", "46266.375", "正常"],
            )
        ],
        mapping=table.mapping,
        ignored_columns=table.ignored_columns,
    )

    outcome = import_normalize.normalize_rows(
        serial_table, data_type=ImportDataType.PUNCH, month=MONTH, employees=employees
    )

    (record,) = outcome.records
    assert isinstance(record, import_normalize.PunchData)
    assert record.attendance_date == date(2026, 9, 1)
    assert record.punch_time.astimezone(SHANGHAI) == datetime(
        2026, 9, 1, 9, 0, tzinfo=SHANGHAI
    )
