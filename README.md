# Spendly — Personal Expense Tracker

A full-stack personal finance web application built with Flask and vanilla JavaScript. Spendly lets users track daily expenses, filter spending by date range, and visualise breakdowns by category — all with a clean, typographic UI and no frontend framework dependencies.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Dev Server](#running-the-dev-server)
  - [Seed Data](#seed-data)
- [Application Routes](#application-routes)
- [Database Schema](#database-schema)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Deployment](#deployment)
- [Design System](#design-system)

---

## Overview

Spendly is a server-side rendered expense tracker. Users register, log in, and manage a personal ledger of expenses. The profile page aggregates spending statistics and supports date-range filtering. All HTML is rendered via Jinja2 templates — there is no client-side routing or JSON API layer.

The project was built as a progressive learning exercise: core features (database setup, auth, CRUD, analytics) are implemented step by step, with each step documented in a spec file under `.claude/specs/`.

---

## Features

| Area | Details |
|------|---------|
| **Authentication** | Registration with email uniqueness check; login with bcrypt-hashed password verification; session-based auth via Flask's signed cookie |
| **Expense management** | Add, edit, and delete expenses with server-side validation; confirmation step before deletion |
| **Profile dashboard** | Total spent, transaction count, top category; recent transactions table; category breakdown with percentage bars |
| **Date range filter** | Filter all profile stats and transactions to a custom `from` / `to` window |
| **Form validation** | Amount range (0 < x ≤ ₹10,000,000), category allow-list, YYYY-MM-DD date format, 200-character description cap |
| **Ownership enforcement** | Editing or deleting another user's expense redirects silently — no 403 leakage |
| **Structured logging** | Rotating log file at `logs/spendly.log` (1 MB × 3 backups); logs registration, login success/failure, CRUD events, and ownership violations |
| **Auto-initialisation** | Database schema and seed data are created automatically on first run — no manual migration step |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Web framework | Flask 3.1.3 |
| Templating | Jinja2 (bundled with Flask) |
| Database | SQLite via Python stdlib `sqlite3` |
| Password hashing | Werkzeug `generate_password_hash` / `check_password_hash` |
| Frontend | Vanilla JS, CSS custom properties |
| Fonts | DM Serif Display + DM Sans (Google Fonts) |
| Production server | Gunicorn 23.0.0 |
| Deployment platform | Railway |
| Testing | pytest 8.3.5, pytest-flask 1.3.0 |

---

## Project Structure

```
expense-tracker/
│
├── app.py                        # Flask application — all routes and form validation
│
├── database/
│   ├── __init__.py
│   ├── db.py                     # Connection helper, schema creation, seed data, write ops
│   └── queries.py                # Read-heavy queries for the profile dashboard
│
├── templates/
│   ├── base.html                 # Master layout (navbar, footer, Jinja2 blocks)
│   ├── landing.html              # Public landing page
│   ├── register.html             # Registration form
│   ├── login.html                # Login form
│   ├── profile.html              # Dashboard — stats, filters, transactions, category bars
│   ├── add_expense.html          # Add expense form
│   ├── edit_expense.html         # Edit expense form
│   ├── delete_expense.html       # Delete confirmation page
│   ├── analytics.html            # Analytics stub page
│   ├── terms.html                # Terms of service
│   └── privacy.html              # Privacy policy
│
├── static/
│   ├── css/style.css             # Single-file design system + landing page styles
│   └── js/main.js                # Client-side enhancements (no framework)
│
├── tests/
│   ├── test_backend_connection.py          # Integration tests against seeded DB
│   ├── test_06_date_filter_profile_page.py # Date filter integration tests
│   ├── test_07-add-expenses.py             # Add expense tests (isolated tmp DB)
│   └── test_08-edit-expenses.py            # Edit expense tests (isolated tmp DB)
│
├── logs/                         # Rotating log files — gitignored, created at runtime
├── .claude/specs/                # Feature specification documents (one per step)
│
├── requirements.txt
├── railway.toml                  # Production start command
└── CLAUDE.md                     # Claude Code project instructions
```

---

## Getting Started

### Prerequisites

- Python **3.10** or later
- `pip`
- (Optional) `git` for cloning

### Installation

```bash
# 1. Clone the repository
git clone <repo-url>
cd expense-tracker

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

### Running the Dev Server

```bash
python app.py
```

The server starts at **http://localhost:5001** with Flask debug mode enabled.

On first run, `init_db()` creates the SQLite schema and `seed_db()` inserts a demo user with 8 sample expenses. The database file (`expense_tracker.db`) is gitignored and recreated automatically if deleted.

### Seed Data

A demo account is pre-loaded so you can explore the app immediately:

| Field | Value |
|-------|-------|
| Email | `demo@spendly.com` |
| Password | `demo123` |

The seed expenses span May 2026 across all 7 categories, giving the dashboard meaningful data from the start.

---

## Application Routes

| Method | Path | Auth required | Description |
|--------|------|:---:|-------------|
| `GET` | `/` | No | Landing page |
| `GET` | `/register` | No | Registration form |
| `POST` | `/register` | No | Create account, auto-login |
| `GET` | `/login` | No | Login form |
| `POST` | `/login` | No | Authenticate and start session |
| `GET` | `/logout` | No | Clear session, redirect to landing |
| `GET` | `/profile` | Yes | Dashboard with optional `?from=&to=` query params |
| `GET` | `/analytics` | Yes | Analytics page |
| `GET` | `/expenses/add` | Yes | Add expense form |
| `POST` | `/expenses/add` | Yes | Submit new expense |
| `GET` | `/expenses/<id>/edit` | Yes | Edit form pre-filled with expense data |
| `POST` | `/expenses/<id>/edit` | Yes | Update expense (ownership-checked) |
| `GET` | `/expenses/<id>/delete` | Yes | Delete confirmation page |
| `POST` | `/expenses/<id>/delete` | Yes | Permanently remove expense (ownership-checked) |
| `GET` | `/terms` | No | Terms of service |
| `GET` | `/privacy` | No | Privacy policy |

**Auth guard:** unauthenticated requests to protected routes redirect to `/login`. Ownership violations (attempting to edit/delete another user's expense) redirect silently to `/profile`.

---

## Database Schema

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    NOT NULL,
    email         TEXT    UNIQUE NOT NULL,
    password_hash TEXT    NOT NULL,
    created_at    TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE expenses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    amount      REAL    NOT NULL,
    category    TEXT    NOT NULL,
    date        TEXT    NOT NULL,          -- stored as YYYY-MM-DD
    description TEXT,                      -- max 200 characters, nullable
    created_at  TEXT    DEFAULT (datetime('now'))
);
```

Foreign key enforcement is enabled per-connection via `PRAGMA foreign_keys = ON`.

**Expense categories (allow-list):** `Food`, `Transport`, `Bills`, `Health`, `Entertainment`, `Shopping`, `Other`

**Amount constraints:** positive number, maximum ₹10,000,000 (`MAX_AMOUNT`).

---

## Configuration

All configuration is read from environment variables with safe in-process defaults for local development.

| Variable | Default | Required in production | Description |
|----------|---------|:---:|-------------|
| `SECRET_KEY` | `dev-secret-change-in-production` | **Yes** | Flask session signing key. Set to a long random string before deploying. |
| `PORT` | — | Yes (injected by Railway) | Port the Gunicorn server binds to. |

Generate a secure key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## Running Tests

The test suite uses two strategies depending on the test file:

- **Integration tests** (`test_backend_connection.py`, `test_06_date_filter_profile_page.py`) — query the real seeded `expense_tracker.db`. They assume the seed user (`id=1`, `demo@spendly.com`) and its 8 seed expenses are present.
- **Isolated tests** (`test_07-add-expenses.py`, `test_08-edit-expenses.py`) — monkey-patch `database.db.DB_PATH` to a temporary on-disk SQLite file per test, giving a clean slate on every run.

```bash
# Run the full test suite
pytest

# Run a specific file
pytest tests/test_07-add-expenses.py

# Run a single test case
pytest tests/test_backend_connection.py::TestGetSummaryStats

# Run with verbose output
pytest -v
```

---

## Deployment

The app is configured to deploy on [Railway](https://railway.app).

### railway.toml

```toml
[deploy]
startCommand = "gunicorn app:app --bind 0.0.0.0:$PORT"
```

### Steps

1. Push your code to GitHub.
2. Create a new Railway project and connect the repository.
3. Set the `SECRET_KEY` environment variable in the Railway service settings.
4. Railway detects `railway.toml` and runs Gunicorn automatically.

> **Note:** The SQLite database file is ephemeral on Railway (it lives on the container's local disk and is reset on each deployment). For a persistent production deployment, migrate the data layer to a managed PostgreSQL service.

---

## Design System

The entire UI is driven by a single CSS file (`static/css/style.css`) using CSS custom properties.

### Colour Palette

| Token | Hex | Usage |
|-------|-----|-------|
| `--ink` | `#0f0f0f` | Primary text |
| `--ink-muted` | `#6b6b6b` | Secondary / label text |
| `--accent` | `#1a472a` | Primary actions, links, highlights |
| `--accent-2` | `#c17f24` | Gold accent — stats, badges |
| `--danger` | `#c0392b` | Destructive actions, error states |
| `--paper` | `#f7f6f3` | Page background |
| `--paper-warm` | `#f0ede6` | Card / panel backgrounds |

### Typography

| Token | Value | Usage |
|-------|-------|-------|
| `--font-display` | DM Serif Display, Georgia, serif | Headings |
| `--font-body` | DM Sans, system-ui, sans-serif | Body copy, UI labels |

### Breakpoints & Layout

- `--max-width: 1200px` — content container
- `--auth-width: 440px` — auth form container
- Primary mobile breakpoint: **600px** (nav collapses to hamburger)
- Secondary breakpoint: **900px** (multi-column grids collapse to single column)
- Fluid typography uses `clamp()` throughout

### Border Radius Scale

| Token | Value |
|-------|-------|
| `--radius-sm` | 6px |
| `--radius-md` | 12px |
| `--radius-lg` | 20px |

### Currency

All monetary values are displayed in **Indian Rupees (₹)**.
