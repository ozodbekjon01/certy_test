from flask import Blueprint, Flask, render_template, request, session, redirect, url_for
from datetime import timedelta
from werkzeug.security import check_password_hash
import sqlite3

bp = Blueprint("auth", __name__)

@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect("/admin")
        else:
            return redirect("/dashboard")
    error = None
    if request.method=='POST':
        username = request.form.get("username")
        password = request.form.get("password")
        with sqlite3.connect("database.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user and check_password_hash(user[1], password):
                session["user_id"] = user[0]
                session["role"] = user[2]
                session.permanent = True
                if user[2] == "admin":
                    return redirect("/admin")
                else:
                    return redirect("/dashboard")
            else:
                error = "Login yoki parol noto'g'ri!"
    return render_template("auth/login.html", error=error)

@bp.route("/url_login/<string:username>/<string:password>")
def url_login(username, password):
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["role"] = user[2]
            session.permanent = True
            if user[2] == "admin":
                return redirect("/admin")
            else:
                return redirect("/dashboard")
    return "Invalid credentials", 401
    

@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")