import os
import re

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
)

# Basic email shape check — not full RFC validation, just a sanity gate.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# ------------------------------------------------------------------ #
# Hardcoded profile data (Step 4 — UI only).                          #
# Step 5 will replace these constants with real queries via get_db(). #
# ------------------------------------------------------------------ #
PROFILE_USER = {
    "name": "Demo User",
    "email": "demo@spendly.com",
    "initials": "DU",
    "member_since": "June 2026",
}

PROFILE_STATS = [
    {"label": "Total spent", "value": "₹12,480"},
    {"label": "Transactions", "value": "24"},
    {"label": "Top category", "value": "Food"},
]

PROFILE_TRANSACTIONS = [
    {"date": "2026-06-18", "description": "Lunch at cafe", "category": "Food", "slug": "food", "amount": "₹420"},
    {"date": "2026-06-16", "description": "Metro pass", "category": "Transport", "slug": "transport", "amount": "₹1,200"},
    {"date": "2026-06-14", "description": "Electricity bill", "category": "Bills", "slug": "bills", "amount": "₹2,150"},
    {"date": "2026-06-11", "description": "Pharmacy", "category": "Health", "slug": "health", "amount": "₹680"},
    {"date": "2026-06-08", "description": "Movie night", "category": "Entertainment", "slug": "entertainment", "amount": "₹560"},
]

PROFILE_CATEGORY_BREAKDOWN = [
    {"name": "Food", "slug": "food", "amount": "₹4,200", "percent": 35},
    {"name": "Bills", "slug": "bills", "amount": "₹3,100", "percent": 25},
    {"name": "Transport", "slug": "transport", "amount": "₹2,400", "percent": 20},
    {"name": "Health", "slug": "health", "amount": "₹1,500", "percent": 10},
    {"name": "Entertainment", "slug": "entertainment", "amount": "₹1,280", "percent": 10},
]

app = Flask(__name__)

# Required for signed session cookies. Read from the environment so a real
# secret is never committed; the fallback keeps local dev runs working.
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# Ensure the database schema and demo data are ready before any request.
# Done at module level so it runs under both `python app.py` and `flask run`.
# Both calls are idempotent, so running on every import is safe.
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
    # Already-authenticated users have no reason to register again.
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "All fields are required."
        elif not EMAIL_RE.match(email):
            error = "Please enter a valid email address."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif get_user_by_email(email):
            error = "An account with that email already exists."
        else:
            create_user(name, email, generate_password_hash(password))
            return redirect(url_for("login"))

        return render_template("register.html", error=error, name=name, email=email)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    # Already-authenticated users skip the login form.
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_user_by_email(email)
        # One generic message for both unknown email and wrong password so the
        # form never reveals which accounts exist. The check short-circuits, so
        # check_password_hash is never called on a missing user.
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Invalid email or password."
            return render_template("login.html", error=error, email=email)

        session["user_id"] = user["id"]
        session["name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    return render_template(
        "profile.html",
        user=PROFILE_USER,
        stats=PROFILE_STATS,
        transactions=PROFILE_TRANSACTIONS,
        categories=PROFILE_CATEGORY_BREAKDOWN,
    )


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #


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
