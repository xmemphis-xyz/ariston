"""Tests for the GALEVO operating-parameter helpers and the menu scan API."""

import asyncio
from pathlib import Path
import sys
import types
import unittest

# The API package imports aiohttp/requests at module level; the helpers under
# test never use them, so lightweight stand-ins are enough here.
for _name in ("aiohttp", "requests"):
    sys.modules.setdefault(_name, types.ModuleType(_name))

sys.path.insert(
    0, str(Path(__file__).resolve().parent / "custom_components" / "ariston_nimbus")
)

from ariston_nimbus_api.ariston_api import AristonAPI  # noqa: E402
from ariston_nimbus_api.galevo_device import AristonGalevoDevice  # noqa: E402
from runpy import run_path  # noqa: E402

MENU_SCAN = run_path(
    str(
        Path(__file__).resolve().parent
        / "custom_components"
        / "ariston_nimbus"
        / "menu_scan.py"
    )
)
scan_menu_items = MENU_SCAN["async_scan_menu_items"]


def _device(items, menu_items=None):
    device = AristonGalevoDevice(None, {"gw": "GW123"})
    device.data = {"items": items}
    device.menu_items = menu_items or []
    return device


class OperatingParameterTests(unittest.TestCase):
    """Helpers exposed as new Home Assistant entities."""

    def test_flow_return_delta(self):
        device = _device(
            [{"id": "ChFlowTemp", "zone": 0, "value": 38.5}],
            [{"id": 124, "value": 33.2}],
        )
        self.assertEqual(device.ch_flow_return_delta_value, 5.3)

    def test_flow_return_delta_missing_return(self):
        device = _device([{"id": "ChFlowTemp", "zone": 0, "value": 38.5}])
        self.assertIsNone(device.ch_flow_return_delta_value)

    def test_zone_heat_request(self):
        device = _device([{"id": "ZoneHeatRequest", "zone": 1, "value": True}])
        self.assertTrue(device.has_zone_heat_request(1))
        self.assertFalse(device.has_zone_heat_request(2))

    def test_heat_generator_presence(self):
        self.assertTrue(
            _device([{"id": "IsFlameOn", "zone": 0, "value": False}]).has_flame_on_value
        )
        self.assertFalse(_device([]).has_flame_on_value)

    def test_antilegionella(self):
        device = _device(
            [
                {"id": "AntilegionellaOnOff", "zone": 0, "value": 1},
                {"id": "AntilegionellaTemp", "zone": 0, "value": 60, "unit": "°C"},
                {
                    "id": "AntilegionellaFreq",
                    "zone": 0,
                    "value": 2,
                    "options": [1, 2],
                    "optTexts": ["Daily", "Weekly"],
                },
            ]
        )
        self.assertTrue(device.antilegionella_on_off_value)
        self.assertEqual(device.antilegionella_temp_value, 60)
        self.assertEqual(device.antilegionella_temp_unit, "°C")
        self.assertEqual(device.antilegionella_freq_value, "Weekly")

    def test_antilegionella_absent(self):
        device = _device([])
        self.assertIsNone(device.antilegionella_on_off_value)
        self.assertIsNone(device.antilegionella_freq_value)


class MenuScanTests(unittest.TestCase):
    """The diagnostics menu scan requests arbitrary item ids."""

    def test_menu_items_by_ids(self):
        api = AristonAPI.__new__(AristonAPI)
        api._AristonAPI__api_url = "https://example/api/v2/"
        requested = []

        async def fake_get(path):
            requested.append(path)
            return [{"id": 3, "value": 1}]

        api._async_get_no_retry = fake_get
        items = asyncio.run(api.async_get_menu_items_by_ids("GW1", [1, 2, 3]))
        self.assertEqual(items, [{"id": 3, "value": 1}])
        self.assertEqual(requested, ["https://example/api/v2/menuItems/GW1?menuItems=1,2,3"])

    def test_menu_items_by_ids_non_list(self):
        api = AristonAPI.__new__(AristonAPI)
        api._AristonAPI__api_url = "https://example/api/v2/"

        async def fake_get(path):
            return None

        api._async_get_no_retry = fake_get
        self.assertEqual(asyncio.run(api.async_get_menu_items_by_ids("GW1", [1])), [])



class FakeMenuApi:
    """Cloud that rejects a whole request when it contains an unknown id."""

    def __init__(self, known, max_ids=None):
        self.known = known
        self.max_ids = max_ids
        self.calls = 0

    async def async_get_menu_items_by_ids(self, gw_id, ids):
        self.calls += 1
        if self.max_ids is not None and len(ids) > self.max_ids:
            raise RuntimeError(500)
        if any(i not in self.known for i in ids):
            raise RuntimeError(500)
        return [{"id": i, "value": self.known[i]} for i in ids]


class MenuScanBisectTests(unittest.TestCase):
    """Bisecting rejected batches isolates the ids the cloud accepts."""

    def _scan(self, api, last=100, **kwargs):
        return asyncio.run(
            scan_menu_items(api, "GW", 1, last, pause_seconds=0, **kwargs)
        )

    def test_finds_known_ids_among_rejected(self):
        api = FakeMenuApi({119: 80, 124: 34.5, 230: 3})
        result = self._scan(api, last=250, max_requests=1000)
        self.assertEqual([i["id"] for i in result["items"]], [119, 124, 230])
        self.assertTrue(result["complete"])
        self.assertIn(1, result["rejected_ids"])

    def test_request_limit_marks_incomplete(self):
        api = FakeMenuApi({124: 34.5})
        result = self._scan(api, last=100, max_requests=5)
        self.assertFalse(result["complete"])
        self.assertLessEqual(api.calls, 5)
        self.assertTrue(result["not_scanned_ids"])

    def test_all_valid_needs_one_request_per_batch(self):
        api = FakeMenuApi({i: i for i in range(1, 51)})
        result = self._scan(api, last=50)
        self.assertEqual(result["items_found"], 50)
        self.assertEqual(api.calls, 2)

    def test_batch_size_limit_is_handled(self):
        api = FakeMenuApi({i: i for i in range(1, 26)}, max_ids=10)
        result = self._scan(api, last=25, max_requests=100)
        self.assertEqual(result["items_found"], 25)


if __name__ == "__main__":
    unittest.main()
