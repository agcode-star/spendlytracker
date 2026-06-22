import os
import re
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

from database.db import (
    get_db,
    init_db,
    seed_db,
    get_user_by_email,
    create_user,
    get_user_by_id,
    get_recent_expenses,
    get_expense_summary,
    get_category_breakdown,
)

# Basic email shape check — not full RFC validation, just a sanity gate.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# ------------------------------------------------------------------ #
# Profile presentation helpers — format raw DB values for the view.   #
# ------------------------------------------------------------------ #
def _format_amount(value):
    """Render a numeric amount as a ₹-prefixed, comma-grouped string."""
    return f"₹{(value or 0):,.2f}"


def _initials(name):
    """Derive avatar initials from a name (first + last word, uppercased)."""
    parts = (name or "").split()
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][0].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _member_since(created_at):
    """Format a users.created_at timestamp as 'Month YYYY'."""
    if not created_at:
        return ""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(created_at[:len(fmt) + 2], fmt).strftime("%B %Y")
        except ValueError:
            continue
    return ""


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
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    user_row = get_user_by_id(user_id)
    if user_row is None:
        # Session points at a user that no longer exists — treat as logged out.
        session.clear()
        return redirect(url_for("login"))

    summary = get_expense_summary(user_id)
    expense_rows = get_recent_expenses(user_id)
    breakdown = get_category_breakdown(user_id)

    user = {
        "name": user_row["name"],
        "email": user_row["email"],
        "initials": _initials(user_row["name"]),
        "member_since": _member_since(user_row["created_at"]),
    }

    stats = [
        {"label": "Total spent", "value": _format_amount(summary["total"])},
        {"label": "Transactions", "value": str(summary["count"])},
        {"label": "Top category", "value": summary["top_category"] or "—"},
    ]

    transactions = [
        {
            "date": row["date"],
            "description": row["description"],
            "category": row["category"],
            "slug": row["category"].lower(),
            "amount": _format_amount(row["amount"]),
        }
        for row in expense_rows
    ]

    total = summary["total"] or 0
    categories = []
    for row in breakdown:
        share = (row["total"] / total * 100) if total else 0
        percent = int(round(share / 5) * 5)  # nearest 5 → maps to a .bar-w-NN class
        categories.append(
            {
                "name": row["category"],
                "slug": row["category"].lower(),
                "amount": _format_amount(row["total"]),
                "percent": percent,
            }
        )

    return render_template(
        "profile.html",
        user=user,
        stats=stats,
        transactions=transactions,
        categories=categories,
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
