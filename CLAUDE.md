# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly — an educational expense tracker web app built with Flask and vanilla JS. Students progressively implement features (database, auth, CRUD) on top of a pre-built UI foundation. Currently in early stage: landing page, auth forms, and legal pages are built; database, authentication, and expense operations are placeholders.

## Commands

```bash
# Run dev server (port 5001, debug mode)
python app.py

# Install dependencies
pip install -r requirements.txt

# Run tests (no test files yet, but pytest + pytest-flask are configured)
pytest
pytest tests/test_foo.py::test_bar   # run a single test
```

No build step — Flask serves directly.

## Architecture

**Stack:** Flask 3.1.3 (Python), Jinja2 templates, vanilla JS, SQLite (planned; `sqlite3` is stdlib, no extra driver needed)

**Backend:** Single-file Flask app (`app.py`) — no blueprints, no application factory. All routes render Jinja2 templates from `/templates`. Database layer lives in `database/db.py` (currently a comment-only placeholder); the intended interface is `get_db()`, `init_db()`, and `seed_db()`. `expense_tracker.db` is gitignored so the DB is regenerated per environment.

**Frontend:** Server-side rendered — no API layer, no JSON responses. `base.html` is the master layout; all other templates extend it. Jinja2 blocks available to child templates: `title`, `head` (extra CSS), `content`, `scripts` (extra JS). Only `landing.html` uses the `scripts` block (video modal handler written inline there, not in `main.js`).

**Auth forms** (`login.html`, `register.html`) already check `{% if error %}` and render an `.auth-error` div — POST handlers just need to pass `error=` to `render_template`.

**Educational step numbering:** placeholder routes in `app.py` are commented with the step at which students implement them. Current roadmap:
- Step 01 — Database Setup (✓ complete)
- Step 02 — Registration (✓ complete)
- Step 03 — Login and Logout (✓ complete)
- Step 04 — Profile Page (in progress)
- Steps 05–06 — (planned)
- Steps 07–09 — Expense CRUD (placeholders exist; students will implement add/edit/delete)

Don't remove step comments from placeholder routes; they guide students on what to implement and in what order.

**Database functions:** All database operations go through `database/db.py`. The intended interface is:
- `get_db()` — returns a SQLite connection with `row_factory = sqlite3.Row` and foreign keys enabled
- `init_db()` — creates tables if they don't exist (idempotent)
- `seed_db()` — populates demo data on first run only
- `create_user(name, email, password_hash)` — inserts a user, returns `user_id`
- `get_user_by_email(email)` — returns a user row or `None`
- Additional query functions follow the pattern: parameterised queries, `try/finally` for connection cleanup

**Feature specifications:** Each feature is defined in a spec document before implementation:
- Location: `.claude/specs/<step_number>-<feature_slug>.md` (e.g., `04-profile-page.md`)
- Content: routes, database changes, templates, files to modify, rules, and a testable definition of done
- Workflow: run `/create-spec <feature_title>` to generate a new spec, review it, then implement
- Purpose: specs provide a contract between planning and coding, making reviews and handoffs clear

## CSS Architecture

Single-file system:
- `static/css/style.css` — all styles: global design system (CSS custom properties, navbar, auth components, footer, legal pages, reusable buttons) plus landing-page styles scoped under `.lp-*` prefix at the bottom of the file

Landing page preview mockup uses inline `style="width: X%"` on `.lp-bar` elements — these are static decorations, not data-driven.

## Design System

- **Colors:** ink `#0f0f0f`, accent teal `#1a472a`, gold `#c17f24`, danger `#c0392b`, paper backgrounds `#f7f6f3` / `#f0ede6`
- **Fonts:** DM Serif Display (headings), DM Sans (body) via Google Fonts
- **CSS variables** defined at `:root` in `style.css`; key ones: `--ink`, `--accent`, `--accent-2`, `--danger`, `--paper`, `--paper-2`, `--font-display`, `--font-body`, `--max-width` (1200px), `--auth-width` (440px), `--radius-*` (6 / 12 / 20px)
- Responsive with `clamp()` fluid typography; main mobile breakpoint at 600px (nav collapses), secondary at 900px (grids collapse)
