import math
import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import init_db, seed_db, create_user, get_user_by_email, create_expense, get_expense_by_id, update_expense, delete_expense as delete_expense_db
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

with app.app_context():
    init_db()
    seed_db()

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]
MAX_AMOUNT = 10_000_000

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("register.html")

    name             = request.form.get("name", "").strip()
    email            = request.form.get("email", "").strip()
    password         = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if not name or not email or not password or not confirm_password:
        return render_template("register.html", error="All fields are required.")

    if len(password) < 8:
        return render_template("register.html", error="Password must be at least 8 characters.")

    if password != confirm_password:
        return render_template("register.html", error="Passwords do not match.")

    try:
        password_hash = generate_password_hash(password)
        user_id = create_user(name, email, password_hash)
        session["user_id"]   = user_id
        session["user_name"] = name
    except sqlite3.IntegrityError:
        return render_template("register.html", error="Email already registered.")

    return redirect(url_for("landing"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect(url_for("landing"))
        return render_template("login.html")

    email    = request.form.get("email", "").strip()
    password = request.form.get("password", "").strip()

    if not email or not password:
        return render_template("login.html", error="All fields are required.")

    user = get_user_by_email(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"]   = user["id"]
    session["user_name"] = user["name"]
    return redirect(url_for("profile"))


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    # implemented early (Step 02) to unblock navbar — originally Step 03
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    # Step 4
    if not session.get("user_id"):
        return redirect(url_for("login"))

    raw_from = request.args.get("from", "").strip()
    raw_to   = request.args.get("to", "").strip()

    display_from = display_to = None
    try:
        if raw_from:
            datetime.strptime(raw_from, "%Y-%m-%d")
            display_from = raw_from
        if raw_to:
            datetime.strptime(raw_to, "%Y-%m-%d")
            display_to = raw_to
    except ValueError:
        display_from = display_to = None

    query_from = display_from or ("0001-01-01" if display_to else None)
    query_to   = display_to   or ("9999-12-31" if display_from else None)

    user       = get_user_by_id(session["user_id"])
    summary    = get_summary_stats(session["user_id"], query_from, query_to)
    expenses   = get_recent_transactions(session["user_id"], date_from=query_from, date_to=query_to)
    categories = get_category_breakdown(session["user_id"], query_from, query_to)
    return render_template("profile.html", user=user, summary=summary,
                           expenses=expenses, categories=categories,
                           date_from=display_from, date_to=display_to)


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")


def _validate_expense_form(form):
    """Parse and validate expense form fields.
    Returns (amount, category, date_str, description, error).
    On error: amount is the raw submitted string; error is a message string.
    On success: amount is float, description is str or None, error is None."""
    amount_str  = form.get("amount", "").strip()
    category    = form.get("category", "")
    date_str    = form.get("date", "").strip()
    description = form.get("description", "").strip()[:200]

    try:
        amount = float(amount_str)
    except ValueError:
        return amount_str, category, date_str, description, "Amount must be a positive number."

    if not math.isfinite(amount) or amount <= 0 or amount > MAX_AMOUNT:
        return amount_str, category, date_str, description, "Amount must be a positive number."

    if category not in EXPENSE_CATEGORIES:
        return amount_str, category, date_str, description, "Please select a valid category."

    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return amount_str, category, date_str, description, "Date must be a valid date in YYYY-MM-DD format."

    return amount, category, date_str, description or None, None


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    # Step 7
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template("add_expense.html", categories=EXPENSE_CATEGORIES)

    amount, category, date_str, description, error = _validate_expense_form(request.form)
    if error:
        return render_template("add_expense.html", categories=EXPENSE_CATEGORIES,
                               error=error,
                               amount=amount, category=category, date=date_str, description=description)

    create_expense(session["user_id"], amount, category, date_str, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    # Step 8
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None or expense["user_id"] != session["user_id"]:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("edit_expense.html", expense=expense,
                               categories=EXPENSE_CATEGORIES,
                               amount=expense["amount"],
                               category=expense["category"],
                               date=expense["date"],
                               description=expense["description"] or "")

    amount, category, date_str, description, error = _validate_expense_form(request.form)
    if error:
        return render_template("edit_expense.html", expense=expense,
                               categories=EXPENSE_CATEGORIES,
                               error=error,
                               amount=amount, category=category, date=date_str, description=description)

    update_expense(id, amount, category, date_str, description)
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
def delete_expense(id):
    # Step 9
    if not session.get("user_id"):
        return redirect(url_for("login"))

    expense = get_expense_by_id(id)
    if expense is None or expense["user_id"] != session["user_id"]:
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("delete_expense.html", expense=expense)

    delete_expense_db(id)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    app.run(debug=True, port=5001)
