# Admin Guide

This guide is for anyone with the `admin` role. It covers user management, flavor management, and PAR settings.

## 🚀 Accessing the Admin Panel

1. Log in as `admin` (or any user with admin role)
2. Click **Admin** in the top navigation
3. Three tabs: **Users | Flavors | PAR Settings**

---

## 👥 Managing Users

### Create a new user

1. Admin → Users → click orange **"+ Add User"**
2. Fill in:
   - **Username** — login name, no spaces (e.g., `maria`, `jose_vsj`, `dispatch_team`)
   - **Password** — starting password (they can change later via reset)
   - **Display Name** — full name shown in the header (e.g., `Maria Rivera`)
   - **Role** — pick one:
     | Role | Access |
     |---|---|
     | `admin` | Everything |
     | `ops_manager` | All boards, no admin panel |
     | `kitchen` | Bake Board only |
     | `dispatch` | Dispatch Board only |
     | `store_manager` | One store only |
   - **Location ID** — only appears if role is `store_manager`:
     | ID | Location |
     |---|---|
     | 1 | San Patricio |
     | 2 | Plaza del Sol |
     | 3 | VSJ (Viejo San Juan) |
     | 4 | Montehiedra |
     | 5 | Plaza Las Americas |
     | 6 | Plaza Carolina |
3. Click green **"Create User"**

The user can now log in at the frontend URL with their username + password.

### Edit an existing user

In the user table:
- **Edit** button → change display name or role inline, then click **Done**
- **Reset PW** button → type new password, click **Save**
- **Active checkbox** → uncheck to disable login without deleting
- **Delete** button → permanently remove user (cannot delete the `admin` account)

### Example: Onboarding a new team member

Maria Santos is the new Plaza Carolina manager:
1. **Username:** `maria_plaza_carolina`
2. **Password:** `temp-plazacarolina-2026` (she'll change it)
3. **Display Name:** `Maria Santos`
4. **Role:** `store_manager`
5. **Location ID:** `6`

Maria gets the URL + credentials. She logs in, sees only Plaza Carolina, and can reset her password by asking you to use the "Reset PW" button.

---

## 🍪 Managing Flavors

The platform has 14 flavor slots (A-N) + 2 cookie shot slots (S1, S2). Each slot has a code, name, active status.

### Rename a flavor

Common scenario: Sticky Toffee Pudding is retired and replaced with Dubai Chocolate.

1. Admin → Flavors
2. Find slot G (row shows "Sticky Toffee Pudding")
3. Click **"Rename"** button (or just click the name)
4. Type the new name: `Dubai Chocolate`
5. Click away or press Tab — saves automatically

**Important:** This only changes the flavor name in the platform. You also need to:
- Update the Sales History Google Sheet header (if still in use) — the IMPORTRANGE relies on name match
- Update the Dispatch PARs and Morning PARs flavor name column

### Reassign a flavor slot (critical — read this)

If slot I was "Guava Crumble" (retired) and is now "Linzer Cake" (new):

1. **Rename** slot I from "Guava Crumble" to "Linzer Cake"
2. Click **"Clear Sales"** button on that row — this deletes ALL historical sales for slot I
   - ⚠️ **Irreversible.** Only do this when genuinely reassigning a slot to a brand-new flavor.
   - Without clearing, the old flavor's sales history will pollute the new flavor's median.
3. Confirm the prompt
4. The new flavor starts with zero sales history. Its median will use **day-of-week fallback values** until it accumulates data:
   | Location | Thu | Fri | Sat | Sun | Mon-Wed |
   |---|---|---|---|---|---|
   | VSJ | 48 | 48 | 48 | 48 | 48 |
   | Plaza Las Americas | 30 | 30 | 30 | 20 | 15 |
   | Other malls | 15 | 15 | 10 | 5 | 10 |

5. After ~4 weeks of real sales, the DB-computed median takes over automatically.

### Deactivate a flavor

Uncheck the **Active** box on a flavor row. The flavor will:
- Still show in the database (preserves history)
- Be hidden from dispatch/bake plans
- Not show in store dashboards

To reactivate, just check the box again.

---

## ⚙️ PAR Settings

PAR settings control how each location computes its dispatch PAR from the median.

### What they mean

| Setting | Description | Default |
|---|---|---|
| **Reduction %** | Multiplier applied to the median. `0.15` = reduce by 15%, `-0.20` = increase by 20% (extra safety stock) | `0.0` |
| **Minimum PAR** | Floor — no flavor gets less than this per location | `10` |
| **Median Weeks** | How many weeks back to compute the 4-week median from | `4` |

The formula:
```
raw_par = median × (1 - reduction_pct)
adjusted_par = MAX(raw_par, minimum_par)
send = MAX(adjusted_par - live_inventory, 0)
```

### Change a location's settings

1. Admin → PAR Settings
2. Click a location button (e.g., "Plaza Las Americas")
3. Fill in the form:
   - Reduction % (decimal, e.g., `0.15` for 15%)
   - Minimum PAR (integer)
   - Median Weeks (integer, usually 4)
4. Click **"Apply (effective today)"**

The new settings take effect from today's plan onwards. The history of past settings stays in the table below for audit purposes.

### Effective dating

Each PAR settings row has an `effective_date`. The system uses the most recent settings on or before the plan date. So if you set reduction to 15% today (4/21), it applies to 4/21 and all future plans — but 4/20's plan uses whatever was set before.

---

## 🔔 Notification Triggers

As admin you see all notifications. They're automatically created when:

| Event | Trigger | Severity |
|---|---|---|
| Store manager requests 2nd delivery | Button click | Warning |
| Any mall hits >80% sell-through | Every 30 min cron | Critical |
| Nightly sales ingest fails | Cron job error | Critical |

Manually firing notifications isn't currently exposed in the UI — you can do it via the API if needed.

---

## 🛡️ Security Best Practices

1. **Change the default admin password immediately.**
   - `admin` / `admin123` is the seed default and is publicly documented.
2. **Create a personal admin account** — don't share the `admin` login.
3. **Set CRON_API_KEY** (in Cloud Run env vars) to be different from `JWT_SECRET`. If they match, a leaked scheduler key could forge admin tokens.
4. **Rotate JWT_SECRET every 6 months.** Doing so will log everyone out, requiring re-login.
5. **Deactivate (don't delete) departed staff** so audit trails remain intact.

---

## 📋 Common Admin Tasks — Cheat Sheet

| Task | Where |
|---|---|
| Add a new employee | Admin → Users → + Add User |
| Someone forgot password | Admin → Users → Reset PW |
| Employee leaves | Admin → Users → uncheck Active |
| New flavor launch | Admin → Flavors → Rename slot + Clear Sales |
| Change location's PAR reduction | Admin → PAR Settings → pick location → fill form |
| Temporarily retire a flavor | Admin → Flavors → uncheck Active |
| Check who's logged in | Look at `users` table via Cloud SQL (not exposed in UI yet) |
