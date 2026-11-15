"""Focused unit tests for the calculation kernel's documented decisions.

The golden cases are the primary contract; these tests pin the individual
rules from spec section 7 so a regression names the broken decision directly.
"""

from datetime import date, datetime, time
from decimal import Decimal

from app.enums import (
    DayStatus,
    DayType,
    HolidayDayType,
    LeaveKind,
    ResultRosterState,
    RosterState,
    TripKind,
)
from app.services.attendance.calc import (
    DayResult,
    Employee,
    Holiday,
    Leave,
    MonthInputs,
    MonthOutputs,
    MonthSummary,
    OvertimeDay,
    Punch,
    RosterEntry,
    Rules,
    ShiftSnapshot,
    Trip,
    run_month,
)

ADM = ShiftSnapshot(
    shift_code="ADM",
    shift_name="行政班",
    start_time=time(8, 30),
    end_time=time(17, 30),
    cross_day=False,
    break_start=None,
    break_end=None,
    rest_minutes=60,
)
EARLY = ShiftSnapshot(
    shift_code="EARLY",
    shift_name="早班",
    start_time=time(6, 0),
    end_time=time(14, 0),
    cross_day=False,
    break_start=None,
    break_end=None,
    rest_minutes=60,
)
MID = ShiftSnapshot(
    shift_code="MID",
    shift_name="中班",
    start_time=time(14, 0),
    end_time=time(22, 0),
    cross_day=False,
    break_start=None,
    break_end=None,
    rest_minutes=60,
)
YL = ShiftSnapshot(
    shift_code="YL",
    shift_name="园林班",
    start_time=time(7, 30),
    end_time=time(17, 30),
    cross_day=False,
    break_start=time(11, 30),
    break_end=time(13, 30),
    rest_minutes=120,
)
NIGHT = ShiftSnapshot(
    shift_code="NIGHT",
    shift_name="夜班",
    start_time=time(22, 0),
    end_time=time(6, 0),
    cross_day=True,
    break_start=time(2, 0),
    break_end=time(3, 0),
    rest_minutes=60,
)
DAWN = ShiftSnapshot(
    shift_code="DAWN",
    shift_name="凌晨班",
    start_time=time(2, 0),
    end_time=time(10, 0),
    cross_day=False,
    break_start=None,
    break_end=None,
    rest_minutes=60,
)
SHIFTS = {shift.shift_code: shift for shift in (ADM, EARLY, MID, YL, NIGHT, DAWN)}


def make_rules(**overrides: object) -> Rules:
    values: dict[str, object] = {
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
        "absent_deduct_per_day": Decimal("100"),
        "late_deduct_per_occurrence": Decimal("20"),
        "early_deduct_per_occurrence": Decimal("20"),
        "missing_punch_deduct_per_occurrence": Decimal("10"),
    }
    values.update(overrides)
    return Rules(**values)  # type: ignore[arg-type]


def employee(
    employee_id: str = "E1",
    *,
    hire_date: date = date(2020, 1, 1),
    resign_date: date | None = None,
) -> Employee:
    return Employee(
        employee_id=employee_id,
        employee_no=employee_id,
        name=employee_id,
        hire_date=hire_date,
        resign_date=resign_date,
    )


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def punch(employee_id: str, attendance_date: str, punch_time: str) -> Punch:
    return Punch(
        employee_id=employee_id,
        attendance_date=date.fromisoformat(attendance_date),
        punch_time=dt(punch_time),
    )


def work(employee_id: str, work_date: str, *shift_codes: str) -> RosterEntry:
    return RosterEntry(
        employee_id=employee_id,
        work_date=date.fromisoformat(work_date),
        state=RosterState.WORK,
        shifts=tuple(SHIFTS[code] for code in shift_codes),
    )


def make_inputs(
    *,
    employees: tuple[Employee, ...] = (employee(),),
    roster: tuple[RosterEntry, ...] = (),
    adjacent_roster: tuple[RosterEntry, ...] = (),
    punches: tuple[Punch, ...] = (),
    trips: tuple[Trip, ...] = (),
    overtime_days: tuple[OvertimeDay, ...] = (),
    leaves: tuple[Leave, ...] = (),
    holidays: tuple[Holiday, ...] = (),
    rules: Rules | None = None,
    month: date = date(2026, 9, 1),
    roster_default: ResultRosterState = ResultRosterState.REST,
) -> MonthInputs:
    return MonthInputs(
        month=month,
        employees=employees,
        roster=roster,
        adjacent_roster=adjacent_roster,
        punches=punches,
        trips=trips,
        overtime_days=overtime_days,
        leaves=leaves,
        holidays=holidays,
        rules=rules or make_rules(),
        roster_default=roster_default,
    )


def only_day(outputs: MonthOutputs, work_date: date) -> DayResult:
    for result in outputs.day_results:
        if result.work_date == work_date:
            return result
    raise AssertionError(f"no day result for {work_date}")


def only_summary(outputs: MonthOutputs, employee_id: str = "E1") -> MonthSummary:
    for summary in outputs.month_summaries:
        if summary.employee_id == employee_id:
            return summary
    raise AssertionError(f"no month summary for {employee_id}")


def test_punch_windows_pick_earliest_in_and_latest_out() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T06:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T10:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T13:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T05:59:00+08:00"),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    shift = day.shift_results[0]
    assert shift.punch_in_at == dt("2026-09-01T06:30:00+08:00")
    assert shift.punch_out_at == dt("2026-09-01T17:00:00+08:00")
    assert shift.worked_minutes == 570
    assert shift.early_minutes == 25
    assert "out_of_window_punch" in day.day_flags


def test_last_shift_ot_cap_uses_next_shift_and_threshold() -> None:
    below_threshold = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:59:00+08:00"),
            ),
        )
    )
    at_threshold = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T18:00:00+08:00"),
            ),
        )
    )
    capped_by_next_shift = run_month(
        make_inputs(
            roster=(
                work("E1", "2026-09-01", "ADM"),
                work("E1", "2026-09-02", "DAWN"),
            ),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T23:59:00+08:00"),
            ),
        )
    )

    assert only_day(below_threshold, date(2026, 9, 1)).ot_weekday_minutes == 0
    assert only_day(at_threshold, date(2026, 9, 1)).ot_weekday_minutes == 30
    assert only_day(capped_by_next_shift, date(2026, 9, 1)).ot_weekday_minutes == 389


def test_four_break_punches_and_missing_break_does_not_change_worked() -> None:
    complete = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "YL"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T07:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T11:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T13:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
        )
    )
    missing_break = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-02", "YL"),),
            punches=(
                punch("E1", "2026-09-02", "2026-09-02T07:30:00+08:00"),
                punch("E1", "2026-09-02", "2026-09-02T17:30:00+08:00"),
            ),
        )
    )

    complete_shift = only_day(complete, date(2026, 9, 1)).shift_results[0]
    assert complete_shift.break_out_at == dt("2026-09-01T11:30:00+08:00")
    assert complete_shift.break_in_at == dt("2026-09-01T13:30:00+08:00")
    assert complete_shift.missing_punch_count == 0

    missing_day = only_day(missing_break, date(2026, 9, 2))
    missing_shift = missing_day.shift_results[0]
    assert missing_shift.worked_minutes == 480
    assert missing_shift.missing_punch_count == 2
    assert missing_day.day_status is DayStatus.MISSING_PUNCH
    assert "break_punch_missing" in missing_day.day_flags
    assert missing_day.missing_punch_deduct_amount == Decimal("-20.00")


def test_cross_month_leave_denominator_splits_without_duplication() -> None:
    cross_leave = Leave(
        id="LV1",
        approval_no="AP1",
        employee_id="E1",
        leave_kind=LeaveKind.UNPAID,
        days=Decimal("1.5"),
        rest_start_at=dt("2026-09-30T08:00:00+08:00"),
        rest_end_at=dt("2026-10-09T18:00:00+08:00"),
    )
    september = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-30", "ADM"),),
            adjacent_roster=(
                work("E1", "2026-10-08", "ADM"),
                work("E1", "2026-10-09", "ADM"),
            ),
            leaves=(cross_leave,),
        )
    )
    october = run_month(
        make_inputs(
            month=date(2026, 10, 1),
            roster=(
                work("E1", "2026-10-08", "ADM"),
                work("E1", "2026-10-09", "ADM"),
            ),
            adjacent_roster=(work("E1", "2026-09-30", "ADM"),),
            leaves=(cross_leave,),
            holidays=tuple(
                Holiday(
                    date=date(2026, 10, day),
                    name="国庆节",
                    day_type=HolidayDayType.HOLIDAY,
                )
                for day in range(1, 8)
            ),
        )
    )

    september_day = only_day(september, date(2026, 9, 30))
    october_days = [
        result
        for result in october.day_results
        if result.work_date in {date(2026, 10, 8), date(2026, 10, 9)}
    ]
    assert september_day.leave_days == Decimal("0.5")
    assert [result.leave_days for result in october_days] == [
        Decimal("0.5"),
        Decimal("0.5"),
    ]
    assert only_summary(september).unpaid_leave_days == Decimal("0.5")
    assert only_summary(october).unpaid_leave_days == Decimal("1.0")


def test_comp_offset_applies_to_work_start_date_only_and_does_not_carry() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-16", "ADM"),),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 13),
                    minutes=480,
                ),
            ),
            leaves=(
                Leave(
                    id="C1",
                    approval_no="AP-C1",
                    employee_id="E1",
                    leave_kind=LeaveKind.COMP,
                    days=Decimal("1"),
                    rest_start_at=dt("2026-09-16T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-16T17:30:00+08:00"),
                    work_start_at=dt("2026-09-13T08:30:00+08:00"),
                    work_end_at=dt("2026-09-13T17:30:00+08:00"),
                ),
            ),
        )
    )

    target = only_day(outputs, date(2026, 9, 13))
    leave_day = only_day(outputs, date(2026, 9, 16))
    summary = only_summary(outputs)
    assert target.ot_weekend_minutes == 0
    assert target.comp_offset_minutes == 480
    assert target.comp_offset_unused_minutes == 0
    assert leave_day.day_status is DayStatus.COMP_LEAVE
    assert leave_day.comp_leave_days == Decimal("1.0")
    assert summary.comp_leave_used_hours == Decimal("8.00")


def test_comp_offset_without_overtime_or_work_start_reports_unused() -> None:
    no_overtime = run_month(
        make_inputs(
            leaves=(
                Leave(
                    id="C1",
                    approval_no="AP-C1",
                    employee_id="E1",
                    leave_kind=LeaveKind.COMP,
                    days=Decimal("1"),
                    rest_start_at=dt("2026-09-20T08:00:00+08:00"),
                    rest_end_at=dt("2026-09-20T17:30:00+08:00"),
                    work_start_at=dt("2026-09-13T08:00:00+08:00"),
                    work_end_at=dt("2026-09-13T17:30:00+08:00"),
                ),
            ),
        )
    )
    missing_work_start = run_month(
        make_inputs(
            leaves=(
                Leave(
                    id="C2",
                    approval_no="AP-C2",
                    employee_id="E1",
                    leave_kind=LeaveKind.COMP,
                    days=Decimal("1"),
                    rest_start_at=dt("2026-09-19T08:00:00+08:00"),
                    rest_end_at=dt("2026-09-19T18:00:00+08:00"),
                ),
            ),
        )
    )

    target = only_day(no_overtime, date(2026, 9, 13))
    assert {
        "comp_offset_no_ot",
        "comp_offset_unused",
    } <= set(target.day_flags)
    assert target.comp_offset_unused_minutes == 480

    rest_day = only_day(missing_work_start, date(2026, 9, 19))
    assert "comp_offset_unused" in rest_day.day_flags
    assert rest_day.comp_offset_unused_minutes == 480


def test_oa_overtime_wins_over_punch_overtime_and_is_capped() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-15", "ADM"),),
            punches=(
                punch("E1", "2026-09-15", "2026-09-15T08:30:00+08:00"),
                punch("E1", "2026-09-15", "2026-09-15T18:00:00+08:00"),
            ),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 15),
                    minutes=480,
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 15))
    assert day.day_status is DayStatus.NORMAL
    assert day.shift_results[0].ot_minutes == 30
    assert day.ot_weekday_minutes == 480
    assert "overtime" in day.day_flags
    assert "oa_ot_only" not in day.day_flags


def test_break_validation_can_be_disabled_without_flagging_break_punches() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "YL"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T07:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T12:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
            rules=make_rules(break_punch_required=False),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.NORMAL
    assert day.missing_punch_count == 0
    assert day.worked_minutes == 480
    assert "out_of_window_punch" not in day.day_flags


def test_partial_leave_attendance_uses_day_fraction_across_shifts() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "EARLY", "MID"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T06:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T14:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T22:00:00+08:00"),
            ),
            leaves=(
                Leave(
                    id="LV1",
                    approval_no="AP1",
                    employee_id="E1",
                    leave_kind=LeaveKind.PAID,
                    days=Decimal("0.5"),
                    rest_start_at=dt("2026-09-01T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-01T12:00:00+08:00"),
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.NORMAL
    assert day.attendance_fraction == Decimal("0.5")
    assert day.leave_days == Decimal("0.5")


def test_partial_leave_with_punches_subtracts_leave_overlap() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
            leaves=(
                Leave(
                    id="LV1",
                    approval_no="AP1",
                    employee_id="E1",
                    leave_kind=LeaveKind.PAID,
                    days=Decimal("0.5"),
                    rest_start_at=dt("2026-09-01T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-01T12:00:00+08:00"),
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.NORMAL
    assert day.attendance_fraction == Decimal("0.5")
    assert day.leave_days == Decimal("0.5")
    assert day.paid_leave_days == Decimal("0.5")
    assert day.worked_minutes == 270
    assert day.shift_results[0].leave_days == Decimal("0.5")
    assert "leave" not in day.shift_results[0].shift_flags


def test_full_day_leave_zeros_work_and_flags_conflicts() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-02T03:30:00+08:00"),
            ),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 1),
                    minutes=120,
                ),
            ),
            leaves=(
                Leave(
                    id="LV1",
                    approval_no="AP1",
                    employee_id="E1",
                    leave_kind=LeaveKind.PAID,
                    days=Decimal("1"),
                    rest_start_at=dt("2026-09-01T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-01T17:30:00+08:00"),
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.PAID_LEAVE
    assert day.attendance_fraction == Decimal("0.0")
    assert day.worked_minutes == 0
    assert day.ot_weekday_minutes == 0
    assert day.shift_results[0].ot_minutes == 0
    assert {"leave", "leave_ot_conflict", "punch_during_leave"} <= set(day.day_flags)
    assert day.shift_results[0].punch_in_at == dt("2026-09-01T08:30:00+08:00")


def test_comp_offset_distribution_is_capped_by_punch_overtime() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-02T03:30:00+08:00"),
            ),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 1),
                    minutes=480,
                ),
            ),
            leaves=(
                Leave(
                    id="C1",
                    approval_no="AP-C1",
                    employee_id="E1",
                    leave_kind=LeaveKind.COMP,
                    days=Decimal("0.5"),
                    rest_start_at=dt("2026-09-02T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-02T17:30:00+08:00"),
                    work_start_at=dt("2026-09-01T08:30:00+08:00"),
                    work_end_at=dt("2026-09-01T17:30:00+08:00"),
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.ot_weekday_minutes == 360
    assert day.comp_offset_minutes == 240
    assert day.shift_results[0].ot_minutes == 600
    assert day.shift_results[0].comp_offset_minutes == 240


def test_multi_shift_day_status_uses_highest_priority_shift() -> None:
    overtime_shift = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "DAWN", "MID"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T02:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T10:00:00+08:00"),
            ),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 1),
                    minutes=120,
                ),
            ),
        )
    )
    trip_shift = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "DAWN", "MID"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T02:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T10:00:00+08:00"),
            ),
            trips=(
                Trip(
                    id="T1",
                    approval_no="AP-T1",
                    employee_id="E1",
                    kind=TripKind.OUT,
                    start_at=dt("2026-09-01T14:00:00+08:00"),
                    end_at=dt("2026-09-01T18:00:00+08:00"),
                ),
            ),
        )
    )

    overtime_day = only_day(overtime_shift, date(2026, 9, 1))
    assert [shift.shift_status for shift in overtime_day.shift_results] == [
        DayStatus.NORMAL,
        DayStatus.OVERTIME,
    ]
    assert overtime_day.day_status is DayStatus.OVERTIME

    trip_day = only_day(trip_shift, date(2026, 9, 1))
    assert [shift.shift_status for shift in trip_day.shift_results] == [
        DayStatus.NORMAL,
        DayStatus.TRIP_OUT,
    ]
    assert trip_day.day_status is DayStatus.TRIP_OUT


def test_absent_day_ignores_other_shifts_late_deduction() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "EARLY", "MID"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T06:10:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T11:00:00+08:00"),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert [shift.shift_status for shift in day.shift_results] == [
        DayStatus.LATE,
        DayStatus.ABSENT,
    ]
    assert day.day_status is DayStatus.ABSENT
    assert day.late_deduct_amount == Decimal("0.00")
    assert day.deduction_total == Decimal("-100.00")
    assert only_summary(outputs).attendance_deduct == Decimal("-100.00")


def test_partial_leave_without_evidence_counts_two_missing_punches_total() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "EARLY", "MID"),),
            leaves=(
                Leave(
                    id="LV1",
                    approval_no="AP1",
                    employee_id="E1",
                    leave_kind=LeaveKind.PAID,
                    days=Decimal("0.5"),
                    rest_start_at=dt("2026-09-01T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-01T12:00:00+08:00"),
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.MISSING_PUNCH
    assert day.missing_punch_count == 2
    assert day.missing_punch_deduct_amount == Decimal("-20.00")


def test_break_punches_never_become_in_or_out_punches() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "YL"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T11:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T13:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    shift = day.shift_results[0]
    assert shift.punch_in_at is None
    assert shift.punch_out_at == dt("2026-09-01T17:30:00+08:00")
    assert shift.late_minutes == 0
    assert shift.missing_punch_count == 1
    assert day.day_status is DayStatus.MISSING_PUNCH


def test_day_status_priority_missing_beats_late_and_leave_beats_absent() -> None:
    missing_and_late = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(punch("E1", "2026-09-01", "2026-09-01T09:30:00+08:00"),),
        )
    )
    full_leave = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            leaves=(
                Leave(
                    id="LV1",
                    approval_no="AP1",
                    employee_id="E1",
                    leave_kind=LeaveKind.PAID,
                    days=Decimal("1"),
                    rest_start_at=dt("2026-09-01T08:30:00+08:00"),
                    rest_end_at=dt("2026-09-01T17:30:00+08:00"),
                ),
            ),
        )
    )

    assert only_day(missing_and_late, date(2026, 9, 1)).day_status is (
        DayStatus.MISSING_PUNCH
    )
    leave_day = only_day(full_leave, date(2026, 9, 1))
    assert leave_day.day_status is DayStatus.PAID_LEAVE
    assert leave_day.attendance_fraction == Decimal("0.0")
    assert leave_day.worked_minutes == 0


def test_attendance_fraction_weights_multi_shift_by_scheduled_minutes() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "EARLY", "MID"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T06:00:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T11:00:00+08:00"),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.attendance_fraction == Decimal("0.5")
    assert day.scheduled_minutes == 840
    assert day.day_status is DayStatus.ABSENT
    assert only_summary(outputs).weekday_attended == Decimal("0.5")


def test_month_summary_splits_workday_weekend_and_ignores_holiday_punch() -> None:
    outputs = run_month(
        make_inputs(
            roster=(
                work("E1", "2026-09-01", "ADM"),
                work("E1", "2026-09-05", "ADM"),
            ),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
                punch("E1", "2026-09-05", "2026-09-05T08:30:00+08:00"),
                punch("E1", "2026-09-05", "2026-09-05T17:30:00+08:00"),
                punch("E1", "2026-09-25", "2026-09-25T08:00:00+08:00"),
            ),
            holidays=(
                Holiday(
                    date=date(2026, 9, 25),
                    name="中秋节",
                    day_type=HolidayDayType.HOLIDAY,
                ),
            ),
        )
    )

    summary = only_summary(outputs)
    holiday_day = only_day(outputs, date(2026, 9, 25))
    assert summary.weekday_full == Decimal("1.0")
    assert summary.weekend_full == Decimal("1.0")
    assert summary.weekday_attended == Decimal("1.0")
    assert summary.weekend_attended == Decimal("1.0")
    assert holiday_day.attendance_fraction == Decimal("1.0")
    assert holiday_day.day_status is DayStatus.UNSCHEDULED_ATTENDANCE


def test_deduction_items_are_negative_and_total_exactly() -> None:
    outputs = run_month(
        make_inputs(
            roster=(
                work("E1", "2026-09-01", "ADM"),
                work("E1", "2026-09-02", "ADM"),
                work("E1", "2026-09-03", "ADM"),
            ),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T09:12:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T16:30:00+08:00"),
                punch("E1", "2026-09-02", "2026-09-02T08:30:00+08:00"),
            ),
        )
    )

    late_day = only_day(outputs, date(2026, 9, 1))
    missing_day = only_day(outputs, date(2026, 9, 2))
    absent_day = only_day(outputs, date(2026, 9, 3))
    summary = only_summary(outputs)
    assert late_day.late_deduct_amount == Decimal("-20.00")
    assert late_day.early_deduct_amount == Decimal("-20.00")
    assert late_day.deduction_total == Decimal("-40.00")
    assert missing_day.missing_punch_deduct_amount == Decimal("-10.00")
    assert absent_day.absent_deduct_amount == Decimal("-100.00")
    assert summary.attendance_deduct == Decimal("-150.00")


def test_numeric_conventions_round_only_contract_values() -> None:
    outputs = run_month(
        make_inputs(
            roster=(
                work("E1", "2026-09-01", "ADM"),
                work("E1", "2026-09-02", "ADM"),
                work("E1", "2026-09-03", "ADM"),
                work("E1", "2026-09-04", "ADM"),
            ),
            trips=(
                Trip(
                    id="T1",
                    approval_no="AP-T",
                    employee_id="E1",
                    kind=TripKind.OUT,
                    start_at=dt("2026-09-01T14:00:00+08:00"),
                    end_at=dt("2026-09-01T18:00:00+08:00"),
                ),
            ),
            overtime_days=(
                OvertimeDay(
                    id="OT1",
                    approval_no="AP-OT1",
                    employee_id="E1",
                    work_date=date(2026, 9, 2),
                    minutes=480,
                ),
                OvertimeDay(
                    id="OT2",
                    approval_no="AP-OT2",
                    employee_id="E1",
                    work_date=date(2026, 9, 3),
                    minutes=480,
                ),
                OvertimeDay(
                    id="OT3",
                    approval_no="AP-OT3",
                    employee_id="E1",
                    work_date=date(2026, 9, 4),
                    minutes=59,
                ),
            ),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    summary = only_summary(outputs)
    assert day.attendance_fraction == Decimal("0.4")
    assert day.trip_fraction == Decimal("0.4")
    assert day.worked_minutes == 187
    assert day.attendance_fraction.as_tuple().exponent == -1
    assert summary.ot_weekday_hours == Decimal("16.98")
    assert summary.ot_weekday_hours.as_tuple().exponent == -2
    assert summary.ot_weekday_minutes == 1019
    assert summary.attendance_deduct.as_tuple().exponent == -2


def test_absent_if_no_punch_false_counts_two_missing_punches() -> None:
    outputs = run_month(
        make_inputs(
            roster=(work("E1", "2026-09-01", "ADM"),),
            rules=make_rules(absent_if_no_punch=False),
        )
    )

    day = only_day(outputs, date(2026, 9, 1))
    assert day.day_status is DayStatus.MISSING_PUNCH
    assert day.missing_punch_count == 2
    assert day.missing_punch_deduct_amount == Decimal("-20.00")


def test_scope_skips_out_of_employment_and_no_data_employees() -> None:
    outputs = run_month(
        make_inputs(
            employees=(
                employee(),
                employee("E2", hire_date=date(2026, 10, 1)),
                employee("E3"),
            ),
            roster=(work("E1", "2026-09-01", "ADM"),),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:30:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
        )
    )

    assert outputs.summary.employees_total == 3
    assert outputs.summary.employees_calculated == 1
    assert outputs.summary.employees_skipped == 2
    assert outputs.summary.skipped_reasons == {
        "no_data": 1,
        "out_of_employment": 1,
    }


def test_resign_date_truncates_the_day_universe() -> None:
    outputs = run_month(
        make_inputs(
            employees=(employee(resign_date=date(2026, 9, 10)),),
            punches=(
                punch("E1", "2026-09-04", "2026-09-04T08:30:00+08:00"),
                punch("E1", "2026-09-04", "2026-09-04T17:30:00+08:00"),
            ),
        )
    )

    assert outputs.summary.days_total == 10
    assert outputs.summary.days_by_status[DayStatus.REST.value] == 9
    assert only_day(outputs, date(2026, 9, 4)).day_type is DayType.WORKDAY


def test_roster_entry_rules_override_month_defaults() -> None:
    overridden = RosterEntry(
        employee_id="E1",
        work_date=date(2026, 9, 1),
        state=RosterState.WORK,
        shifts=(ADM,),
        rules=make_rules(late_grace_min=0),
    )
    outputs = run_month(
        make_inputs(
            roster=(overridden,),
            punches=(
                punch("E1", "2026-09-01", "2026-09-01T08:33:00+08:00"),
                punch("E1", "2026-09-01", "2026-09-01T17:30:00+08:00"),
            ),
        )
    )

    result = only_day(outputs, date(2026, 9, 1))
    assert result.day_status is DayStatus.LATE
    assert result.late_minutes == 3
