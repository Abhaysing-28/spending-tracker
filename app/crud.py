"""
Database access layer — keeps raw SQLAlchemy queries out of the route
handlers so main.py stays focused on HTTP concerns.
"""
import datetime as dt
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app import models, schemas


def create_expense(db: Session, expense: schemas.ExpenseCreate) -> models.Expense:
    db_expense = models.Expense(
        amount_cents=round(expense.amount * 100),
        category=expense.category.value,
        note=expense.note,
        date=expense.date,
    )
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense


def list_expenses(
    db: Session,
    category: Optional[str] = None,
    start_date: Optional[dt.date] = None,
    end_date: Optional[dt.date] = None,
) -> list[models.Expense]:
    query = db.query(models.Expense)
    filters = []
    if category is not None:
        filters.append(models.Expense.category == category)
    if start_date is not None:
        filters.append(models.Expense.date >= start_date)
    if end_date is not None:
        filters.append(models.Expense.date <= end_date)
    if filters:
        query = query.filter(and_(*filters))
    return query.order_by(models.Expense.date.desc(), models.Expense.id.desc()).all()


def expenses_in_month(db: Session, year: int, month: int) -> list[models.Expense]:
    start = dt.date(year, month, 1)
    if month == 12:
        end = dt.date(year + 1, 1, 1)
    else:
        end = dt.date(year, month + 1, 1)
    return (
        db.query(models.Expense)
        .filter(models.Expense.date >= start, models.Expense.date < end)
        .all()
    )
