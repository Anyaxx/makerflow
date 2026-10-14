from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(os.getenv("DATABASE_PATH", "data/orders.db"))


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                contact TEXT,
                item TEXT NOT NULL,
                specifications TEXT,
                price REAL,
                deposit_amount REAL NOT NULL DEFAULT 0,
                currency TEXT NOT NULL DEFAULT 'USD',
                due_date TEXT,
                delivery_details TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                source_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(orders)").fetchall()
        }
        if "deposit_amount" not in columns:
            connection.execute(
                "ALTER TABLE orders ADD COLUMN deposit_amount REAL NOT NULL DEFAULT 0"
            )


def create_order(order: dict[str, Any]) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO orders
            (customer_name, contact, item, specifications, price, deposit_amount, currency, due_date,
             delivery_details, notes, status, source_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.get("customer_name") or "Unknown customer",
                order.get("contact"),
                order.get("item") or "Unspecified item",
                order.get("specifications"),
                order.get("price"),
                order.get("deposit_amount") or 0,
                order.get("currency") or "USD",
                order.get("due_date"),
                order.get("delivery_details"),
                order.get("notes"),
                order.get("status") or "new",
                order.get("source_message"),
            ),
        )
        return int(cursor.lastrowid)


def get_orders() -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT * FROM orders ORDER BY CASE status WHEN 'completed' THEN 2 WHEN 'cancelled' THEN 3 ELSE 1 END, due_date IS NULL, due_date, id DESC"
        ).fetchall()
    return [dict(row) for row in rows]


def update_order_status(order_id: int, status: str) -> bool:
    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE orders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, order_id),
        )
    return cursor.rowcount == 1
