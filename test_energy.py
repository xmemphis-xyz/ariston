"""Regression tests for Ariston's two-hour rolling energy sequence."""

from pathlib import Path
from runpy import run_path
import unittest


ENERGY_HELPERS = run_path(
    str(
        Path(__file__).resolve().parent
        / "custom_components"
        / "ariston_nimbus"
        / "ariston_nimbus_api"
        / "energy.py"
    )
)
sum_today = ENERGY_HELPERS["sum_completed_two_hour_periods"]


class DailyEnergyTests(unittest.TestCase):
    """Ensure past days do not contaminate the daily totals."""

    def setUp(self) -> None:
        # Sixteen older intervals, then 29 October's eight completed periods.
        self.readings = [0.73875] * 16 + [
            0.35,
            0.42,
            1.20,
            0.70,
            0.28,
            0.36,
            0.01,
            1.24,
        ]

    def test_only_today_is_summed(self) -> None:
        self.assertEqual(round(sum(self.readings), 3), 16.38)
        self.assertEqual(sum_today(self.readings, 17), 4.56)
        self.assertEqual(sum_today(self.readings, 16), 4.56)

    def test_reset_at_midnight_and_first_complete_period(self) -> None:
        self.assertEqual(sum_today(self.readings, 0), 0.0)
        self.assertEqual(sum_today(self.readings, 1), 0.0)
        early_morning_readings = [0.0] * 23 + [0.75]
        self.assertEqual(sum_today(early_morning_readings, 2), 0.75)
        self.assertEqual(sum_today(early_morning_readings, 3), 0.75)

    def test_last_unfinished_period_excluded(self) -> None:
        self.assertEqual(sum_today([0.5] * 24, 22), 5.5)
        self.assertEqual(sum_today([0.5] * 24, 23), 5.5)

    def test_bad_data_is_unavailable(self) -> None:
        self.assertIsNone(sum_today(None, 17))
        self.assertIsNone(sum_today([], 0))
        self.assertIsNone(sum_today([1.0] * 4, 17))
        self.assertIsNone(sum_today([1.0, float("nan")], 4))
        self.assertIsNone(sum_today([1.0, True], 4))
        self.assertIsNone(sum_today([1.0, -1.0], 4))
        self.assertIsNone(sum_today([1.0] * 24, 24))


if __name__ == "__main__":
    unittest.main()
