def add(client, amount, category, date):
    resp = client.post(
        "/expenses",
        json={"amount": amount, "category": category, "date": date},
    )
    assert resp.status_code == 201, resp.text


class TestSummary:
    def test_summary_with_no_expenses(self, client):
        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_spend"] == 0
        assert body["spend_by_category"] == []
        assert body["month_over_month_change_pct"] is None
        assert body["insights"] == []

    def test_summary_totals_and_category_breakdown(self, client):
        add(client, 50, "food", "2026-09-05")
        add(client, 30, "food", "2026-09-10")
        add(client, 100, "housing", "2026-09-01")

        resp = client.get("/summary", params={"month": "2026-09"})
        body = resp.json()
        assert body["total_spend"] == 180
        by_cat = {c["category"]: c["total"] for c in body["spend_by_category"]}
        assert by_cat == {"food": 80, "housing": 100}

    def test_summary_excludes_other_months(self, client):
        add(client, 50, "food", "2026-08-15")  # previous month
        add(client, 20, "food", "2026-09-15")  # target month

        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.json()["total_spend"] == 20

    def test_month_over_month_change_positive(self, client):
        add(client, 100, "food", "2026-08-01")
        add(client, 150, "food", "2026-09-01")

        resp = client.get("/summary", params={"month": "2026-09"})
        body = resp.json()
        assert body["previous_month_total"] == 100
        assert body["month_over_month_change_pct"] == 50.0

    def test_month_over_month_change_negative(self, client):
        add(client, 200, "food", "2026-08-01")
        add(client, 100, "food", "2026-09-01")

        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.json()["month_over_month_change_pct"] == -50.0

    def test_month_over_month_none_when_no_prior_month_data(self, client):
        add(client, 100, "food", "2026-09-01")
        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.json()["month_over_month_change_pct"] is None

    def test_insight_flags_category_increase_over_20_percent(self, client):
        add(client, 100, "entertainment", "2026-08-01")
        add(client, 130, "entertainment", "2026-09-01")  # +30%

        resp = client.get("/summary", params={"month": "2026-09"})
        insights = resp.json()["insights"]
        assert len(insights) == 1
        assert "entertainment" in insights[0]
        assert "30.0%" in insights[0]

    def test_insight_not_flagged_under_threshold(self, client):
        add(client, 100, "entertainment", "2026-08-01")
        add(client, 110, "entertainment", "2026-09-01")  # +10%, under threshold

        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.json()["insights"] == []

    def test_insight_not_flagged_for_new_category_with_no_history(self, client):
        # Category only exists this month — nothing to compare against,
        # should not be treated as an "infinite %" increase.
        add(client, 100, "utilities", "2026-09-01")
        resp = client.get("/summary", params={"month": "2026-09"})
        assert resp.json()["insights"] == []

    def test_invalid_month_format_rejected(self, client):
        resp = client.get("/summary", params={"month": "September-2026"})
        assert resp.status_code == 400

    def test_invalid_month_number_rejected(self, client):
        resp = client.get("/summary", params={"month": "2026-13"})
        assert resp.status_code == 400

    def test_summary_defaults_to_current_month_when_omitted(self, client):
        resp = client.get("/summary")
        assert resp.status_code == 200
        assert "month" in resp.json()
