# Spec: Edit Expenses

## Overview
Step 8 replaces the `GET /expenses/<id>/edit` placeholder with a fully working
edit flow. A logged-in user can click an "Edit" link next to any of their own
expenses on the profile page, see a pre-filled form identical in structure to
the add-expense form, modify any fields, and save the changes. The row in the
`expenses` table is updated in-place and the user is redirected back to the
profile. Ownership is enforced server-side — a user cannot edit another user's
expense. This is the first update operation on the `expenses` table from the
web UI.

## Depends on
- Step 1: Database setup (`expenses` table)
- Step 3: Login / Logout (`session["user_id"]` available, auth guard pattern)
- Step 4 / 5: Profile page (source of edit links, destination after save)
- Step 7: Add expense (establishes form conventions and CSS classes this step reuses)

## Routes
- `GET  /expenses/<int:id>/edit` — fetch the expense, verify ownership, render pre-filled form — logged-in only
- `POST /expenses/<int:id>/edit` — validate input, update the row, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. Two new helper functions are needed in `database/db.py`:

- `get_expense_by_id(expense_id)` — fetches a single row from `expenses` by
  `id`; returns `None` if not found. Used to pre-fill the edit form and to
  verify ownership.

- `update_expense(expense_id, amount, category, date, description)` — executes
  a parameterised `UPDATE expenses SET ... WHERE id = ?`; returns nothing.

## Templates
- **Create:** `templates/edit_expense.html`
  - Extends `base.html`.
  - Identical structure to `add_expense.html` — reuse the same CSS classes
    (`auth-section`, `auth-container`, `auth-header`, `auth-card`, `form-group`,
    `form-input`, `expense-form-actions`).
  - Title: "Edit Expense" / subtitle: "Update your spending entry".
  - All four fields (Amount, Category, Date, Description) pre-filled from the
    existing expense row passed in as `expense`.
  - Submit button label: "Save Changes"; cancel link returns to `/profile`.
  - If `error` is passed, render an `.auth-error` div (same pattern as
    login/register and add_expense).
  - The form `action` points to `url_for('edit_expense', id=expense['id'])`,
    `method="POST"`.

- **Modify:** `templates/profile.html`
  - In the Recent Transactions table, add an "Actions" column header after
    "Amount".
  - In each `<tr>` add a `<td>` containing an "Edit" link:
    `<a href="{{ url_for('edit_expense', id=exp['id']) }}">Edit</a>`
  - Style the link with a small utility class (e.g., `.txn-action-link`) —
    use existing CSS variables only.

## Files to change
- `app.py`
  - Replace the single-GET `edit_expense` stub with a two-method route:
    ```python
    @app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
    def edit_expense(id):
    ```
  - `GET`:
    1. Guard: `if not session.get("user_id"): return redirect(url_for("login"))`.
    2. Fetch: `expense = get_expense_by_id(id)`.
    3. Ownership check: if `expense` is `None` or
       `expense["user_id"] != session["user_id"]`, redirect to `url_for("profile")`.
    4. Render `edit_expense.html` passing `expense=expense` and
       `categories=EXPENSE_CATEGORIES`.
  - `POST`:
    1. Same session guard and ownership check as GET (re-fetch the expense; the
       id comes from the URL).
    2. Read `amount`, `category`, `date`, `description` from `request.form`.
    3. Validate with the same rules as `add_expense`:
       - `amount` → positive float, ≤ `MAX_AMOUNT`
       - `category` → must be in `EXPENSE_CATEGORIES`
       - `date` → valid `YYYY-MM-DD` via `datetime.strptime`
    4. On validation failure: re-render `edit_expense.html` with `error=` and
       submitted values (pass `expense=expense` to keep the form `action` URL
       correct, but override individual fields with submitted values).
    5. On success: call `update_expense(id, amount, category, date_str,
       description or None)`, then `redirect(url_for("profile"))`.
  - Add `get_expense_by_id` and `update_expense` to the import line from
    `database.db`.
  - Keep the `# Step 8` comment on the route.

- `database/db.py`
  - Add `get_expense_by_id(expense_id)`:
    ```python
    def get_expense_by_id(expense_id):
        conn = get_db()
        try:
            return conn.execute(
                "SELECT * FROM expenses WHERE id = ?", (expense_id,)
            ).fetchone()
        finally:
            conn.close()
    ```
  - Add `update_expense(expense_id, amount, category, date, description)`:
    ```python
    def update_expense(expense_id, amount, category, date, description):
        conn = get_db()
        try:
            conn.execute(
                "UPDATE expenses SET amount=?, category=?, date=?, description=? WHERE id=?",
                (amount, category, date, description, expense_id),
            )
            conn.commit()
        finally:
            conn.close()
    ```

- `templates/profile.html`
  - Add "Actions" `<th>` to the table header.
  - Add an Edit `<td>` with `.txn-action-link` anchor in each row.

- `static/css/style.css`
  - Add a minimal `.txn-action-link` rule (small font, uses `--accent` colour,
    no underline by default, underline on hover). No new section needed — append
    to the existing `/* Profile */` section.

## Files to create
- `templates/edit_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (not applicable here)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard on both GET and POST — unauthenticated requests redirect to `/login`
- Ownership check on both GET and POST — if the expense doesn't belong to
  `session["user_id"]`, redirect silently to `/profile` (no 404 leak)
- Category validated server-side against `EXPENSE_CATEGORIES`
- `amount` cast to `float` after validation; never store the raw string
- Date validated with `datetime.strptime(date_str, "%Y-%m-%d")`
- On validation failure, re-render the form with submitted values pre-filled
- Currency always displays as ₹ — never £ or $
- Do not use `redirect(request.url)` after POST — always redirect to a named route
- Keep the `# Step 8` comment on the route in `app.py`

## Definition of done
- [ ] `GET /expenses/<id>/edit` while logged out redirects to `/login`
- [ ] `GET /expenses/<id>/edit` for an expense that belongs to the current user
      renders a form pre-filled with that expense's amount, category, date, and
      description
- [ ] `GET /expenses/<id>/edit` for an expense that belongs to a different user
      redirects to `/profile` without showing the form
- [ ] `GET /expenses/<id>/edit` for a non-existent id redirects to `/profile`
- [ ] Submitting valid changes updates the row in the database and redirects to
      `/profile`, where the updated values are visible in the transactions table
- [ ] Submitting with an invalid amount shows an inline error; form retains the
      other submitted values
- [ ] Submitting with an invalid category (e.g. via curl/Postman) is rejected
      with an error message
- [ ] Submitting with an invalid date is rejected with an error message
- [ ] The Recent Transactions table on `/profile` shows an "Edit" link for each
      expense row
- [ ] Clicking "Cancel" on the edit form returns to `/profile` without changing
      the expense
- [ ] A user cannot edit another user's expense by crafting a direct POST request
