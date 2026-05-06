# Spec: Add Expenses

## Overview
Step 7 turns the placeholder `GET /expenses/add` route into a working two-method
route that lets a logged-in user record a new expense. A dedicated form page
collects the amount, category, date, and an optional description. On valid
submission the expense is persisted to the `expenses` table and the user is
redirected to their profile, where the new entry immediately appears in the
recent transactions list. This is the first write operation on the `expenses`
table from the web UI.

## Depends on
- Step 1: Database setup (`expenses` table in `database/db.py`)
- Step 3: Login / Logout (`session["user_id"]` set on login, auth guard pattern)
- Step 4 / 5: Profile page (destination after a successful add)

## Routes
- `GET  /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert a new expense, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

A new helper function is needed in `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` — inserts one
  row into `expenses` and returns the new `id`.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - A centred form card (reuse `.auth-card` width or a new `.expense-form-card`)
  - Fields:
    - **Amount** — `<input type="number" name="amount" step="0.01" min="0.01" required>`
    - **Category** — `<select name="category" required>` with options: Food, Transport,
      Bills, Health, Entertainment, Shopping, Other
    - **Date** — `<input type="date" name="date" required>` (pre-filled to today via JS)
    - **Description** — `<input type="text" name="description">` (optional, max 200 chars)
  - A submit button ("Add Expense") and a cancel link back to `/profile`
  - If `error` is passed, render an `.auth-error` div (same pattern as login/register)
  - The form `action` points to `/expenses/add`, `method="POST"`

- **Modify:** `templates/base.html`
  - Add an "Add Expense" link in the navbar (visible only when logged in) that
    points to `url_for('add_expense')`. Place it before the profile/logout links.

## Files to change
- `app.py`
  - Replace the single-method `add_expense` stub with a two-method route:
    ```
    @app.route("/expenses/add", methods=["GET", "POST"])
    def add_expense():
    ```
  - `GET`: guard with `session.get("user_id")` (redirect to `/login` if missing),
    then `render_template("add_expense.html")`.
  - `POST`: guard session, then:
    1. Read `amount`, `category`, `date`, `description` from `request.form`.
    2. Validate: amount must be a positive number; category must be one of the
       seven allowed values; date must be a valid `YYYY-MM-DD` string.
    3. On validation failure: re-render the form with `error=` and the submitted
       values so the user does not have to retype everything.
    4. On success: call `create_expense(...)`, then `redirect(url_for("profile"))`.
  - Add `create_expense` to the import line from `database.db`.

- `database/db.py`
  - Add `create_expense(user_id, amount, category, date, description)`:
    - Parameterised `INSERT INTO expenses (user_id, amount, category, date, description)
      VALUES (?, ?, ?, ?, ?)`.
    - Returns `cursor.lastrowid`.
    - Uses `try/finally` for connection cleanup (same pattern as `create_user`).

- `templates/base.html`
  - Inside the `{% if session.user_id %}` block in the navbar, add a link to
    `url_for('add_expense')` labelled "Add Expense" before the existing profile /
    logout links.

- `static/css/style.css`
  - Add styles for the add-expense form card. Reuse existing design-system tokens.
  - Suggested class names to append in a new `/* Add Expense */` section:
    - `.expense-form-section` — full-height centred wrapper (mirror `.auth-section`)
    - `.expense-form-card` — card container (max-width ~560px, same card style as
      profile cards)
    - `.expense-form-title` — heading inside the card
    - `.expense-form-group` — label + input column wrapper (mirrors auth form groups)
    - `.expense-form-actions` — flex row for submit button and cancel link

## Files to create
- `templates/add_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (not applicable here, but keep the import)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard on both GET and POST — any unauthenticated request redirects to `/login`
- Category must be validated server-side against the fixed allowlist (not just
  client-side) to prevent arbitrary categories being inserted
- `amount` must be cast to `float` after validation; never store the raw string
- Date must be validated with `datetime.strptime(date_str, "%Y-%m-%d")` — reject
  anything that doesn't parse
- On validation failure, re-render the form with the submitted values pre-filled
  so the user doesn't lose their input
- Currency must always display as ₹ — never £ or $
- Do not use `redirect(request.url)` after POST — always redirect to a named route
- Keep the `# Step 7` comment on the route in `app.py`

## Definition of done
- [ ] `GET /expenses/add` while logged out redirects to `/login`
- [ ] `GET /expenses/add` while logged in renders a form with Amount, Category,
      Date, and Description fields
- [ ] The Date field is pre-filled to today's date on page load
- [ ] Submitting the form with all valid fields inserts a row in `expenses` and
      redirects to `/profile`
- [ ] The newly added expense appears in the recent transactions list on `/profile`
- [ ] Submitting with a missing or zero amount shows an inline error without losing
      the other field values
- [ ] Submitting with an invalid category (e.g. via curl/Postman) is rejected with
      an error message
- [ ] Submitting with an invalid date (e.g. `date=not-a-date`) is rejected with an
      error message
- [ ] The navbar shows an "Add Expense" link for logged-in users only
- [ ] Clicking "Cancel" on the form returns to `/profile` without inserting anything
- [ ] Amounts are stored as `REAL` (e.g. 1250.50) and displayed with ₹ and two
      decimal places wherever shown
