import datetime as dt

TODAY = dt.date.today().isoformat()


def make_expense(**overrides):
    payload = {
        "amount": 25.50,
        "category": "food",
        "note": "Groceries",
        "date": TODAY,
    }
    payload.update(overrides)
    return payload


class TestCreateExpense:
    def test_create_expense_happy_path(self, client):
        resp = client.post("/expenses", json=make_expense())
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount"] == 25.50
        assert body["category"] == "food"
        assert body["note"] == "Groceries"
        assert body["date"] == TODAY
        assert "id" in body

    def test_create_expense_without_note(self, client):
        payload = make_expense()
        del payload["note"]
        resp = client.post("/expenses", json=payload)
        assert resp.status_code == 201
        assert resp.json()["note"] is None

    def test_negative_amount_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(amount=-10))
        assert resp.status_code == 422
        assert "error" in resp.json()

    def test_zero_amount_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(amount=0))
        assert resp.status_code == 422

    def test_amount_with_too_many_decimals_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(amount=10.999))
        assert resp.status_code == 422

    def test_invalid_category_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(category="crypto"))
        assert resp.status_code == 422

    def test_missing_required_field_rejected(self, client):
        payload = make_expense()
        del payload["amount"]
        resp = client.post("/expenses", json=payload)
        assert resp.status_code == 422

    def test_future_date_rejected(self, client):
        future = (dt.date.today() + dt.timedelta(days=5)).isoformat()
        resp = client.post("/expenses", json=make_expense(date=future))
        assert resp.status_code == 422

    def test_malformed_date_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(date="not-a-date"))
        assert resp.status_code == 422

    def test_note_too_long_rejected(self, client):
        resp = client.post("/expenses", json=make_expense(note="x" * 501))
        assert resp.status_code == 422


class TestListExpenses:
    def test_list_empty(self, client):
        resp = client.get("/expenses")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_returns_created_expenses(self, client):
        client.post("/expenses", json=make_expense(amount=10))
        client.post("/expenses", json=make_expense(amount=20))
        resp = client.get("/expenses")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_filter_by_category(self, client):
        client.post("/expenses", json=make_expense(category="food"))
        client.post("/expenses", json=make_expense(category="transport"))
        resp = client.get("/expenses", params={"category": "food"})
        assert resp.status_code == 200
        results = resp.json()
        assert len(results) == 1
        assert results[0]["category"] == "food"

    def test_filter_by_category_no_matches(self, client):
        client.post("/expenses", json=make_expense(category="food"))
        resp = client.get("/expenses", params={"category": "housing"})
        assert resp.status_code == 200
        assert resp.json() == []

    def test_filter_by_date_range(self, client):
        client.post("/expenses", json=make_expense(date="2026-01-01"))
        client.post("/expenses", json=make_expense(date="2026-06-15"))
        client.post("/expenses", json=make_expense(date="2026-09-01"))
        resp = client.get(
            "/expenses",
            params={"start_date": "2026-01-01", "end_date": "2026-06-30"},
        )
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_date_range_boundaries_are_inclusive(self, client):
        client.post("/expenses", json=make_expense(date="2026-03-01"))
        resp = client.get(
            "/expenses",
            params={"start_date": "2026-03-01", "end_date": "2026-03-01"},
        )
        assert len(resp.json()) == 1

    def test_start_date_after_end_date_rejected(self, client):
        resp = client.get(
            "/expenses",
            params={"start_date": "2026-06-01", "end_date": "2026-01-01"},
        )
        assert resp.status_code == 400

    def test_invalid_category_filter_rejected(self, client):
        resp = client.get("/expenses", params={"category": "not-a-real-category"})
        assert resp.status_code == 422
