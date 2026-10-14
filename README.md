# Print Shop Order Desk MVP

A manual-first order-management MVP for a small 3D-printing business. Capture requests from WhatsApp, Instagram, or phone calls, keep customer and print specifications together, and move each order through a simple production pipeline.

## Features

- Create orders with customer/contact, item, specifications, price, due date, delivery details, and notes.
- Track deposits paid and the remaining balance due.
- Track `new`, `quoted`, `paid`, `in production`, `ready`, `shipped`, `completed`, and `cancelled`.
- Dashboard for active orders with overdue highlighting and Active/Overdue/All filters.
- Export the order queue as CSV for bookkeeping or fulfillment handoffs.
- Optional Gemma/Ollama helper that turns pasted customer messages into editable order drafts. Manual entry still works without Ollama.
- SQLite persistence and a small FastAPI API.

## Run locally

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
ollama pull gemma3:4b  # optional, only needed for Draft with Gemma
uvicorn app.main:app --reload
```

Open http://localhost:8000. Orders are stored in `data/orders.db`.

## Docker and DigitalOcean

```bash
docker compose up -d --build
docker compose exec ollama ollama pull gemma3:4b
```

The app and Ollama run on a private Docker network; only the app port is published. For a small DigitalOcean Droplet, use at least 4 GB RAM, put Caddy or Nginx in front of port 8000 for HTTPS, back up the `order_data` volume, and keep Ollama inaccessible from the public internet. For higher order volume, move SQLite to managed PostgreSQL and add object storage for customer files.

Before charging users, add authentication, per-business ownership, audit history for status changes, background jobs for AI drafts, rate limiting, and automated backups. PDF/file ingestion is intentionally out of scope for this first manual workflow.

## API

- `GET /api/health`
- `GET /api/orders`
- `GET /api/orders.csv` — download the order queue with deposit and balance columns
- `POST /api/draft` with `message`
- `POST /api/orders` with order form fields, including `deposit_amount`
- `PATCH /api/orders/{id}/status` with `status`
