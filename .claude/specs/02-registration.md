# Spec: Registration

## Overview
Wire up the registration form so new users can create an account. The `register.html`
template and its POST action are already in place; this step adds the POST handler,
validates input, hashes the password, inserts the user into the `users` table, starts
a Flask session, and redirects on success. It also updates the navbar in `base.html`
to switch between guest links (Sign in / Get started) and a logged-in state (username
+ Logout) based on `session`.

## Depends on
Step 01 — Database Setup (`users` table, `get_db()`, and the `GET /` landing route
must exist and work).

## Routes
- `GET  /register` — render registration form — public (already exists, no change)
- `POST /register` — process form, create user, start session, redirect — public
- `GET  /logout`   — clear session, redirect to `url_for('landing')` — public
  - Implementation: call `session.clear()`, then `return redirect(url_for('landing'))`
  - Added in this step so the navbar Logout link is not broken

## Database changes
No new tables or columns. Relies on the `users` table from Step 01:
- `name TEXT NOT NULL`
- `email TEXT UNIQUE NOT NULL`
- `password_hash TEXT NOT NULL`

## Templates
- **Verify (no edit needed):** `templates/register.html` — confirm the `<form>` tag
  has `method="POST"` and `action="/register"` before starting. The template already
  renders the `{% if error %}` block. No further markup changes required.
- **Modify:** `templates/base.html` — update `<nav>` to branch on `session`:
  - Guest (no `user_id` in session): show "Sign in" and "Get started" links
  - Logged-in (`session.user_name` exists): show the user's name as a non-clickable
    `<span>` and a "Logout" link pointing to `url_for('logout')`
  - Note: `/profile` is intentionally not linked in this step — that route does not
    exist yet and will be added later

## Files to change
- `app.py`
  - Add `request`, `redirect`, `url_for`, `session` to the Flask import
  - Set `app.secret_key` (hard-coded dev string; must be changed for production)
  - Convert the existing `GET /register` route to accept `GET, POST`
  - Implement POST handler logic (see Rules for implementation)
  - Add `GET /logout` route (see Routes section above)
- `templates/base.html` — nav session branch described above

## Files to create
None.

## New dependencies
None. `werkzeug.security` is already installed as part of Flask.

## Rules for implementation
- No SQLAlchemy or ORMs — use `sqlite3` via `get_db()` only
- Parameterised queries only — never use f-strings or `%` formatting in SQL
- Hash passwords with `werkzeug.security.generate_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Secret key: set `app.secret_key = "dev-secret-change-in-production"` directly in
  `app.py` (simple hard-coded string is fine for this educational stage)
- Session keys to set on success:
  - `session['user_id']` — the `id` of the newly inserted row (use `cursor.lastrowid`)
  - `session['user_name']` — the exact value submitted in the `name` form field
    (i.e. `request.form.get('name', '').strip()`)
- Validation order (stop at first failure and re-render with `error=`):
  1. Name, email, password must all be non-empty after `.strip()`
  2. Password must be at least 8 characters
  3. Email must not already exist in the `users` table
- On duplicate email: catch `sqlite3.IntegrityError` **or** pre-check with a
  `SELECT` — either approach is acceptable
- On success: redirect to `url_for('landing')`
  - `landing` is the `GET /` route defined in Step 01; the redirect target may
    change to a dashboard route in a later step
- Always close the DB connection using a `try/finally` block:
```python
  db = get_db()
  try:
      # all db operations here
      ...
  finally:
      db.close()
```

## Definition of done
- [ ] Submitting the form with valid data creates a new row in the `users` table with
      a hashed password (not plaintext)
- [ ] After successful registration, `session['user_id']` and `session['user_name']`
      are set and the user is redirected to the landing page
- [ ] The navbar shows the user's name as a non-clickable `<span>` and a Logout link
      when logged in
- [ ] The navbar shows Sign in / Get started when no session exists
- [ ] Clicking Logout clears the session and redirects to the landing page — no
      broken link or 404
- [ ] Submitting with an empty name, email, or password re-renders the form with an
      error message (no crash)
- [ ] Submitting a password shorter than 8 characters re-renders with an error message
- [ ] Registering with an already-used email re-renders with "Email already registered"
      (or similar) — no duplicate row is inserted
- [ ] The app starts without errors after changes to `app.py`