"""First weekday of the month guard.

Exit 0  proceed
Exit 10 not the first weekday, do nothing

The scheduled job fires on the 1st, 2nd and 3rd. Only the run that lands on the
first weekday of the month should do work. If the 1st is a Saturday, the 2nd is
Sunday and the 3rd is Monday, so only the run on the 3rd proceeds.
"""
from __future__ import annotations

import argparse
import calendar
import sys
from datetime import date, datetime


def first_weekday(year: int, month: int) -> date:
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        if d.weekday() < 5:
            return d
    raise AssertionError("a month always contains a weekday")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date", help="override today, as YYYY-MM-DD, for testing")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    today = (
        datetime.strptime(a.date, "%Y-%m-%d").date() if a.date else date.today()
    )
    target = first_weekday(today.year, today.month)

    if today == target:
        if not a.quiet:
            print(f"PROCEED {today:%Y-%m-%d %A} is the first weekday of "
                  f"{today:%B %Y}.")
        return 0

    if not a.quiet:
        print(f"SKIP {today:%Y-%m-%d %A}. The first weekday of "
              f"{today:%B %Y} is {target:%Y-%m-%d %A}.")
    return 10


if __name__ == "__main__":
    sys.exit(main())
