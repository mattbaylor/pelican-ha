"""Parsing for the Pelican Vacation schedule (the setpoints used while Vacant).

Kept free of Home Assistant imports so it can be unit tested on its own.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import time
from typing import Any


def _text(elem: ET.Element, tag: str) -> str | None:
    child = elem.find(tag)
    return child.text if child is not None and child.text else None


def _number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _start_time(value: str | None) -> time | None:
    """Parse a 24 hr "HH:MM" start time."""
    if not value:
        return None
    try:
        hour, minute = value.split(":")[:2]
        return time(int(hour), int(minute))
    except ValueError:
        return None


def parse_vacation_schedule(xml_text: str) -> list[dict[str, Any]] | None:
    """Parse a ThermostatSchedule GET response into set times sorted by setTime.

    Returns None when the response is unsuccessful or unparseable, and an empty
    list when the request worked but no Vacation set times are programmed.
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    success = root.find("success")
    if success is None or success.text != "1":
        return None

    entries = []
    for elem in root.iter("ThermostatSchedule"):
        set_time = _number(_text(elem, "setTime"))
        entries.append(
            {
                "set_time": int(set_time) if set_time is not None else None,
                "start_time": _text(elem, "startTime"),
                "system": _text(elem, "system"),
                "heat_setting": _number(_text(elem, "heatSetting")),
                "cool_setting": _number(_text(elem, "coolSetting")),
                "fan": _text(elem, "fan"),
            }
        )

    entries.sort(key=lambda e: (e["set_time"] is None, e["set_time"] or 0))
    return entries


def active_vacation_entry(
    entries: list[dict[str, Any]], now: time
) -> dict[str, Any] | None:
    """Return the Vacation set time in effect at `now`.

    The entry in effect is the latest one whose start time has passed today;
    before the first start time, the last entry of the day still applies.
    Entries without a parseable start time are only used as a last resort.
    """
    if not entries:
        return None

    timed = [(t, e) for e in entries if (t := _start_time(e["start_time"])) is not None]
    if not timed:
        return entries[0]

    timed.sort(key=lambda pair: pair[0])
    current = timed[-1][1]
    for start, entry in timed:
        if start <= now:
            current = entry
    return current
