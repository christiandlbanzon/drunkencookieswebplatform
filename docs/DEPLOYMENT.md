# Deployment Guide

How to deploy, configure, and operate the Drunken Cookies Platform in production.

## 🌐 Production URLs

| Service | URL |
|---|---|
| **Frontend** | https://dc-platform-frontend-703996360436.us-central1.run.app |
| **Backend** | https://dc-platform-backend-703996360436.us-central1.run.app |
| **API Docs (Swagger)** | https://dc-platform-backend-703996360436.us-central1.run.app/api/docs |

## 🏢 GCP Project

- **Project ID:** `boxwood-chassis-332307`
- **Project Name:** Drunken Cookies Automations
- **Region:** `us-central1`

---

## 🚀 Deploying Changes

### Backend

```bash
cd backend
gcloud run deploy dc-platform-backend \
  --source . \
  --region us-central1 \
  --project boxwood-chassis-332307
```

This:
1. Uploads source to Google Cloud Build
2. Builds the Docker image from `backend/Dockerfile`
3. Deploys to Cloud Run with a new revision number
4. Routes 100% traffic to the new revision

Build takes ~3-5 minutes.

### Frontend

```bash
cd frontend
gcloud run deploy dc-platform-frontend \
  --source . \
  --region us-central1 \
  --project boxwood-chassis-332307
```

**Important:** The frontend's `NEXT_PUBLIC_API_URL` is inlined at build time from `.env.production`. If you need to change the backend URL, update `.env.production` BEFORE deploying.

---

## 🔐 Environment Variables

### Backend (`dc-platform-backend`)

Set via `gcloud run services update` or Cloud Console:

```bash
gcloud run services update dc-platform-backend \
  --region us-central1 \
  --project boxwood-chassis-332307 \
  --update-env-vars KEY=VALUE
```

| Variable | Required | Description |
|---|---|---|
| `DB_URL` | ✅ | PostgreSQL connection string |
| `JWT_SECRET` | ✅ | Random string for signing tokens (32+ chars) |
| `CRON_API_KEY` | ✅ | Separate secret for cron authentication |
| `JWT_EXPIRATION_MINUTES` | | Default: 480 (8 hours) |
| `GOOGLE_SERVICE_ACCOUNT_FILE` | ✅ | Path to service account JSON (bundled in Docker image) |
| `SALES_SHEET_ID` | ✅ | Sales History sheet ID |
| `MALL_PARS_SHEET_ID` | ✅ | Mall PARs sheet ID |
| `DISPATCH_PARS_SHEET_ID` | ✅ | Dispatch PARs sheet ID |
| `MORNING_PARS_SHEET_ID` | ✅ | Morning PARs sheet ID |
| `SHOPIFY_STORE_NAME` | | For Shopify order sync |
| `SHOPIFY_API_TOKEN` | | |
| `CORS_ORIGINS` | ✅ | JSON array of allowed frontend origins |
| `DUAL_WRITE_ENABLED` | | Default: `false` (sheet writes disabled) |
| `TIMEZONE` | | Default: `America/Puerto_Rico` |

### Frontend (`dc-platform-frontend`)

Set in `frontend/.env.production` BEFORE build:

```
NEXT_PUBLIC_API_URL=https://dc-platform-backend-703996360436.us-central1.run.app/api
```

---

## 🗄️ Database (Cloud SQL)

### Connecting

Production PostgreSQL is at `34.31.68.95`. Connect with any tool:

- **TablePlus / DBeaver / pgAdmin**
  - Host: `34.31.68.95`
  - Port: `5432`
  - Database: `drunken_cookies`
  - User: `platform`
  - Password: (in Cloud Run env `DB_URL`)

- **Command line:**
  ```bash
  psql "postgresql://platform:PASSWORD@34.31.68.95:5432/drunken_cookies"
  ```

### Backups

Cloud SQL auto-backups enabled (daily, 7-day retention). See Cloud Console → SQL → instance → Backups.

To manually back up:
```bash
gcloud sql backups create --instance=drunken-cookies-db --project=boxwood-chassis-332307
```

### Migrations

No Alembic — we use `Base.metadata.create_all()` on app startup. Additional columns are added idempotently in `app/main.py` via the `run_migrations()` hook.

**To add a new column:**
1. Update the SQLAlchemy model
2. Add to the `new_cols` dict in `main.py run_migrations()`
3. Deploy — the ALTER TABLE runs automatically on startup

**To add a new table:**
1. Create the model in `app/models/`
2. Import it in `main.py run_migrations()`
3. Add `Base.metadata.tables["table_name"].create(bind=engine)` if missing
4. Deploy

---

## ⏰ Scheduled Jobs (Cloud Scheduler)

All jobs POST to `/api/cron/*` with `X-Cron-Key` header.

### Current jobs

| Job | Schedule (PR time) | Endpoint |
|---|---|---|
| `dc-platform-daily-plans` | `57 4 * * *` | `/api/cron/nightly-pipeline` |
| `dc-platform-sync-inventory` | `*/30 7-23 * * *` | `/api/cron/sync-inventory` |
| `dc-platform-check-alerts` | `*/30 8-22 * * *` | `/api/cron/check-alerts` |
| `dc-platform-live-sales` | `*/5 8-22 * * *` | `/api/cron/live-sales` |
| `dc-platform-sync-orders` | `3,33 * * * *` | `/api/cron/sync-orders` |

### Adding a new job

```bash
gcloud scheduler jobs create http dc-platform-my-new-job \
  --project boxwood-chassis-332307 \
  --location us-central1 \
  --schedule "0 8 * * *" \
  --time-zone "America/Puerto_Rico" \
  --uri "https://dc-platform-backend-703996360436.us-central1.run.app/api/cron/my-endpoint" \
  --http-method POST \
  --headers "X-Cron-Key=YOUR_CRON_KEY,User-Agent=Google-Cloud-Scheduler" \
  --description "What this job does"
```

### Listing / editing

```bash
# List
gcloud scheduler jobs list --project boxwood-chassis-332307 --location us-central1

# Pause
gcloud scheduler jobs pause JOB_NAME --project boxwood-chassis-332307 --location us-central1

# Run manually (for testing)
gcloud scheduler jobs run JOB_NAME --project boxwood-chassis-332307 --location us-central1

# Delete
gcloud scheduler jobs delete JOB_NAME --project boxwood-chassis-332307 --location us-central1
```

---

## 🔑 Local Development

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate              # Windows
source venv/bin/activate           # Mac/Linux
pip install -r requirements.txt

# Copy the example .env and fill in values
cp .env.example .env
# Edit .env — at minimum set DB_URL pointing to a local PostgreSQL

# Initialize the database with seed data
python seed_data.py

# Run
uvicorn app.main:app --reload
```

Visit http://localhost:8000/api/docs for Swagger.

### Frontend

```bash
cd frontend
npm install

# Create .env.local with local backend URL
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local

npm run dev
```

Visit http://localhost:3000.

### Test credentials (after `seed_data.py`)

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `ops_mgr` | `ops123` | ops_manager |
| `kitchen1` | `kitchen123` | kitchen |
| `dispatch1` | `dispatch123` | dispatch |
| `store_sp` | `store123` | store_manager (San Patricio) |

---

## 🔄 First-Time Setup (Fresh GCP project)

### 1. Create Cloud SQL instance
```bash
gcloud sql instances create drunken-cookies-db \
  --database-version=POSTGRES_14 \
  --region=us-central1 \
  --tier=db-f1-micro \
  --project=YOUR_PROJECT
```

### 2. Create the database
```bash
gcloud sql databases create drunken_cookies --instance=drunken-cookies-db
```

### 3. Create a user
```bash
gcloud sql users create platform --instance=drunken-cookies-db --password=STRONG_PASSWORD
```

### 4. Deploy backend (source deployment)
```bash
cd backend
gcloud run deploy dc-platform-backend --source . --region us-central1

# Set env vars
gcloud run services update dc-platform-backend \
  --region us-central1 \
  --update-env-vars DB_URL=postgresql://platform:STRONG_PASSWORD@PUBLIC_IP:5432/drunken_cookies
gcloud run services update dc-platform-backend \
  --region us-central1 \
  --update-env-vars JWT_SECRET=$(openssl rand -hex 32)
gcloud run services update dc-platform-backend \
  --region us-central1 \
  --update-env-vars CRON_API_KEY=$(openssl rand -hex 32)
# ... set all other env vars
```

### 5. Seed the database
```bash
# Temporarily connect to Cloud SQL from your laptop
# (allow your IP in Cloud SQL settings)
DB_URL=... python seed_data.py
```

### 6. Backfill sales history (optional)
```bash
DB_PASS=your_password python backfill_from_sheet.py
```

### 7. Deploy frontend
```bash
cd frontend
echo "NEXT_PUBLIC_API_URL=https://dc-platform-backend-....run.app/api" > .env.production
gcloud run deploy dc-platform-frontend --source . --region us-central1
```

### 8. Create scheduled jobs
See "Scheduled Jobs" section above.

### 9. Upload service account
Put your Google service account JSON at `backend/service_account.json`. It's bundled into the Docker image via the COPY line in `Dockerfile`.

---

## 🐛 Rolling Back

If a deployment breaks something:

```bash
# List recent revisions
gcloud run revisions list --service=dc-platform-backend --region=us-central1

# Route traffic back to a previous revision
gcloud run services update-traffic dc-platform-backend \
  --region=us-central1 \
  --to-revisions=dc-platform-backend-00035-ckh=100
```

---

## 📦 Docker Images

Both services use simple Dockerfiles:

### backend/Dockerfile
- Base: `python:3.12-slim`
- Copies source, installs `requirements.txt`
- Runs `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### frontend/Dockerfile
- Base: `node:20-alpine`
- Multi-stage: builds Next.js, serves standalone output
- Runs on port 3000

Images are built by Cloud Build when you run `gcloud run deploy --source .`.

---

## 💰 Cost

Approximate monthly cost (light usage):

| Service | Cost |
|---|---|
| Cloud Run (backend) | $5-15 (scales to zero) |
| Cloud Run (frontend) | $2-10 |
| Cloud SQL (db-f1-micro) | $8-15 |
| Cloud Scheduler (7 jobs) | Free (first 3 free, rest ~$0.10/month) |
| Cloud Build | Free (first 120 min/day) |
| **Total** | **~$15-40/month** |

For a business running 6 locations + VSJ bakery, that's negligible.
