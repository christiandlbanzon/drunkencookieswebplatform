# User Guide — Walkthrough by Role

This guide walks through how each role uses the platform day-to-day.

## 🔐 Logging In

1. Go to **https://dc-platform-frontend-703996360436.us-central1.run.app**
2. Enter your username and password
3. You'll land on your role's main page automatically

**Forgot your password?** Ask your admin to reset it via Admin → Users → Reset PW.

---

## 👨‍🍳 Kitchen Staff (role: `kitchen`)

**What you see:** Just the **Bake Board** — clean and focused.

### Your daily routine

1. **Arrive at VSJ** → open the web app on the tablet/phone
2. **Look at the Bake Board** for today's date
3. **"Total to Bake"** at the top is your target number of cookies
4. The table shows each flavor with:
   - **Bake** (green) — how many to bake
   - **Priority** — which flavors to start first (you can set this)
   - **Website** — online orders that need to be fulfilled
   - **Missing (Malls)** — top-ups needed for malls
   - **Closing Inv** — how many cookies are left from yesterday
   - **Mall Forecast + 4-Wk Median** — the math behind the plan

### Editing

- Click any **green cell** to type a number. Press Enter to save.
- If the plan says "bake 300" but you think you need 350, click the Bake cell and change it. Your override sticks.
- **Cooking Priority** — set 1-14 to order flavors by preference (optional).

### Exporting

- **Print / PDF** button top-right → opens print dialog. Choose "Save as PDF" if you want a file.
- **CSV** button → downloads a spreadsheet for records.

---

## 🚚 Dispatch Team (role: `dispatch`)

**What you see:** Just the **Dispatch Board**.

### Your daily routine

1. **Look at the Dispatch Board** — 6 location blocks (one per mall + VSJ)
2. For each location, you see a table:
   - **Flavor** | **4-Wk Median** | **PAR** | **Adj. PAR** | **Inventory** | **Send** | **%**
3. **"Send"** (green) is the number of cookies to pack and ship to that mall
4. **Total to send** is at the top of each location block
5. Scroll to the bottom for the **"Amount to Bake" summary** — same as the Google Sheet's grand total table

### Workflow

1. Pack cookies according to the "Send" amount for each mall
2. If the plan says 20 but you want to send 25, click the cell → edit → saves instantly
3. Once a location is packed, click the blue **"Packed"** button next to that location — status flips to `packed`
4. When the delivery truck leaves, click **"Sent"** — status flips to `sent`

### Alerts (the bell icon 🔔)

You'll get notifications for:
- **2nd Delivery Requests** — when a store manager asks for more cookies mid-day
- **Low Stock** — when a mall hits >80% sell-through, they're likely to need more

Click any notification to jump to the relevant page.

### Exporting

- **Print / PDF** — one page per location, great for handing physical packing slips to the delivery driver
- **CSV** — full dispatch plan for records

---

## 🏪 Store Manager (role: `store_manager`)

**What you see:** Just your own store's dashboard. You cannot see other stores.

### Your daily routine

#### Morning (when you open)
1. Open the app on your phone/tablet
2. The **Store Dashboard** shows all 14 flavors
3. Fill in the **green "Begin Inv."** column — how many cookies you started with
4. Fill in **"Received"** — how many cookies the delivery driver dropped off
5. **Opening** (blue) auto-calculates = Begin Inv + Received
6. **Live Sales** (green auto) updates every 5 min from Clover — don't touch

#### During the day
- Watch the **"Expected"** column (orange). It shows cookies you should have right now.
- If it goes negative or you're running low, click the red **"Request 2nd Delivery"** button
- Log any waste throughout the day in the yellow columns:
  - **Expired** — past shelf life
  - **Flawed** — broken, cracked, crushed
  - **Display** — used for display
  - **Given Away** — samples
  - **Production** — misshapen, soft, over/underbaked

#### End of day (closing)
1. Count your remaining cookies
2. Fill in the **"Closing"** column (gray — final stock for tomorrow)
3. System will warn you if the math doesn't add up

### Numbers not matching?

If you type something wrong, the platform will show a warning like:
> ⚠️ "Live sales (40) exceed opening stock (37). Check beginning inventory."

Fix the wrong number and save again.

---

## 📊 Operations Manager (role: `ops_manager`)

**What you see:** Bake Board, Dispatch Board, Store Dashboards (all), Live Ops, Analytics, Orders.

### Your daily routine

**Morning check-in (8-9 AM):**
1. **Live Ops** page — see sell-through per location as the day starts
2. **Bake Board** — confirm today's bake plan looks reasonable
3. **Dispatch Board** — confirm total dispatch to each mall

**Midday (12-2 PM):**
1. **Live Ops** — any location hitting yellow (>50%) or red (>80%) sell-through?
2. If yes, proactively talk to dispatch about a 2nd delivery before the store manager has to request one

**End of day (9-10 PM):**
1. **Store Dashboards** — spot-check that all stores entered their closing inventory
2. **Analytics** — review the day's sales vs forecast

### Live Ops Dashboard

Shows for each of 6 locations:
- **Sold Today** — Clover live sales (green)
- **Opening** — opening stock + deliveries
- **Dispatched** — total cookies sent from VSJ to this mall
- **Sell-through %** — green / yellow / red bar
  - 🟢 < 50% — no worries
  - 🟡 50-80% — keep watching
  - 🔴 > 80% — needs intervention

### Notifications

You get **all** operational notifications:
- 2nd delivery requests (also sent to dispatch)
- Low stock alerts
- Ingest failures (sales not synced overnight)

---

## 🔧 Admin (role: `admin`)

Admins see everything plus the **Admin** panel. See [ADMIN_GUIDE.md](ADMIN_GUIDE.md) for full details.

---

## 📤 Export & Printing (All Roles)

Every main page (Bake, Dispatch, Store, Orders) has two buttons in the top-right:

### Print / PDF
- Click → opens browser print dialog
- Headers, navigation, and buttons are hidden automatically — only data prints
- **For PDF:** choose "Save as PDF" as the printer
- Each section stays on one page (no awkward breaks)

### CSV
- Click → downloads a `.csv` file immediately
- Filename includes today's date: `bake-plan-2026-04-21.csv`, etc.
- Opens in Excel, Google Sheets, or Numbers
- Includes **all** columns — no hidden data

---

## 🔔 Notifications (All Roles)

The **bell icon** 🔔 in the top-right of every page shows alerts targeted at your role.

- **Red badge** = unread count
- Click the bell → dropdown shows recent notifications
- Click a notification → marks it read + jumps to the related page
- **"Mark all read"** at the top clears the badge

Notifications you'll see depend on your role:

| Notification | Who gets it |
|---|---|
| 2nd Delivery Requested | Dispatch, Ops Manager, Admin |
| Low Stock (>80% sell-through) | Dispatch, Ops Manager, Admin |
| Ingest Failure | Ops Manager, Admin |

Notifications auto-expire after 14 days.

---

## ❓ FAQ

**Q: I can't see the dashboard for other stores.**
A: Correct — store managers only see their assigned location. If you need access to another, ask admin to update your role to `ops_manager`.

**Q: The number I see is different from the Google Sheet.**
A: The platform pulls data from the sheet every 30 min, so they're usually in sync. Tiny differences (1-3 cookies per flavor) are expected because the platform uses slightly fresher data than the sheet's IMPORTRANGE cache.

**Q: How do I request a 2nd delivery?**
A: Store Dashboard → click the red "Request 2nd Delivery" button. Dispatch and ops will be notified instantly.

**Q: What if I enter a wrong number?**
A: Just click the cell and re-type. It overwrites instantly. The system also shows warnings if something's obviously wrong.

**Q: Do I need to be on wifi?**
A: Yes, for now. The app doesn't work offline (yet).
