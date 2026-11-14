"""Shift time validation is a pure rule set shared by create and update."""

from datetime import time
from typing import Any

import pytest

from app.core.errors import DomainError
from app.services.attendance.shifts import ShiftTimeValues, validate_shift_times


def _values(**overrides: Any) -> ShiftTimeValues:
    base: dict[str, Any] = {
        "start_time": time(8, 30),
        "end_time": time(17, 30),
        "cross_day": False,
        "break_start": None,
        "break_end": None,
        "rest_minutes": 60,
    }
    base.update(overrides)
    return ShiftTimeValues(**base)


def _assert_invalid(fields: set[str], **overrides: Any) -> DomainError:
    with pytest.raises(DomainError) as exc_info:
        validate_shift_times(_values(**overrides))
    error = exc_info.value
    assert error.code == "invalid_time_range"
    assert set(error.field_errors) == fields
    assert all(message for message in error.field_errors.values())
    return error


def test_accepts_a_normal_shift_with_a_break_inside_it() -> None:
    validate_shift_times(
        _values(
            break_start=time(11, 30),
            break_end=time(13, 30),
            rest_minutes=120,
        )
    )


def test_accepts_a_cross_day_shift_with_a_break_after_midnight() -> None:
    validate_shift_times(
        _values(
            start_time=time(22, 0),
            end_time=time(6, 0),
            cross_day=True,
            break_start=time(2, 0),
            break_end=time(3, 0),
            rest_minutes=60,
        )
    )


def test_accepts_a_break_that_crosses_midnight_on_a_cross_day_shift() -> None:
    validate_shift_times(
        _values(
            start_time=time(22, 0),
            end_time=time(6, 0),
            cross_day=True,
            break_start=time(23, 0),
            break_end=time(2, 0),
            rest_minutes=180,
        )
    )


def test_accepts_a_full_day_cross_day_shift() -> None:
    validate_shift_times(
        _values(
            start_time=time(8, 0),
            end_time=time(8, 0),
            cross_day=True,
            rest_minutes=1440,
        )
    )


def test_rejects_a_non_cross_day_shift_that_ends_before_it_starts() -> None:
    error = _assert_invalid({"end_time"}, end_time=time(8, 0))
    assert "晚于" in error.field_errors["end_time"]


def test_rejects_a_non_cross_day_shift_with_equal_start_and_end() -> None:
    _assert_invalid({"end_time"}, end_time=time(8, 30))


def test_rejects_a_cross_day_shift_that_ends_after_it_starts() -> None:
    error = _assert_invalid({"end_time"}, cross_day=True)
    assert "跨天" in error.field_errors["end_time"]


def test_requires_both_break_times() -> None:
    assert set(_assert_invalid({"break_end"}, break_start=time(12, 0)).field_errors)
    assert set(_assert_invalid({"break_start"}, break_end=time(13, 0)).field_errors)


def test_rejects_a_break_with_its_end_before_its_start() -> None:
    error = _assert_invalid(
        {"break_start", "break_end"},
        break_start=time(13, 30),
        break_end=time(11, 30),
    )
    assert "休息" in error.field_errors["break_start"]


def test_rejects_a_break_outside_the_shift() -> None:
    _assert_invalid(
        {"break_start", "break_end"},
        break_start=time(7, 0),
        break_end=time(8, 0),
    )
    _assert_invalid(
        {"break_start", "break_end"},
        break_start=time(17, 0),
        break_end=time(18, 0),
    )


def test_rejects_a_break_touching_a_shift_boundary() -> None:
    _assert_invalid(
        {"break_start", "break_end"},
        break_start=time(8, 30),
        break_end=time(9, 30),
    )
    _assert_invalid(
        {"break_start", "break_end"},
        break_start=time(16, 30),
        break_end=time(17, 30),
    )


def test_accepts_rest_minutes_equal_to_the_shift_span() -> None:
    validate_shift_times(_values(rest_minutes=540))


def test_rejects_rest_minutes_beyond_the_shift_span() -> None:
    error = _assert_invalid({"rest_minutes"}, rest_minutes=541)
    assert "班次时长" in error.field_errors["rest_minutes"]
