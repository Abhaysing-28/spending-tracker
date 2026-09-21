"""
Spend Tracker API — FastAPI app and route handlers.

Routes:
  POST /expenses  — create an expense
  GET  /expenses  — list expenses, filterable by category and date range
  GET  /summary   — total spend, spend by category, month-over-month change,
                     and insights (>20% category increase flags)

GET / serves the frontend UI and GET /health is a liveness check. All
/expenses and /summary routes are protected by an optional API key
(see app/auth.py) — disabled by default for local dev, enabled by setting
SPEND_TRACKER_API_KEY.
"""
import datetime as dt
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app import crud, models, schemas, summary
from app.auth import require_api_key
from app.database import Base, SessionLocal, engine, get_db

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Spend Tracker API", version="1.0.0")

# Wide-open CORS so the minimal frontend (served separately, e.g. as a local
# file or a different static host) can call the API without extra config.
# In a real product this would be locked down to a specific origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    """
    Turn FastAPI/Pydantic's default validation error shape into the
    consistent {"error": ..., "detail": ...} envelope used everywhere else
    in this API, so clients only need to handle one error format.
    """
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = first_error["msg"]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": f"Invalid input: {field}", "detail": message},
    )


FRONTEND_INDEX = Path(__file__).resolve().parent.parent / "frontend" / "index.html"


@app.get("/", include_in_schema=False)
def root():
    # Serve the minimal UI from the same origin as the API so a single
    # public URL gives the full end-to-end experience.
    return FileResponse(FRONTEND_INDEX)


@app.get("/health")
def health():
    return {"status": "ok", "service": "spend-tracker-api"}


@app.post(
    "/expenses",
    response_model=schemas.ExpenseOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    db_expense = crud.create_expense(db, expense)
    return schemas.ExpenseOut.from_orm_expense(db_expense)


@app.get(
    "/expenses",
    response_model=list[schemas.ExpenseOut],
    dependencies=[Depends(require_api_key)],
)
def list_expenses(
    category: Optional[schemas.Category] = Query(default=None),
    start_date: Optional[dt.date] = Query(default=None),
    end_date: Optional[dt.date] = Query(default=None),
    db: Session = Depends(get_db),
):
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    category_value = category.value if category is not None else None
    db_expenses = crud.list_expenses(db, category_value, start_date, end_date)
    return [schemas.ExpenseOut.from_orm_expense(e) for e in db_expenses]


@app.get(
    "/summary",
    response_model=schemas.SummaryOut,
    dependencies=[Depends(require_api_key)],
)
def get_summary(
    month: Optional[str] = Query(
        default=None, description="Month to summarize, format YYYY-MM. Defaults to current month."
    ),
    db: Session = Depends(get_db),
):
    if month is None:
        today = dt.date.today()
        year, month_num = today.year, today.month
    else:
        try:
            year, month_num = (int(p) for p in month.split("-"))
            dt.date(year, month_num, 1)  # validates ranges (month 1-12 etc.)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be in YYYY-MM format, e.g. 2026-09",
            )
    result = summary.build_summary(db, year, month_num)
    return schemas.SummaryOut(**result)
