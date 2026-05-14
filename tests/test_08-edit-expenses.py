"""
Tests for Step 08 — Edit Expenses.

Spec: .claude/specs/08-edit-expenses.md

Behaviour contract under test:
  - GET /expenses/<id>/edit while logged out → redirects to /login (302)
  - POST /expenses/<id>/edit while logged out → redirects to /login (302)
  - GET /expenses/<id>/edit for own expense → 200 with pre-filled form
  - Form pre-filled with correct amount, category, date, and description
  - Form structure: title, subtitle, Save Changes button, Cancel to /profile,
    POST method, correct action URL, all four fields, all seven categories, ₹ symbol
  - GET /expenses/<id>/edit for another user's expense → redirects to /profile
  - GET /expenses/<id>/edit for non-existent id → redirects to /profile
  - POST with valid changes → updates DB row, redirects to /profile
  - Updated values visible in /profile recent transactions
  - Valid POST does NOT create a new row (updates the existing one)
  - POST with invalid amount (blank/zero/negative/non-numeric) → 200 + auth-error; form retains values
  - POST with invalid category → 200 + auth-error; no DB mutation
  - POST with invalid date → 200 + auth-error; no DB mutation
  - POST for another user's expense → redirects to /profile; DB unchanged
  - /profile shows an "Actions" <th> column and an "Edit" link per expense row
  - "Edit" link href points to /expenses/<id>/edit for the correct id
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_user(conn, name, email, password="testpassword"):
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    return cursor.lastrowid


def _insert_expense(conn, user_id, amount, category, date, description="Test"):
    cursor = conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description)"
        " VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description),
    )
    conn.commit()
    return cursor.lastrowid


def _login(client, email, password):
    client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """
    Isolated Flask app backed by a temporary on-disk SQLite database.
    Monkey-patches database.db.DB_PATH so every test gets a clean slate.
    """
    db_file = str(tmp_path / "test_expense_tracker.db")

    import database.db as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_file

    flask_app.config.update({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key-for-pytest",
        "WTF_CSRF_ENABLED": False,
    })

    with flask_app.app_context():
        init_db()

    yield flask_app

    db_module.DB_PATH = original_path


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app, client):
    """
    A logged-in test client.  Returns (client, user_id, expense_id) so that
    tests can verify DB state against known ids.

    Seed: one user with one expense:
      amount=500.00, category="Food", date="2026-05-10", description="Lunch"
    """
    conn = get_db()
    user_id = _insert_user(conn, "Test User", "testuser@example.com", "securepassword")
    expense_id = _insert_expense(conn, user_id, 500.00, "Food", "2026-05-10", "Lunch")
    conn.close()

    _login(client, "testuser@example.com", "securepassword")
    return client, user_id, expense_id


@pytest.fixture
def two_user_client(app, client):
    """
    Two users; user 1 owns expense_id.  The client is logged in as user 2.
    Returns (client, user1_id, user2_id, expense_id).
    """
    conn = get_db()
    user1_id = _insert_user(conn, "User One", "user1@example.com", "password1")
    expense_id = _insert_expense(conn, user1_id, 750.00, "Transport", "2026-06-01", "Taxi")
    user2_id = _insert_user(conn, "User Two", "user2@example.com", "password2")
    conn.close()

    _login(client, "user2@example.com", "password2")
    return client, user1_id, user2_id, expense_id


# ---------------------------------------------------------------------------
# 1. Auth guard — GET
# ---------------------------------------------------------------------------

class TestAuthGuardGet:
    def test_unauthenticated_get_redirects(self, client, app):
        """A logged-out GET to any edit URL must redirect (not serve a form)."""
        conn = get_db()
        user_id = _insert_user(conn, "A", "a@a.com")
        eid = _insert_expense(conn, user_id, 100, "Food", "2026-01-01")
        conn.close()

        response = client.get(f"/expenses/{eid}/edit")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/<id>/edit must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect destination must be /login"
        )

    def test_unauthenticated_get_does_not_return_200(self, client, app):
        conn = get_db()
        user_id = _insert_user(conn, "B", "b@b.com")
        eid = _insert_expense(conn, user_id, 100, "Food", "2026-01-01")
        conn.close()

        response = client.get(f"/expenses/{eid}/edit")
        assert response.status_code != 200, (
            "Unauthenticated GET must never return 200"
        )


# ---------------------------------------------------------------------------
# 2. Auth guard — POST
# ---------------------------------------------------------------------------

class TestAuthGuardPost:
    def test_unauthenticated_post_redirects_to_login(self, client, app):
        conn = get_db()
        user_id = _insert_user(conn, "C", "c@c.com")
        eid = _insert_expense(conn, user_id, 100, "Food", "2026-01-01")
        conn.close()

        response = client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "200",
                "category": "Food",
                "date": "2026-05-01",
                "description": "Updated",
            },
        )
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/<id>/edit must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Unauthenticated POST redirect must go to /login"
        )

    def test_unauthenticated_post_does_not_mutate_db(self, client, app):
        """An unauthenticated POST must not change the expense in the database."""
        conn = get_db()
        user_id = _insert_user(conn, "D", "d@d.com")
        eid = _insert_expense(conn, user_id, 100, "Food", "2026-01-01", "Original")
        conn.close()

        client.post(
            f"/expenses/{eid}/edit",
            data={
                "amount": "9999",
                "category": "Shopping",
                "date": "2026-12-31",
                "description": "Hacked",
            },
        )
        conn = get_db()
        row = conn.execute("SELECT amount FROM expenses WHERE id = ?", (eid,)).fetchone()
        conn.close()
        assert abs(row["amount"] - 100.0) < 0.001, (
            "Unauthenticated POST must not change the stored amount"
        )


# ---------------------------------------------------------------------------
# 3. GET — happy path (own expense)
# ---------------------------------------------------------------------------

class TestGetEditFormHappyPath:
    def test_returns_200_for_own_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert response.status_code == 200, (
            "GET /expenses/<id>/edit for own expense must return 200"
        )

    def test_amount_prefilled_from_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"500" in response.data, (
            "Expense amount (500) must be pre-filled in the form"
        )

    def test_category_prefilled_from_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        # The existing category "Food" must appear as the selected option.
        assert b"Food" in response.data, (
            "Expense category 'Food' must be pre-filled in the form"
        )

    def test_date_prefilled_from_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"2026-05-10" in response.data, (
            "Expense date (2026-05-10) must be pre-filled in the form"
        )

    def test_description_prefilled_from_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"Lunch" in response.data, (
            "Expense description 'Lunch' must be pre-filled in the form"
        )


# ---------------------------------------------------------------------------
# 4. GET — form structure
# ---------------------------------------------------------------------------

class TestGetEditFormStructure:
    def test_page_title_contains_edit_expense(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"Edit Expense" in response.data, (
            "Page must contain the heading 'Edit Expense'"
        )

    def test_page_subtitle_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"Update your spending entry" in response.data, (
            "Page must show subtitle 'Update your spending entry'"
        )

    def test_save_changes_button_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"Save Changes" in response.data, (
            "Submit button must be labelled 'Save Changes'"
        )

    def test_cancel_link_points_to_profile(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'href="/profile"' in response.data, (
            "Cancel link must point to /profile"
        )

    def test_cancel_link_has_cancel_text(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"Cancel" in response.data, (
            "Cancel link must have visible 'Cancel' text"
        )

    def test_form_method_is_post(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'method="POST"' in response.data, (
            "Edit form method must be POST"
        )

    def test_form_action_points_to_edit_url(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        expected_action = f'/expenses/{expense_id}/edit'.encode()
        assert expected_action in response.data, (
            f"Form action must point to /expenses/{expense_id}/edit"
        )

    def test_amount_field_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'name="amount"' in response.data, (
            "Form must contain an amount input field"
        )

    def test_category_select_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'name="category"' in response.data, (
            "Form must contain a category select field"
        )

    def test_all_seven_categories_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        for cat in VALID_CATEGORIES:
            assert cat.encode() in response.data, (
                f"Category option '{cat}' must be present in the select"
            )

    def test_date_field_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'name="date"' in response.data, (
            "Form must contain a date input field"
        )

    def test_date_field_type_is_date(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'type="date"' in response.data, (
            "Date input must be type='date'"
        )

    def test_description_field_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b'name="description"' in response.data, (
            "Form must contain a description input field"
        )

    def test_rupee_symbol_present(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert "₹".encode("utf-8") in response.data, (
            "Currency label must use ₹ (INR) — never $ or £"
        )

    def test_no_error_div_on_clean_get(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert b"auth-error" not in response.data, (
            "No error div must appear on a clean GET request"
        )


# ---------------------------------------------------------------------------
# 5. GET — ownership and non-existence guards
# ---------------------------------------------------------------------------

class TestGetOwnershipGuard:
    def test_other_users_expense_redirects_to_profile(self, two_user_client):
        """User 2 (logged in) tries to GET user 1's expense — must redirect to /profile."""
        client, _, _, expense_id = two_user_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert response.status_code == 302, (
            "Accessing another user's expense must result in a 302"
        )
        assert "/profile" in response.headers["Location"], (
            "Ownership violation on GET must redirect to /profile, not leak the form"
        )

    def test_other_users_expense_does_not_return_200(self, two_user_client):
        client, _, _, expense_id = two_user_client
        response = client.get(f"/expenses/{expense_id}/edit")
        assert response.status_code != 200, (
            "Accessing another user's expense must never return 200"
        )

    def test_nonexistent_expense_redirects_to_profile(self, auth_client):
        client, _, _ = auth_client
        non_existent_id = 999999
        response = client.get(f"/expenses/{non_existent_id}/edit")
        assert response.status_code == 302, (
            "GET for a non-existent expense id must redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Non-existent expense GET must redirect to /profile"
        )

    def test_nonexistent_expense_does_not_return_200(self, auth_client):
        client, _, _ = auth_client
        response = client.get("/expenses/999999/edit")
        assert response.status_code != 200, (
            "Non-existent expense id must never return 200"
        )


# ---------------------------------------------------------------------------
# 6. POST — happy path (valid update)
# ---------------------------------------------------------------------------

class TestPostHappyPath:
    def test_valid_post_redirects_to_profile(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "750.00",
                "category": "Transport",
                "date": "2026-06-01",
                "description": "Cab ride",
            },
        )
        assert response.status_code == 302, (
            "Valid POST to edit must redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Valid POST must redirect to /profile"
        )

    def test_valid_post_updates_amount_in_db(self, auth_client):
        client, user_id, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "1234.56",
                "category": "Food",
                "date": "2026-05-10",
                "description": "Lunch",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT amount FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert abs(row["amount"] - 1234.56) < 0.001, (
            f"Updated amount must be 1234.56 in DB (got {row['amount']})"
        )

    def test_valid_post_updates_category_in_db(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Shopping",
                "date": "2026-05-10",
                "description": "Lunch",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT category FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert row["category"] == "Shopping", (
            f"Updated category must be 'Shopping' in DB (got '{row['category']}')"
        )

    def test_valid_post_updates_date_in_db(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Food",
                "date": "2026-07-15",
                "description": "Lunch",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT date FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert row["date"] == "2026-07-15", (
            f"Updated date must be '2026-07-15' in DB (got '{row['date']}')"
        )

    def test_valid_post_updates_description_in_db(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Food",
                "date": "2026-05-10",
                "description": "Edited description",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert row["description"] == "Edited description", (
            f"Updated description must be 'Edited description' in DB (got '{row['description']}')"
        )

    def test_valid_post_updated_amount_visible_on_profile(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "9876.50",
                "category": "Bills",
                "date": "2026-05-10",
                "description": "Utility",
            },
        )
        profile_response = client.get("/profile")
        assert b"9876" in profile_response.data, (
            "Updated amount (9876.50) must be visible in /profile recent transactions"
        )

    def test_valid_post_updated_category_visible_on_profile(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Health",
                "date": "2026-05-10",
                "description": "Clinic",
            },
        )
        profile_response = client.get("/profile")
        assert b"Health" in profile_response.data, (
            "Updated category 'Health' must be visible on /profile"
        )

    def test_valid_post_updated_date_visible_on_profile(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Food",
                "date": "2026-08-20",
                "description": "Dinner",
            },
        )
        profile_response = client.get("/profile")
        assert b"2026-08-20" in profile_response.data, (
            "Updated date '2026-08-20' must be visible on /profile"
        )

    def test_valid_post_without_description_succeeds(self, auth_client):
        """Description is optional — clearing it must not cause an error."""
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "300",
                "category": "Other",
                "date": "2026-06-01",
                "description": "",
            },
        )
        assert response.status_code == 302, (
            "Edit with empty description must still redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Clearing description must redirect to /profile"
        )


# ---------------------------------------------------------------------------
# 7. POST does NOT create a new row
# ---------------------------------------------------------------------------

class TestPostDoesNotCreateNewRow:
    def test_edit_does_not_increase_row_count(self, auth_client):
        """After a successful edit the total number of expenses must remain the same."""
        client, user_id, expense_id = auth_client

        conn = get_db()
        count_before = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()["cnt"]
        conn.close()

        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "600",
                "category": "Transport",
                "date": "2026-05-11",
                "description": "Updated",
            },
        )

        conn = get_db()
        count_after = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()["cnt"]
        conn.close()

        assert count_after == count_before, (
            f"Edit must not insert a new row (before={count_before}, after={count_after})"
        )

    def test_edit_preserves_original_expense_id(self, auth_client):
        """The expense row id must be the same before and after the edit."""
        client, user_id, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "600",
                "category": "Transport",
                "date": "2026-05-11",
                "description": "Updated",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT id FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert row is not None, (
            "The original expense row must still exist after the edit"
        )
        assert row["id"] == expense_id, (
            "The expense row id must not change after an edit"
        )


# ---------------------------------------------------------------------------
# 8. POST — validation errors: amount
# ---------------------------------------------------------------------------

class TestPostValidationAmount:
    def test_blank_amount_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "", "category": "Food", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Blank amount must re-render form (200)"
        assert b"auth-error" in response.data, "Blank amount must produce an error message"

    def test_zero_amount_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "0", "category": "Food", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Zero amount must re-render form (200)"
        assert b"auth-error" in response.data, "Zero amount must produce an error message"

    def test_negative_amount_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "-50", "category": "Food", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Negative amount must re-render form (200)"
        assert b"auth-error" in response.data, "Negative amount must produce an error message"

    def test_nonnumeric_amount_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "abc", "category": "Food", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Non-numeric amount must re-render form (200)"
        assert b"auth-error" in response.data, "Non-numeric amount must produce an error message"

    @pytest.mark.parametrize("bad_amount", [
        "",        # blank
        "0",       # zero
        "-1",      # negative
        "0.00",    # zero as decimal
        "-0.01",   # tiny negative
        "abc",     # non-numeric
        " ",       # whitespace only
        "1e999",   # extreme scientific notation
    ])
    def test_invalid_amount_parametrized(self, auth_client, bad_amount):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-05-10",
                "description": "Test",
            },
        )
        assert response.status_code == 200, (
            f"Amount '{bad_amount}' must be rejected with a 200 re-render"
        )

    def test_invalid_amount_does_not_mutate_db(self, auth_client):
        """When amount is invalid, the existing expense must not be changed."""
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "0", "category": "Bills", "date": "2026-05-10", "description": "X"},
        )
        conn = get_db()
        row = conn.execute("SELECT amount FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
        assert abs(row["amount"] - 500.00) < 0.001, (
            "Invalid amount POST must not change the stored amount (still 500.00)"
        )

    def test_invalid_amount_form_retains_category(self, auth_client):
        """Other submitted fields must survive an amount validation failure."""
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "0",
                "category": "Entertainment",
                "date": "2026-09-01",
                "description": "Concert",
            },
        )
        assert b"Entertainment" in response.data, (
            "Submitted category 'Entertainment' must be re-populated on amount error"
        )

    def test_invalid_amount_form_retains_date(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "-10",
                "category": "Food",
                "date": "2026-11-11",
                "description": "",
            },
        )
        assert b"2026-11-11" in response.data, (
            "Submitted date must be re-populated on amount validation error"
        )

    def test_invalid_amount_form_retains_description(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "",
                "category": "Food",
                "date": "2026-05-10",
                "description": "My special note",
            },
        )
        assert b"My special note" in response.data, (
            "Submitted description must be re-populated on amount validation error"
        )


# ---------------------------------------------------------------------------
# 9. POST — validation errors: category
# ---------------------------------------------------------------------------

class TestPostValidationCategory:
    def test_invalid_category_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Gambling", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Invalid category must re-render form (200)"
        assert b"auth-error" in response.data, "Invalid category must produce an error message"

    def test_missing_category_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "", "date": "2026-05-10", "description": ""},
        )
        assert response.status_code == 200, "Missing category must re-render form (200)"
        assert b"auth-error" in response.data, "Missing category must produce an error message"

    @pytest.mark.parametrize("bad_category", [
        "",
        "Nonsense",
        "food",           # wrong capitalisation
        "FOOD",
        "Food ",          # trailing space
        " Food",          # leading space
        "food; DROP TABLE expenses;",
    ])
    def test_invalid_category_parametrized(self, auth_client, bad_category):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": bad_category,
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            f"Category '{bad_category}' must be rejected with a 200 re-render"
        )

    def test_invalid_category_does_not_mutate_db(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Luxury", "date": "2026-05-10", "description": ""},
        )
        conn = get_db()
        row = conn.execute("SELECT category FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
        assert row["category"] == "Food", (
            "Invalid category POST must not change the stored category (still 'Food')"
        )

    def test_invalid_category_form_retains_amount(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "750.25",
                "category": "NotACategory",
                "date": "2026-05-10",
                "description": "Test",
            },
        )
        assert b"750.25" in response.data, (
            "Submitted amount must be re-populated on category validation error"
        )


# ---------------------------------------------------------------------------
# 10. POST — validation errors: date
# ---------------------------------------------------------------------------

class TestPostValidationDate:
    def test_invalid_date_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Food", "date": "not-a-date", "description": ""},
        )
        assert response.status_code == 200, "Invalid date must re-render form (200)"
        assert b"auth-error" in response.data, "Invalid date must produce an error message"

    def test_missing_date_returns_200_with_error(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Food", "date": "", "description": ""},
        )
        assert response.status_code == 200, "Missing date must re-render form (200)"
        assert b"auth-error" in response.data, "Missing date must produce an error message"

    def test_date_wrong_format_ddmmyyyy_rejected(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Food", "date": "10-05-2026", "description": ""},
        )
        assert response.status_code == 200, "DD-MM-YYYY format must be rejected (200)"
        assert b"auth-error" in response.data, "Wrong-format date must show error message"

    @pytest.mark.parametrize("bad_date", [
        "",
        "not-a-date",
        "10-05-2026",      # DD-MM-YYYY
        "2026/05/10",      # slashes
        "2026-13-01",      # month 13
        "2026-00-15",      # month 00
        "abcd-ef-gh",
        "20260510",        # no separators
    ])
    def test_invalid_date_parametrized(self, auth_client, bad_date):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Food",
                "date": bad_date,
                "description": "",
            },
        )
        assert response.status_code == 200, (
            f"Date '{bad_date}' must be rejected with a 200 re-render"
        )

    def test_invalid_date_does_not_mutate_db(self, auth_client):
        client, _, expense_id = auth_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={"amount": "500", "category": "Food", "date": "bad-date", "description": ""},
        )
        conn = get_db()
        row = conn.execute("SELECT date FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        conn.close()
        assert row["date"] == "2026-05-10", (
            "Invalid date POST must not change the stored date (still '2026-05-10')"
        )

    def test_invalid_date_form_retains_description(self, auth_client):
        client, _, expense_id = auth_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "500",
                "category": "Food",
                "date": "not-a-date",
                "description": "Retained note",
            },
        )
        assert b"Retained note" in response.data, (
            "Submitted description must be re-populated on date validation error"
        )


# ---------------------------------------------------------------------------
# 11. POST — ownership enforcement
# ---------------------------------------------------------------------------

class TestPostOwnershipEnforcement:
    def test_other_users_post_redirects_to_profile(self, two_user_client):
        """User 2 (logged in) crafts a POST to user 1's expense — must redirect to /profile."""
        client, _, _, expense_id = two_user_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "Hijacked",
            },
        )
        assert response.status_code == 302, (
            "POST to another user's expense must redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Ownership violation on POST must redirect to /profile"
        )

    def test_other_users_post_does_not_mutate_db(self, two_user_client):
        """User 2's POST must not change user 1's expense in the database."""
        client, _, _, expense_id = two_user_client
        client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "Hijacked",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT amount, description FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
        conn.close()
        assert abs(row["amount"] - 750.00) < 0.001, (
            "Cross-user POST must not change the stored amount (still 750.00)"
        )
        assert row["description"] != "Hijacked", (
            "Cross-user POST must not change the stored description"
        )

    def test_other_users_post_does_not_return_200(self, two_user_client):
        client, _, _, expense_id = two_user_client
        response = client.post(
            f"/expenses/{expense_id}/edit",
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2026-01-01",
                "description": "Hijacked",
            },
        )
        assert response.status_code != 200, (
            "Ownership violation on POST must never return 200"
        )


# ---------------------------------------------------------------------------
# 12. Profile page — Edit links
# ---------------------------------------------------------------------------

class TestProfileEditLinks:
    def test_profile_shows_actions_column_header(self, auth_client):
        client, _, _ = auth_client
        response = client.get("/profile")
        assert b"Actions" in response.data, (
            "Recent Transactions table must have an 'Actions' column header"
        )

    def test_profile_shows_edit_link_text(self, auth_client):
        client, _, _ = auth_client
        response = client.get("/profile")
        assert b"Edit" in response.data, (
            "Each expense row in the Recent Transactions table must have an 'Edit' link"
        )

    def test_profile_edit_link_href_contains_expense_id(self, auth_client):
        client, _, expense_id = auth_client
        response = client.get("/profile")
        expected_href = f'/expenses/{expense_id}/edit'.encode()
        assert expected_href in response.data, (
            f"Edit link must href to /expenses/{expense_id}/edit"
        )

    def test_profile_edit_link_href_contains_edit_segment(self, auth_client):
        """href must include the /edit segment, not just the expense id."""
        client, _, expense_id = auth_client
        response = client.get("/profile")
        assert b"/edit" in response.data, (
            "Edit link href must include the '/edit' path segment"
        )

    def test_profile_multiple_expenses_all_have_edit_links(self, app, client):
        """When a user has multiple expenses, every row must render an Edit link."""
        conn = get_db()
        user_id = _insert_user(conn, "Multi User", "multi@example.com", "pass123")
        ids = []
        for i in range(3):
            eid = _insert_expense(
                conn, user_id, 100 * (i + 1), "Food", f"2026-0{i+1}-10", f"Expense {i}"
            )
            ids.append(eid)
        conn.close()

        _login(client, "multi@example.com", "pass123")
        response = client.get("/profile")
        data = response.data
        for eid in ids:
            expected = f'/expenses/{eid}/edit'.encode()
            assert expected in data, (
                f"Edit link for expense id={eid} must appear on /profile"
            )

    def test_profile_edit_links_absent_when_no_expenses(self, app, client):
        """A user with no expenses must see no Edit link and no Actions header in the table body."""
        conn = get_db()
        _insert_user(conn, "Empty User", "empty@example.com", "pass456")
        conn.close()

        _login(client, "empty@example.com", "pass456")
        response = client.get("/profile")
        # The profile shows "No transactions yet." message; no Edit link should appear.
        assert b"No transactions yet." in response.data, (
            "Profile must show empty state message when user has no expenses"
        )
        # No /edit href should be present in the response body.
        assert b"/edit" not in response.data, (
            "No Edit links should appear when there are no expenses"
        )
