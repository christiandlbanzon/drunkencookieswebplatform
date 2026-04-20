# Drunken Cookies Operations Platform

Unified web platform replacing the Mall PARs, Dispatch PARs, Morning PARs, and Sales History Google Sheets. Built for the Drunken Cookies operations team (kitchen, dispatch, store managers).

## Stack

- **Backend:** FastAPI (Python 3.12), SQLAlchemy, PostgreSQL (Cloud SQL)
- **Frontend:** Next.js 14 (App Router), Tailwind CSS, Zustand, TanStack Query
- **Infra:** Google Cloud Run (backend + frontend), Cloud Scheduler (cron), Cloud SQL
- **Integrations:** Clover POS, Shopify, Google Sheets (read-only transition)

## Modules

1. **Bake Board** — Morning bake plan for VSJ (kitchen)
2. **Dispatch Board** — What to send to each mall today (dispatch team)
3. **Store Dashboard** — Per-location inventory tracking (store managers)
4. **Live Operations** — Real-time sell-through per location
5. **Analytics** — Sales trends and reporting
6. **Orders** — Shopify order management
7. **Admin** — User, flavor, PAR settings management

## Key Features

- Role-based access (admin / ops_manager / kitchen / dispatch / store_manager)
- Real-time inventory sync from Mall PARs Google Sheet (30 min cadence)
- Live sales polling from Clover POS every 5 min
- In-app notifications for low stock and 2nd delivery requests
- Print + CSV export on all main boards
- Dynamic reduction % (reads from Morning PARs J3 daily)
- Automatic fallback values for new flavor launches

## Directory Structure

```
platform/
├── backend/              # FastAPI app
│   ├── app/
│   │   ├── api/          # Routes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic (PAR calculator, sheet readers, etc.)
│   │   ├── schemas/      # Pydantic schemas
│   │   └── auth/         # JWT + role-based deps
│   ├── alembic/          # DB migrations (unused — we use startup migration)
│   ├── seed_data.py      # Seed flavors, locations, demo users
│   ├── backfill_from_sheet.py  # One-time backfill from Sales History sheet
│   └── Dockerfile
└── frontend/             # Next.js app
    ├── src/
    │   ├── app/          # App Router pages
    │   ├── components/   # Shared UI components
    │   ├── lib/          # API client, types, constants
    │   └── stores/       # Zustand stores
    └── Dockerfile
```

## Local Development

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env    # Fill in DB_URL, JWT_SECRET, etc.
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`.

## Deployment

Both services deploy to Google Cloud Run from source:

```bash
# Backend
cd backend
gcloud run deploy dc-platform-backend --source . --region us-central1

# Frontend
cd frontend
gcloud run deploy dc-platform-frontend --source . --region us-central1
```

## Environment Variables

### Backend (`.env`)

| Variable | Description |
|---|---|
| `DB_URL` | PostgreSQL connection string |
| `JWT_SECRET` | Random string for token signing |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | Path to service account JSON (for Google Sheets reads) |
| `SALES_SHEET_ID` | Sales History sheet ID |
| `MALL_PARS_SHEET_ID` | Mall PARs sheet ID |
| `DISPATCH_PARS_SHEET_ID` | Dispatch PARs sheet ID |
| `MORNING_PARS_SHEET_ID` | Morning PARs sheet ID |
| `DUAL_WRITE_ENABLED` | `false` (legacy — writes are disabled) |

### Frontend (`.env.production`)

| Variable | Description |
|---|---|
| `NEXT_PUBLIC_API_URL` | URL of deployed backend (inlined at build time) |

## Scheduled Jobs

All run via Google Cloud Scheduler (see Cloud Console):

| Job | Schedule | Purpose |
|---|---|---|
| `dc-platform-daily-plans` | 4:57 AM PR time | Generate dispatch + bake plans |
| `dc-platform-sync-inventory` | Every 30 min, 7am-11pm | Pull Mall PARs data into DB |
| `dc-platform-check-alerts` | Every 30 min, 8am-10pm | Fire low-stock notifications |
| `dc-platform-live-sales` | Every 5 min, 8am-10pm | Poll Clover for today's sales |
| `dc-platform-sync-orders` | :03 and :33 hourly | Sync Shopify orders |

## Security Notes

- `service_account.json` and all `.env*` files are gitignored
- JWT tokens expire after 8 hours
- Admin role is required for user/flavor management
- Role-based access enforced at the API layer (`require_role`, `require_module`)

## Default Admin Account

On first run, `seed_data.py` creates `admin` / `admin123`. **Change this immediately in production** via the Admin UI.
