import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import init_db, seed_db, create_user, get_user_by_email
from database.queries import get_user_by_id, get_summary_stats, get_recent_transactions, get_category_breakdown

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

with app.app_context():
    init_db()
    seed_db()


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


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
