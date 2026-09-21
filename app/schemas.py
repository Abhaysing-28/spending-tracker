"""
Pydantic schemas for request/response validation.

The API speaks dollars (as a decimal) to the outside world for usability,
but internally we store/compute in integer cents (see models.py). Conversion
happens right here at the boundary.
"""
import datetime as dt
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    food = "food"
    transport = "transport"
    housing = "housing"
    entertainment = "entertainment"
    utilities = "utilities"
    health = "health"
    other = "other"


class ExpenseCreate(BaseModel):
    amount: float = Field(..., gt=0, description="Amount in dollars, must be > 0")
    category: Category
    note: Optional[str] = Field(None, max_length=500)
    date: dt.date

    @field_validator("date")
    @classmethod
    def date_not_in_future(cls, v: dt.date) -> dt.date:
        if v > dt.date.today():
            raise ValueError("date cannot be in the future")
        return v

    @field_validator("amount")
    @classmethod
    def amount_two_decimal_places(cls, v: float) -> float:
        # Reject absurd precision like 12.3456 — money has at most 2 decimals.
        if round(v, 2) != v:
            raise ValueError("amount must have at most 2 decimal places")
        return v


class ExpenseOut(BaseModel):
    id: int
    amount: float
    category: Category
    note: Optional[str]
    date: dt.date
    created_at: dt.datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_expense(cls, expense) -> "ExpenseOut":
        """Build an ExpenseOut from a DB Expense row, converting cents -> dollars."""
        return cls(
            id=expense.id,
            amount=expense.amount_cents / 100,
            category=expense.category,
            note=expense.note,
            date=expense.date,
            created_at=expense.created_at,
        )


class CategoryTotal(BaseModel):
    category: str
    total: float


class SummaryOut(BaseModel):
    month: str  # "YYYY-MM"
    total_spend: float
    spend_by_category: list[CategoryTotal]
    previous_month_total: float
    month_over_month_change_pct: Optional[float]  # None if no prior month data
    insights: list[str]


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
