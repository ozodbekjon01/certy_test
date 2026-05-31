from flask import Blueprint, render_template, request, session, redirect
from werkzeug.security import check_password_hash
import sqlite3
import hmac
import hashlib
import time
import os
from dotenv import load_dotenv

load_dotenv()

bp = Blueprint("auth", __name__)
SECRET_KEY = os.environ.get("SECRET_KEY", "")


def _make_token(username: str, ts: int) -> str:
    msg = f"{username}:{ts}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()


@bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect("/admin" if session.get("role") == "admin" else "/dashboard")
    error = None
    if request.method == "POST":
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
                return redirect("/admin" if user[2] == "admin" else "/dashboard")
            else:
                error = "Login yoki parol noto'g'ri!"
    return render_template("auth/login.html", error=error)


@bp.route("/url_login/<string:username>")
def url_login(username):
    """Token asosida login. Bot: hmac(SECRET_KEY, 'username:ts'). Token 5 daqiqa amal qiladi."""
    token = request.args.get("token", "")
    ts_str = request.args.get("ts", "")
    if not token or not ts_str:
        return "Noto'g'ri so'rov", 400
    try:
        ts = int(ts_str)
    except ValueError:
        return "Noto'g'ri so'rov", 400
    if abs(time.time() - ts) > 300:
        return "Token muddati o'tgan", 401
    if not hmac.compare_digest(_make_token(username, ts), token):
        return "Ruxsat yo'q", 401
    with sqlite3.connect("database.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
    if not user:
        return "Foydalanuvchi topilmadi", 404
    session["user_id"] = user[0]
    session["role"] = user[1]
    session.permanent = True
    return redirect("/admin" if user[1] == "admin" else "/dashboard")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
