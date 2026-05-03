# Spec: Login and Logout

## Overview
Wire up the login form so existing users can sign in with their email and password.
The `login.html` template, its `{% if error %}` block, and the `GET /login` route
are already in place; this step adds the POST handler, validates credentials against
the database, starts a Flask session on success, and redirects. The `GET /logout`
route was implemented early in Step 02 to unblock the navbar — no changes to it
are needed here. This step completes the full auth loop: register → login → logout.

## Depends on
- Step 01 — Database Setup (`users` table, `get_db()` must exist and work)
- Step 02 — Registration (`users` rows exist; session keys `user_id` / `user_name`
  already established as the convention)

## Routes
- `GET  /login` — render login form — public (already exists, no change to handler)
- `POST /login` — verify credentials, start session, redirect — public
- `GET  /logout` — already implemented in Step 02; no change required

## Database changes
No new tables or columns. Need one new helper function in `database/db.py`:

- `get_user_by_email(email)` — fetch a single `users` row by email using a
  parameterised query; return `None` if not found

## Templates
- **No change needed:** `templates/login.html` — form already has `method="POST"`
  and `action="/login"`; `{% if error %}` block already present
- **No change needed:** `templates/base.html` — session-aware nav was completed
  in Step 02

## Files to change
- `database/db.py` — add `get_user_by_email(email)`
- `app.py`
  - Import `check_password_hash` from `werkzeug.security`
  - Import `get_user_by_email` from `database.db`
  - Convert `GET /login` route to accept `GET, POST`
  - Implement POST handler (see Rules for implementation)

## Files to create
None.

## New dependencies
None. `werkzeug.security` is already installed as part of Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()` only
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Verify passwords with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Session keys to set on successful login (same convention as registration):
  - `session['user_id']` — the `id` column from the matched `users` row
  - `session['user_name']` — the `name` column from the matched `users` row
- Validation order for POST handler (stop at first failure, re-render with `error=`):
  1. Both email and password must be non-empty after `.strip()`
  2. A user with the given email must exist (`get_user_by_email` returns non-None)
  3. `check_password_hash(user['password_hash'], password)` must return `True`
  - Steps 2 and 3 must return the **same generic error message**
    ("Invalid email or password.") — never reveal which check failed
- On success: redirect to `url_for('landing')`
- Always close the DB connection in a `try/finally` block inside `get_user_by_email`
- If `session.get('user_id')` is already set when `GET /login` is requested,
  redirect to `url_for('landing')` instead of rendering the form

## Definition of done
- [ ] Submitting valid email + password sets `session['user_id']` and
      `session['user_name']` and redirects to the landing page
- [ ] The navbar shows the user's name and Logout link after successful login
- [ ] Submitting a non-existent email re-renders the form with "Invalid email or
      password." (no 500 error, no stack trace)
- [ ] Submitting a correct email but wrong password re-renders with the same
      "Invalid email or password." message
- [ ] Submitting with an empty email or empty password re-renders with an error
      (no crash, no DB query attempted)
- [ ] A user who is already logged in and visits `/login` is redirected to landing
- [ ] Clicking Logout still clears the session and returns to the landing page
      (regression check — must not break Step 02 behaviour)
- [ ] The demo user (`demo@spendly.com` / `demo123`) can log in successfully
- [ ] The app starts without errors after all changes to `app.py` and `database/db.py`
