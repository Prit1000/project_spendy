# Spec: Profile Page

## Overview
Implement the `/profile` route so logged-in users can view their account details and a
high-level spending summary. This is the first page that requires authentication — it
introduces the auth-guard pattern (redirect to `/login` if no session) that all future
protected routes will reuse. The page reads from both the `users` and `expenses` tables,
making it a practical bridge between auth (Steps 1–3) and expense CRUD (Steps 7–9).
The navbar's username span is also upgraded to a clickable link pointing to this route.

## Depends on
Step 01 — Database Setup (`users` and `expenses` tables must exist).
Step 03 — Login and Logout (session must be established; `session['user_id']` is the
lookup key).

## Routes
- `GET /profile` — render user profile and spending summary — logged-in only
  - Auth guard: if `session.get('user_id')` is falsy, `return redirect(url_for('login'))`
  - Fetch user row by `session['user_id']` via `get_user_by_id()`
  - Fetch spending summary via `get_expense_summary(user_id)`
  - Pass both to `render_template('profile.html', user=user, summary=summary)`

## Database changes
No new tables or columns. Two new query functions are needed in `database/db.py`:

1. `get_user_by_id(user_id)` — returns a single `sqlite3.Row` or `None`:
   ```python
   SELECT * FROM users WHERE id = ?
   ```

2. `get_expense_summary(user_id)` — returns a single row with `count` and `total`:
   ```python
   SELECT COUNT(*) AS count, COALESCE(SUM(amount), 0) AS total
   FROM expenses WHERE user_id = ?
   ```
   Use `COALESCE` so `total` is `0.0` (not `None`) for users with no expenses yet.

## Templates
- **Create:** `templates/profile.html`
  - Extends `base.html`
  - `{% block title %}Profile — Spendly{% endblock %}`
  - Two visual sections:
    1. **Account card** — display `user['name']`, `user['email']`,
       and `user['created_at']` (format the date string with Jinja's `strftime` filter
       or slice to `YYYY-MM-DD`)
    2. **Spending summary card** — display `summary['count']` (total expenses logged)
       and `summary['total']` formatted as INR (`₹{{ "%.2f"|format(summary['total']) }}`)
  - No forms — read-only display page
  - Use existing CSS variables and utility classes; do not add inline styles or new CSS

- **Modify:** `templates/base.html`
  - In the logged-in nav branch, convert the static `<span>{{ session.user_name }}</span>`
    into an anchor tag:
    ```html
    <a href="{{ url_for('profile') }}">{{ session.user_name }}</a>
    ```

## Files to change
- `app.py`
  - Import `get_user_by_id` and `get_expense_summary` from `database.db`
  - Replace the placeholder `/profile` route body with the auth guard + db queries +
    `render_template` call described in Routes
- `database/db.py`
  - Add `get_user_by_id(user_id)` function
  - Add `get_expense_summary(user_id)` function
- `templates/base.html`
  - Username span → profile link (see Templates section)

## Files to create
- `templates/profile.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()` only
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Passwords must never be displayed; do not pass `password_hash` to the template
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard is a simple early-return, not a decorator:
  ```python
  if not session.get("user_id"):
      return redirect(url_for("login"))
  ```
- Always close the DB connection using `try/finally` in each db function
- Format currency as INR (₹) with two decimal places
- Keep the educational step comment `# Step 4` on the `/profile` route in `app.py`

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in renders the profile page without errors
- [ ] The page displays the logged-in user's name, email, and member-since date
- [ ] The spending summary shows the correct count of expenses for that user
- [ ] The spending summary shows the correct total amount formatted as ₹X.XX
- [ ] A user with zero expenses sees ₹0.00 and count 0 (no crash or None displayed)
- [ ] The navbar username is now a clickable link that navigates to `/profile`
- [ ] The app starts without errors after changes to `app.py` and `database/db.py`
