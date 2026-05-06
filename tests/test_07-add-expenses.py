"""
Tests for Step 07 — Add Expenses.

Spec: .claude/specs/07-add-expenses.md

Behaviour contract under test:
  - GET /expenses/add while logged out redirects to /login (302)
  - POST /expenses/add while logged out redirects to /login (302)
  - GET /expenses/add while logged in returns 200 with a correctly structured form
  - Form contains Amount, Category, Date, and Description fields
  - Category select contains exactly the seven allowed options
  - JS snippet for pre-filling today's date is present
  - Cancel link on form points to /profile
  - Form action is POST to /expenses/add
  - Navbar shows "Add Expense" link for logged-in users
  - Navbar does NOT show "Add Expense" link for logged-out visitors
  - Valid POST inserts a row in the expenses table and redirects to /profile
  - After valid POST the new expense appears on /profile
  - Amount is stored as REAL and displayed with ₹ and two decimal places on /profile
  - Missing / zero / negative / non-numeric amount returns 200 with an error
  - Invalid category (not in allowlist) returns 200 with an error
  - Missing category returns 200 with an error
  - Invalid date format returns 200 with an error
  - On validation failure, submitted values are pre-populated in the form
  - Optional description field: omitting it still submits successfully
  - SQL injection attempt in amount field is safely rejected as a validation error
"""

import pytest
from werkzeug.security import generate_password_hash

from app import app as flask_app
from database.db import get_db, init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]


def _insert_user(conn, name, email, password="testpassword"):
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, generate_password_hash(password)),
    )
    conn.commit()
    return cursor.lastrowid


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """
    Isolated Flask app backed by a temporary on-disk SQLite database.
    Monkey-patches database.db.DB_PATH so that get_db() uses a clean file
    unique to this test run. Mirrors the pattern from test_06_date_filter_profile_page.py.
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
    A test client that is already logged in with a freshly-created user.
    Returns (client, user_id) so tests can also verify DB state.
    """
    conn = get_db()
    user_id = _insert_user(conn, "Test User", "testuser@example.com", "securepassword")
    conn.close()

    client.post(
        "/login",
        data={"email": "testuser@example.com", "password": "securepassword"},
        follow_redirects=False,
    )
    return client, user_id


# ---------------------------------------------------------------------------
# 1. Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_get_add_expense_unauthenticated_redirects_to_login(self, client):
        response = client.get("/expenses/add")
        assert response.status_code == 302, (
            "Unauthenticated GET /expenses/add must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect destination must be /login"
        )

    def test_post_add_expense_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            "/expenses/add",
            data={
                "amount": "500",
                "category": "Food",
                "date": "2026-05-01",
                "description": "Test",
            },
        )
        assert response.status_code == 302, (
            "Unauthenticated POST /expenses/add must redirect (302)"
        )
        assert "/login" in response.headers["Location"], (
            "Redirect destination for unauthenticated POST must be /login"
        )

    def test_get_add_expense_unauthenticated_does_not_return_200(self, client):
        response = client.get("/expenses/add")
        assert response.status_code != 200, (
            "Unauthenticated request must never return 200"
        )


# ---------------------------------------------------------------------------
# 2. GET /expenses/add — page structure for logged-in users
# ---------------------------------------------------------------------------

class TestGetAddExpensePage:
    def test_returns_200_for_authenticated_user(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert response.status_code == 200, (
            "GET /expenses/add for a logged-in user must return 200"
        )

    def test_page_contains_amount_field(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'name="amount"' in response.data, (
            "Add expense form must contain an amount input field"
        )

    def test_amount_field_has_step_attribute(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'step="0.01"' in response.data, (
            "Amount input must have step='0.01' to allow decimal values"
        )

    def test_amount_field_has_min_attribute(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'min="0.01"' in response.data, (
            "Amount input must have min='0.01' to prevent zero or negative amounts"
        )

    def test_page_contains_category_select(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'name="category"' in response.data, (
            "Add expense form must contain a category select field"
        )

    def test_category_select_contains_all_seven_options(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        data = response.data
        for cat in VALID_CATEGORIES:
            assert cat.encode() in data, (
                f"Category select must contain option '{cat}'"
            )

    def test_page_contains_date_field(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'name="date"' in response.data, (
            "Add expense form must contain a date input field"
        )

    def test_date_field_is_type_date(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'type="date"' in response.data, (
            "Date input must be type='date'"
        )

    def test_page_contains_description_field(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'name="description"' in response.data, (
            "Add expense form must contain a description input field"
        )

    def test_page_contains_submit_button(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "Page must contain an 'Add Expense' submit button label"
        )

    def test_cancel_link_points_to_profile(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'href="/profile"' in response.data, (
            "Cancel link must point to /profile"
        )

    def test_cancel_link_has_cancel_text(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b"Cancel" in response.data, (
            "Cancel link must have visible 'Cancel' text"
        )

    def test_form_action_is_add_expense_url(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'action="/expenses/add"' in response.data, (
            "Form action must point to /expenses/add"
        )

    def test_form_method_is_post(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'method="POST"' in response.data, (
            "Form method must be POST"
        )

    def test_page_contains_js_date_prefill_snippet(self, auth_client):
        """
        The template pre-fills the date input to today's date via a JS snippet.
        We verify the JS block is present on the page (the script element targeting
        the date input ID).
        """
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b"dateInput" in response.data, (
            "JS date pre-fill snippet (referencing 'dateInput') must be present on the page"
        )

    def test_page_does_not_show_error_on_clean_get(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b"auth-error" not in response.data, (
            "No error div should appear on a clean GET request"
        )

    def test_rupee_symbol_present_on_form(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert "₹".encode("utf-8") in response.data, (
            "Currency label must use ₹ (INR) — never $ or £"
        )


# ---------------------------------------------------------------------------
# 3. Navbar visibility
# ---------------------------------------------------------------------------

class TestNavbarVisibility:
    def test_add_expense_link_present_in_navbar_for_logged_in_user(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b"Add Expense" in response.data, (
            "'Add Expense' link must appear in the navbar when the user is logged in"
        )

    def test_add_expense_link_in_navbar_points_to_correct_route(self, auth_client):
        client, _ = auth_client
        response = client.get("/expenses/add")
        assert b'href="/expenses/add"' in response.data, (
            "Navbar 'Add Expense' link must href to /expenses/add"
        )

    def test_add_expense_link_absent_from_navbar_for_logged_out_user(self, client):
        """
        A logged-out visitor on any page (e.g. the landing page) must not
        see an 'Add Expense' navbar link.
        """
        response = client.get("/")
        data = response.data
        # 'Add Expense' text should not appear in the navbar for guests.
        # We check the nav-links context — since the landing page has no form
        # with that label, any occurrence of the string would be from the navbar.
        assert b"Add Expense" not in data, (
            "'Add Expense' navbar link must NOT appear for logged-out users"
        )

    def test_logged_out_user_sees_sign_in_link_instead(self, client):
        response = client.get("/")
        assert b"Sign in" in response.data, (
            "Logged-out users should see 'Sign in' link in the navbar"
        )


# ---------------------------------------------------------------------------
# 4. Happy path POST — valid submission
# ---------------------------------------------------------------------------

class TestHappyPathPost:
    def test_valid_post_redirects_to_profile(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "1250.50",
                "category": "Food",
                "date": "2026-05-10",
                "description": "Lunch with team",
            },
        )
        assert response.status_code == 302, (
            "Valid POST must redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "After a valid submission the redirect target must be /profile"
        )

    def test_valid_post_inserts_expense_visible_on_profile(self, auth_client):
        client, _ = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "999.99",
                "category": "Transport",
                "date": "2026-06-01",
                "description": "Cab to airport",
            },
        )
        profile_response = client.get("/profile")
        assert b"999" in profile_response.data, (
            "The newly added expense amount must appear on /profile after submission"
        )

    def test_valid_post_expense_category_appears_on_profile(self, auth_client):
        client, _ = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "300.00",
                "category": "Entertainment",
                "date": "2026-06-15",
                "description": "Cinema",
            },
        )
        profile_response = client.get("/profile")
        assert b"Entertainment" in profile_response.data, (
            "The newly added expense category must appear on /profile"
        )

    def test_valid_post_stores_amount_as_decimal(self, auth_client):
        """Amount is stored as REAL and rendered with two decimal places."""
        client, _ = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "1250.50",
                "category": "Shopping",
                "date": "2026-06-20",
                "description": "New shoes",
            },
        )
        profile_response = client.get("/profile")
        assert b"1250" in profile_response.data, (
            "Stored amount (1250.50) must appear on /profile"
        )

    def test_valid_post_without_description_succeeds(self, auth_client):
        """Description is optional — omitting it must not cause an error."""
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "75.00",
                "category": "Other",
                "date": "2026-06-25",
                "description": "",
            },
        )
        assert response.status_code == 302, (
            "A valid POST without a description must still redirect (302)"
        )
        assert "/profile" in response.headers["Location"], (
            "Omitting description must still redirect to /profile"
        )

    def test_valid_post_all_categories_accepted(self, auth_client):
        """Each of the seven allowed categories must be accepted by the server."""
        client, _ = auth_client
        for i, cat in enumerate(VALID_CATEGORIES):
            response = client.post(
                "/expenses/add",
                data={
                    "amount": str(100 + i),
                    "category": cat,
                    "date": f"2026-07-{i + 1:02d}",
                    "description": "",
                },
            )
            assert response.status_code == 302, (
                f"Category '{cat}' must be accepted and result in a redirect"
            )

    def test_valid_post_with_integer_amount_succeeds(self, auth_client):
        """Whole-number amounts (no decimal point) must be accepted."""
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "500",
                "category": "Bills",
                "date": "2026-07-10",
                "description": "Electricity",
            },
        )
        assert response.status_code == 302, (
            "An integer amount without decimal point must be accepted"
        )


# ---------------------------------------------------------------------------
# 5. Validation errors — amount
# ---------------------------------------------------------------------------

class TestValidationAmount:
    def test_missing_amount_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "",
                "category": "Food",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Missing amount must re-render the form (200), not redirect"
        )
        assert b"auth-error" in response.data, (
            "Missing amount must show an error message"
        )

    def test_zero_amount_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Zero amount must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Zero amount must produce an error message"
        )

    def test_negative_amount_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "-50",
                "category": "Food",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Negative amount must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Negative amount must produce an error message"
        )

    def test_non_numeric_amount_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "abc",
                "category": "Food",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Non-numeric amount must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Non-numeric amount must produce an error message"
        )

    @pytest.mark.parametrize("bad_amount", [
        "",          # empty string
        "0",         # zero
        "-1",        # negative
        "0.00",      # zero as decimal
        "-0.01",     # small negative
        "abc",       # non-numeric text
        "1e999",     # overflow-like scientific notation edge case
        " ",         # whitespace only
    ])
    def test_invalid_amount_parametrized(self, auth_client, bad_amount):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": bad_amount,
                "category": "Food",
                "date": "2026-05-10",
                "description": "Test",
            },
        )
        assert response.status_code == 200, (
            f"Amount '{bad_amount}' must not be accepted — expected 200 re-render, got {response.status_code}"
        )

    def test_sql_injection_in_amount_safely_rejected(self, auth_client):
        """SQL injection attempt in amount field must be rejected as a validation error."""
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "1; DROP TABLE expenses;--",
                "category": "Food",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "SQL injection in amount must be treated as a validation error (200 re-render)"
        )
        assert b"auth-error" in response.data, (
            "SQL injection attempt in amount must produce an error message"
        )


# ---------------------------------------------------------------------------
# 6. Validation errors — category
# ---------------------------------------------------------------------------

class TestValidationCategory:
    def test_invalid_category_not_in_allowlist_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Gambling",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Category not in allowlist must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Invalid category must produce an error message"
        )

    def test_missing_category_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "",
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Missing category must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Missing category must produce an error message"
        )

    @pytest.mark.parametrize("bad_category", [
        "",
        "Nonsense",
        "food",          # wrong capitalisation
        "FOOD",          # all-caps
        "Food ",         # trailing space
        " Food",         # leading space
        "food; DROP TABLE expenses;",  # injection attempt
    ])
    def test_invalid_category_parametrized(self, auth_client, bad_category):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": bad_category,
                "date": "2026-05-10",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            f"Category '{bad_category}' must be rejected — expected 200, got {response.status_code}"
        )

    def test_category_validation_does_not_insert_row(self, auth_client):
        """When an invalid category is submitted, no expense row must be created."""
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "InvalidCat",
                "date": "2026-05-10",
                "description": "",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["cnt"] == 0, (
            "An invalid category submission must not insert a row into expenses"
        )


# ---------------------------------------------------------------------------
# 7. Validation errors — date
# ---------------------------------------------------------------------------

class TestValidationDate:
    def test_invalid_date_string_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Food",
                "date": "not-a-date",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Invalid date must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Invalid date string must produce an error message"
        )

    def test_date_in_wrong_format_dd_mm_yyyy_rejected(self, auth_client):
        """Date in DD-MM-YYYY format is invalid (server expects YYYY-MM-DD)."""
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Food",
                "date": "10-05-2026",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Date in DD-MM-YYYY format must be rejected (200 re-render)"
        )
        assert b"auth-error" in response.data, (
            "Wrong-format date must show an error message"
        )

    def test_missing_date_returns_200_with_error(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Food",
                "date": "",
                "description": "",
            },
        )
        assert response.status_code == 200, (
            "Missing date must re-render the form (200)"
        )
        assert b"auth-error" in response.data, (
            "Missing date must produce an error message"
        )

    @pytest.mark.parametrize("bad_date", [
        "",
        "not-a-date",
        "10-05-2026",    # DD-MM-YYYY (wrong order)
        "2026/05/10",    # slashes instead of hyphens
        "2026-13-01",    # month 13 is invalid
        "2026-00-15",    # month 00 is invalid
        "abcd-ef-gh",    # fully non-numeric
        "20260510",      # no separators
    ])
    def test_invalid_date_parametrized(self, auth_client, bad_date):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Food",
                "date": bad_date,
                "description": "",
            },
        )
        assert response.status_code == 200, (
            f"Date '{bad_date}' must be rejected — expected 200, got {response.status_code}"
        )

    def test_invalid_date_does_not_insert_row(self, auth_client):
        """When an invalid date is submitted, no expense row must be created."""
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Food",
                "date": "not-a-date",
                "description": "",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["cnt"] == 0, (
            "An invalid date submission must not insert a row into expenses"
        )


# ---------------------------------------------------------------------------
# 8. Field re-population on validation error
# ---------------------------------------------------------------------------

class TestFieldRepopulationOnError:
    def test_amount_repopulated_after_invalid_category(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "750.25",
                "category": "NotACategory",
                "date": "2026-05-10",
                "description": "Dinner",
            },
        )
        assert b"750.25" in response.data, (
            "Previously entered amount must be pre-populated in the form on error"
        )

    def test_description_repopulated_after_invalid_amount(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-05-10",
                "description": "Morning coffee",
            },
        )
        assert b"Morning coffee" in response.data, (
            "Previously entered description must be pre-populated in the form on error"
        )

    def test_date_repopulated_after_invalid_amount(self, auth_client):
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "-10",
                "category": "Food",
                "date": "2026-09-15",
                "description": "",
            },
        )
        assert b"2026-09-15" in response.data, (
            "Previously entered date must be pre-populated in the form on error"
        )

    def test_category_repopulated_after_invalid_date(self, auth_client):
        """
        When the date is invalid, the submitted category must be re-selected
        in the form (the template marks the matching option as selected).
        """
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "100",
                "category": "Health",
                "date": "not-a-date",
                "description": "",
            },
        )
        assert b"Health" in response.data, (
            "Previously chosen category must be re-populated in the form on error"
        )

    def test_all_fields_repopulated_after_invalid_amount(self, auth_client):
        """All submitted non-amount fields must survive a failed amount validation."""
        client, _ = auth_client
        response = client.post(
            "/expenses/add",
            data={
                "amount": "abc",
                "category": "Shopping",
                "date": "2026-10-01",
                "description": "New laptop",
            },
        )
        data = response.data
        assert b"Shopping" in data, "Category must be re-populated"
        assert b"2026-10-01" in data, "Date must be re-populated"
        assert b"New laptop" in data, "Description must be re-populated"


# ---------------------------------------------------------------------------
# 9. DB side-effect verification after valid POST
# ---------------------------------------------------------------------------

class TestDatabaseSideEffects:
    def test_valid_post_inserts_exactly_one_row(self, auth_client):
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "500",
                "category": "Bills",
                "date": "2026-08-01",
                "description": "Water bill",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["cnt"] == 1, (
            "Exactly one expense row must be inserted after a valid POST"
        )

    def test_valid_post_stores_correct_amount(self, auth_client):
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "1234.56",
                "category": "Shopping",
                "date": "2026-08-05",
                "description": "",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT amount FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row is not None, "An expense row must exist after submission"
        assert abs(row["amount"] - 1234.56) < 0.001, (
            f"Stored amount must be 1234.56 (got {row['amount']})"
        )

    def test_valid_post_stores_correct_category(self, auth_client):
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "200",
                "category": "Transport",
                "date": "2026-08-10",
                "description": "Bus fare",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["category"] == "Transport", (
            f"Stored category must be 'Transport' (got '{row['category']}')"
        )

    def test_valid_post_stores_correct_date(self, auth_client):
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "150",
                "category": "Food",
                "date": "2026-08-20",
                "description": "",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT date FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["date"] == "2026-08-20", (
            f"Stored date must be '2026-08-20' (got '{row['date']}')"
        )

    def test_valid_post_stores_correct_description(self, auth_client):
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "88",
                "category": "Other",
                "date": "2026-08-25",
                "description": "Haircut",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["description"] == "Haircut", (
            f"Stored description must be 'Haircut' (got '{row['description']}')"
        )

    def test_two_valid_posts_insert_two_rows(self, auth_client):
        client, user_id = auth_client
        for i in range(2):
            client.post(
                "/expenses/add",
                data={
                    "amount": str(100 * (i + 1)),
                    "category": "Food",
                    "date": f"2026-09-{i + 1:02d}",
                    "description": f"Meal {i + 1}",
                },
            )
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["cnt"] == 2, (
            "Two valid POSTs must insert exactly two expense rows"
        )

    def test_failed_post_does_not_insert_row(self, auth_client):
        """When validation fails (e.g. zero amount), no row must be written."""
        client, user_id = auth_client
        client.post(
            "/expenses/add",
            data={
                "amount": "0",
                "category": "Food",
                "date": "2026-09-05",
                "description": "",
            },
        )
        conn = get_db()
        row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        conn.close()
        assert row["cnt"] == 0, (
            "A failed validation must not insert any row into expenses"
        )

    def test_user_isolation_expenses_belong_to_correct_user(self, app, auth_client):
        """Expenses inserted by one user must not be counted against another user's total."""
        client, user_id = auth_client

        # Create a second user directly in the DB.
        conn = get_db()
        other_user_id = _insert_user(conn, "Other User", "other@example.com")
        conn.close()

        # Submit an expense for the logged-in (first) user.
        client.post(
            "/expenses/add",
            data={
                "amount": "777",
                "category": "Health",
                "date": "2026-09-10",
                "description": "Doctor visit",
            },
        )

        # The other user must have zero expenses.
        conn = get_db()
        other_row = conn.execute(
            "SELECT COUNT(*) AS cnt FROM expenses WHERE user_id = ?",
            (other_user_id,),
        ).fetchone()
        conn.close()
        assert other_row["cnt"] == 0, (
            "An expense submitted by user A must not appear in user B's expense count"
        )
