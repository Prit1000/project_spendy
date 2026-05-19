# Spec: Delete Expenses

## Overview
Step 9 replaces the `GET /expenses/<id>/delete` placeholder with a working
delete flow. A logged-in user can click a "Delete" link next to any of their
own expenses on the profile page, land on a confirmation screen that shows the
expense details, and confirm to permanently remove it. The row is deleted from
the `expenses` table and the user is redirected back to the profile page.
Ownership is enforced server-side — a user cannot delete another user's expense.
This is the first destructive write operation on the `expenses` table from the
web UI.

## Depends on
- Step 1: Database setup (`expenses` table)
- Step 3: Login / Logout (`session["user_id"]` available, auth guard pattern)
- Step 4 / 5: Profile page (source of delete links, destination after delete)
- Step 7: Add expense (establishes auth-card CSS conventions reused here)
- Step 8: Edit expense (`get_expense_by_id` already in `database/db.py`, "Actions" column already in `profile.html`)

## Routes
- `GET  /expenses/<int:id>/delete` — fetch the expense, verify ownership, render confirmation page — logged-in only
- `POST /expenses/<int:id>/delete` — verify ownership, delete the row, redirect to `/profile` — logged-in only

## Database changes
No new tables or columns. One new helper function in `database/db.py`:

- `delete_expense(expense_id)` — executes a parameterised
  `DELETE FROM expenses WHERE id = ?`; returns nothing.

`get_expense_by_id` already exists from Step 8 and is reused here.

## Templates
- **Create:** `templates/delete_expense.html`
  - Extends `base.html`.
  - Reuses the same CSS classes as the auth/expense forms:
    `auth-section`, `auth-container`, `auth-header`, `auth-card`, `form-group`,
    `expense-form-actions`.
  - Title: "Delete Expense" / subtitle: "This action cannot be undone".
  - Displays a read-only summary of the expense being deleted: amount, category,
    date, and description.
  - Contains a `<form method="POST">` pointing to
    `url_for('delete_expense', id=expense['id'])`.
  - Two buttons: "Delete" (submit, styled with `.btn-danger`) and a "Cancel"
    link back to `/profile` (styled with `.btn-ghost`).

- **Modify:** `templates/profile.html`
  - In each `<tr>` in the Recent Transactions table, add a "Delete" link in the
    existing `.col-actions` `<td>` alongside the existing "Edit" link:
    `<a href="{{ url_for('delete_expense', id=exp['id']) }}" class="txn-action-link txn-action-danger">Delete</a>`

## Files to change
- `app.py`
  - Replace the single-line `delete_expense` stub with a two-method route:
    ```python
    @app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
    def delete_expense(id):
    ```
  - `GET`:
    1. Guard: `if not session.get("user_id"): return redirect(url_for("login"))`.
    2. Fetch: `expense = get_expense_by_id(id)`.
    3. Ownership check: if `expense` is `None` or
       `expense["user_id"] != session["user_id"]`, redirect to `url_for("profile")`.
    4. Render `delete_expense.html` passing `expense=expense`.
  - `POST`:
    1. Same session guard.
    2. Re-fetch expense with `get_expense_by_id(id)` and repeat the ownership
       check — never trust the URL alone.
    3. Call `delete_expense_db(id)` (alias import, see note below), then
       `redirect(url_for("profile"))`.
  - Add `delete_expense` to the import from `database.db`.
    Note: the route function is also named `delete_expense`, so import the db
    helper under an alias:
    `from database.db import ..., delete_expense as delete_expense_db`
  - Keep the `# Step 9` comment on the route.

- `database/db.py`
  - Add `delete_expense(expense_id)`:
    ```python
    def delete_expense(expense_id):
        conn = get_db()
        try:
            conn.execute(
                "DELETE FROM expenses WHERE id = ?", (expense_id,)
            )
            conn.commit()
        finally:
            conn.close()
    ```

- `templates/profile.html`
  - In `.col-actions` `<td>`, add a "Delete" anchor after the existing "Edit"
    anchor, styled with `.txn-action-link.txn-action-danger`.

- `static/css/style.css`
  - Add a `.txn-action-danger` modifier rule in the existing `/* Profile */`
    section:
    ```css
    .txn-action-danger { color: var(--danger); }
    .txn-action-danger:hover { color: var(--danger); opacity: 0.8; }
    ```
  - Add a `.btn-danger` rule (solid red button, mirrors `.btn-primary` but uses
    `--danger` as background):
    ```css
    .btn-danger { background: var(--danger); color: #fff; ... }
    ```
    Place it near `.btn-primary` in the global button section.

## Files to create
- `templates/delete_expense.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Passwords hashed with werkzeug (not applicable here)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Auth guard on both GET and POST — unauthenticated requests redirect to `/login`
- Ownership check on both GET and POST — if the expense doesn't belong to
  `session["user_id"]`, redirect silently to `/profile` (no 404 leak)
- The actual delete must happen via POST, not GET — a GET request must only show
  the confirmation page, never modify the database
- Import `delete_expense` from `database.db` under the alias `delete_expense_db`
  to avoid shadowing the Flask route function
- Currency always displays as ₹ — never £ or $
- Keep the `# Step 9` comment on the route in `app.py`

## Definition of done
- [ ] `GET /expenses/<id>/delete` while logged out redirects to `/login`
- [ ] `GET /expenses/<id>/delete` for an expense belonging to the current user
      renders a confirmation page showing the expense's amount, category, date,
      and description
- [ ] `GET /expenses/<id>/delete` for an expense belonging to a different user
      redirects to `/profile` without showing the confirmation page
- [ ] `GET /expenses/<id>/delete` for a non-existent id redirects to `/profile`
- [ ] Clicking "Cancel" on the confirmation page returns to `/profile` without
      deleting the expense
- [ ] Submitting the confirmation form (POST) deletes the expense from the
      database and redirects to `/profile`, where the row no longer appears
- [ ] A GET request to `/expenses/<id>/delete` never deletes the expense (safe
      navigation / link prefetching cannot trigger a delete)
- [ ] A user cannot delete another user's expense by crafting a direct POST
      request to that expense's delete URL
- [ ] The Recent Transactions table on `/profile` shows a "Delete" link for each
      expense row alongside the existing "Edit" link
- [ ] The "Delete" link on the profile page is visually distinct (red/danger
      colour) from the "Edit" link
