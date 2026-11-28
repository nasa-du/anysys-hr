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


# Payroll enums. Values are the API and database vocabulary; Chinese labels
# live in the frontend. The vocabulary is fixed by
# ``docs/specs/payroll-management.md`` section 4.24.


class PayrollMonthStatus(StrEnum):
    DRAFT = "draft"
    CALCULATED = "calculated"
    CONFIRMED = "confirmed"
    PAID = "paid"


class PayrollCalcRunTrigger(StrEnum):
    INITIAL = "initial"
    MANUAL = "manual"
    ATTENDANCE_REFRESH = "attendance_refresh"


class PayrollCalcRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class PayrollImportBatchStatus(StrEnum):
    PREVIEW = "preview"
    COMMITTED = "committed"
    SUPERSEDED = "superseded"
    DISCARDED = "discarded"


class PayrollImportBatchSource(StrEnum):
    UPLOAD = "upload"
    PASTE = "paste"


class PayrollImportRowStatus(StrEnum):
    VALID = "valid"
    ERROR = "error"
    SKIPPED = "skipped"


class PayrollInputSource(StrEnum):
    IMPORT = "import"
    MANUAL = "manual"


class PayrollResultSource(StrEnum):
    PLAN = "plan"
    IMPORT = "import"
    FORMULA = "formula"
    FIXED = "fixed"
    MANUAL = "manual"


class SalaryFieldCategory(StrEnum):
    EARNING = "earning"
    ADDON = "addon"
    DEDUCTION = "deduction"
    TOTAL = "total"
    REFERENCE = "reference"


class SalaryFieldCalcMode(StrEnum):
    PLAN = "plan"
    IMPORT = "import"
    FORMULA = "formula"
    FIXED = "fixed"


class PayrollGlobalParamType(StrEnum):
    NUMBER = "number"
    JSON = "json"


class PayrollExportType(StrEnum):
    PAYSLIP_SINGLE = "payslip_single"
    PAYSLIP_ZIP = "payslip_zip"
    PAYSLIP_MERGED = "payslip_merged"
    PAYROLL_DETAIL_XLSX = "payroll_detail_xlsx"
    DEPARTMENT_SUMMARY_XLSX = "department_summary_xlsx"


class PayrollExportStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXPIRED = "expired"


class PayrollMonthEventType(StrEnum):
    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    PAID = "paid"
    UNLOCKED = "unlocked"


class PayrollConfigEntityType(StrEnum):
    COMPENSATION_COMPOSITION = "compensation_composition"
    CALC_SCHEME = "calc_scheme"
    WORKDAY_PARAM = "workday_param"
    SALARY_FIELD_DEF = "salary_field_def"
    PAYROLL_GLOBAL_PARAM = "payroll_global_param"
    POSITION_PAYROLL_CONFIG = "position_payroll_config"
