"""
Summary and insight computation, isolated from the route layer so it can be
unit-tested directly without spinning up the HTTP app.
"""
import datetime as dt
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from app import crud, models

INSIGHT_THRESHOLD_PCT = 20.0


def _month_str(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def _prev_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _totals_by_category(expenses: list[models.Expense]) -> dict[str, int]:
    totals: dict[str, int] = defaultdict(int)
    for e in expenses:
        totals[e.category] += e.amount_cents
    return totals


def build_summary(db: Session, year: int, month: int) -> dict:
    """
    Computes:
    - total spend for the given month
    - spend broken down by category
    - month-over-month % change in total spend vs the previous month
    - insight strings flagging any category whose spend rose >20% MoM

    Returns a plain dict shaped to match schemas.SummaryOut so the route
    layer can construct the response model directly.
    """
    current_expenses = crud.expenses_in_month(db, year, month)
    prev_year, prev_month = _prev_month(year, month)
    prev_expenses = crud.expenses_in_month(db, prev_year, prev_month)

    current_totals = _totals_by_category(current_expenses)
    prev_totals = _totals_by_category(prev_expenses)

    total_spend_cents = sum(current_totals.values())
    prev_total_cents = sum(prev_totals.values())

    spend_by_category = [
        {"category": cat, "total": cents / 100}
        for cat, cents in sorted(current_totals.items())
    ]

    if prev_total_cents == 0:
        # No prior month data to compare against — avoid divide-by-zero,
        # report None rather than a misleading 0% or infinite change.
        mom_change_pct: Optional[float] = None
    else:
        mom_change_pct = round(
            ((total_spend_cents - prev_total_cents) / prev_total_cents) * 100, 2
        )

    insights = []
    for cat, current_cents in current_totals.items():
        prev_cents = prev_totals.get(cat, 0)
        if prev_cents == 0:
            continue  # new category this month — nothing to compare against
        change_pct = ((current_cents - prev_cents) / prev_cents) * 100
        if change_pct > INSIGHT_THRESHOLD_PCT:
            insights.append(
                f"Spend in '{cat}' is up {change_pct:.1f}% vs last month "
                f"(${prev_cents / 100:.2f} -> ${current_cents / 100:.2f})"
            )

    return {
        "month": _month_str(year, month),
        "total_spend": total_spend_cents / 100,
        "spend_by_category": spend_by_category,
        "previous_month_total": prev_total_cents / 100,
        "month_over_month_change_pct": mom_change_pct,
        "insights": insights,
    }
