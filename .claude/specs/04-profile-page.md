# Spec: Profile Page

## Overview
Replace the `/profile` stub with a fully designed profile page showing **hardcoded static data**. Goal: validate the complete UI layout (user info card, stats, transaction table, category breakdown) before wiring real DB queries. Also establish the `login_required` guard pattern that subsequent steps will reuse. Name/password update handlers are **deferred to Step 5**.

## Depends on
- Step 1: DB setup (`users` + `expenses` tables, `get_db()`)
- Step 2: Registration (session keys `user_id` / `user_name` established)
- Step 3: Login + Logout (session must be set before visiting `/profile`)

## Routes

| Method | Route | Auth | Purpose |
|---|---|---|---|
| GET | `/profile` | Required | Render profile page with hardcoded data |

> `POST /profile/name` and `POST /profile/password` are defined in Step 5 — do not implement here.

## Database Changes
None. No new tables, columns, or helper functions in this step.

## Templates

**Create:** `templates/profile.html` — extends `base.html`, four sections:

1. **User info card** — avatar initials, name, email, member-since date (hardcoded)
2. **Summary stats row** — total spent, transaction count, top category (hardcoded)
3. **Transaction history table** — date, description, category badge, amount (≥3 hardcoded rows)
4. **Category breakdown** — per-category totals as list or progress-bar rows (≥3 hardcoded categories)

## Files to Change
- `app.py` — replace `/profile` stub with a real view that:
  - Guards with `session.get('user_id')` — redirect to `url_for('login')` if falsy
  - Passes hardcoded Python dicts/lists as context to `profile.html`
  - No DB queries in this step

## Files to Create
- `templates/profile.html`

## New Dependencies
None.

## Rules for Implementation
- No SQLAlchemy — raw `sqlite3` via `get_db()` only (not needed this step, but keep the pattern ready)
- Parameterised queries only when SQL is written — never f-strings or `%` formatting
- Passwords: `werkzeug.security` — no auth changes in this step
- CSS variables only — no hardcoded hex values, no inline styles
- All templates extend `base.html`
- All data must be hardcoded in `app.py` as dicts/lists — zero DB calls this step
- Category badges must use a CSS class, not inline colour

## Step 5 Additions (not now — logged for reference)
These come from Spec 1 and land in the next step:
- `get_user_by_id(user_id)` and `update_user_name` / `update_user_password` in `database/db.py`
- `POST /profile/name` — validate, update DB, refresh `session['user_name']`, redirect
- `POST /profile/password` — validate current password, enforce 8-char minimum, confirm match, update hash
- Fetch live user row from DB on `GET /profile` (replace hardcoded data)
- Always close DB connections in `try/finally`

## Definition of Done
- [ ] `/profile` without login → redirects to `/login`
- [ ] `/profile` while logged in → HTTP 200
- [ ] User info card displays name and email
- [ ] Summary stats row shows ≥3 values (total spent, transaction count, top category)
- [ ] Transaction table shows ≥3 hardcoded rows
- [ ] Category breakdown shows ≥3 categories
- [ ] Navbar shows logged-in state (username + logout link)
- [ ] Zero hex colour values in `profile.html` — CSS variables only
- [ ] App starts without errors after changes to `app.py`