# Operations Guide

Day-to-day operations, monitoring, and troubleshooting.

## 🕒 Daily Timeline

| Time (PR) | Event | What's happening |
|---|---|---|
| 11:59 PM | Yesterday's sales ingest | Clover data for previous day pulled into `daily_sales` |
| 4:57 AM | Nightly pipeline | Dispatch + bake plans generated for today |
| 7:00 AM | Staff arrives at VSJ | Kitchen checks Bake Board |
| 7:00 AM - 11:00 PM | Inventory sync (every 30 min) | Mall PARs sheet → DB |
| 8:00 AM | Mall stores open | Store managers enter beginning inventory |
| 8:00 AM - 10:00 PM | Live sales polling (every 5 min) | Clover → `inventory.live_sales` |
| 8:00 AM - 10:00 PM | Alert check (every 30 min) | Low stock notifications fire |
| Every :03 and :33 | Shopify order sync | Orders pulled into `shopify_orders` |
| ~9:00 PM | Stores close | Managers enter closing inventory |

---

## 🔍 Monitoring

### Health checks

Quick one-liner to verify everything is running:

```bash
curl -s https://dc-platform-backend-703996360436.us-central1.run.app/health
# Should return: {"status": "ok", "database": "connected"}
```

### Cloud Run metrics

Google Cloud Console → Cloud Run → service → Metrics tab

Watch for:
- **Request count** — steady during business hours (8am-10pm)
- **Request latency p95** — should be < 500ms
- **Instance count** — scales between 0-1 normally
- **Container CPU** — should not be pegged at 100%
- **Error rate (5xx)** — should be near 0%

### Cloud Scheduler status

```bash
gcloud scheduler jobs list --project boxwood-chassis-332307 --location us-central1
```

All should show `ENABLED`. Check the last-run result:

```bash
gcloud scheduler jobs describe dc-platform-daily-plans --project boxwood-chassis-332307 --location us-central1
```

### Database

Connect with psql or a GUI tool (see [DEPLOYMENT.md](DEPLOYMENT.md#connecting)) and run:

```sql
-- Today's data health check
SELECT COUNT(*) FROM dispatch_plans WHERE plan_date = CURRENT_DATE;  -- expect 84+ (6 locs × 14 flavors)
SELECT COUNT(*) FROM bake_plans WHERE plan_date = CURRENT_DATE;      -- expect 13-14

-- Recent sales ingested
SELECT sale_date, COUNT(*), SUM(quantity)
FROM daily_sales
WHERE sale_date >= CURRENT_DATE - 7
GROUP BY sale_date ORDER BY sale_date DESC;

-- Unread notifications by role
SELECT target_role, COUNT(*) FROM notifications
WHERE is_read = false AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY target_role;
```

---

## 🛠️ Common Operations

### Manually trigger a scheduled job

```bash
gcloud scheduler jobs run dc-platform-daily-plans \
  --project boxwood-chassis-332307 \
  --location us-central1
```

Or hit the endpoint directly:

```bash
curl -X POST \
  -H "X-Cron-Key: YOUR_CRON_KEY" \
  https://dc-platform-backend-703996360436.us-central1.run.app/api/cron/sync-inventory
```

### Force regenerate today's plans

Log in as admin and hit:
- `POST /api/dispatch/2026-04-21/generate`
- `POST /api/bake/2026-04-21/generate`

Or via the UI — click "Generate Plan" on the Dispatch / Bake Board.

### Re-sync inventory for a specific date

```bash
curl -X POST \
  -H "X-Cron-Key: YOUR_CRON_KEY" \
  "https://dc-platform-backend-703996360436.us-central1.run.app/api/cron/sync-inventory?target_date=2026-04-20"
```

### Back-date a plan (e.g., fix a missing day)

Plans default to `today`. Any endpoint that accepts `target_date` will let you regenerate for a past date up to 7 days back:

```
POST /api/dispatch/2026-04-18/generate
POST /api/bake/2026-04-18/generate
```

---

## 🐛 Troubleshooting

### "Backend is down"

1. Check Cloud Run dashboard for error spikes
2. Tail logs:
   ```bash
   gcloud run logs read dc-platform-backend --region us-central1 --project boxwood-chassis-332307 --limit 50
   ```
3. Common causes:
   - DB connection refused → check Cloud SQL is up
   - OOM → scale up memory: `gcloud run services update ... --memory 1Gi`
   - Bad deployment → roll back to a previous revision

### "Bake plan shows 0 for everything"

Most likely: yesterday's closing inventory is very high (VSJ has plenty of leftover stock), so `MAX(0, projection - closing)` is 0 for every flavor.

Check:
```sql
SELECT flavor_id, closing_inv_yesterday, total_projection, amount_to_bake
FROM bake_plans WHERE plan_date = CURRENT_DATE;
```

### "Numbers don't match the Google Sheet"

Expected — the platform computes from its own data, which is usually 12-24 hours fresher than the sheet's IMPORTRANGE cache. Differences up to ~10% are normal.

If the difference is larger, check:
1. Did yesterday's sales ingest succeed? `SELECT MAX(sale_date) FROM daily_sales;`
2. Is the Mall PARs sheet syncing? Check `inventory` table for today.
3. Is the reduction % correct? It's read dynamically from Morning PARs J3 cell.

### "Linzer Cake (or other new flavor) shows too high"

Check if you cleared old sales history when reassigning the slot:
```sql
SELECT COUNT(*) FROM daily_sales WHERE flavor_id = 9;  -- Linzer Cake is slot I = id 9
```

If there are old records from the previous flavor (e.g., Guava Crumble), go to Admin → Flavors → click "Clear Sales" on that row.

### "Low stock alerts not firing"

1. Check the scheduler job is running: `gcloud scheduler jobs describe dc-platform-check-alerts ...`
2. Manually trigger: `gcloud scheduler jobs run dc-platform-check-alerts ...`
3. Check the logs for the alert endpoint
4. Verify a location actually has > 80% sell-through:
   ```sql
   SELECT l.name,
          SUM(i.beginning_inventory + i.received_cookies) as opening,
          SUM(i.live_sales) as sold,
          100.0 * SUM(i.live_sales) / SUM(i.beginning_inventory + i.received_cookies) as sell_through
   FROM inventory i JOIN locations l ON l.id = i.location_id
   WHERE i.inventory_date = CURRENT_DATE GROUP BY l.name;
   ```

### "Frontend loads forever / shows blank"

1. Check browser console for errors (F12)
2. Most common: `NEXT_PUBLIC_API_URL` is wrong in `.env.production`
3. Second most common: CORS error → update `CORS_ORIGINS` env var on backend
4. Force refresh (Ctrl+Shift+R) — Next.js cache can get stale

### "I can't log in"

1. Try the seeded admin: `admin` / `admin123`
2. If that fails, check DB:
   ```sql
   SELECT username, is_active FROM users WHERE username = 'admin';
   ```
3. If admin is missing, re-run `seed_data.py`
4. If password hash seems wrong (e.g., migrated DB), reset via:
   ```sql
   -- Generate a new bcrypt hash in Python first
   UPDATE users SET password_hash = '$2b$12$...' WHERE username = 'admin';
   ```

### "Inventory sync is way behind"

1. Check Cloud Scheduler `dc-platform-sync-inventory` is enabled and running
2. Check for Google Sheets API quota errors in logs
3. Manually run: `curl -X POST -H "X-Cron-Key: ..." .../api/cron/sync-inventory`
4. Verify service account has read access to the Mall PARs sheet

### "Notifications not appearing for a role"

Check:
1. Are notifications actually being created?
   ```sql
   SELECT * FROM notifications ORDER BY created_at DESC LIMIT 10;
   ```
2. Is `target_role` set correctly? Admin sees all; others only see their role or their user_id.
3. Is the user logged in with the right role?

---

## 🔄 Rolling Out a Change

### Backend change

1. Edit code locally
2. (Optional) Test locally with `uvicorn app.main:app --reload`
3. Commit and push to GitHub
4. Deploy: `gcloud run deploy dc-platform-backend --source . --region us-central1`
5. Verify: hit `/health` and a key endpoint
6. If broken, roll back (see [DEPLOYMENT.md](DEPLOYMENT.md#rolling-back))

### Frontend change

1. Edit code locally
2. Test with `npm run dev`
3. Commit and push
4. Deploy: `cd frontend && gcloud run deploy dc-platform-frontend --source . --region us-central1`
5. Force refresh browser (Ctrl+Shift+R) — service workers can cache

### Database change

1. Update the SQLAlchemy model in `app/models/`
2. Add migration logic in `app/main.py run_migrations()`:
   - New column: add to the `new_cols` dict
   - New table: add `Base.metadata.tables["name"].create(bind=engine)` if not in `existing_tables`
3. Deploy backend — migration runs on startup

For destructive changes (drop column, rename table), use raw SQL in migrations — we don't have Alembic set up.

---

## 📅 Regular Maintenance

### Weekly
- [ ] Check that all 6 stores entered closing inventory every day
- [ ] Review the analytics page for anomalies
- [ ] Check notification count — are too many low-stock alerts firing? Tune threshold if so.

### Monthly
- [ ] Review Cloud Run costs — are we within budget?
- [ ] Verify database backups are running (Cloud SQL → Backups tab)
- [ ] Audit active user list — deactivate anyone who left

### Quarterly
- [ ] Rotate `JWT_SECRET` and `CRON_API_KEY` (requires updating scheduler jobs)
- [ ] Review notification retention (currently 14 days — acceptable)
- [ ] Consider archiving old `daily_sales` / `inventory` / `dispatch_plans` rows (>1 year old)

### As needed
- [ ] Flavor launches: update Admin → Flavors
- [ ] New team members: Admin → Users
- [ ] Seasonal PAR adjustments: Admin → PAR Settings

---

## 🆘 Emergency Contacts

If the platform is down and blocking operations:

1. **Fall back to Google Sheets.** They're still the source of truth during transition. The legacy automation runs independently.
2. **Check Cloud Run dashboard** for obvious errors
3. **Roll back to the last known good revision** (see DEPLOYMENT.md)
4. **Post in team channel** with what you're seeing so ops knows

---

## 🧾 Audit Log

Currently there's no formal audit log. To see what changed:

- **Git history** — for code changes
- **Cloud Run revisions** — for deployments
- **Notifications** — for operational events
- **DB `updated_at`** columns — for record changes (where present)

Planned: add a `audit_log` table that captures who changed what field, when.
