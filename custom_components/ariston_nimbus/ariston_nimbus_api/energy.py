"""Helpers for Ariston's rolling energy-consumption reports."""

from __future__ import annotations

import math


def sum_completed_two_hour_periods(
    readings: object, local_hour: int
) -> float | None:
    """Sum only the completed two-hour periods since local midnight.

    The API's ``p=1`` sequence has 24 rolling two-hour readings, ordered
    oldest to newest. Summing all of them also includes prior-day energy.
    The newest reading covers the last completed local two-hour period.
    """
    if not isinstance(readings, list) or not readings:
        return None
    if (
        not isinstance(local_hour, int)
        or isinstance(local_hour, bool)
        or not 0 <= local_hour <= 23
    ):
        return None

    periods_today = local_hour // 2
    if periods_today > len(readings):
        return None
    if periods_today == 0:
        return 0.0

    today = readings[-periods_today:]
    if any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
        for value in today
    ):
        return None

    return round(sum(today), 3)
