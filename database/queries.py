import sqlite3
from datetime import datetime
from database.db import get_db


def _date_filter(date_from, date_to):
    if date_from is not None and date_to is not None:
        return " AND date >= ? AND date <= ?", [date_from, date_to]
    return "", []


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


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        clause, params = _date_filter(date_from, date_to)
        row = conn.execute(
            f"SELECT COUNT(*) AS cnt, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?{clause}",
            [user_id] + params
        ).fetchone()
        top_row = conn.execute(
            f"SELECT category FROM expenses WHERE user_id = ?{clause} GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
            [user_id] + params
        ).fetchone()
        top_cat = top_row["category"] if top_row else "—"
        return {"total_spent": float(row["total"]), "transaction_count": int(row["cnt"]), "top_category": top_cat}
    finally:
        conn.close()


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    try:
        clause, params = _date_filter(date_from, date_to)
        rows = conn.execute(
            f"SELECT id, date, description, category, amount FROM expenses WHERE user_id = ?{clause} ORDER BY date DESC LIMIT ?",
            [user_id] + params + [limit]
        ).fetchall()
        return [{"id": row["id"], "date": row["date"], "description": row["description"], "category": row["category"], "amount": row["amount"]} for row in rows]
    finally:
        conn.close()


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    try:
        clause, params = _date_filter(date_from, date_to)
        rows = conn.execute(
            f"SELECT category, COALESCE(SUM(amount), 0) AS total FROM expenses WHERE user_id = ?{clause} GROUP BY category ORDER BY total DESC",
            [user_id] + params
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
