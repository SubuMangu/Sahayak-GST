"""GST filing due-date logic (US-02, US-03, FR-009 compliance calendar).

Standard monthly cadence for regular taxpayers:
  - GSTR-1  : 11th of the following month
  - GSTR-3B : 20th of the following month

Composition dealers file CMP-08 quarterly (18th of month after quarter). We expose helpers
the dashboard and reminder scheduler use.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class DueItem:
    return_type: str
    period: str  # MMYYYY
    due_date: date
    days_remaining: int


def _add_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def period_label(period: str) -> str:
    """MMYYYY -> 'Mon YYYY'."""
    months = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    mm, yyyy = int(period[:2]), period[2:]
    return f"{months[mm]} {yyyy}"


def current_period(today: date | None = None) -> str:
    """Return the most recent *completed* tax period (the one currently being filed)."""
    today = today or date.today()
    y, m = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    return f"{m:02d}{y}"


def due_date_for(return_type: str, period: str) -> date:
    """Compute the statutory due date for a return_type & period (MMYYYY)."""
    mm, yyyy = int(period[:2]), int(period[2:])
    ny, nm = _add_month(yyyy, mm)
    day = 11 if return_type.upper() == "GSTR1" else 20
    return date(ny, nm, day)


def upcoming_due_dates(
    *, scheme: str = "regular", today: date | None = None, horizon_days: int = 45
) -> list[DueItem]:
    """List upcoming GSTR due items within ``horizon_days`` for the dashboard calendar."""
    today = today or date.today()
    items: list[DueItem] = []
    if scheme == "composition":
        return items  # CMP-08 quarterly handled separately (out of MVP detail)

    # Consider the last completed period and the one before it (late-filing window).
    periods = [current_period(today)]
    prev_mm, prev_yyyy = int(periods[0][:2]), int(periods[0][2:])
    py, pm = (prev_yyyy - 1, 12) if prev_mm == 1 else (prev_yyyy, prev_mm - 1)
    periods.append(f"{pm:02d}{py}")

    for period in periods:
        for rtype in ("GSTR1", "GSTR3B"):
            dd = due_date_for(rtype, period)
            delta = (dd - today).days
            if -5 <= delta <= horizon_days:
                items.append(
                    DueItem(return_type=rtype, period=period, due_date=dd, days_remaining=delta)
                )
    return sorted(items, key=lambda i: i.due_date)


def reminders_due(today: date | None = None, days_before: int = 3) -> list[DueItem]:
    """Return due items exactly ``days_before`` away — used by the WhatsApp reminder job."""
    today = today or date.today()
    return [
        item
        for item in upcoming_due_dates(today=today)
        if item.days_remaining == days_before
    ]


def next_due(today: date | None = None) -> DueItem | None:
    items = [i for i in upcoming_due_dates(today=today) if i.days_remaining >= 0]
    return items[0] if items else None


def days_until_next_due(today: date | None = None) -> int | None:
    item = next_due(today)
    return item.days_remaining if item else None


__all__ = [
    "DueItem",
    "current_period",
    "days_until_next_due",
    "due_date_for",
    "next_due",
    "period_label",
    "reminders_due",
    "upcoming_due_dates",
]
