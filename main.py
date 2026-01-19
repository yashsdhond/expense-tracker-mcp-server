from fastmcp import FastMCP
from pydantic import BaseModel
from typing import Optional
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP("ExpenseTracker")

def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

init_db()

# -----------------------------
# Pydantic Schemas (CRITICAL)
# -----------------------------

class AddExpenseArgs(BaseModel):
    date: str
    amount: float
    category: str
    subcategory: Optional[str] = ""
    note: Optional[str] = ""

class ListExpensesArgs(BaseModel):
    start_date: str
    end_date: str

class SummarizeArgs(BaseModel):
    start_date: str
    end_date: str
    category: Optional[str] = None

# -----------------------------
# MCP Tools
# -----------------------------

@mcp.tool()
def add_expense(args: AddExpenseArgs):
    """Add a new expense entry to the database."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            INSERT INTO expenses(date, amount, category, subcategory, note)
            VALUES (?,?,?,?,?)
            """,
            (
                args.date,
                args.amount,
                args.category,
                args.subcategory or "",
                args.note or "",
            )
        )
        return {"status": "ok", "id": cur.lastrowid}

@mcp.tool()
def list_expenses(args: ListExpensesArgs):
    """List expense entries within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (args.start_date, args.end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

@mcp.tool()
def summarize(args: SummarizeArgs):
    """Summarize expenses by category within an inclusive date range."""
    with sqlite3.connect(DB_PATH) as c:
        query = """
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """
        params = [args.start_date, args.end_date]

        if args.category:
            query += " AND category = ?"
            params.append(args.category)

        query += " GROUP BY category ORDER BY category ASC"

        cur = c.execute(query, params)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]

# -----------------------------
# Resource
# -----------------------------

@mcp.resource("expense://categories", mime_type="application/json")
def categories():
    with open(CATEGORIES_PATH, "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    mcp.run()
