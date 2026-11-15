"""Pure attendance calculation kernel (spec section 7).

``run_month`` consumes frozen contract dataclasses built by the database
adapter (C2) and returns day results, month summaries, and a run summary. No
function in this package opens a session or reads the database.
"""

from app.services.attendance.calc.models import (
    CALC_VERSION,
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
    RunSummary,
    ShiftResult,
    ShiftSnapshot,
    Trip,
)
from app.services.attendance.calc.runner import run_month

__all__ = [
    "CALC_VERSION",
    "DayResult",
    "Employee",
    "Holiday",
    "Leave",
    "MonthInputs",
    "MonthOutputs",
    "MonthSummary",
    "OvertimeDay",
    "Punch",
    "RosterEntry",
    "Rules",
    "RunSummary",
    "ShiftResult",
    "ShiftSnapshot",
    "Trip",
    "run_month",
]
