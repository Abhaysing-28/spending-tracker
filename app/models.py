"""
SQLAlchemy ORM models.

Design notes:
- amount_cents is stored as an integer (cents) rather than a float, to avoid
  floating point rounding errors when summing many expenses for the summary
  endpoint. Converted to/from dollars at the API boundary (see schemas.py).
- `date` is the date the expense actually happened (user-supplied), separate
  from `created_at` which is a server-side audit timestamp of when the row
  was inserted. These can differ if someone logs an expense late.
- category is constrained by CheckConstraint to the fixed set of allowed
  values, matching the enum used in the Pydantic schema. This keeps
  aggregation (summary / insight) logic simple and typo-proof, at the DB
  layer too (not just API validation).
"""
import datetime as dt

from sqlalchemy import CheckConstraint, Column, Date, DateTime, Integer, String

from app.database import Base

ALLOWED_CATEGORIES = [
    "food",
    "transport",
    "housing",
    "entertainment",
    "utilities",
    "health",
    "other",
]


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    category = Column(String, nullable=False, index=True)
    note = Column(String, nullable=True)
    date = Column(Date, nullable=False, index=True)
    created_at = Column(
        DateTime, default=lambda: dt.datetime.now(dt.timezone.utc), nullable=False
    )

    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_positive"),
        CheckConstraint(
            "category IN ({})".format(
                ", ".join(f"'{c}'" for c in ALLOWED_CATEGORIES)
            ),
            name="category_allowed",
        ),
    )
