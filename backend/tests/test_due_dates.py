"""Due-date logic tests (US-02/03, FR-009)."""
from datetime import date

from app.services.due_dates import (
    current_period,
    due_date_for,
    period_label,
    reminders_due,
    upcoming_due_dates,
)


def test_due_dates_standard():
    # March 2026 period -> GSTR-1 on 11 Apr, GSTR-3B on 20 Apr.
    assert due_date_for("GSTR1", "032026") == date(2026, 4, 11)
    assert due_date_for("GSTR3B", "032026") == date(2026, 4, 20)


def test_december_rolls_to_next_year():
    assert due_date_for("GSTR3B", "122025") == date(2026, 1, 20)


def test_current_period():
    assert current_period(date(2026, 4, 15)) == "032026"
    assert current_period(date(2026, 1, 5)) == "122025"


def test_period_label():
    assert period_label("032026") == "Mar 2026"


def test_upcoming_due_dates_within_horizon():
    items = upcoming_due_dates(today=date(2026, 4, 9))
    types = {(i.return_type, i.period) for i in items}
    assert ("GSTR1", "032026") in types
    assert ("GSTR3B", "032026") in types


def test_reminders_three_days_before():
    # 3 days before GSTR-1 (11 Apr) is 8 Apr.
    reminders = reminders_due(today=date(2026, 4, 8))
    assert any(r.return_type == "GSTR1" for r in reminders)
