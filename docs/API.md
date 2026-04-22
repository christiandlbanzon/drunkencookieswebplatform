# API Reference

Quick reference for the platform's REST API. For the full interactive docs, visit the Swagger UI:

**https://dc-platform-backend-703996360436.us-central1.run.app/api/docs**

## 🔐 Authentication

All endpoints except `/auth/login` and `/health` require a JWT.

### Login

```
POST /api/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

**Response:**
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "role": "admin",
  "display_name": "Admin",
  "location_id": null
}
```

Include token on subsequent requests:
```
Authorization: Bearer eyJhbGc...
```

Tokens expire after 8 hours.

---

## 📋 Endpoints by Module

### 🍪 Bake (`/api/bake`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/bake/{plan_date}` | `bake` module | Get bake plan for date |
| POST | `/api/bake/{plan_date}/generate` | `bake` module | Regenerate from sheet + DB |
| PATCH | `/api/bake/{plan_date}/{flavor_id}` | `bake` module | Override amount / priority / website demand |

Example:
```bash
curl -H "Authorization: Bearer TOKEN" \
  https://dc-platform-backend-...run.app/api/bake/2026-04-21
```

### 🚚 Dispatch (`/api/dispatch`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/dispatch/{plan_date}` | `dispatch` module | Get dispatch plan (all locations) |
| POST | `/api/dispatch/{plan_date}/generate` | `dispatch` module | Regenerate |
| PATCH | `/api/dispatch/{plan_date}/{location_id}/{flavor_id}` | `dispatch` module | Override send amount for one flavor |
| PATCH | `/api/dispatch/{plan_date}/{location_id}/confirm?new_status=packed` | `dispatch` module | Mark entire location packed/sent/received |

### 🏪 Inventory (`/api/inventory`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/inventory/{inv_date}/{location_id}` | `store` module | Get inventory for date + location |
| PATCH | `/api/inventory/{inv_date}/{location_id}/{flavor_id}` | `store` module | Update inventory fields |
| POST | `/api/inventory/delivery-request/{location_id}` | logged in | Request 2nd delivery |
| GET | `/api/inventory/delivery-requests` | `dispatch` module | List today's requests |
| PATCH | `/api/inventory/delivery-request/{request_id}/status` | `dispatch` module | Update request status |

PATCH body supports all manual fields:
```json
{
  "beginning_inventory": 10,
  "received_cookies": 20,
  "second_delivery": 0,
  "closing_inventory": 5,
  "expired": 2,
  "flawed": 0,
  "used_as_display": 0,
  "given_away": 0,
  "production_waste": 0
}
```

### 👥 Admin (`/api/admin`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/admin/locations` | admin or ops_manager | List all locations |
| GET | `/api/admin/flavors` | admin or ops_manager | List all flavors |
| POST | `/api/admin/flavors` | admin | Create a new flavor |
| PATCH | `/api/admin/flavors/{flavor_id}` | admin | Update flavor (name, is_active) |
| DELETE | `/api/admin/flavors/{flavor_id}/sales-history` | admin | Clear sales for slot reassignment |
| GET | `/api/admin/users` | admin | List all users |
| POST | `/api/admin/users` | admin | Create a user |
| PATCH | `/api/admin/users/{user_id}` | admin | Update user |
| DELETE | `/api/admin/users/{user_id}` | admin | Delete user (cannot delete 'admin') |
| GET | `/api/admin/par-settings/{location_id}` | admin | List PAR settings history |
| PUT | `/api/admin/par-settings/{location_id}/{effective_date}` | admin | Set PAR settings |
| GET | `/api/admin/transition-status` | admin or ops_manager | DB vs sheet readiness |

### 🔔 Notifications (`/api/notifications`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/notifications?unread_only=false&limit=50` | any logged-in | List notifications for my role |
| GET | `/api/notifications/unread-count` | any logged-in | Quick unread count |
| POST | `/api/notifications/{id}/read` | any logged-in | Mark one as read |
| POST | `/api/notifications/read-all` | any logged-in | Mark all as read for my role |

### 📊 Analytics (`/api/analytics`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/analytics/live-ops` | ops_manager or admin | Live sell-through per location |
| GET | `/api/analytics/sales-trend?days=30` | ops_manager or admin | Sales over time |
| GET | `/api/analytics/top-flavors?days=30` | ops_manager or admin | Best-selling flavors |

### 🛒 Orders (`/api/orders`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/orders?page=1&status=&search=&date_from=&date_to=` | ops_manager or admin | Paginated order list |
| GET | `/api/orders/{order_number}` | ops_manager or admin | Single order detail |
| PATCH | `/api/orders/{order_number}` | ops_manager or admin | Update notes / feedback / endorsement |

### ⏰ Cron (`/api/cron`)

All require `X-Cron-Key: {CRON_API_KEY}` header OR admin JWT.

| Method | Path | Description |
|---|---|---|
| POST | `/api/cron/daily-plans` | Generate plans for a date |
| POST | `/api/cron/ingest-sales` | Pull Clover sales for date |
| POST | `/api/cron/nightly-pipeline` | Full nightly: ingest + plans |
| POST | `/api/cron/live-sales` | Poll Clover for today's sales |
| POST | `/api/cron/sync-inventory?target_date=` | Sync Mall PARs → DB |
| POST | `/api/cron/check-alerts` | Fire low-stock notifications |
| POST | `/api/cron/import-inventory` | Legacy closing-inventory import |
| POST | `/api/cron/sync-orders?days=7` | Sync Shopify orders |

---

## 📦 Response Shapes

### BakePlanResponse
```json
{
  "plan_date": "2026-04-21",
  "rows": [
    {
      "flavor_id": 1,
      "flavor_code": "A",
      "flavor_name": "Chocolate Chip Nutella",
      "amount_to_bake": 280,
      "cooking_priority": 1,
      "website_demand": 0,
      "missing_for_malls": 16,
      "closing_inv_yesterday": 12,
      "mall_forecast": 127.0,
      "sales_trend_median": 180.0,
      "total_projection": 276,
      "override_amount": null
    }
  ],
  "total_to_bake": 2828,
  "total_closing_inventory": 134
}
```

### DispatchPlanResponse
```json
{
  "plan_date": "2026-04-21",
  "locations": [
    {
      "location_id": 1,
      "location_name": "San Patricio",
      "rows": [...],
      "total_to_send": 119,
      "dispatch_status": "pending"
    }
  ]
}
```

### InventoryResponse
```json
{
  "inventory_date": "2026-04-21",
  "location_id": 1,
  "location_name": "San Patricio",
  "rows": [
    {
      "flavor_id": 1,
      "flavor_code": "A",
      "flavor_name": "Chocolate Chip Nutella",
      "beginning_inventory": 10,
      "sent_cookies": 0,
      "received_cookies": 15,
      "opening_stock": 25,
      "live_sales": 8,
      "second_delivery": 0,
      "closing_inventory": 0,
      "expired": 0,
      "flawed": 0,
      "used_as_display": 0,
      "given_away": 0,
      "production_waste": 0
    }
  ]
}
```

---

## 🧪 Testing the API

### Get a token
```bash
TOKEN=$(curl -s -X POST \
  -d "username=admin&password=admin123" \
  https://dc-platform-backend-...run.app/api/auth/login \
  | jq -r '.access_token')
```

### Call a protected endpoint
```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://dc-platform-backend-...run.app/api/bake/2026-04-21
```

### Test a cron endpoint (with key)
```bash
curl -X POST \
  -H "X-Cron-Key: $CRON_API_KEY" \
  https://dc-platform-backend-...run.app/api/cron/sync-inventory
```

---

## ⚠️ Error Responses

| Status | Meaning |
|---|---|
| `400` | Bad request (validation error) |
| `401` | Missing or invalid token |
| `403` | Token valid but insufficient permissions |
| `404` | Resource not found |
| `500` | Server error (check logs) |

Error body format:
```json
{ "detail": "Human-readable error message" }
```
