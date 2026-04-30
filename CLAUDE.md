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

**Educational step numbering:** placeholder routes in `app.py` are commented with the step at which students implement them (Step 3 = logout, Step 4 = profile, Steps 7–9 = expense CRUD). Don't remove those comments.

## CSS Architecture

Two-file system:
- `static/css/style.css` — global design system (CSS custom properties, navbar, auth components, footer, legal pages, reusable buttons)
- `static/css/landing.css` — landing-only styles, all scoped under `.lp-*` prefix to avoid collisions; loaded via `{% block head %}` in `landing.html`

Landing page preview mockup uses inline `style="width: X%"` on `.lp-bar` elements — these are static decorations, not data-driven.

## Design System

- **Colors:** ink `#0f0f0f`, accent teal `#1a472a`, gold `#c17f24`, danger `#c0392b`, paper backgrounds `#f7f6f3` / `#f0ede6`
- **Fonts:** DM Serif Display (headings), DM Sans (body) via Google Fonts
- **CSS variables** defined at `:root` in `style.css`; key ones: `--ink`, `--accent`, `--accent-2`, `--danger`, `--paper`, `--paper-2`, `--font-display`, `--font-body`, `--max-width` (1200px), `--auth-width` (440px), `--radius-*` (6 / 12 / 20px)
- Responsive with `clamp()` fluid typography; main mobile breakpoint at 600px (nav collapses), secondary at 900px (grids collapse)
