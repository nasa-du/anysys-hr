"""Calendar, overlap, and numeric-convention helpers for the calc kernel."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")

_ONE_DAY = timedelta(days=1)


def month_bounds(month: date) -> tuple[date, date]:
    """Return the first and last day of the month containing ``month``."""
    start = month.replace(day=1)
    if start.month == 12:
        next_start = date(start.year + 1, 1, 1)
    else:
        next_start = date(start.year, start.month + 1, 1)
    return start, next_start - _ONE_DAY


def dates_in(start: date, end: date) -> list[date]:
    if end < start:
        return []
    return [start + timedelta(days=offset) for offset in range((end - start).days + 1)]


def at(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=SHANGHAI)


def ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=SHANGHAI)
    return value


def minutes_between(start: datetime, end: datetime) -> int:
    return int((end - start).total_seconds() // 60)


def overlap_minutes(
    first_start: datetime,
    first_end: datetime,
    second_start: datetime,
    second_end: datetime,
) -> int:
    start = max(first_start, second_start)
    end = min(first_end, second_end)
    return max(0, minutes_between(start, end))


def to_fraction(value: Decimal | int | Fraction) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(value)
    return Fraction(value)


def quantize(value: Fraction | Decimal | int, places: int) -> Decimal:
    """Round half-up at the contract boundary (spec section 7.14)."""
    if isinstance(value, Fraction):
        decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
    elif isinstance(value, int):
        decimal_value = Decimal(value)
    else:
        decimal_value = value
    return decimal_value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)


def day_value(value: Fraction | Decimal | int) -> Decimal:
    """Days and fractions use one decimal place."""
    return quantize(value, 1)


def hours_value(minutes: int) -> Decimal:
    """Overtime hours use two decimal places."""
    return quantize(Decimal(minutes) / Decimal(60), 2)


def amount_value(value: Fraction | Decimal | int) -> Decimal:
    """Money amounts use two decimal places."""
    return quantize(value, 2)


def minutes_value(value: Fraction) -> int:
    """Worked minutes derived from an overlap fraction round half-up."""
    return int(quantize(value, 0))
