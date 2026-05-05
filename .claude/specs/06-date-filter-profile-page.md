# Spec: Date Filter for Profile Page

## Overview
Step 6 adds a date range filter to the profile page so users can narrow their
spending view to a specific period. The summary stats, category breakdown, and
recent transactions are all scoped to the selected date range. Filtering is
done via query string parameters (`from` and `to`) passed as a GET form — this
keeps filtered views bookmarkable. If no dates are supplied, the page falls
back to showing all-time data (preserving the current default behaviour). This
step builds directly on the live query layer introduced in Step 5.

## Depends on
- Step 1: Database setup (`expenses` table with `date TEXT` column)
- Step 3: Login / Logout (`session["user_id"]` set on login)
- Step 4: Profile page static UI (template renders all four sections)
- Step 5: Backend routes — profile page (live queries in `database/queries.py`)

## Routes
No new routes. The existing `GET /profile` route is extended to read optional
`from` and `to` query parameters.

- `GET /profile?from=YYYY-MM-DD&to=YYYY-MM-DD` — profile filtered to date range
- `GET /profile` — profile showing all-time data (unchanged default)

## Database changes
No database changes. `expenses.date` is already `TEXT NOT NULL` in ISO 8601
format (`YYYY-MM-DD`), so SQLite string comparisons (`>=`, `<=`) are exact.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date filter card above the stats cards containing two sections:
    1. **Preset chips** — a row of pill-shaped links for quick ranges:
       All Time, This Month, Last Month, Last 3 Months, Last 6 Months.
       Chips are plain `<a>` tags; their `href` values are computed by inline
       JS at page load (see Scripts section below) so they always reflect the
       current date. The chip matching the active URL params gets the
       `.profile-preset-active` class (filled dark).
    2. **Custom date form** — `<form method="GET" action="/profile">` with two
       `<input type="date">` fields (`name="from"` and `name="to"`), a "Filter"
       submit button, and a "Clear" link that resets to `/profile` (no params);
       the Clear link is only shown when a filter is active.
  - When a filter is active (either param present in the URL), show an
    active-range label below the form, e.g. "Showing: 2026-05-01 – 2026-05-15".
  - Pre-fill the date inputs with the currently applied `from` / `to` values so
    the user can see and adjust them.
  - No structural changes to the stats, category breakdown, or transaction
    sections — they already render whatever data the route passes.

- **Scripts** (`{% block scripts %}` in `templates/profile.html`):
  - After the Lucide icon initialisation, add an inline `<script>` that:
    - Computes the six date ranges using the JS `Date` API relative to today.
    - Sets the correct `href` on each preset chip (`/profile` for All Time,
      `/profile?from=...&to=...` for the rest).
    - Compares the current URL params (`URLSearchParams`) against each preset's
      expected `from`/`to` values and adds `.profile-preset-active` to the
      matching chip.
  - No external JS libraries — vanilla JS only.

## Files to change
- `app.py`
  - In `profile()`: read `request.args.get("from")` and `request.args.get("to")`.
  - Validate both values: if present, they must match `YYYY-MM-DD` (use a
    `datetime.strptime` check); discard silently if invalid.
  - If `date_to` is provided but `date_from` is not, treat `date_from` as
    `"0001-01-01"` (open-ended left bound). If `date_from` is provided but
    `date_to` is not, treat `date_to` as `"9999-12-31"` (open-ended right
    bound).
  - Pass `date_from` and `date_to` to all four query helpers.
  - Pass the original validated user inputs (not the sentinel-filled values)
    back to `render_template` as `date_from` / `date_to` so the template can
    pre-fill the custom inputs and show the active-filter label cleanly.

- `database/queries.py`
  - Add optional `date_from=None, date_to=None` parameters to
    `get_summary_stats`, `get_recent_transactions`, and `get_category_breakdown`.
  - When both are `None`, queries behave exactly as they do today (no `WHERE`
    date clause added).
  - When either is set, append `AND date >= ? AND date <= ?` to the existing
    `WHERE user_id = ?` clause and bind the values.
  - `get_user_by_id` does not need date params (user info is not filtered).

- `templates/profile.html`
  - Add the filter card (preset chips + custom date form) described in the
    Templates section above.
  - Add the inline preset JS described in the Scripts section above.

- `static/css/style.css`
  - Append inside the profile section:
    - `.profile-preset-chips` — flex row with wrap for the preset chip links
    - `.profile-preset` — pill-shaped link (rounded border, muted colour)
    - `.profile-preset:hover` — ink border + ink text on hover
    - `.profile-preset-active` — filled dark background (active preset state)
    - `.profile-filter-form` — flex row layout for the two date inputs and buttons
    - `.profile-filter-field` — flex column wrapper for each label+input pair
    - `.profile-filter-actions` — flex row for the buttons
    - `.profile-filter-active` — small muted label showing the active date range

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Filtering uses GET (not POST) so filtered URLs are bookmarkable
- Invalid or missing date params must degrade gracefully to all-time view —
  never raise an unhandled exception
- Currency must always display as ₹ — never £ or $
- The filter form must be accessible: use `<label>` elements paired with each
  `<input>` via `for`/`id` attributes
- Do not add a new route — keep everything on `GET /profile`
- Date comparison relies on ISO 8601 string sort order in SQLite — do not
  convert to integers or use `strftime` in SQL

## Definition of done
- [ ] Visiting `/profile` with no params shows all-time data (unchanged behaviour)
- [ ] "All Time" preset chip is highlighted (dark fill) on `/profile` with no params
- [ ] Clicking "This Month" preset navigates to the correct `?from=...&to=...` URL
      and highlights only that chip
- [ ] Clicking "Last Month" preset navigates to the first–last day of the previous
      calendar month and shows only that month's expenses
- [ ] Clicking "Last 3 Months" and "Last 6 Months" presets each navigate to the
      correct date range and highlight only the clicked chip
- [ ] Submitting the custom date form with `from=2026-05-01` and `to=2026-05-15`
      shows only expenses between 01 May and 15 May inclusive; no preset chip
      is highlighted (custom range doesn't match any preset)
- [ ] Summary stats (total spent, transaction count) reflect only the filtered
      date range
- [ ] Category breakdown reflects only the filtered date range
- [ ] Transaction list shows only transactions within the filtered range
- [ ] The custom date inputs are pre-filled with the applied `from` / `to` values
      after filtering
- [ ] An active-range label ("Showing: … – …") is visible when a filter is active
- [ ] Clicking "Clear" returns to `/profile` with no params and shows all-time data;
      "All Time" chip is re-highlighted
- [ ] Entering an invalid date (e.g. `from=not-a-date`) does not crash — falls
      back to all-time view
- [ ] A user with no expenses in the filtered range sees ₹0.00, 0 transactions,
      and empty category breakdown — no errors
