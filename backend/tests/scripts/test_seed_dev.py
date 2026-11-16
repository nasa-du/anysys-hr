"""Development seed script: guard rails and generated-dataset contracts.

The seed is deterministic: ``SMALL_SCALE`` runs the same code paths as the
development ``FULL_SCALE`` with a few dozen employees, so these tests can
assert exact contracts without paying for a mid-sized seed on every test.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from sqlmodel import Session, col, select

from app import seed_dev
from app.core.db import engine
from app.core.security import verify_password
from app.enums import (
    AttendanceMonthStatus,
    CalcRunStatus,
    ContractType,
    EmployeeStatus,
    HolidayDayType,
    ImportBatchStatus,
    ImportDataType,
    ImportSource,
    RosterSource,
    RosterState,
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
    User,
)

ATTENDANCE_MONTHS = [date(2026, 8, 1), date(2026, 9, 1), date(2026, 10, 1)]


def _seed() -> None:
    with Session(engine) as session:
        seed_dev.seed(session, scale=seed_dev.SMALL_SCALE)


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
        for department in session.exec(select(Department)).all():
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
        for position in session.exec(select(Position)).all():
            positions[company_codes[position.company_id]].append(position)
        return positions


def _cost_centers_by_company() -> dict[str, list[CostCenter]]:
    with Session(engine) as session:
        company_codes = {
            company.id: company.company_code
            for company in session.exec(select(Company)).all()
        }
        cost_centers: dict[str, list[CostCenter]] = {
            code: [] for code in company_codes.values()
        }
        for cost_center in session.exec(select(CostCenter)).all():
            cost_centers[company_codes[cost_center.company_id]].append(cost_center)
        return cost_centers


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
        for employee in session.exec(select(Employee)).all():
            company_id = departments[employee.dept_id].company_id
            employees[company_codes[company_id]].append(employee)
        return employees


def _company_by_code(code: str) -> Company:
    with Session(engine) as session:
        return session.exec(select(Company).where(Company.company_code == code)).one()


def _attendance_company_rows() -> tuple[
    list[Shift], list[AttendanceRule], list[Holiday]
]:
    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C3")
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


# ---------------------------------------------------------------------------
# Guard rails
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("environment", ["production", None])
def test_seed_refuses_outside_development(
    monkeypatch: pytest.MonkeyPatch, environment: str | None
) -> None:
    monkeypatch.setattr(seed_dev.settings, "FASTAPI_ENV", environment)

    with pytest.raises(SystemExit, match="development"):
        seed_dev.main()

    assert _companies() == []


def test_seed_inserts_three_companies_once() -> None:
    _seed()
    _seed()

    companies = _companies()
    assert [company.company_code for company in companies] == ["C1", "C2", "C3"]
    assert [company.company_name for company in companies] == [
        "华信建设",
        "云启科技",
        "明德考勤演示",
    ]
    assert all(company.is_active for company in companies)
    assert all("荣新" not in company.company_name for company in companies)


def test_full_scale_is_mid_sized_and_deterministic() -> None:
    counts = list(seed_dev.FULL_SCALE.employees.values())
    assert len(counts) == 3
    assert all(200 <= count <= 1000 for count in counts)
    assert len(set(counts)) > 1
    assert all(
        seed_dev.SMALL_SCALE.employees[code] < seed_dev.FULL_SCALE.employees[code]
        for code in seed_dev.FULL_SCALE.employees
    )

    first = seed_dev.generate_employees(seed_dev.SMALL_SCALE)
    second = seed_dev.generate_employees(seed_dev.SMALL_SCALE)
    assert first == second


def test_seed_does_not_overwrite_existing_edits() -> None:
    _seed()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        company.company_name = "用户修改后的名称"
        company.note = "用户备注"
        session.add(company)
        session.commit()

    _seed()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C1")
        ).one()
        assert company.company_name == "用户修改后的名称"
        assert company.note == "用户备注"


# ---------------------------------------------------------------------------
# Organization tree
# ---------------------------------------------------------------------------


def test_seed_inserts_the_department_tree_once() -> None:
    _seed()
    _seed()

    departments = _departments_by_company()

    assert {department.dept_code for department in departments["C1"]} == {
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "D6",
        "D7",
        "D8",
        "D9",
        "D10",
        "D11",
        "D12",
        "D13",
    }
    assert {department.dept_code for department in departments["C2"]} == {
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
        "K9",
    }
    assert {department.dept_code for department in departments["C3"]} == {
        "D1",
        "D2",
        "D3",
        "D4",
        "D5",
        "D6",
        "D7",
        "D8",
        "D9",
        "D10",
        "D11",
        "D12",
        "D13",
    }

    full_company = {
        department.dept_code: department for department in departments["C1"]
    }
    assert full_company["D1"].parent_id is None
    assert full_company["D2"].parent_id == full_company["D1"].id
    assert full_company["D3"].parent_id == full_company["D2"].id
    assert full_company["D4"].parent_id == full_company["D2"].id
    assert full_company["D8"].parent_id == full_company["D2"].id
    assert full_company["D9"].parent_id == full_company["D2"].id
    assert full_company["D10"].parent_id == full_company["D1"].id


def test_seed_includes_one_inactive_department_without_active_employees() -> None:
    _seed()

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
        any_employees = session.exec(
            select(Employee).where(Employee.dept_id.in_(inactive_ids))
        ).all()

    assert [department.dept_code for department in inactive_departments] == ["D7"]
    assert active_employees == []
    assert any_employees == []


def test_seed_inserts_positions_once() -> None:
    _seed()
    _seed()

    positions = _positions_by_company()

    assert {position.position_code for position in positions["C1"]} == {
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "P10",
        "P11",
        "P12",
    }
    assert {position.position_code for position in positions["C2"]} == {
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
        "K9",
        "K10",
    }
    assert {position.position_code for position in positions["C3"]} == {
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "P7",
        "P8",
        "P9",
        "P10",
        "P11",
        "P12",
    }

    full_company = {position.position_code: position for position in positions["C1"]}
    assert full_company["P1"].dept_id is not None
    assert full_company["P2"].dept_id is not None
    assert full_company["P6"].dept_id is None
    assert all(position.is_active for position in positions["C1"])


def test_seed_position_default_departments_use_the_same_company() -> None:
    _seed()

    with Session(engine) as session:
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        for position in session.exec(select(Position)).all():
            if position.dept_id is None:
                continue
            assert departments[position.dept_id].company_id == position.company_id


def test_seed_does_not_overwrite_existing_position_edits() -> None:
    _seed()

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

    _seed()

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
    _seed()

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

    _seed()

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


def test_seed_inserts_the_cost_center_tree_once() -> None:
    _seed()
    _seed()

    cost_centers = _cost_centers_by_company()

    assert {cost_center.cost_org_code for cost_center in cost_centers["C1"]} == {
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
        "K9",
        "K10",
        "K11",
        "K12",
    }
    assert {cost_center.cost_org_code for cost_center in cost_centers["C2"]} == {
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
    }
    assert cost_centers["C3"] == []

    full_company = {
        cost_center.cost_org_code: cost_center for cost_center in cost_centers["C1"]
    }
    assert full_company["K1"].parent_id is None
    assert full_company["K2"].parent_id == full_company["K1"].id
    assert full_company["K3"].parent_id == full_company["K2"].id
    assert full_company["K4"].parent_id == full_company["K2"].id
    assert full_company["K6"].is_active is False
    assert all(cost_center.is_active for cost_center in cost_centers["C2"])


def test_seed_includes_one_inactive_cost_center_without_active_employees() -> None:
    _seed()

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

    assert [cost_center.cost_org_code for cost_center in inactive_cost_centers] == [
        "K6"
    ]
    assert active_employees == []


def test_seed_cost_center_parents_and_budgets_use_the_same_company() -> None:
    _seed()

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
    _seed()

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

    _seed()

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


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------


def test_seed_inserts_generated_employees_once() -> None:
    _seed()
    _seed()

    employees = _employees_by_company()
    for company_code, expected in seed_dev.SMALL_SCALE.employees.items():
        assert len(employees[company_code]) == expected
        numbers = [employee.employee_no for employee in employees[company_code]]
        assert len(numbers) == len(set(numbers))
        names = [employee.name for employee in employees[company_code]]
        assert len(names) == len(set(names)), "OA imports match employees by name"
        assert all(employee.name for employee in employees[company_code])

    all_numbers = [
        employee.employee_no for rows in employees.values() for employee in rows
    ]
    assert len(all_numbers) == len(set(all_numbers))


def test_seed_employee_managers_are_same_company_and_dates_are_valid() -> None:
    _seed()

    generated = {
        data["employee_no"]: data
        for data in seed_dev.generate_employees(seed_dev.SMALL_SCALE)
    }

    with Session(engine) as session:
        departments = {
            department.id: department
            for department in session.exec(select(Department)).all()
        }
        employees = {
            employee.employee_no: employee
            for employee in session.exec(select(Employee)).all()
        }

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
                assert generated[employee.employee_no]["manager_no"] is None
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
            assert generated[employee.employee_no]["manager_no"] == manager.employee_no


def test_seed_employee_statuses_contracts_and_unassigned_are_varied() -> None:
    _seed()

    employees = _employees_by_company()
    full_company = employees["C1"]

    assert {employee.status for employee in full_company} == set(EmployeeStatus)
    assert {employee.contract_type for employee in full_company} == set(ContractType)
    assert any(employee.cost_org_id is None for employee in full_company)
    assert sum(employee.manager_id is not None for employee in full_company) >= 10
    assert any(
        employee.status is EmployeeStatus.RESIGNED for employee in employees["C2"]
    )
    assert any(employee.cost_org_id is None for employee in employees["C2"])
    assert all(employee.cost_org_id is None for employee in employees["C3"])


def test_seed_does_not_overwrite_existing_employee_edits() -> None:
    _seed()

    with Session(engine) as session:
        employee = session.exec(
            select(Employee).where(Employee.employee_no == "E1001")
        ).one()
        employee.name = "用户修改后的员工"
        employee.note = "用户备注"
        session.add(employee)
        session.commit()

    _seed()

    with Session(engine) as session:
        employee = session.exec(
            select(Employee).where(Employee.employee_no == "E1001")
        ).one()
        assert employee.name == "用户修改后的员工"
        assert employee.note == "用户备注"


def test_seed_creates_about_ten_users() -> None:
    _seed()
    _seed()

    with Session(engine) as session:
        users = list(session.exec(select(User)).all())
        assert len(users) == 10
        assert sum(user.is_superuser for user in users) == 1
        generated = [user for user in users if not user.is_superuser]
        assert len(generated) == len(seed_dev.USERS)
        assert all(user.is_active for user in generated)
        assert {user.email for user in generated} == {
            email for email, _ in seed_dev.USERS
        }
        assert all(
            verify_password(seed_dev.USER_PASSWORD, user.hashed_password)
            for user in generated
        )


# ---------------------------------------------------------------------------
# Attendance reference data
# ---------------------------------------------------------------------------


def test_seed_inserts_attendance_reference_data_once() -> None:
    _seed()
    _seed()

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
    assert {shift.color for shift in shifts} == {
        "#2563EB",
        "#7C3AED",
        "#16A34A",
        "#F59E0B",
        "#0EA5E9",
        "#1E293B",
        "#DC2626",
    }

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
        date(2026, 10, 10),
    ]
    assert holidays[0].name == "中秋节"
    assert holidays[0].day_type == HolidayDayType.HOLIDAY
    assert holidays[1].name == "调休上班"
    assert holidays[1].day_type == HolidayDayType.ADJUSTED_WORKDAY
    assert {holiday.name for holiday in holidays[2:9]} == {"国庆节"}
    assert holidays[-1].name == "调休上班"
    assert holidays[-1].day_type == HolidayDayType.ADJUSTED_WORKDAY


def test_attendance_reference_data_never_touches_other_companies() -> None:
    _seed()

    with Session(engine) as session:
        other_company_ids = [
            company.id
            for company in session.exec(
                select(Company).where(Company.company_code.in_(["C1", "C2"]))
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
    _seed()

    with Session(engine) as session:
        company = session.exec(
            select(Company).where(Company.company_code == "C3")
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

    _seed()

    shifts, rules, holidays = _attendance_company_rows()
    stored_shift = next(item for item in shifts if item.shift_code == "ADM")
    assert stored_shift.shift_name == "用户修改后的班次"
    assert rules[0].punch_window_min == 45
    stored_holiday = next(item for item in holidays if item.date == date(2026, 9, 25))
    assert stored_holiday.name == "用户修改后的节假日"


def test_seed_attendance_employees_cover_employment_windows() -> None:
    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        employees = {
            employee.employee_no: employee
            for employee in session.exec(select(Employee)).all()
        }
        c3_employees = [
            employee
            for employee in employees.values()
            if session.get(Department, employee.dept_id).company_id == c3.id
        ]
        resigned_sept = next(
            employee
            for employee in c3_employees
            if employee.resign_date == date(2026, 9, 10)
        )
        resigned_pre_august = next(
            employee
            for employee in c3_employees
            if employee.resign_date is not None
            and employee.resign_date < date(2026, 8, 1)
        )
        late_sept = next(
            employee
            for employee in c3_employees
            if employee.hire_date == date(2026, 9, 15)
        )
        late_oct = next(
            employee
            for employee in c3_employees
            if employee.hire_date == date(2026, 10, 8)
        )

        def roster_dates(employee: Employee) -> list[date]:
            return sorted(
                entry.work_date
                for entry in session.exec(
                    select(RosterEntry).where(RosterEntry.employee_id == employee.id)
                ).all()
            )

        assert roster_dates(resigned_pre_august) == []
        september = roster_dates(resigned_sept)
        assert september
        assert september[-1] == date(2026, 9, 10)
        assert min(roster_dates(late_sept)) == date(2026, 9, 15)
        october = roster_dates(late_oct)
        assert october
        assert min(october) == date(2026, 10, 8)


# ---------------------------------------------------------------------------
# Plans, roster, imports, calculations
# ---------------------------------------------------------------------------


def _c3_plans_by_month() -> dict[date, dict[str, SchedulePlan]]:
    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        plans: dict[date, dict[str, SchedulePlan]] = {}
        for plan in session.exec(
            select(SchedulePlan).where(SchedulePlan.company_id == c3.id)
        ).all():
            plans.setdefault(plan.month, {})[plan.plan_name] = plan
        return plans


def test_seed_inserts_four_plans_per_month_and_expands_them() -> None:
    _seed()
    _seed()

    plans_by_month = _c3_plans_by_month()
    assert set(plans_by_month) == set(ATTENDANCE_MONTHS)
    for plans in plans_by_month.values():
        assert len(plans) == 4
        assert {plan.scope_type for plan in plans.values()} == {
            ScheduleScopeType.ALL,
            ScheduleScopeType.DEPT,
            ScheduleScopeType.POSITION,
            ScheduleScopeType.EMPLOYEE,
        }
        assert all(plan.status.value == "enabled" for plan in plans.values())
        garden = plans["园林班"]
        override = None
        with Session(engine) as session:
            override = session.get(PlanRuleOverride, garden.id)
        assert override is not None
        assert override.ot_threshold_min == 15

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        departments = {
            department.dept_code: department
            for department in session.exec(
                select(Department).where(Department.company_id == c3.id)
            ).all()
        }
        positions = {
            position.position_code: position
            for position in session.exec(
                select(Position).where(Position.company_id == c3.id)
            ).all()
        }
        employees = {
            employee.employee_no: employee
            for employee in session.exec(
                select(Employee)
                .join(Department, col(Employee.dept_id) == col(Department.id))
                .where(Department.company_id == c3.id)
            ).all()
        }
        roster = list(
            session.exec(
                select(RosterEntry).where(RosterEntry.company_id == c3.id)
            ).all()
        )
        assert roster
        by_employee_date = {
            (entry.employee_id, entry.work_date): entry for entry in roster
        }

        september_plans = plans_by_month[date(2026, 9, 1)]
        target_plan = next(
            plan
            for plan in september_plans.values()
            if plan.scope_type is ScheduleScopeType.EMPLOYEE
        )
        target_no = target_plan.plan_name.removesuffix("夜班")
        target = employees[target_no]
        night = by_employee_date[(target.id, date(2026, 9, 30))]
        assert night.plan_id == target_plan.id
        night_shift_codes = [
            shift.shift_code
            for shift in session.exec(
                select(Shift).where(
                    Shift.id.in_(
                        select(PlanDay.shift_id).where(
                            PlanDay.plan_id == target_plan.id,
                            PlanDay.day_of_month == 30,
                        )
                    )
                )
            ).all()
        ]
        assert night_shift_codes == ["NIGHT"]
        # The employee plan's adjusted-workday row wins over the all plan's rest.
        assert by_employee_date[(target.id, date(2026, 9, 27))].state.value == "work"
        assert (
            by_employee_date[(target.id, date(2026, 9, 27))].plan_id == target_plan.id
        )

        garden_employee = next(
            employee
            for employee in employees.values()
            if employee.position_id == positions["P2"].id
            and employee.status is EmployeeStatus.ACTIVE
            and employee.hire_date <= date(2026, 9, 1)
            and employee.resign_date is None
        )
        assert (
            by_employee_date[(garden_employee.id, date(2026, 9, 1))].plan_id
            == september_plans["园林班"].id
        )
        finance_employee = next(
            employee
            for employee in employees.values()
            if employee.dept_id == departments["D2"].id
            and employee.status is EmployeeStatus.ACTIVE
            and employee.hire_date <= date(2026, 9, 1)
            and employee.resign_date is None
        )
        assert (
            by_employee_date[(finance_employee.id, date(2026, 9, 1))].plan_id
            == september_plans["财务技术班"].id
        )
        all_employee = next(
            employee
            for employee in employees.values()
            if employee.status is EmployeeStatus.ACTIVE
            and employee.dept_id != departments["D2"].id
            and employee.position_id != positions["P2"].id
            and employee.id != target.id
            and employee.hire_date <= date(2026, 9, 1)
            and employee.resign_date is None
        )
        assert (
            by_employee_date[(all_employee.id, date(2026, 9, 1))].plan_id
            == september_plans["行政班"].id
        )

        manual_entries = [
            entry for entry in roster if entry.source == RosterSource.MANUAL
        ]
        assert len(manual_entries) == 2
        rest_entry = next(
            entry for entry in manual_entries if entry.state is RosterState.REST
        )
        assert rest_entry.work_date == date(2026, 9, 10)
        assert rest_entry.note == "个人调休"
        work_entry = next(
            entry for entry in manual_entries if entry.state is RosterState.WORK
        )
        assert work_entry.work_date == date(2026, 9, 11)
        assert work_entry.note == "临时双班"
        assert [
            shift.shift_code
            for shift in session.exec(
                select(RosterEntryShift)
                .where(RosterEntryShift.roster_entry_id == work_entry.id)
                .order_by(RosterEntryShift.seq)
            ).all()
        ] == ["EARLY", "MID"]


def _c3_batches_by_scope() -> dict[tuple[date, ImportDataType], ImportBatch]:
    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        return {
            (batch.month, batch.data_type): batch
            for batch in session.exec(
                select(ImportBatch).where(ImportBatch.company_id == c3.id)
            ).all()
        }


def test_seed_commits_twelve_generated_batches_once() -> None:
    _seed()

    batches = _c3_batches_by_scope()
    assert len(batches) == 12
    expected_oa_valid = {
        ImportDataType.TRIP: 10,
        ImportDataType.OT: 15,
        ImportDataType.LEAVE: 12,
    }
    for month in ATTENDANCE_MONTHS:
        for data_type in (
            ImportDataType.PUNCH,
            ImportDataType.TRIP,
            ImportDataType.OT,
            ImportDataType.LEAVE,
        ):
            batch = batches[(month, data_type)]
            assert batch.status == ImportBatchStatus.COMMITTED
            assert batch.source == ImportSource.UPLOAD
            assert batch.source_rows > 0
            assert batch.valid_records > 0
            assert batch.error_records == 0
            assert batch.file_size is not None and batch.file_size > 0
            assert batch.file_sha256 is not None and len(batch.file_sha256) == 64
            assert batch.column_mapping
            assert batch.header_columns
            assert batch.operator_id is not None
            assert batch.committed_at is not None
            assert batch.expires_at is None
            if data_type in expected_oa_valid:
                assert batch.valid_records == expected_oa_valid[data_type]

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        assert (
            session.exec(
                select(ImportBatch).where(
                    ImportBatch.company_id == c3.id,
                    ImportBatch.status != ImportBatchStatus.COMMITTED,
                )
            ).all()
            == []
        )
        templates = session.exec(
            select(ImportMappingTemplate).where(
                ImportMappingTemplate.company_id == c3.id
            )
        ).all()
        assert len(templates) == 4
        # Every committed punch row keeps its raw source row.
        assert all(
            row.raw_row
            for row in session.exec(
                select(PunchRecord).where(PunchRecord.company_id == c3.id)
            ).all()
        )


def _seed_batch_fingerprint() -> tuple:
    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        return (
            len(
                session.exec(
                    select(ImportBatch).where(ImportBatch.company_id == c3.id)
                ).all()
            ),
            len(session.exec(select(PunchRecord)).all()),
            len(session.exec(select(OaTrip)).all()),
            len(session.exec(select(OaOvertime)).all()),
            len(session.exec(select(OaLeave)).all()),
            len(
                session.exec(
                    select(ImportBatch).where(ImportBatch.company_id != c3.id)
                ).all()
            ),
            len(
                session.exec(
                    select(ImportMappingTemplate).where(
                        ImportMappingTemplate.company_id == c3.id
                    )
                ).all()
            ),
        )


def test_seed_runs_twice_with_stable_import_counts() -> None:
    _seed()
    first = _seed_batch_fingerprint()
    _seed()
    second = _seed_batch_fingerprint()

    assert first == second
    batch_count, punch, trips, overtime, leaves, other_batches, templates = first
    assert batch_count == 12
    assert punch > 0
    assert trips == 30
    assert overtime == 45
    assert leaves == 36
    assert other_batches == 0
    assert templates == 4


def test_seed_does_not_overwrite_committed_import_batches() -> None:
    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        batch = session.exec(
            select(ImportBatch).where(
                ImportBatch.company_id == c3.id,
                ImportBatch.data_type == ImportDataType.PUNCH,
                ImportBatch.month == date(2026, 9, 1),
            )
        ).one()
        batch.file_name = "用户替换后的文件.csv"
        batch.valid_records = 1
        session.add(batch)
        session.commit()

    _seed()

    batch = _c3_batches_by_scope()[(date(2026, 9, 1), ImportDataType.PUNCH)]
    assert batch.file_name == "用户替换后的文件.csv"
    assert batch.valid_records == 1


def test_seed_calculates_three_months_without_confirming() -> None:
    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        months = list(
            session.exec(
                select(AttendanceMonth)
                .where(AttendanceMonth.company_id == c3.id)
                .order_by(AttendanceMonth.month)
            ).all()
        )
        assert [month.month for month in months] == ATTENDANCE_MONTHS
        for month in months:
            assert month.status is AttendanceMonthStatus.CALCULATED
            assert month.is_stale is False
            runs = session.exec(
                select(CalcRun).where(CalcRun.attendance_month_id == month.id)
            ).all()
            assert len(runs) == 1
            assert runs[0].status is CalcRunStatus.SUCCESS
            assert runs[0].summary
            assert (
                session.exec(
                    select(AttendanceMonthSnapshot).where(
                        AttendanceMonthSnapshot.attendance_month_id == month.id
                    )
                ).all()
                == []
            )
            day_results = session.exec(
                select(AttendanceDayResult).where(
                    AttendanceDayResult.attendance_month_id == month.id
                )
            ).all()
            assert day_results
            summaries = session.exec(
                select(AttendanceMonthSummary).where(
                    AttendanceMonthSummary.attendance_month_id == month.id
                )
            ).all()
            assert summaries
            assert (
                session.exec(
                    select(AttendanceResultAdjustment).where(
                        AttendanceResultAdjustment.company_id == c3.id
                    )
                ).all()
                == []
            )
        assert (
            session.exec(
                select(CalcRun).where(CalcRun.status != CalcRunStatus.SUCCESS)
            ).all()
            == []
        )
        assert (
            session.exec(
                select(AttendanceDayShiftResult).where(
                    AttendanceDayShiftResult.company_id == c3.id
                )
            ).all()
            != []
        )


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
    _seed()
    _seed()

    with Session(engine) as session:
        other_company_ids = [
            company.id
            for company in session.exec(
                select(Company).where(Company.company_code.in_(["C1", "C2"]))
            ).all()
        ]
        assert len(other_company_ids) == 2
        for model in TOP_LEVEL_COMPANY_MODELS:
            rows = session.exec(
                select(model).where(model.company_id.in_(other_company_ids))
            ).all()
            assert rows == [], model.__tablename__


def test_seed_recreates_a_missing_named_plan_without_touching_others() -> None:
    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        plans = {
            plan.plan_name: plan
            for plan in session.exec(
                select(SchedulePlan).where(
                    SchedulePlan.company_id == c3.id,
                    SchedulePlan.month == date(2026, 9, 1),
                )
            ).all()
        }
        removed = plans.pop("行政班")
        removed_id = removed.id
        expected_names = set(plans) | {"行政班"}
        other_ids = {name: plan.id for name, plan in plans.items()}
        session.delete(removed)
        session.commit()

    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        plans = {
            plan.plan_name: plan
            for plan in session.exec(
                select(SchedulePlan).where(
                    SchedulePlan.company_id == c3.id,
                    SchedulePlan.month == date(2026, 9, 1),
                )
            ).all()
        }
        assert set(plans) == expected_names
        assert plans["行政班"].id != removed_id
        assert {
            name: plan.id for name, plan in plans.items() if name != "行政班"
        } == other_ids


def test_seed_preserves_an_existing_mapping_template() -> None:
    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        template = session.exec(
            select(ImportMappingTemplate).where(
                ImportMappingTemplate.company_id == c3.id,
                ImportMappingTemplate.data_type == ImportDataType.PUNCH,
            )
        ).one()
        template.mapping = {
            "employee_no": {"column": "用户自定义列", "index": 0},
        }
        session.add(template)
        batch_id = session.exec(
            select(ImportBatch.id).where(
                ImportBatch.company_id == c3.id,
                ImportBatch.data_type == ImportDataType.PUNCH,
                ImportBatch.month == date(2026, 9, 1),
                ImportBatch.status == ImportBatchStatus.COMMITTED,
            )
        ).one()
        session.commit()

    from app.services.attendance import imports as import_service

    with Session(engine) as session:
        import_service.revoke_batch(session, batch_id)

    _seed()

    with Session(engine) as session:
        c3 = session.exec(select(Company).where(Company.company_code == "C3")).one()
        template = session.exec(
            select(ImportMappingTemplate).where(
                ImportMappingTemplate.company_id == c3.id,
                ImportMappingTemplate.data_type == ImportDataType.PUNCH,
            )
        ).one()
        assert template.mapping == {
            "employee_no": {"column": "用户自定义列", "index": 0},
        }
        committed = session.exec(
            select(ImportBatch).where(
                ImportBatch.company_id == c3.id,
                ImportBatch.data_type == ImportDataType.PUNCH,
                ImportBatch.month == date(2026, 9, 1),
                ImportBatch.status == ImportBatchStatus.COMMITTED,
            )
        ).one()
        assert committed is not None
        assert (
            session.exec(
                select(PunchRecord).where(PunchRecord.company_id == c3.id)
            ).all()
            != []
        )
