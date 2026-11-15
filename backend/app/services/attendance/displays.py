"""Batched employee/department display resolution for result queries and exports."""

import uuid

from sqlmodel import Session, col, select

from app.models import Department, Employee, User


def user_display_name(user: User | None) -> str | None:
    """Operators display their full name, falling back to their email."""
    if user is None:
        return None
    return user.full_name or user.email


def user_display_map(
    session: Session, user_ids: set[uuid.UUID]
) -> dict[uuid.UUID, str | None]:
    """Resolve operator display names in one query."""
    if not user_ids:
        return {}
    users = session.exec(select(User).where(col(User.id).in_(user_ids))).all()
    return {user.id: user_display_name(user) for user in users}


def employee_display_map(
    session: Session, employee_ids: set[uuid.UUID]
) -> dict[uuid.UUID, tuple[Employee, Department]]:
    """Resolve employee and department rows in two queries, avoiding N+1 reads."""
    if not employee_ids:
        return {}
    employees = {
        employee.id: employee
        for employee in session.exec(
            select(Employee).where(col(Employee.id).in_(employee_ids))
        ).all()
    }
    departments = {
        department.id: department
        for department in session.exec(
            select(Department).where(
                col(Department.id).in_(
                    {employee.dept_id for employee in employees.values()}
                )
            )
        ).all()
    }
    return {
        employee.id: (employee, departments[employee.dept_id])
        for employee in employees.values()
        if employee.dept_id in departments
    }
