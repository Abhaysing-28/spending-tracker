# Spend Tracker

A small REST API + minimal UI for logging expenses and viewing a spend summary.

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full record of options considered at each decision point and why we picked what we picked. This README covers how to run it and a condensed version of the key decisions.

---

## How to run it

**Requirements:** Python 3.10+

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the API (from the project root)
uvicorn app.main:app --reload

# API is now at http://localhost:8000
# Interactive docs (Swagger UI) at http://localhost:8000/docs
```

**Run the tests:**
```bash
pytest tests/ -v
```

**Use the frontend:**
Just open `frontend/index.html` directly in a browser (no build step, no server needed for the frontend itself). It defaults to calling `http://localhost:8000` — change the "API base URL" field at the top if your API is running elsewhere (e.g. the deployed Render URL).

**Enable API key auth (optional):**
```bash
export SPEND_TRACKER_API_KEY=some-secret-value
uvicorn app.main:app --reload
```
With this set, every request must include an `X-API-Key: some-secret-value` header (the frontend has a field for this). If the env var is unset, auth is a no-op — useful for local dev.

---

## API

| Method | Path | Description |
|---|---|---|
| `POST` | `/expenses` | Create an expense: `{amount, category, note?, date}` |
| `GET` | `/expenses` | List expenses. Optional query params: `category`, `start_date`, `end_date` |
| `GET` | `/summary` | Summary for a month. Optional query param: `month=YYYY-MM` (defaults to current month) |

**Categories** (fixed list): `food`, `transport`, `housing`, `entertainment`, `utilities`, `health`, `other`

**Example — create an expense:**
```bash
curl -X POST http://localhost:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"amount": 45.99, "category": "food", "note": "Groceries", "date": "2026-09-15"}'
```

**Example — summary:**
```bash
curl "http://localhost:8000/summary?month=2026-09"
```
```json
{
  "month": "2026-09",
  "total_spend": 305.99,
  "spend_by_category": [{"category": "food", "total": 45.99}, {"category": "housing", "total": 260.0}],
  "previous_month_total": 200.0,
  "month_over_month_change_pct": 53.0,
  "insights": ["Spend in 'housing' is up 30.0% vs last month ($200.00 -> $260.00)"]
}
```

**Error responses** use a consistent shape across the API:
```json
{"error": "Invalid input: amount", "detail": "Input should be greater than 0"}
```

---

## Key design decisions

*(Condensed — full rationale and alternatives considered in `ARCHITECTURE.md`)*

- **FastAPI + SQLAlchemy + SQLite.** FastAPI gives validation and API docs almost for free via Pydantic; SQLAlchemy keeps the schema/queries readable and makes tests easy to isolate; SQLite satisfies "real database" with zero infrastructure.
- **Money stored as integer cents**, not float — avoids floating-point rounding errors when summing many expenses. Converted to/from dollars at the API boundary.
- **Fixed category enum**, not freeform text — keeps the summary and 20%-increase insight logic simple and avoids the same category fragmenting across inconsistent spellings/casing.
- **`date` (expense date) vs `created_at` (row insert time)** are separate fields, since someone might log an expense a few days late.
- **API key auth is a no-op unless `SPEND_TRACKER_API_KEY` is set** — deliberately, so local dev/testing stays frictionless while still satisfying the auth bonus when deployed.
- **Consistent error envelope** (`{"error": ..., "detail": ...}`) across all validation failures via a custom FastAPI exception handler, rather than leaking FastAPI's default (differently-shaped) error format.
- **Tests target edge cases, not just happy paths**: negative/zero amounts, malformed dates, future dates, invalid categories, empty-state summary, divide-by-zero protection when there's no prior month to compare against, and the insight logic specifically (over/under the 20% threshold, and categories with no prior-month history).

---

## Deployment

Deployed via [Render](https://render.com)'s free tier — chosen because it requires no card on file for a basic web service (unlike Railway/Fly.io, which require one after a trial period). See `render.yaml` for the blueprint config.

**Steps to deploy:**
1. Push this repo to GitHub.
2. In Render: "New +" → "Blueprint" → connect the repo. Render reads `render.yaml` and provisions the service.
3. (Optional) Set `SPEND_TRACKER_API_KEY` in the Render dashboard's environment variables to enable auth.
4. Once live, update the "API base URL" field in `frontend/index.html` (or just type the Render URL into that field in the browser) to point the UI at the deployed API.

**Known limitation:** Render's free tier uses ephemeral disk, so the SQLite file resets on every redeploy or restart. This is an accepted tradeoff for a zero-cost demo deployment, not an oversight — see `ARCHITECTURE.md` for the alternatives considered.

---

## What I'd do differently with more time

- **Persistent database.** Move to a managed Postgres (e.g. Render's Postgres add-on) so data survives redeploys — the SQLAlchemy layer is already set up to make this a connection-string change, not a rewrite.
- **Pagination** on `GET /expenses` — currently returns the full result set, which is fine at demo scale but wouldn't hold up with years of data.
- **Multi-user support with real auth** (JWT + per-user data isolation) instead of a single shared API key — the current auth is intentionally minimal since this is a single-user tool.
- **Editing/deleting expenses** — the spec only asked for create + list + summary, so `PUT`/`DELETE /expenses/{id}` weren't built, but they're the obvious next endpoints.
- **More summary flexibility** — e.g. custom date ranges for summary (not just calendar months), and a trend view across multiple months rather than just current-vs-previous.
- **Frontend polish** — it's intentionally bare-bones per the task's scope ("design/styling will not be evaluated"); a real version would use a framework and proper state management instead of hand-rolled `fetch` calls.

---

## Note on AI tool usage

I used Claude to help scaffold the FastAPI/SQLAlchemy structure, generate the initial test cases, and draft this README. I reviewed and adjusted the generated validation logic (particularly the divide-by-zero handling in the month-over-month calculation and the decision to store money as integer cents rather than floats, which the first draft didn't handle), and rewrote several test cases to cover edge cases the initial pass missed, like categories with no prior-month data for the insight check.
