#!/usr/bin/env python3
"""Unit tests for Vacation schedule parsing (no Home Assistant needed)."""

import importlib.util
import os
import unittest
from datetime import time

# Load vacation.py directly so the package __init__ (which needs Home Assistant) is skipped
_PATH = os.path.join(
    os.path.dirname(__file__), "custom_components", "pelican_thermostat", "vacation.py"
)
_spec = importlib.util.spec_from_file_location("pelican_vacation", _PATH)
vacation = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vacation)

TWO_SET_TIMES = """<?xml version="1.0" encoding="UTF-8"?>
<result>
  <ThermostatSchedule>
    <setTime>2</setTime><startTime>22:00</startTime><system>Auto</system>
    <heatSetting>58</heatSetting><coolSetting>82</coolSetting><fan>Auto</fan>
  </ThermostatSchedule>
  <ThermostatSchedule>
    <setTime>1</setTime><startTime>6:00</startTime><system>Auto</system>
    <heatSetting>60</heatSetting><coolSetting>80</coolSetting><fan>Auto</fan>
  </ThermostatSchedule>
  <success>1</success>
</result>"""


class ParseTests(unittest.TestCase):
    def test_entries_sorted_by_set_time(self):
        entries = vacation.parse_vacation_schedule(TWO_SET_TIMES)
        self.assertEqual([e["set_time"] for e in entries], [1, 2])
        self.assertEqual(entries[0]["heat_setting"], 60.0)
        self.assertEqual(entries[0]["cool_setting"], 80.0)
        self.assertEqual(entries[1]["system"], "Auto")

    def test_failure_returns_none(self):
        xml = "<result><success>0</success><message>nope</message></result>"
        self.assertIsNone(vacation.parse_vacation_schedule(xml))
        self.assertIsNone(vacation.parse_vacation_schedule("not xml"))

    def test_empty_schedule_returns_empty_list(self):
        self.assertEqual(vacation.parse_vacation_schedule("<result><success>1</success></result>"), [])


class ActiveEntryTests(unittest.TestCase):
    def setUp(self):
        self.entries = vacation.parse_vacation_schedule(TWO_SET_TIMES)

    def test_daytime_uses_morning_entry(self):
        self.assertEqual(vacation.active_vacation_entry(self.entries, time(12, 0))["set_time"], 1)

    def test_after_last_start_uses_last_entry(self):
        self.assertEqual(vacation.active_vacation_entry(self.entries, time(23, 0))["set_time"], 2)

    def test_before_first_start_wraps_to_last_entry(self):
        self.assertEqual(vacation.active_vacation_entry(self.entries, time(3, 0))["set_time"], 2)

    def test_no_entries(self):
        self.assertIsNone(vacation.active_vacation_entry([], time(12, 0)))

    def test_untimed_entry_used_as_fallback(self):
        entries = [{"set_time": 1, "start_time": None, "heat_setting": 55.0}]
        self.assertEqual(vacation.active_vacation_entry(entries, time(12, 0))["heat_setting"], 55.0)


if __name__ == "__main__":
    unittest.main()
