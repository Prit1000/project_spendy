# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly — an educational expense tracker web app built with Flask and vanilla JS. Students progressively implement features (database, auth, CRUD) on top of a pre-built UI foundation.

## Commands

```bash
# Run dev server (port 5001, debug mode)
python app.py

# Install dependencies
pip install -r requirements.txt

# Run all tests
pytest

# Run a single test
pytest tests/test_backend_connection.py::TestGetSummaryStats

# Format Python files
black <file.py>
```

No build step — Flask serves directly.

## Architecture

**Stack:** Flask 3.1.3 (Python), Jinja2 templates, vanilla JS, SQLite (`sqlite3` stdlib)

**Backend:** Single-file Flask app (`app.py`) — no blueprints, no application factory. All routes render Jinja2 templates from `/templates`. `expense_tracker.db` is gitignored and regenerated on first run via `init_db()` + `seed_db()`.

**Database layer — two files:**
- `database/db.py` — connection helper (`get_db()`), schema creation (`init_db()`), seed data (`seed_db()`), and write operations (`create_user`, `create_expense`) plus simple reads (`get_user_by_email`). All functions open a connection, use `try/finally` to close it, and use parameterised queries.
- `database/queries.py` — read-heavy queries used by the profile page: `get_user_by_id`, `get_summary_stats`, `get_recent_transactions`, `get_category_breakdown`. All four accept optional `date_from`/`date_to` parameters handled by the `_date_filter` helper.

**App constants (app.py):**
- `EXPENSE_CATEGORIES` — the canonical list of valid categories; validated server-side on expense submission.
- `MAX_AMOUNT` — upper bound for expense amounts (10,000,000).

**Session:** Flask session stores `user_id` (int) and `user_name` (str) after login/register. Auth guard pattern: `if not session.get("user_id"): return redirect(url_for("login"))`.

**Frontend:** Server-side rendered — no API layer, no JSON responses. `base.html` is the master layout; all other templates extend it. Jinja2 blocks available to child templates: `title`, `head` (extra CSS), `content`, `scripts` (extra JS). Only `landing.html` uses the `scripts` block (video modal handler written inline, not in `main.js`).

**Auth forms** (`login.html`, `register.html`) already check `{% if error %}` and render an `.auth-error` div — POST handlers just need to pass `error=` to `render_template`.

**Educational step numbering:** placeholder routes in `app.py` are commented with the step at which students implement them. Current roadmap:
- Step 01 — Database Setup (✓ complete)
- Step 02 — Registration (✓ complete)
- Step 03 — Login and Logout (✓ complete)
- Step 04 — Profile Page backend routes (✓ complete)
- Step 05 — Backend routes / profile page queries (✓ complete)
- Step 06 — Date filter on profile page (✓ complete)
- Step 07 — Add expense (✓ complete)
- Step 08 — Edit expense (placeholder: `GET /expenses/<id>/edit`)
- Step 09 — Delete expense (placeholder: `GET /expenses/<id>/delete`)

Don't remove step comments from placeholder routes; they guide students on what to implement and in what order.

**Feature specifications:** Each feature is defined in a spec document before implementation:
- Location: `.claude/specs/<step_number>-<feature_slug>.md` (e.g., `07-add-expenses.md`)
- Workflow: run `/create-spec <feature_title>` to generate a new spec, review it, then implement

## Tests

Tests live in `tests/` and run against the real seeded SQLite database — there is no conftest.py and no mocking. Tests assume the seed user (`id=1`, `demo@spendly.com`) and its 8 seed expenses are present. If `expense_tracker.db` is missing or empty, `init_db()` + `seed_db()` run automatically when `app.py` is imported.

## CSS Architecture

Single-file system:
- `static/css/style.css` — global design system (CSS custom properties, navbar, auth components, footer, legal pages, reusable buttons) plus landing-page styles scoped under `.lp-*` prefix at the bottom.

Landing page preview mockup uses inline `style="width: X%"` on `.lp-bar` elements — static decorations, not data-driven.

## Design System

- **Colors:** ink `#0f0f0f`, accent teal `#1a472a`, gold `#c17f24`, danger `#c0392b`, paper backgrounds `#f7f6f3` / `#f0ede6`
- **Fonts:** DM Serif Display (headings), DM Sans (body) via Google Fonts
- **CSS variables** defined at `:root` in `style.css`; key ones: `--ink`, `--accent`, `--accent-2`, `--danger`, `--paper`, `--paper-2`, `--font-display`, `--font-body`, `--max-width` (1200px), `--auth-width` (440px), `--radius-*` (6 / 12 / 20px)
- Responsive with `clamp()` fluid typography; main mobile breakpoint at 600px (nav collapses), secondary at 900px (grids collapse)
- Currency is INR (₹) throughout
