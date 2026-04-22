# Drunken Cookies Platform — Documentation

Welcome. This folder contains everything you need to understand, use, operate, and extend the Drunken Cookies Operations Platform.

## 📚 Documentation Index

### For end users
- **[User Guide](USER_GUIDE.md)** — How each role (kitchen, dispatch, store manager, ops) uses the platform day-to-day
- **[Admin Guide](ADMIN_GUIDE.md)** — Managing users, flavors, PAR settings

### For operators
- **[Operations Guide](OPERATIONS.md)** — Daily operations, scheduled jobs, troubleshooting
- **[Deployment Guide](DEPLOYMENT.md)** — How to deploy to production, environment setup

### For developers
- **[Architecture](ARCHITECTURE.md)** — System design, data flow, tech stack
- **[API Reference](API.md)** — Endpoint documentation

---

## 🔥 Quick Start

1. **Web app:** https://dc-platform-frontend-703996360436.us-central1.run.app
2. **Default admin:** `admin` / `admin123` — **change this immediately after first login**
3. **Backend API:** https://dc-platform-backend-703996360436.us-central1.run.app/api/docs (Swagger)

---

## 🏗️ What This Platform Replaces

The platform replaces **4 Google Sheets** that the business used for operations:

| Google Sheet | Replaced by |
|---|---|
| Sales History | `daily_sales` table + DB-computed medians |
| Mall PARs | Store Dashboard (per-location inventory) |
| Dispatch PARs | Dispatch Board |
| Morning PARs | Bake Board |

The Google Sheets are still running in parallel during the transition. The platform syncs from them every 30 minutes and computes its own plans. Once the team is fully comfortable, the sheets can be retired.

---

## 🧩 Modules

1. **Bake Board** — Morning bake plan for VSJ (kitchen staff)
2. **Dispatch Board** — What cookies to send to each mall (dispatch team)
3. **Store Dashboard** — Per-location inventory + waste tracking (store managers)
4. **Live Operations** — Real-time sell-through per location
5. **Analytics** — Historical sales trends
6. **Orders** — Shopify order management
7. **Admin** — User, flavor, and PAR settings management

---

## 🎯 Key Design Decisions

- **Parallel operation with Google Sheets** — Zero disruption during rollout. Read from sheets, compute locally, compare nightly.
- **Role-based access** — Each role sees only what they need. Kitchen sees bake plan, store managers see only their store.
- **VSJ-centric bake plan** — Matches the existing operational model. Old San Juan (VSJ) is the bakery; all other locations receive cookies from VSJ.
- **DB-first median** — Once 4+ weeks of data exist, we compute medians from our own DB instead of the sheets.
- **Staff-facing, not dev-facing** — Every config (flavors, users, PAR reduction %) is editable via the web admin panel.

---

## 📞 Support

- **Repo:** https://github.com/christiandlbanzon/drunkencookieswebplatform
- **Issues:** Track bugs and feature requests via GitHub Issues
- **Production logs:** Google Cloud Console → Cloud Run → `dc-platform-backend` / `dc-platform-frontend` → Logs
