# Architecture

Technical overview of how the Drunken Cookies Operations Platform is built.

## 🏗️ High-Level Diagram

```
┌──────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                  │
│                                                           │
│  ┌─────────────────┐       ┌─────────────────┐          │
│  │   Cloud Run     │       │   Cloud Run     │          │
│  │   (Frontend)    │──────▶│    (Backend)    │          │
│  │   Next.js 14    │       │    FastAPI      │          │
│  └─────────────────┘       └────────┬────────┘          │
│                                     │                    │
│                            ┌────────▼────────┐          │
│                            │    Cloud SQL    │          │
│                            │   PostgreSQL    │          │
│                            └─────────────────┘          │
│                                     ▲                    │
│                                     │                    │
│  ┌─────────────────────────────────┴──────┐             │
│  │       Cloud Scheduler (7 jobs)         │             │
│  │  - Daily plans (4:57 AM)              │             │
│  │  - Sync inventory (every 30 min)      │             │
│  │  - Check alerts (every 30 min)        │             │
│  │  - Live sales (every 5 min)           │             │
│  │  - Sync orders (hourly)               │             │
│  └────────────────────────────────────────┘             │
└──────────────────────────────────────────────────────────┘
         ▲                        ▲                 ▲
         │                        │                 │
  ┌──────┴──────┐          ┌─────┴──────┐   ┌─────┴──────┐
  │   Clover    │          │  Shopify   │   │  Google    │
  │     POS     │          │   Store    │   │   Sheets   │
  └─────────────┘          └────────────┘   └────────────┘
```

## 🧱 Tech Stack

### Backend
- **Framework:** FastAPI (Python 3.12)
- **ORM:** SQLAlchemy 2.x
- **Database:** PostgreSQL on Cloud SQL
- **Auth:** JWT (HS256), passlib/bcrypt for password hashing
- **Scheduled jobs:** Google Cloud Scheduler → HTTP POST to `/api/cron/*`
- **External APIs:** Google Sheets API (read/write), Clover REST API, Shopify Admin API

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Styling:** Tailwind CSS
- **State:** Zustand (auth, date selection)
- **Data fetching:** TanStack Query (React Query)
- **Language:** TypeScript
- **Components:** Custom (EditableCell, ExportBar, NotificationBell, Toast)

### Infrastructure
- **Hosting:** Google Cloud Run (both services, autoscaling)
- **Database:** Google Cloud SQL (PostgreSQL, db-f1-micro tier)
- **Cron:** Google Cloud Scheduler
- **Source:** GitHub → manual `gcloud run deploy --source .`

---

## 📁 Directory Layout

```
platform/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entrypoint + startup migrations
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy engine + session
│   │   ├── api/                 # Route handlers (one file per module)
│   │   │   ├── auth_routes.py
│   │   │   ├── dispatch_routes.py
│   │   │   ├── bake_routes.py
│   │   │   ├── inventory_routes.py
│   │   │   ├── admin_routes.py
│   │   │   ├── cron_routes.py
│   │   │   ├── analytics_routes.py
│   │   │   ├── orders_routes.py
│   │   │   ├── notifications_routes.py
│   │   │   └── sales_routes.py
│   │   ├── models/              # SQLAlchemy models
│   │   │   ├── user.py
│   │   │   ├── flavor.py
│   │   │   ├── location.py
│   │   │   ├── inventory.py
│   │   │   ├── daily_sales.py
│   │   │   ├── dispatch.py
│   │   │   ├── bake_plan.py
│   │   │   ├── par_settings.py
│   │   │   ├── notification.py
│   │   │   ├── shopify_order.py
│   │   │   └── delivery_request.py
│   │   ├── schemas/             # Pydantic response/request schemas
│   │   ├── services/            # Business logic
│   │   │   ├── par_calculator.py       # Core bake/dispatch algorithm
│   │   │   ├── inventory_sync.py       # Pull from Mall PARs sheet
│   │   │   ├── mall_pars_reader.py     # Read closing inventory
│   │   │   ├── bake_sheet_reader.py    # Read Morning PARs
│   │   │   ├── sheets_median.py        # Read Dispatch PARs medians
│   │   │   ├── clover_ingest.py        # Clover sales → DB
│   │   │   ├── shopify_sync.py         # Shopify orders → DB
│   │   │   ├── live_sales.py           # Real-time sales polling
│   │   │   └── transition_tracker.py   # Track DB vs sheet readiness
│   │   └── auth/
│   │       ├── dependencies.py  # require_role, require_module, get_current_user
│   │       ├── jwt_handler.py
│   │       └── roles.py
│   ├── seed_data.py             # Initial DB seed (flavors, locations, users)
│   ├── backfill_from_sheet.py   # One-time Sales History import
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    ├── src/
    │   ├── app/                 # App Router pages
    │   │   ├── login/
    │   │   ├── bake/
    │   │   ├── dispatch/
    │   │   ├── store/
    │   │   │   ├── page.tsx     # Location picker
    │   │   │   └── [locationId]/page.tsx  # Actual dashboard
    │   │   ├── ops/             # Live operations dashboard
    │   │   ├── analytics/
    │   │   ├── orders/
    │   │   └── admin/
    │   │       ├── page.tsx
    │   │       ├── UsersTab.tsx
    │   │       ├── FlavorsTab.tsx
    │   │       └── ParSettingsTab.tsx
    │   ├── components/
    │   │   ├── layout/
    │   │   │   └── AppShell.tsx        # Nav, header, auth guard
    │   │   └── shared/
    │   │       ├── EditableCell.tsx
    │   │       ├── ExportBar.tsx       # Print + CSV
    │   │       ├── NotificationBell.tsx
    │   │       ├── Toast.tsx
    │   │       └── ErrorBoundary.tsx
    │   ├── lib/
    │   │   ├── api.ts                  # Axios client w/ auth interceptor
    │   │   ├── types.ts                # TypeScript types (matches backend)
    │   │   └── constants.ts            # Nav items, role defaults
    │   └── stores/
    │       ├── authStore.ts            # Zustand: role, token, displayName
    │       └── dateStore.ts            # Zustand: selected date
    └── Dockerfile
```

---

## 🔄 Data Flow

### 1. Daily Plan Generation (Nightly, 4:57 AM PR time)

```
Cloud Scheduler
  └─▶ POST /api/cron/nightly-pipeline
      ├─▶ ingest_sales_for_date(yesterday)      # Clover → daily_sales
      ├─▶ generate_dispatch_plan(today)         # → dispatch_plans table
      │     └─▶ compute_four_week_median(DB) → par_calculator
      └─▶ generate_bake_plan(today)             # → bake_plans table
            └─▶ read Morning PARs sheet for forecast + reduction %
```

### 2. Live Sales (Every 5 min, 8am-10pm)

```
Cloud Scheduler
  └─▶ POST /api/cron/live-sales
      └─▶ poll_live_sales()
          ├─▶ CloverDataFetcher.fetch_orders_for_date(today) × 6 locations
          ├─▶ aggregate by (location, flavor)
          └─▶ UPSERT inventory.live_sales
```

### 3. Inventory Sync from Google Sheet (Every 30 min)

```
Cloud Scheduler
  └─▶ POST /api/cron/sync-inventory
      └─▶ sync_inventory_from_sheet(today)
          ├─▶ Google Sheets API: batchGet ranges for 6 locations
          ├─▶ Parse each location's 13-col block (VSJ is special, 4 cols)
          └─▶ UPSERT inventory (beginning, received, closing, waste)
```

### 4. User Interaction

```
Browser
  └─▶ GET https://frontend.run.app/bake
      └─▶ TanStack Query fetches /api/bake/2026-04-21
          └─▶ FastAPI → SQLAlchemy → Cloud SQL
              └─▶ Returns JSON
          └─▶ React renders table with green editable cells

User clicks a cell, types 250, presses Enter
  └─▶ PATCH /api/bake/2026-04-21/{flavor_id}
      └─▶ Update bake_plans.override_amount
      └─▶ TanStack Query invalidates + refetches
```

---

## 🔐 Authentication & Authorization

### Login flow

1. User POSTs username/password to `/api/auth/login` (OAuth2 form data)
2. Backend validates bcrypt hash, issues JWT signed with `JWT_SECRET` (HS256, 8-hour expiry)
3. Frontend stores JWT in Zustand `authStore` (persisted to localStorage)
4. All subsequent requests include `Authorization: Bearer {token}` header
5. Backend decodes JWT via `get_current_user` dependency

### Role-based access

Two layers of protection:

1. **Module-level** — `require_module("dispatch")` — checks if the user's role includes the module in `ROLE_PERMISSIONS` map
2. **Role-specific** — `require_role(Role.ADMIN)` — requires an exact role (or one of several)

Example from `cron_routes.py`:
```python
def verify_cron_caller(x_cron_key, authorization):
    if x_cron_key == CRON_API_KEY:
        return "scheduler"
    # else fall back to JWT admin check
```

### Cron authentication

Cloud Scheduler calls `/api/cron/*` with `X-Cron-Key` header. The key is stored in Cloud Run env as `CRON_API_KEY` (should be different from `JWT_SECRET`).

---

## 🧮 Core Algorithm — PAR Calculator

The heart of the platform is in `backend/app/services/par_calculator.py`.

### 4-Week 2-Day-Sum Median

For a target date, sum each (day + next day) from 7/14/21/28 days ago. Take median of non-zero sums.

```python
def compute_four_week_median(db, location_id, flavor_id, target_date, weeks=4):
    two_day_sums = []
    for w in range(1, weeks + 1):
        day1 = target_date - timedelta(days=w * 7)
        day2 = day1 + timedelta(days=1)
        total = sales_on(day1) + sales_on(day2)
        if total > 0:
            two_day_sums.append(total)
    return statistics.median(two_day_sums) if two_day_sums else 0, len(two_day_sums)
```

### Dispatch PAR

```python
raw_par = median × (1 - reduction_pct)
adjusted_par = max(round(raw_par), minimum_par)
amount_to_send = max(adjusted_par - live_inventory, 0)
```

### Bake Plan (VSJ-centric)

```python
total_projection = round((mall_forecast + sales_trend_median) × (1 - reduction_pct))
amount_to_bake = max(0, total_projection - closing_inv_yesterday) + missing_for_malls
```

Where:
- `mall_forecast` = 4-week median of past Dispatch PARs grand totals (read from Morning PARs sheet G column)
- `sales_trend_median` = 4-week median of VSJ's own sales (from our DB, or fallback table for new flavors)
- `missing_for_malls` = 2nd-delivery shortfall (read from Morning PARs sheet E column during transition)

### Fallback values (new flavors with no history)

Per-location, per-day-of-week table:

| Location | Thu | Fri | Sat | Sun | Mon-Wed |
|---|---|---|---|---|---|
| VSJ | 48 | 48 | 48 | 48 | 48 |
| Plaza Las Americas | 30 | 30 | 30 | 20 | 15 |
| Other malls | 15 | 15 | 10 | 5 | 10 |

For Mon/Tue/Wed, it first tries yesterday's actual sales before falling back to the default.

---

## 🔔 Notifications

### Data model
- `notifications` table with `kind`, `severity`, `title`, `body`, `target_role`, `target_user_id`, `is_read`
- Expire after 14 days (retention in query, not hard delete)

### Who sees what
- Admin sees ALL notifications
- Others see only those where `target_role == user.role` OR `target_user_id == user.id` OR broadcast (both null)

### Triggers (3 types)
1. `delivery_request` — created when `POST /api/inventory/delivery-request/{location_id}` is called
2. `low_stock` — created by `POST /api/cron/check-alerts` when sell-through > 80%
3. `ingest_failure` — created when nightly pipeline ingest step throws

### Frontend polling
`NotificationBell` component polls `/api/notifications/unread-count` every 30 seconds.

---

## 🗃️ Database Schema

Key tables:

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | Login accounts | `username`, `role`, `location_id`, `password_hash` |
| `flavors` | Cookie flavors | `code` (A-N + S1/S2), `name`, `is_active`, `sort_order` |
| `locations` | Malls + VSJ | `name`, `display_name`, `clover_merchant_id` |
| `daily_sales` | Historical sales | `sale_date`, `location_id`, `flavor_id`, `quantity`, `source` |
| `inventory` | Per-day, per-location stock | `inventory_date`, `location_id`, `flavor_id`, `beginning_inventory`, `received_cookies`, `live_sales`, `closing_inventory`, waste columns |
| `dispatch_plans` | Generated dispatch | `plan_date`, `location_id`, `flavor_id`, `adjusted_par`, `amount_to_send`, `override_amount`, `dispatch_status` |
| `bake_plans` | Generated bake | `plan_date`, `flavor_id`, `amount_to_bake`, `missing_for_malls`, `closing_inv_yesterday`, `mall_forecast`, `sales_trend_median`, `total_projection`, `override_amount` |
| `par_settings` | Per-location settings | `location_id`, `effective_date`, `reduction_pct`, `minimum_par`, `median_weeks` |
| `notifications` | In-app alerts | `kind`, `severity`, `target_role`, `target_user_id`, `is_read`, `created_at` |
| `shopify_orders` | Online order tracking | `order_number`, `customer_name`, `total_price`, `delivery_status`, `refund_status` |
| `delivery_requests` | 2nd delivery log | `request_date`, `location_id`, `requested_by`, `status`, `notes` |

### Migrations
Currently using `create_all()` from `Base.metadata` on startup (no Alembic). The `run_migrations()` hook in `main.py` adds any missing columns on startup (idempotent).

---

## 🔌 External Integrations

### Google Sheets
- **Read:** Sales History, Mall PARs, Dispatch PARs, Morning PARs
- **Write:** Previously wrote live sales back to Mall PARs — **disabled** due to race condition with the legacy inventory-updater Cloud Run Job
- **Auth:** Service account JSON (not in repo)

### Clover POS
- Legacy Python code in `backend/legacy/` (old inventory-updater)
- Used for `fetch_clover_data.py` → orders → item-level sales
- Config: `merchants.json` with API tokens per merchant (not in repo)

### Shopify
- `shopify_sync.py` pulls orders via Shopify Admin API
- Orders imported into `shopify_orders` table
- Config: `shopify_config.json` (not in repo)

---

## 📊 Observability

### Logs
- Cloud Run captures stdout/stderr from both services
- Python: standard `logging` module → `INFO` level
- Access via: Google Cloud Console → Cloud Run → service → Logs tab

### Metrics
- Not yet instrumented with Prometheus/Datadog
- Cloud Run built-in metrics: request count, latency, memory, CPU

### Alerts
- No automatic alerting on infra (yet)
- Notifications table captures operational issues (ingest failures, low stock)
