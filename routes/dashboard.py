from flask import Blueprint, session, redirect, render_template
from datetime import timedelta
import sqlite3

bp=Blueprint("dashboard", __name__)

def login_required():
    if "user_id" not in session:
        return redirect("/auth/login")

@bp.route("/")
def dashboard():
    check = login_required()
    if check: return check
    
    user_id = session.get("user_id")
    
    with sqlite3.connect("database.db") as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        # Foydalanuvchiga tegishli tariflardagi testlarni olish
        c.execute("""
            SELECT DISTINCT
                t.id,
                t.name,
                t.bio,
                t.image_location
            FROM contracts c

            JOIN offers o
                ON c.offer_id = o.id

            JOIN offer_tests ot
                ON o.id = ot.offer_id

            JOIN tests t
                ON ot.test_id = t.id

            WHERE c.user_id = ?

            AND datetime(
                c.contract_date,
                '+' || o.offer_time || ' days'
            ) >= datetime('now')
        """, (user_id,))
        tests = c.fetchall()
        
        # Foydalanuvchining urinishlari (attempts) ro'yxati
        c.execute("""
            SELECT id, score, correct_answers, wrong_answers, percentage, created_at, test_id
            FROM attempts
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (user_id,))
        attempts = c.fetchall()
        
        # Statistika hisoblash
        c.execute("SELECT count(*) as total, avg(percentage) as avg_p, max(score) as max_s FROM attempts WHERE user_id = ?", (user_id,))
        stat_row = c.fetchone()
        
        stats = {
            "total_attempts": stat_row["total"] or 0,
            "average_score": stat_row["avg_p"] or 0.0,
            "best_score": stat_row["max_s"] or 0
        }
        
    return render_template("dashboard/index.html", tests=tests, attempts=attempts, stats=stats)