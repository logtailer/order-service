# order-service

A Flask microservice for order management with a built-in web UI. Backed by PostgreSQL, containerised with Docker, and schema-managed with Alembic migrations.

---

## Quick start

```bash
git clone <repo-url>
cd order-service
docker compose up --build
```

App runs at **http://localhost:5001** — the web UI loads at `/`, the API is at `/orders`.

To enable API key auth, set the variable before starting:

```bash
API_KEY=mysecret docker compose up --build
```

---

## Web UI

The UI is served by Flask at `/`. It provides:

- Live DB health indicator
- Order counts per status
- Paginated order table with status filter
- Click-to-expand order detail (items + status history)
- Create order form with dynamic item rows

No build step, no framework — plain HTML/CSS/JS.

---

## API

All order endpoints are prefixed `/orders`. Dates use ISO 8601. Amounts are floats.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Returns app and DB status |

```json
{ "status": "healthy", "db": "connected" }
```

### Orders

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/orders` | Create an order |
| `GET` | `/orders` | List orders (paginated, filterable) |
| `GET` | `/orders/:id` | Get order by ID |
| `PATCH` | `/orders/:id` | Update order status |
| `DELETE` | `/orders/:id` | Cancel an order |

**Create order** — `POST /orders`

```json
{
  "user_id": 1,
  "status": "pending",
  "notes": "leave at door",
  "items": [
    { "product_id": 42, "quantity": 2, "price": 9.99 }
  ]
}
```

Valid creation statuses: `pending`, `processing`, `shipped`.

**List orders** — `GET /orders`

| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `page` | int | `1` | Page number |
| `per_page` | int | `20` | Max 100 |
| `status` | string | — | Filter by status |
| `user_id` | int | — | Filter by user |
| `min_price` | float | — | Filter by total price |
| `max_price` | float | — | Filter by total price |
| `created_after` | ISO datetime | — | |
| `created_before` | ISO datetime | — | |
| `updated_after` | ISO datetime | — | |
| `updated_before` | ISO datetime | — | |
| `sort_by` | string | `created_at` | `created_at`, `updated_at`, `total_price` |
| `sort_order` | string | `desc` | `asc` or `desc` |

**Update status** — `PATCH /orders/:id`

```json
{ "status": "shipped", "reason": "dispatched via courier" }
```

Valid statuses: `pending`, `processing`, `shipped`, `delivered`. Orders in `delivered` or `cancelled` state cannot be updated.

**Cancel order** — `DELETE /orders/:id`

```json
{ "reason": "customer request" }
```

Body is optional.

### Order items

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orders/:id/items` | List items for an order |
| `PATCH` | `/orders/:id/items/:item_id` | Update item quantity |

`GET /orders/:id/items` accepts an optional `product_id` query param to filter.

`PATCH /orders/:id/items/:item_id` recalculates `total_price` on the order.

```json
{ "quantity": 3 }
```

Items on `delivered` or `cancelled` orders cannot be modified.

### Bulk operations

| Method | Path | Description |
|--------|------|-------------|
| `PATCH` | `/orders/bulk-status` | Update status for multiple orders |

```json
{ "order_ids": [1, 2, 3], "status": "shipped" }
```

Returns counts of updated and skipped (terminal-state) order IDs.

### Queries

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/orders/user/:user_id` | Orders for a user |
| `GET` | `/orders/status/:status` | Orders by status |
| `GET` | `/orders/count` | Count with optional `status` and `user_id` filters |
| `GET` | `/orders/summary` | Counts grouped by all statuses |

### Notes & history

| Method | Path | Description |
|--------|------|-------------|
| `PATCH` | `/orders/:id/notes` | Set or clear notes on an order |
| `GET` | `/orders/:id/history` | Status transition history, oldest first |

---

## Configuration

Environment variables (all optional except DB connection in production):

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `orderdb` | Database name |
| `DB_USER` | `postgres` | Database user |
| `DB_PASSWORD` | `postgres` | Database password |
| `DATABASE_URL` | — | Full connection string (overrides above) |
| `API_KEY` | — | If set, all `/orders` requests require `X-API-Key` header |
| `FLASK_ENV` | — | Set to `testing` to use SQLite in-memory |
| `HOST` | `localhost` | Bind address (set to `0.0.0.0` in containers) |
| `PORT` | `5000` | Port (for `run.py` only; gunicorn uses `--bind`) |

---

## Development

**Requirements:** Python 3.11+, Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pre-commit install
```

**Run tests:**

```bash
FLASK_ENV=testing python -m pytest
```

Tests use SQLite in-memory — no database needed.

**Run locally without Docker:**

```bash
# Requires a running PostgreSQL or set FLASK_ENV=testing
python run.py
```

**Generate a migration after model changes:**

```bash
FLASK_APP=run.py flask db migrate -m "describe the change"
FLASK_APP=run.py flask db upgrade
```

---

## Project layout

```
order-service/
├── app/
│   ├── __init__.py       # app factory, blueprint registration, middleware
│   ├── config.py         # environment-based config
│   ├── models.py         # SQLAlchemy models (Order, OrderItem, OrderStatusHistory)
│   ├── routes.py         # Flask routes
│   ├── services.py       # business logic
│   ├── middleware.py     # request logging, API key auth
│   ├── templates/        # Jinja2 templates (index.html)
│   └── static/           # CSS and JS for the web UI
├── migrations/           # Alembic migration files
├── tests/
│   └── test_endpoints.py # 54 integration tests
├── docker/
│   └── entrypoint.sh     # waits for postgres, runs migrations, starts gunicorn
├── k8s/                  # Kubernetes manifests
├── bin/
│   └── setup.sh          # docker compose up --build helper
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Order status lifecycle

```
         ┌──────────┐
   create │  PENDING │
    ──────►          ├──────────────────────────┐
          └────┬─────┘                          │
               │                                │
               ▼                                │
        ┌─────────────┐                         │
        │  PROCESSING │                         │ cancel
        └──────┬──────┘                         │
               │                                │
               ▼                                ▼
          ┌─────────┐                    ┌───────────┐
          │ SHIPPED │                    │ CANCELLED │
          └────┬────┘                    └───────────┘
               │
               ▼
         ┌───────────┐
         │ DELIVERED │
         └───────────┘
```

`DELIVERED` and `CANCELLED` are terminal — no further status updates or item modifications are allowed.
