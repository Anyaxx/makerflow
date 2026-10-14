from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import requests

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")


def _normalize(data: dict[str, Any]) -> dict[str, Any]:
    price = data.get("price")
    try:
        price = float(price) if price not in (None, "") else None
    except (TypeError, ValueError):
        price = None
    due_date = str(data.get("due_date") or "").strip()
    for source_format in ("%Y-%m-%d", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            due_date = datetime.strptime(due_date, source_format).strftime("%Y-%m-%d")
            break
        except ValueError:
            continue
    return {
        "customer_name": str(data.get("customer_name") or "").strip(),
        "contact": str(data.get("contact") or "").strip(),
        "item": str(data.get("item") or "").strip(),
        "specifications": str(data.get("specifications") or "").strip(),
        "price": price,
        "currency": str(data.get("currency") or "USD").strip().upper(),
        "due_date": due_date,
        "delivery_details": str(data.get("delivery_details") or "").strip(),
        "notes": str(data.get("notes") or "").strip(),
        "status": "new",
    }


def draft_order_from_message(message: str) -> dict[str, Any]:
    text = message.strip()
    if not text:
        return _normalize({})
    prompt = f"""
Turn this customer message into a 3D-printing order draft. Return JSON only with:
customer_name, contact, item, specifications, price, currency, due_date (YYYY-MM-DD),
delivery_details, notes. Do not invent missing values; use null or empty strings.

Customer message:
{text}
"""
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": "json",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=90,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "{}")
    return _normalize(json.loads(content))
