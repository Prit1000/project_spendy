import sqlite3
from datetime import datetime
from database.db import get_db


def get_user_by_id(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT name, email, created_at FROM users WHERE id = ?",
            (user_id,)
        ).fetchone()
        if row is None:
            return None
        formatted_date = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
        return {"name": row["name"], "email": row["email"], "member_since": formatted_date}
    finally:
        conn.close()


def get_summary_stats(user_id):
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        top_row = conn.execute(
            "SELECT category FROM expenses WHERE user_id = ? GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            (user_id,)
        ).fetchone()
        top_cat = top_row["category"] if top_row else "—"
        return {"total_spent": float(row["total"]), "transaction_count": int(row["cnt"]), "top_category": top_cat}
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT date, description, category, amount FROM expenses WHERE user_id = ? ORDER BY date DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
        return [{"date": row["date"], "description": row["description"], "category": row["category"], "amount": row["amount"]} for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id):
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC",
            (user_id,)
        ).fetchall()
        if not rows:
            return []
        grand_total = sum(row["total"] for row in rows)
        raws = [row["total"] / grand_total * 100 for row in rows]
        floor_pcts = [int(r) for r in raws]
        remainder = 100 - sum(floor_pcts)
        indices_by_frac = sorted(range(len(raws)), key=lambda i: raws[i] % 1, reverse=True)
        for i in range(remainder):
            floor_pcts[indices_by_frac[i]] += 1
        return [
            {"name": rows[i]["category"], "amount": rows[i]["total"], "pct": floor_pcts[i]}
            for i in range(len(rows))
        ]
    finally:
        conn.close()
