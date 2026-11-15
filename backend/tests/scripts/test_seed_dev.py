"""Development seed script: guard and idempotency."""

from datetime import date, time
from decimal import Decimal
from typing import NamedTuple

import pytest
from sqlmodel import Session, select

from app import seed_dev
from app.core.db import engine
from app.enums import (
    AttendanceMonthStatus,
    ContractType,
    EmployeeStatus,
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    ImportSource,
    RosterSource,
    ScheduleScopeType,
)
from app.models import (
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonth,
    AttendanceMonthSnapshot,
    AttendanceMonthSummary,
    AttendanceResultAdjustment,
    AttendanceRule,
    CalcRun,
    Company,
    CostCenter,
    Department,
    Employee,
    Holiday,
    ImportBatch,
    ImportMappingTemplate,
    OaLeave,
    OaOvertime,
    OaTrip,
    PlanDay,
    PlanRuleOverride,
    Position,
    PunchRecord,
    RosterEntry,
    RosterEntryShift,
    SchedulePlan,
    Shift,
)
from app.services.attendance import imports as import_service

SEEDED_CODES = ["C1", "C2", "C3", "C4"]
SEEDED_NAMES = ["荣新建设", "荣新科技", "荣新物流", "荣新考勤演示"]
SEEDED_DEPARTMENTS = {
    "C1": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"],
    "C2": ["K1", "K2", "K3"],
    "C3": [],
    "C4": ["D1", "D2", "D3", "D4"],
}
SEEDED_POSITIONS = {
    "C1": ["P1", "P2", "P3", "P4", "P5", "P6"],
    "C2": ["K1", "K2"],
    "C3": [],
    "C4": ["P1", "P2", "P3", "P4", "P5"],
}
SEEDED_COST_CENTERS = {
    "C1": ["K1", "K2", "K3", "K4", "K5", "K6"],
    "C2": ["K1", "K2"],
    "C3": [],
    "C4": [],
}
# Kept independent of seed_dev.EMPLOYEES so accidental data changes fail the test.
SEEDED_EMPLOYEES = {
    "C1": [
        "E1001",
        "E1002",
        "E1003",
        "E1004",
        "E1005",
        "E1006",
        "E1007",
        "E1008",
        "E1009",
        "E1010",
        "E1011",
        "E1012",
        "E1013",
        "E1014",
        "E1015",
        "E1016",
    ],
    "C2": ["E2001", "E2002", "E2003", "E2004"],
    "C3": [],
    "C4": [
        "E101",
        "E102",
        "E103",
        "E104",
        "E105",
        "E106",
        "E107",
        "E108",
        "E109",
        "E110",
        "E111",
        "E112",
        "E113",
    ],
}


def _companies() -> list[Company]:
    with Session(engine) as session:
        return list(session.exec(select(Company).order_by(Company.company_code)).all())


def _departments_by_company() -> dict[str, list[Department]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        departments: dict[str, list[Department]] = {
            code: [] for code in company_codes.values()
        }
        for department in session.exec(
            select(Department).order_by(Department.dept_code)
        ).all():
            departments[company_codes[department.company_id]].append(department)
        return departments


def _positions_by_company() -> dict[str, list[Position]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        positions: dict[str, list[Position]] = {
            code: [] for code in company_codes.values()
        }
        for position in session.exec(
            select(Position).order_by(Position.position_code)
        ).all():
            positions[company_codes[position.company_id]].append(position)
        return positions


@pytest.mark.parametrize("environment", ["production", None])
def test_seed_refuses_outside_development(
    monkeypatch: pytest.MonkeyPatch, environment: str | None
) -> None:
    monkeypatch.setattr(seed_dev.settings, "FASTAPI_ENV", environment)

    with pytest.raises(SystemExit, match="development"):
        seed_dev.main()

    assert _companies() == []


def test_seed_inserts_four_companies_once() -> None:
    seed_dev.main()
    seed_dev.main()

    companies = _companies()
    assert [company.company_code for company in companies] == SEEDED_CODES
    assert [company.company_name for company in companies] == SEEDED_NAMES
    assert all(company.is_active for company in companies)


def test_seed_does_not_overwrite_existing_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        company.company_name = "用户修改后的名称"
        company.note = "用户备注"
        session.add(company)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        assert company.company_name == "用户修改后的名称"
        assert company.note == "用户备注"


def test_seed_inserts_the_department_tree_once() -> None:
    seed_dev.main()
    seed_dev.main()

    departments = _departments_by_company()

    for company_code, expected_codes in SEEDED_DEPARTMENTS.items():
        assert [d.dept_code for d in departments[company_code]] == expected_codes

    full_company = {d.dept_code: d for d in departments["C1"]}
    assert full_company["D2"].parent_id == full_company["D1"].id
    assert full_company["D3"].parent_id == full_company["D2"].id
    assert full_company["D4"].parent_id == full_company["D2"].id
    assert full_company["D1"].parent_id is None


def test_seed_includes_one_inactive_department_without_active_employees() -> None:
    seed_dev.main()

    with Session(engine) as session:
        inactive_departments = session.exec(
            select(Department).where(Department.is_active.is_(False))
        ).all()
        inactive_ids = [department.id for department in inactive_departments]
        active_employees = session.exec(
            select(Employee).where(
                Employee.dept_id.in_(inactive_ids),
                Employee.status.in_([EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]),
            )
        ).all()

    assert [department.dept_code for department in inactive_departments] == ["D7"]
    assert active_employees == []


def test_seed_inserts_positions_once() -> None:
    seed_dev.main()
    seed_dev.main()

    positions = _positions_by_company()

    for company_code, expected_codes in SEEDED_POSITIONS.items():
        assert [p.position_code for p in positions[company_code]] == expected_codes

    full_company = {p.position_code: p for p in positions["C1"]}
    assert full_company["P1"].dept_id is not None
    assert full_company["P2"].dept_id is not None
    assert full_company["P6"].dept_id is None
    assert all(p.is_active for p in positions["C1"])


def test_seed_position_default_departments_use_the_same_company() -> None:
    seed_dev.main()

    with Session(engine) as session:
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        positions = session.exec(select(Position)).all()

        for position in positions:
            if position.dept_id is None:
                continue
            assert departments[position.dept_id].company_id == position.company_id


def test_seed_does_not_overwrite_existing_position_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        position = session.exec(
            select(Position).where(
                Position.company_id == company.id,
                Position.position_code == "P1",
            )
        ).one()
        position.position_name = "用户修改后的岗位"
        position.order_no = 42
        session.add(position)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        position = session.exec(
            select(Position).where(
                Position.company_id == company.id,
                Position.position_code == "P1",
            )
        ).one()
        assert position.position_name == "用户修改后的岗位"
        assert position.order_no == 42


def test_seed_does_not_overwrite_existing_department_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        department = session.exec(
            select(Department).where(
                Department.company_id == company.id,
                Department.dept_code == "D2",
            )
        ).one()
        department.dept_name = "用户修改后的部门"
        department.order_no = 42
        session.add(department)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        department = session.exec(
            select(Department).where(
                Department.company_id == company.id,
                Department.dept_code == "D2",
            )
        ).one()
        assert department.dept_name == "用户修改后的部门"
        assert department.order_no == 42


def _cost_centers_by_company() -> dict[str, list[CostCenter]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        cost_centers: dict[str, list[CostCenter]] = {
            code: [] for code in company_codes.values()
        }
        for cost_center in session.exec(
            select(CostCenter).order_by(CostCenter.cost_org_code)
        ).all():
            cost_centers[company_codes[cost_center.company_id]].append(cost_center)
        return cost_centers


def test_seed_inserts_the_cost_center_tree_once() -> None:
    seed_dev.main()
    seed_dev.main()

    cost_centers = _cost_centers_by_company()

    for company_code, expected_codes in SEEDED_COST_CENTERS.items():
        assert [c.cost_org_code for c in cost_centers[company_code]] == expected_codes

    full_company = {c.cost_org_code: c for c in cost_centers["C1"]}
    assert full_company["K1"].parent_id is None
    assert full_company["K2"].parent_id == full_company["K1"].id
    assert full_company["K3"].parent_id == full_company["K2"].id
    assert full_company["K4"].parent_id == full_company["K2"].id
    assert full_company["K5"].parent_id == full_company["K1"].id
    assert full_company["K6"].parent_id == full_company["K1"].id
    assert full_company["K6"].is_active is False
    assert all(c.is_active for c in cost_centers["C2"])


def test_seed_includes_one_inactive_cost_center_without_active_employees() -> None:
    seed_dev.main()

    with Session(engine) as session:
        inactive_cost_centers = session.exec(
            select(CostCenter).where(CostCenter.is_active.is_(False))
        ).all()
        inactive_ids = [cost_center.id for cost_center in inactive_cost_centers]
        active_employees = session.exec(
            select(Employee).where(
                Employee.cost_org_id.in_(inactive_ids),
                Employee.status.in_([EmployeeStatus.ACTIVE, EmployeeStatus.PROBATION]),
            )
        ).all()

    assert [c.cost_org_code for c in inactive_cost_centers] == ["K6"]
    assert active_employees == []


def test_seed_cost_center_parents_and_budgets_use_the_same_company() -> None:
    seed_dev.main()

    with Session(engine) as session:
        cost_centers = {
            cost_center.id: cost_center
            for cost_center in session.exec(select(CostCenter)).all()
        }

        for cost_center in cost_centers.values():
            assert cost_center.budget >= 0
            assert 1 <= cost_center.warn_pct <= 100
            if cost_center.parent_id is None:
                continue
            parent = cost_centers[cost_center.parent_id]
            assert parent.company_id == cost_center.company_id


def test_seed_does_not_overwrite_existing_cost_center_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        cost_center = session.exec(
            select(CostCenter).where(
                CostCenter.company_id == company.id,
                CostCenter.cost_org_code == "K2",
            )
        ).one()
        cost_center.cost_org_name = "用户修改后的成本中心"
        cost_center.budget = Decimal("42.00")
        cost_center.warn_pct = 66
        session.add(cost_center)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        cost_center = session.exec(
            select(CostCenter).where(
                CostCenter.company_id == company.id,
                CostCenter.cost_org_code == "K2",
            )
        ).one()
        assert cost_center.cost_org_name == "用户修改后的成本中心"
        assert cost_center.budget == Decimal("42.00")
        assert cost_center.warn_pct == 66


def _employees_by_company() -> dict[str, list[Employee]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        employees: dict[str, list[Employee]] = {
            code: [] for code in company_codes.values()
        }
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        for employee in session.exec(
            select(Employee).order_by(Employee.employee_no)
        ).all():
            company_id = departments[employee.dept_id].company_id
            employees[company_codes[company_id]].append(employee)
        return employees


def test_seed_inserts_employees_once() -> None:
    seed_dev.main()
    seed_dev.main()

    employees = _employees_by_company()

    for company_code, expected_numbers in SEEDED_EMPLOYEES.items():
        assert [e.employee_no for e in employees[company_code]] == expected_numbers

    assert 15 <= len(employees["C1"]) <= 20
    assert 3 <= len(employees["C2"]) <= 5
    assert employees["C3"] == []
    assert len(employees["C4"]) == 13


def test_seed_employee_statuses_contracts_and_unassigned_are_varied() -> None:
    seed_dev.main()

    employees = _employees_by_company()
    full_company = employees["C1"]

    assert {e.status for e in full_company} == set(EmployeeStatus)
    assert {e.contract_type for e in full_company} == set(ContractType)
    assert any(e.cost_org_id is None for e in full_company)
    assert sum(e.manager_id is not None for e in full_company) >= 10
    assert any(e.status is EmployeeStatus.RESIGNED for e in employees["C2"])
    assert any(e.cost_org_id is None for e in employees["C2"])


def test_seed_employee_managers_are_same_company_and_dates_are_valid() -> None:
    seed_dev.main()

    with Session(engine) as session:
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        employees = {
            employee.employee_no: employee
            for employee in session.exec(select(Employee)).all()
        }
        seed_data = {data["employee_no"]: data for data in seed_dev.EMPLOYEES}

        for employee in employees.values():
            department = departments[employee.dept_id]
            assert employee.hire_date <= date.today()
            if employee.status is EmployeeStatus.RESIGNED:
                assert employee.resign_date is not None
                assert employee.resign_date <= date.today()
                assert employee.resign_date >= employee.hire_date
            else:
                assert employee.resign_date is None

            if employee.manager_id is None:
                continue
            manager = session.get(Employee, employee.manager_id)
            assert manager is not None
            manager_department = departments[manager.dept_id]
            assert manager_department.company_id == department.company_id
            assert manager.status in (
                EmployeeStatus.ACTIVE,
                EmployeeStatus.PROBATION,
            )
            assert manager.employee_no != employee.employee_no
            assert seed_data[employee.employee_no]["manager_no"] == (
                manager.employee_no
            )


def test_seed_does_not_overwrite_existing_employee_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        employee = session.exec(
            select(Employee).where(Employee.employee_no == "E1001")
        ).one()
        employee.name = "用户修改后的员工"
        employee.note = "用户备注"
        session.add(employee)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        employee = session.exec(
            select(Employee).where(Employee.employee_no == "E1001")
        ).one()
        assert employee.name == "用户修改后的员工"
        assert employee.note == "用户备注"


def _company_by_code(code: str) -> Company:
    with Session(engine) as session:
        return session.exec(select(Company).where(Company.company_code == code)).one()


def _attendance_company_rows() -> tuple[
    list[Shift], list[AttendanceRule], list[Holiday]
]:
    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C4")
        ).one()
        shifts = list(
            session.exec(
                select(Shift)
                .where(Shift.company_id == company.id)
                .order_by(Shift.shift_code)
            ).all()
        )
        rules = list(
            session.exec(
                select(AttendanceRule).where(AttendanceRule.company_id == company.id)
            ).all()
        )
        holidays = list(
            session.exec(
                select(Holiday)
                .where(Holiday.company_id == company.id)
                .order_by(Holiday.date)
            ).all()
        )
        return shifts, rules, holidays


def test_seed_inserts_attendance_reference_data_once() -> None:
    seed_dev.main()
    seed_dev.main()

    shifts, rules, holidays = _attendance_company_rows()

    assert [shift.shift_code for shift in shifts] == [
        "ADM",
        "DAWN",
        "EARLY",
        "MID",
        "NIGHT",
        "TEC",
        "YL",
    ]
    assert all(shift.is_active for shift in shifts)
    by_code = {shift.shift_code: shift for shift in shifts}
    # The seven golden-case shifts keep their exact times and fixed colors.
    assert by_code["ADM"].start_time == time(8, 30)
    assert by_code["ADM"].end_time == time(17, 30)
    assert by_code["TEC"].start_time == time(8, 0)
    assert by_code["TEC"].end_time == time(18, 0)
    assert by_code["YL"].break_start == time(11, 30)
    assert by_code["YL"].break_end == time(13, 30)
    assert by_code["YL"].rest_minutes == 120
    assert by_code["NIGHT"].cross_day is True
    assert by_code["NIGHT"].break_start == time(2, 0)
    assert by_code["NIGHT"].break_end == time(3, 0)
    assert [by_code[code].color for code in sorted(by_code)] == [
        "#2563EB",
        "#DC2626",
        "#F59E0B",
        "#0EA5E9",
        "#1E293B",
        "#7C3AED",
        "#16A34A",
    ]
    assert len(rules) == 1
    rule = rules[0]
    assert rule.punch_window_min == 120
    assert rule.late_cap_min == 240
    assert rule.early_cap_min == 240
    assert rule.ot_max_min == 600
    assert rule.late_grace_min == 5
    assert rule.early_grace_min == 5
    assert rule.ot_threshold_min == 30
    assert rule.absent_if_no_punch is True
    assert rule.break_punch_required is True
    assert rule.break_punch_tolerance_min == 60
    assert rule.absent_deduct_per_day == Decimal("100.00")
    assert rule.late_deduct_per_occurrence == Decimal("20.00")
    assert rule.early_deduct_per_occurrence == Decimal("20.00")
    assert rule.missing_punch_deduct_per_occurrence == Decimal("10.00")

    assert [holiday.date for holiday in holidays] == [
        date(2026, 9, 25),
        date(2026, 9, 27),
        date(2026, 10, 1),
        date(2026, 10, 2),
        date(2026, 10, 3),
        date(2026, 10, 4),
        date(2026, 10, 5),
        date(2026, 10, 6),
        date(2026, 10, 7),
    ]
    assert holidays[0].name == "中秋节"
    assert holidays[0].day_type == HolidayDayType.HOLIDAY
    assert holidays[1].name == "调休上班"
    assert holidays[1].day_type == HolidayDayType.ADJUSTED_WORKDAY
    assert {holiday.name for holiday in holidays[2:]} == {"国庆节"}


def test_attendance_reference_data_never_touches_other_companies() -> None:
    seed_dev.main()

    with Session(engine) as session:
        other_company_ids = [
            company.id
            for company in session.exec(
                select(Company).where(Company.company_code.in_(["C1", "C2", "C3"]))
            ).all()
        ]
        assert (
            session.exec(
                select(Shift).where(Shift.company_id.in_(other_company_ids))
            ).all()
            == []
        )
        assert (
            session.exec(
                select(AttendanceRule).where(
                    AttendanceRule.company_id.in_(other_company_ids)
                )
            ).all()
            == []
        )
        assert (
            session.exec(
                select(Holiday).where(Holiday.company_id.in_(other_company_ids))
            ).all()
            == []
        )


def test_seed_does_not_overwrite_existing_attendance_edits() -> None:
    seed_dev.main()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C4")
        ).one()
        shift = session.exec(
            select(Shift).where(
                Shift.company_id == company.id,
                Shift.shift_code == "ADM",
            )
        ).one()
        shift.shift_name = "用户修改后的班次"
        rule = session.exec(
            select(AttendanceRule).where(AttendanceRule.company_id == company.id)
        ).one()
        rule.punch_window_min = 45
        holiday = session.exec(
            select(Holiday).where(
                Holiday.company_id == company.id,
                Holiday.date == date(2026, 9, 25),
            )
        ).one()
        holiday.name = "用户修改后的节假日"
        session.add(shift)
        session.add(rule)
        session.add(holiday)
        session.commit()

    seed_dev.main()

    shifts, rules, holidays = _attendance_company_rows()
    stored_shift = next(item for item in shifts if item.shift_code == "ADM")
    assert stored_shift.shift_name == "用户修改后的班次"
    assert rules[0].punch_window_min == 45
    stored_holiday = next(item for item in holidays if item.date == date(2026, 9, 25))
    assert stored_holiday.name == "用户修改后的节假日"


def test_seed_attendance_employees_match_the_fixture_contract() -> None:
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        departments = {
            department.dept_code: department
            for department in session.exec(
                select(Department).where(Department.company_id == c4.id)
            ).all()
        }
        positions = {
            position.position_code: position
            for position in session.exec(
                select(Position).where(Position.company_id == c4.id)
            ).all()
        }
        employees = {
            employee.employee_no: employee
            for employee in session.exec(select(Employee)).all()
        }

        assert employees["E108"].position_id == positions["P2"].id
        assert employees["E112"].status is EmployeeStatus.RESIGNED
        assert employees["E112"].resign_date == date(2026, 8, 31)
        assert employees["E113"].hire_date == date(2026, 9, 15)
        assert employees["E110"].name == "张伟"
        assert employees["E111"].name == "张伟"
        assert employees["E110"].dept_id != employees["E111"].dept_id
        assert employees["E110"].dept_id == departments["D1"].id
        assert employees["E111"].dept_id == departments["D2"].id


def test_seed_inserts_four_plans_and_expands_september_once() -> None:
    seed_dev.main()
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        plans = {
            plan.plan_name: plan
            for plan in session.exec(
                select(SchedulePlan).where(SchedulePlan.company_id == c4.id)
            ).all()
        }
        assert set(plans) == {"行政班", "财务技术班", "园林班", "李金辉夜班"}
        assert {plan.scope_type for plan in plans.values()} == {
            ScheduleScopeType.ALL,
            ScheduleScopeType.DEPT,
            ScheduleScopeType.POSITION,
            ScheduleScopeType.EMPLOYEE,
        }
        assert all(plan.month == date(2026, 9, 1) for plan in plans.values())
        assert all(plan.status.value == "enabled" for plan in plans.values())

        garden_override = session.get(PlanRuleOverride, plans["园林班"].id)
        assert garden_override is not None
        assert garden_override.ot_threshold_min == 15
        assert session.get(PlanRuleOverride, plans["行政班"].id) is None

        month = session.exec(
            select(AttendanceMonth).where(
                AttendanceMonth.company_id == c4.id,
                AttendanceMonth.month == date(2026, 9, 1),
            )
        ).one()
        assert month.status.value == "draft"

        employees = {
            employee.employee_no: employee
            for employee in session.exec(
                select(Employee).where(
                    Employee.dept_id.in_(
                        select(Department.id).where(Department.company_id == c4.id)
                    )
                )
            ).all()
        }
        roster = list(
            session.exec(
                select(RosterEntry).where(RosterEntry.company_id == c4.id)
            ).all()
        )
        assert roster
        assert all(
            date(2026, 9, 1) <= entry.work_date <= date(2026, 9, 30) for entry in roster
        )
        assert [
            entry for entry in roster if entry.employee_id == employees["E112"].id
        ] == []
        late_hire_entries = [
            entry for entry in roster if entry.employee_id == employees["E113"].id
        ]
        assert late_hire_entries
        assert min(entry.work_date for entry in late_hire_entries) == date(2026, 9, 15)

        by_employee_date = {
            (entry.employee_id, entry.work_date): entry for entry in roster
        }
        # Employee scope outranks position/department/all.
        night_entry = by_employee_date[(employees["E105"].id, date(2026, 9, 30))]
        assert night_entry.plan_id == plans["李金辉夜班"].id
        night_shifts = session.exec(
            select(Shift).where(
                Shift.id.in_(
                    select(PlanDay.shift_id).where(
                        PlanDay.plan_id == plans["李金辉夜班"].id,
                        PlanDay.day_of_month == 30,
                    )
                )
            )
        ).all()
        assert [shift.shift_code for shift in night_shifts] == ["NIGHT"]
        # The employee plan has no 09-27 row, so higher-specificity rest wins.
        assert (
            by_employee_date[(employees["E105"].id, date(2026, 9, 27))].state.value
            == "rest"
        )
        # Position scope outranks the all-company plan.
        assert (
            by_employee_date[(employees["E108"].id, date(2026, 9, 1))].plan_id
            == plans["园林班"].id
        )
        # Department scope outranks the all-company plan.
        assert (
            by_employee_date[(employees["E102"].id, date(2026, 9, 1))].plan_id
            == plans["财务技术班"].id
        )
        assert (
            by_employee_date[(employees["E101"].id, date(2026, 9, 1))].plan_id
            == plans["行政班"].id
        )

        # The two documented manual exceptions are seeded after expansion and
        # keep the overridden plan id.
        manual_entries = {
            (entry.employee_id, entry.work_date): entry
            for entry in roster
            if entry.source == RosterSource.MANUAL
        }
        assert set(manual_entries) == {
            (employees["E103"].id, date(2026, 9, 10)),
            (employees["E104"].id, date(2026, 9, 11)),
        }
        rest_entry = manual_entries[(employees["E103"].id, date(2026, 9, 10))]
        assert rest_entry.state.value == "rest"
        assert rest_entry.plan_id == plans["行政班"].id
        assert rest_entry.note == "个人调休"
        multi_entry = manual_entries[(employees["E104"].id, date(2026, 9, 11))]
        assert multi_entry.state.value == "work"
        assert multi_entry.plan_id == plans["行政班"].id
        assert [
            shift.shift_code
            for shift in session.exec(
                select(RosterEntryShift)
                .where(RosterEntryShift.roster_entry_id == multi_entry.id)
                .order_by(RosterEntryShift.seq)
            ).all()
        ] == ["EARLY", "MID"]


# The four fixtures in spec section 15.4, with the row-level counts asserted
# by the import fixture regression. ``warnings`` and ``errors`` are issues,
# while ``skipped`` includes business filters such as non-approved OA rows.
class FixtureStats(NamedTuple):
    file_name: str
    source_rows: int
    valid: int
    skipped: int
    errors: int
    warnings: int


IMPORT_FIXTURE_STATS: dict[ImportDataType, FixtureStats] = {
    ImportDataType.PUNCH: FixtureStats("punch-2026-09.csv", 37, 27, 10, 4, 5),
    ImportDataType.TRIP: FixtureStats("oa-trip-2026-09.csv", 15, 8, 9, 5, 0),
    ImportDataType.OT: FixtureStats("oa-overtime-2026-09.csv", 15, 8, 7, 3, 1),
    ImportDataType.LEAVE: FixtureStats("oa-leave-2026-09.csv", 19, 8, 11, 8, 1),
}
IMPORT_RECORD_MODELS = (PunchRecord, OaTrip, OaOvertime, OaLeave)


class SeedBatchState(NamedTuple):
    batch_count: int
    records: dict[str, int]
    other_company_batches: int
    template_count: int


def _seed_batch_state() -> SeedBatchState:
    """Stable fingerprint of the C4 import payload for idempotency checks."""
    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        batch_count = len(
            session.exec(
                select(ImportBatch).where(ImportBatch.company_id == c4.id)
            ).all()
        )
        records = {
            model.__tablename__: len(
                session.exec(select(model).where(model.company_id == c4.id)).all()
            )
            for model in IMPORT_RECORD_MODELS
        }
        other_company_batches = len(
            session.exec(
                select(ImportBatch).where(ImportBatch.company_id != c4.id)
            ).all()
        )
        template_count = len(
            session.exec(
                select(ImportMappingTemplate).where(
                    ImportMappingTemplate.company_id == c4.id
                )
            ).all()
        )
        return SeedBatchState(
            batch_count, records, other_company_batches, template_count
        )


def _c4_batches() -> dict[ImportDataType, ImportBatch]:
    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        return {
            batch.data_type: batch
            for batch in session.exec(
                select(ImportBatch).where(ImportBatch.company_id == c4.id)
            ).all()
        }


def test_seed_commits_the_four_fixture_batches_once() -> None:
    seed_dev.main()

    batches = _c4_batches()
    assert set(batches) == set(IMPORT_FIXTURE_STATS)
    for data_type, stats in IMPORT_FIXTURE_STATS.items():
        batch = batches[data_type]
        assert batch.status == ImportBatchStatus.COMMITTED
        assert batch.month == date(2026, 9, 1)
        assert batch.file_name == stats.file_name
        assert batch.source == ImportSource.UPLOAD
        assert batch.source_rows == stats.source_rows
        assert batch.valid_records == stats.valid
        assert batch.skipped_records == stats.skipped
        assert batch.error_records == stats.errors
        assert batch.warning_records == stats.warnings
        assert batch.file_size is not None and batch.file_size > 0
        assert batch.file_sha256 is not None and len(batch.file_sha256) == 64
        assert batch.column_mapping
        assert batch.header_columns
        assert batch.operator_id is not None
        assert batch.committed_at is not None
        assert batch.expires_at is None

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        assert (
            session.exec(
                select(ImportBatch).where(
                    ImportBatch.company_id == c4.id,
                    ImportBatch.status != ImportBatchStatus.COMMITTED,
                )
            ).all()
            == []
        )
        records = {
            model.__tablename__: session.exec(
                select(model).where(model.company_id == c4.id)
            ).all()
            for model in IMPORT_RECORD_MODELS
        }
        assert {name: len(rows) for name, rows in records.items()} == {
            "punch_record": IMPORT_FIXTURE_STATS[ImportDataType.PUNCH].valid,
            "oa_trip": IMPORT_FIXTURE_STATS[ImportDataType.TRIP].valid,
            "oa_overtime": IMPORT_FIXTURE_STATS[ImportDataType.OT].valid,
            "oa_leave": IMPORT_FIXTURE_STATS[ImportDataType.LEAVE].valid,
        }
        assert all(row.raw_row for row in records["punch_record"])
        assert (
            len(
                session.exec(
                    select(ImportMappingTemplate).where(
                        ImportMappingTemplate.company_id == c4.id
                    )
                ).all()
            )
            == 4
        )


def test_seed_runs_twice_with_stable_import_counts() -> None:
    seed_dev.main()
    first = _seed_batch_state()
    seed_dev.main()
    second = _seed_batch_state()

    assert first == second
    assert first.batch_count == 4
    assert first.records == {
        "punch_record": 27,
        "oa_trip": 8,
        "oa_overtime": 8,
        "oa_leave": 8,
    }
    assert first.other_company_batches == 0
    assert first.template_count == 4


def test_seed_does_not_overwrite_committed_import_batches() -> None:
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        batch = session.exec(
            select(ImportBatch).where(
                ImportBatch.company_id == c4.id,
                ImportBatch.data_type == ImportDataType.PUNCH,
            )
        ).one()
        batch.file_name = "用户替换后的文件.csv"
        batch.valid_records = 1
        session.add(batch)
        session.commit()

    seed_dev.main()

    batch = _c4_batches()[ImportDataType.PUNCH]
    assert batch.file_name == "用户替换后的文件.csv"
    assert batch.valid_records == 1


def test_seed_does_not_create_calculation_outputs() -> None:
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        month = session.exec(
            select(AttendanceMonth).where(AttendanceMonth.company_id == c4.id)
        ).one()
        assert month.status == AttendanceMonthStatus.DRAFT
        assert (
            session.exec(
                select(CalcRun).where(CalcRun.attendance_month_id == month.id)
            ).all()
            == []
        )
        assert (
            session.exec(
                select(AttendanceMonthSnapshot).where(
                    AttendanceMonthSnapshot.attendance_month_id == month.id
                )
            ).all()
            == []
        )
        for model in (
            AttendanceDayResult,
            AttendanceDayShiftResult,
            AttendanceMonthSummary,
            AttendanceResultAdjustment,
        ):
            assert (
                session.exec(select(model).where(model.company_id == c4.id)).all() == []
            ), model.__tablename__


TOP_LEVEL_COMPANY_MODELS = (
    Shift,
    AttendanceRule,
    Holiday,
    SchedulePlan,
    RosterEntry,
    AttendanceMonth,
    ImportBatch,
    ImportMappingTemplate,
    PunchRecord,
    OaTrip,
    OaOvertime,
    OaLeave,
    AttendanceDayResult,
    AttendanceDayShiftResult,
    AttendanceMonthSummary,
    AttendanceResultAdjustment,
)


def test_seed_never_writes_attendance_rows_for_other_companies() -> None:
    seed_dev.main()
    seed_dev.main()

    with Session(engine) as session:
        other_company_ids = [
            company.id
            for company in session.exec(
                select(Company).where(Company.company_code.in_(["C1", "C2", "C3"]))
            ).all()
        ]
        assert len(other_company_ids) == 3
        for model in TOP_LEVEL_COMPANY_MODELS:
            rows = session.exec(
                select(model).where(model.company_id.in_(other_company_ids))
            ).all()
            assert rows == [], model.__tablename__


def test_seed_recreates_a_missing_named_plan_without_touching_others() -> None:
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        plans = {
            plan.plan_name: plan
            for plan in session.exec(
                select(SchedulePlan).where(SchedulePlan.company_id == c4.id)
            ).all()
        }
        removed = plans.pop("行政班")
        removed_id = removed.id
        other_ids = {name: plan.id for name, plan in plans.items()}
        session.delete(removed)
        session.commit()

    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        plans = {
            plan.plan_name: plan
            for plan in session.exec(
                select(SchedulePlan).where(SchedulePlan.company_id == c4.id)
            ).all()
        }
        assert set(plans) == {"行政班", "财务技术班", "园林班", "李金辉夜班"}
        assert plans["行政班"].id != removed_id
        assert {name: plan.id for name, plan in plans.items() if name != "行政班"} == (
            other_ids
        )


def test_seed_preserves_an_existing_mapping_template() -> None:
    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        template = session.exec(
            select(ImportMappingTemplate).where(
                ImportMappingTemplate.company_id == c4.id,
                ImportMappingTemplate.data_type == ImportDataType.PUNCH,
            )
        ).one()
        template.mapping = {
            "employee_no": {"column": "用户自定义列", "index": 0},
        }
        session.add(template)
        batch_id = session.exec(
            select(ImportBatch.id).where(
                ImportBatch.company_id == c4.id,
                ImportBatch.data_type == ImportDataType.PUNCH,
                ImportBatch.status == ImportBatchStatus.COMMITTED,
            )
        ).one()
        session.commit()

    with Session(engine) as session:
        import_service.revoke_batch(session, batch_id)

    seed_dev.main()

    with Session(engine) as session:
        c4 = session.exec(select(Company).where(Company.company_code == "C4")).one()
        template = session.exec(
            select(ImportMappingTemplate).where(
                ImportMappingTemplate.company_id == c4.id,
                ImportMappingTemplate.data_type == ImportDataType.PUNCH,
            )
        ).one()
        assert template.mapping == {
            "employee_no": {"column": "用户自定义列", "index": 0},
        }
        assert (
            session.exec(
                select(ImportBatch).where(
                    ImportBatch.company_id == c4.id,
                    ImportBatch.data_type == ImportDataType.PUNCH,
                    ImportBatch.status == ImportBatchStatus.COMMITTED,
                )
            ).one()
            is not None
        )
        assert (
            session.exec(
                select(PunchRecord).where(PunchRecord.company_id == c4.id)
            ).all()
            != []
        )
