from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    PROBATION = "probation"
    RESIGNED = "resigned"


class ContractType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    INTERN = "intern"
    LABOR = "labor"


# Attendance enums. Codes are stored in the database and API; Chinese labels
# live in the frontend (``frontend/src/lib/enums.ts``).


class ScheduleScopeType(StrEnum):
    ALL = "all"
    DEPT = "dept"
    POSITION = "position"
    EMPLOYEE = "employee"


class PlanStatus(StrEnum):
    ENABLED = "enabled"
    ARCHIVED = "archived"


class RosterState(StrEnum):
    """States persisted on roster entries. ``unscheduled`` is API-only."""

    WORK = "work"
    REST = "rest"


class ResultRosterState(StrEnum):
    """Roster state stored on calculated day results."""

    WORK = "work"
    REST = "rest"
    UNSCHEDULED = "unscheduled"


class RosterSource(StrEnum):
    PLAN = "plan"
    MANUAL = "manual"


class HolidayDayType(StrEnum):
    HOLIDAY = "holiday"
    ADJUSTED_WORKDAY = "adjusted_workday"


class AttendanceMonthStatus(StrEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    CONFIRMED = "confirmed"
    LOCKED = "locked"


class CalcRunTrigger(StrEnum):
    INITIAL = "initial"
    MANUAL = "manual"
    REIMPORT = "reimport"
    ROSTER_CHANGE = "roster_change"
    RULE_CHANGE = "rule_change"
    HOLIDAY_CHANGE = "holiday_change"


class CalcRunStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"


class DayType(StrEnum):
    WORKDAY = "workday"
    WEEKEND = "weekend"
    HOLIDAY = "holiday"


class DayStatus(StrEnum):
    NORMAL = "normal"
    LATE = "late"
    EARLY = "early"
    MISSING_PUNCH = "missing_punch"
    ABSENT = "absent"
    OVERTIME = "overtime"
    TRIP_OUT = "trip_out"
    TRIP_BUSINESS = "trip_business"
    PERSONAL_LEAVE = "personal_leave"
    PAID_LEAVE = "paid_leave"
    COMP_LEAVE = "comp_leave"
    REST = "rest"
    UNSCHEDULED_ATTENDANCE = "unscheduled_attendance"


class LeaveKind(StrEnum):
    PAID = "paid"
    UNPAID = "unpaid"
    COMP = "comp"


class TripKind(StrEnum):
    OUT = "out"
    BUSINESS = "business"


class AdjustmentStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    ORPHANED = "orphaned"


class ImportDataType(StrEnum):
    PUNCH = "punch"
    TRIP = "trip"
    OT = "ot"
    LEAVE = "leave"


class ImportBatchStatus(StrEnum):
    PREVIEW = "preview"
    COMMITTED = "committed"
    SUPERSEDED = "superseded"
    DISCARDED = "discarded"
    REVOKED = "revoked"


class ImportSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


class ImportSource(StrEnum):
    UPLOAD = "upload"
    PASTE = "paste"
