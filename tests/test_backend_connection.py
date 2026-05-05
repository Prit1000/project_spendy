import pytest
from app import app
from database.queries import (
    get_user_by_id,
    get_summary_stats,
    get_recent_transactions,
    get_category_breakdown,
)

# --- SUBAGENT 1 TESTS (user + transactions + route) ---

import re

SEED_USER_ID = 1
UNKNOWN_USER_ID = 99999


class TestGetUserById:
    def test_returns_dict(self):
        result = get_user_by_id(SEED_USER_ID)
        assert isinstance(result, dict)

    def test_has_member_since_key(self):
        result = get_user_by_id(SEED_USER_ID)
        assert "member_since" in result

    def test_member_since_format(self):
        result = get_user_by_id(SEED_USER_ID)
        assert re.match(r"^[A-Z][a-z]+ \d{4}$", result["member_since"])

    def test_no_created_at_key(self):
        result = get_user_by_id(SEED_USER_ID)
        assert "created_at" not in result

    def test_has_name_and_email(self):
        result = get_user_by_id(SEED_USER_ID)
        assert result["name"] == "Demo User"
        assert result["email"] == "demo@spendly.com"

    def test_returns_none_for_unknown_id(self):
        result = get_user_by_id(UNKNOWN_USER_ID)
        assert result is None


class TestGetRecentTransactions:
    def test_returns_list(self):
        result = get_recent_transactions(SEED_USER_ID)
        assert isinstance(result, list)

    def test_each_item_is_dict(self):
        result = get_recent_transactions(SEED_USER_ID)
        assert all(isinstance(item, dict) for item in result)

    def test_required_keys(self):
        result = get_recent_transactions(SEED_USER_ID)
        for item in result:
            assert "date" in item
            assert "description" in item
            assert "category" in item
            assert "amount" in item

    def test_ordered_newest_first(self):
        result = get_recent_transactions(SEED_USER_ID)
        dates = [item["date"] for item in result]
        assert dates == sorted(dates, reverse=True)

    def test_limit_respected(self):
        result = get_recent_transactions(SEED_USER_ID, limit=3)
        assert len(result) <= 3

    def test_returns_all_seed_transactions(self):
        result = get_recent_transactions(SEED_USER_ID, limit=100)
        assert len(result) == 8

    def test_empty_for_unknown_user(self):
        result = get_recent_transactions(UNKNOWN_USER_ID)
        assert result == []


class TestProfileRoute:
    def test_redirects_unauthenticated(self):
        with app.test_client() as client:
            response = client.get("/profile")
            assert response.status_code == 302
            assert "/login" in response.headers["Location"]

    def test_profile_loads_authenticated(self):
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = SEED_USER_ID
                sess["user_name"] = "Demo User"
            response = client.get("/profile")
            assert response.status_code == 200
            assert b"Demo User" in response.data

# --- SUBAGENT 2 TESTS (summary stats) ---

SEED_USER_ID_SA2 = 1
UNKNOWN_USER_ID_SA2 = 99999


class TestGetSummaryStats:
    def test_returns_dict(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert isinstance(result, dict)

    def test_has_all_keys(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert "total_spent" in result
        assert "transaction_count" in result
        assert "top_category" in result

    def test_total_spent_is_float(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert isinstance(result["total_spent"], float)

    def test_transaction_count_is_int(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert isinstance(result["transaction_count"], int)

    def test_top_category_is_str(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert isinstance(result["top_category"], str)

    def test_seed_user_total_spent(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert result["total_spent"] == pytest.approx(6220.0)

    def test_seed_user_transaction_count(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert result["transaction_count"] == 8

    def test_seed_user_top_category(self):
        result = get_summary_stats(SEED_USER_ID_SA2)
        assert result["top_category"] == "Shopping"

    def test_empty_user_returns_zero_total(self):
        result = get_summary_stats(UNKNOWN_USER_ID_SA2)
        assert result["total_spent"] == 0.0

    def test_empty_user_returns_zero_count(self):
        result = get_summary_stats(UNKNOWN_USER_ID_SA2)
        assert result["transaction_count"] == 0

    def test_empty_user_top_category_is_dash(self):
        result = get_summary_stats(UNKNOWN_USER_ID_SA2)
        assert result["top_category"] == "—"

# --- SUBAGENT 3 TESTS (category breakdown) ---

SEED_USER_ID_SA3 = 1
UNKNOWN_USER_ID_SA3 = 99999


class TestGetCategoryBreakdown:
    def test_returns_list(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        assert isinstance(result, list)

    def test_each_item_is_dict(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        assert all(isinstance(item, dict) for item in result)

    def test_required_keys(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        for item in result:
            assert "name" in item
            assert "amount" in item
            assert "pct" in item

    def test_pct_are_integers(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        for item in result:
            assert isinstance(item["pct"], int)

    def test_pct_sum_to_100(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        assert len(result) > 0
        assert sum(item["pct"] for item in result) == 100

    def test_ordered_by_amount_desc(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        amounts = [item["amount"] for item in result]
        assert amounts == sorted(amounts, reverse=True)

    def test_seven_categories_for_seed_user(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        assert len(result) == 7

    def test_uses_name_not_category_key(self):
        result = get_category_breakdown(SEED_USER_ID_SA3)
        for item in result:
            assert "category" not in item
            assert "name" in item

    def test_empty_for_unknown_user(self):
        result = get_category_breakdown(UNKNOWN_USER_ID_SA3)
        assert result == []
