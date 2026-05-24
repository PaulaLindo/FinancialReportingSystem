"""Human-readable date/time formatting for UI (converts stored UTC to display timezone)."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

_DEFAULT_TZ = "Africa/Johannesburg"


def display_timezone() -> ZoneInfo:
    """IANA zone for UI labels (default South Africa — SAST, UTC+2)."""
    name = (os.getenv("DISPLAY_TIMEZONE") or _DEFAULT_TZ).strip() or _DEFAULT_TZ
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(_DEFAULT_TZ)


def _parse_to_utc(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace("Z", "+00:00")
    if "." in normalized:
        base, frac = normalized.split(".", 1)
        suffix = ""
        if "+" in frac:
            frac, suffix = frac.split("+", 1)
            suffix = "+" + suffix
        elif "-" in frac[1:]:  # offset after fractional seconds
            idx = frac.find("-", 1)
            if idx > 0:
                suffix = frac[idx:]
                frac = frac[:idx]
        normalized = base + suffix

    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_display_datetime(value: Any) -> str:
    """
    Format ISO or datetime values for display in the app timezone.

    Stored values (Supabase ``timestamptz``, ISO with ``Z``) are UTC; shown as
    local time e.g. ``2026-05-20 15:47`` in ``Africa/Johannesburg``.
    """
    dt_utc = _parse_to_utc(value)
    if dt_utc is None:
        return ""

    local = dt_utc.astimezone(display_timezone())
    return local.strftime("%Y-%m-%d %H:%M")


def format_display_date_range(start: Any, end: Any, separator: str = " - ") -> str:
    """Format a start/end pair in the display timezone."""
    start_s = format_display_datetime(start)
    end_s = format_display_datetime(end)
    if start_s and end_s:
        return f"{start_s}{separator}{end_s}"
    return start_s or end_s
