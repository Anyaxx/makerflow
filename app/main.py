from __future__ import annotations

import json
import csv
import io
from datetime import date
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import create_order, get_orders, init_db, update_order_status
from app.llm import draft_order_from_message

BASE_DIR = Path(__file__).resolve().parent
STATUSES = {"new", "quoted", "paid", "in production", "ready", "shipped", "completed", "cancelled"}

app = FastAPI(title="Print Shop Order Desk", version="0.2.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.on_event("startup")
def startup_event() -> None:
    init_db()


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "orders": get_orders()})


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/orders")
async def orders_api() -> JSONResponse:
    orders = get_orders()
    today = date.today().isoformat()
    for order in orders:
        order["balance_due"] = max((order["price"] or 0) - (order["deposit_amount"] or 0), 0)
        order["overdue"] = bool(
            order["due_date"]
            and order["due_date"] < today
            and order["status"] not in {"completed", "cancelled"}
        )
    return JSONResponse({"orders": orders})


@app.get("/api/orders.csv")
async def export_orders_csv() -> StreamingResponse:
    output = io.StringIO()
    fields = [
        "id", "customer_name", "contact", "item", "specifications", "price",
        "deposit_amount", "balance_due", "currency", "due_date", "status",
        "delivery_details", "notes", "created_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    for order in get_orders():
        row = {field: order.get(field, "") for field in fields}
        row["balance_due"] = max((order["price"] or 0) - (order["deposit_amount"] or 0), 0)
        writer.writerow(row)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=print-orders.csv"},
    )


@app.post("/api/draft")
async def draft_api(message: str = Form(...)) -> JSONResponse:
    try:
        return JSONResponse({"order": draft_order_from_message(message)})
    except (requests.RequestException, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail=f"Ollama draft failed: {error}") from error


@app.post("/api/orders")
async def create_order_api(
    customer_name: str = Form(...),
    contact: str = Form(""),
    item: str = Form(...),
    specifications: str = Form(""),
    price: str = Form(""),
    deposit_amount: str = Form("0"),
    currency: str = Form("USD"),
    due_date: str = Form(""),
    delivery_details: str = Form(""),
    notes: str = Form(""),
    status: str = Form("new"),
    source_message: str = Form(""),
) -> JSONResponse:
    if status not in STATUSES:
        raise HTTPException(status_code=422, detail="Invalid order status.")
    try:
        amount = float(price) if price else None
        deposit = float(deposit_amount) if deposit_amount else 0
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Price and deposit must be numbers.") from error
    if deposit < 0 or (amount is not None and deposit > amount):
        raise HTTPException(status_code=422, detail="Deposit must be between zero and the price.")
    order_id = create_order(
        {
            "customer_name": customer_name,
            "contact": contact,
            "item": item,
            "specifications": specifications,
            "price": amount,
            "deposit_amount": deposit,
            "currency": currency,
            "due_date": due_date,
            "delivery_details": delivery_details,
            "notes": notes,
            "status": status,
            "source_message": source_message,
        }
    )
    return JSONResponse({"id": order_id, "status": "saved"})


@app.patch("/api/orders/{order_id}/status")
async def update_status(order_id: int, status: str = Form(...)) -> JSONResponse:
    if status not in STATUSES:
        raise HTTPException(status_code=422, detail="Invalid order status.")
    if not update_order_status(order_id, status):
        raise HTTPException(status_code=404, detail="Order not found.")
    return JSONResponse({"status": "updated"})
