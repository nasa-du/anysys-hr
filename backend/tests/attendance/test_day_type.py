"""Day-type precedence is deterministic for holidays and weekends."""

from datetime import date

import pytest

from app.enums import DayType, HolidayDayType
from app.services.attendance.holidays import resolve_day_type


@pytest.mark.parametrize(
    ("day", "holiday_day_type", "expected"),
    [
        (date(2026, 9, 25), None, DayType.WORKDAY),
        (date(2026, 9, 26), None, DayType.WEEKEND),
        (date(2026, 9, 27), None, DayType.WEEKEND),
        (date(2026, 9, 27), HolidayDayType.ADJUSTED_WORKDAY, DayType.WORKDAY),
        (date(2026, 9, 26), HolidayDayType.HOLIDAY, DayType.HOLIDAY),
        (date(2026, 9, 25), HolidayDayType.HOLIDAY, DayType.HOLIDAY),
        (date(2026, 9, 25), HolidayDayType.ADJUSTED_WORKDAY, DayType.WORKDAY),
    ],
)
def test_day_type_precedence(
    day: date,
    holiday_day_type: HolidayDayType | None,
    expected: DayType,
) -> None:
    assert resolve_day_type(day, holiday_day_type) is expected
