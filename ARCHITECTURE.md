# Architecture & Design Decisions — Spend Tracker

This document captures the options we considered at each decision point, what we chose, and why. It's meant to be read alongside the README (which covers "how to run it") — this file is the "why did we build it this way" record.

---

## 1. Backend Framework

| Option | Pros | Cons |
|---|---|---|
| **FastAPI** (chosen) | Built-in request validation via Pydantic, automatic OpenAPI/Swagger docs, async-ready, minimal boilerplate, great fit for a small validated REST API | Slightly less "batteries included" than Django (no built-in admin/ORM) |
| Flask | Very simple, huge ecosystem, most people already know it | Validation, serialization, and docs all need extra libraries (marshmallow/flask-smorest) — more boilerplate for the same result |
| Django + DRF | Full-featured, admin panel, ORM built in | Heavy for a small service; more setup overhead than the task warrants |

**Why FastAPI:** the task explicitly calls for input validation and clean REST endpoints. FastAPI gives us that almost for free via Pydantic models, plus auto-generated docs we can point reviewers to without extra work.

---

## 2. Database Layer

| Option | Pros | Cons |
|---|---|---|
| SQLite via **SQLAlchemy ORM** (chosen) | Clean schema definitions, easy to swap in an in-memory/temp SQLite DB for tests, readable query code, migration path if we ever needed to move to Postgres | Small learning-curve overhead vs raw SQL |
| Raw `sqlite3` | Zero dependencies, very explicit | More manual boilerplate for filtering/joins, harder to test in isolation |
| Postgres (hosted) | Production-grade, persistent | Requires a hosted DB service (cost/setup) — overkill for this scope, and the task explicitly says SQLite is fine |

**Why SQLAlchemy + SQLite:** SQLite satisfies "real database, not an in-memory list" with zero infrastructure cost. SQLAlchemy makes the test suite easy (spin up a fresh in-memory DB per test run) and keeps the schema/queries readable.

---

## 3. Money Representation

| Option | Pros | Cons |
|---|---|---|
| **Integer cents** (chosen) | No floating-point rounding errors, safe for sums/aggregations | Requires converting to/from dollars at API boundary |
| Float | Simple to read | Classic floating-point rounding bugs when summing many values — risky for a spend tracker |
| Decimal | Precise, human-readable | SQLite has no native Decimal type; needs extra serialization handling |

**Why integer cents:** money math needs to be exact, especially once we're summing across categories and months for the summary/insight endpoints. Storing as integer cents avoids float drift entirely with minimal extra code.

---

## 4. Category Field

| Option | Pros | Cons |
|---|---|---|
| **Fixed enum list** (chosen) | Cleaner grouping for summary/insight logic, prevents typo'd categories fragmenting the data (`"food"` vs `"Food"` vs `"foood"`) | Less flexible — user can't invent new categories on the fly |
| Freeform string | Maximum flexibility | Summary/MoM/insight logic gets messy with inconsistent casing/spelling |

**Why fixed enum:** the summary and "20% increase" insight features depend on clean category grouping. A small fixed list (e.g. `food`, `transport`, `housing`, `entertainment`, `utilities`, `other`) keeps aggregation logic simple and correct.

---

## 5. Frontend

| Option | Pros | Cons |
|---|---|---|
| **Plain HTML/JS** (chosen) | No build step, single file, fastest to stand up, sufficient since styling isn't evaluated | Less polished, no component reuse |
| React | Nicer for larger UIs, component model | Needs a build toolchain (Vite/CRA) — unnecessary overhead for two simple views |
| Flutter | Cross-platform | Massive overkill for a form + summary view |

**Why plain HTML/JS:** the task says styling won't be evaluated and the UI only needs to prove end-to-end functionality (add expense, view summary). A single `index.html` with `fetch()` calls does that with zero tooling overhead.

---

## 6. Testing

**Chosen:** `pytest` + FastAPI's `TestClient`, with a fresh SQLite (temp file or in-memory) database per test run via a fixture, so tests don't pollute each other or the real dev DB.

**Coverage targets (not just happy path):**
- Validation failures (negative amount, missing fields, bad date format, invalid category)
- Empty-state summary (no expenses yet)
- Category filtering with no matches
- Date range boundary conditions (inclusive start/end)
- Month-over-month calc when there's no prior month's data
- The 20%-increase insight with edge cases (previous month = 0 spend, avoiding divide-by-zero)

---

## 7. Deployment (Bonus)

| Option | Free tier? | Notes |
|---|---|---|
| **Render** (chosen) | Yes, no card required for basic free web service | Cold starts after inactivity (~30s spin-up), but zero cost and simple to set up |
| Railway | Trial credit only, then requires card + usage billing | Risk of incurring charges after trial runs out |
| Fly.io | Free allowances exist | Requires card on file; easy to accidentally cross into paid usage |

**Why Render:** it's the only option here with a genuinely free tier that doesn't require a card on file. The cold-start delay is a minor UX tradeoff for a demo project, not a real cost. This keeps total project spend at **$0**.

**Database on Render's free tier:** disk is ephemeral — the SQLite file resets on redeploy/restart. This is a known, documented limitation rather than something we're paying to avoid (e.g. via a managed persistent DB add-on). Called out explicitly in the README so it's not mistaken for a bug.

---

## 8. Authentication (Bonus)

*(To be filled in once we decide whether to implement — API key via header is the lightweight default if we do: simple to implement, simple to test, no session/JWT infrastructure needed for a single-user demo tool.)*

---

## 9. Cost Summary

| Item | Cost |
|---|---|
| Hosting (Render free tier) | $0 |
| Database (SQLite, file-based) | $0 |
| Domain (Render subdomain) | $0 |
| AI coding tools | Covered by existing subscription, not project-specific |
| **Total** | **$0** |

---

## 10. What We'd Do Differently With More Time

*(To be expanded as we build — placeholder for the README's "what I'd do differently" section, kept here too since it's architecture-relevant.)*
- Move to a persistent managed Postgres if this needed to survive redeploys
- Add pagination to `GET /expenses` for large datasets
- Add proper JWT-based multi-user auth instead of a single API key
