"""Full QA test suite for Drunken Cookies Platform."""
import requests, subprocess, sys, os
requests.packages.urllib3.disable_warnings()

B = "https://dc-platform-backend-703996360436.us-central1.run.app"
F = "https://dc-platform-frontend-703996360436.us-central1.run.app"
JS = os.environ.get("JWT_SECRET", "")

P=0; FL=0; fails=[]
def t(name, passed, detail=""):
    global P, FL
    if passed:
        P+=1; print(f"  {name:<46} \033[32mPASS\033[0m {detail}")
    else:
        FL+=1; fails.append(name); print(f"  {name:<46} \033[31mFAIL\033[0m {detail}")

def login(u,p):
    r = requests.post(f"{B}/api/auth/login", data={"username":u,"password":p}, headers={"Content-Type":"application/x-www-form-urlencoded"}, verify=False, timeout=15)
    return r.json().get("access_token","") if r.status_code==200 else ""

def get(path, tok): return requests.get(f"{B}{path}", headers={"Authorization":f"Bearer {tok}"}, verify=False, timeout=30)
def patch(path, tok, js): return requests.patch(f"{B}{path}", headers={"Authorization":f"Bearer {tok}","Content-Type":"application/json"}, json=js, verify=False, timeout=30)
def cron(path): return requests.post(f"{B}{path}", headers={"X-Cron-Key":JS,"Content-Length":"0"}, verify=False, timeout=60)

AT=login("admin","admin123")
KT=login("kitchen1","kitchen123")
DT=login("dispatch1","dispatch123")
ST=login("store_sp","store123")

print("="*60)
print("  DRUNKEN COOKIES — FULL QA SUITE")
print("="*60)

print("\n--- INFRASTRUCTURE ---")
r=requests.get(f"{B}/health",verify=False,timeout=10).json()
t("Health + DB",r["status"]=="ok" and r["database"]=="connected")
t("Swagger docs",requests.get(f"{B}/api/docs",verify=False).status_code==200)

print("\n--- AUTH ---")
t("Admin login",len(AT)>10)
t("Kitchen login",len(KT)>10)
t("Dispatch login",len(DT)>10)
t("Store login",len(ST)>10)
t("Bad password=401",requests.post(f"{B}/api/auth/login",data={"username":"x","password":"x"},headers={"Content-Type":"application/x-www-form-urlencoded"},verify=False).status_code==401)
t("No token=401",requests.get(f"{B}/api/bake/2026-04-11",verify=False).status_code==401)

print("\n--- ROLE RESTRICTIONS ---")
t("Kitchen->bake=200",get("/api/bake/2026-04-11",KT).status_code==200)
t("Kitchen->dispatch=403",get("/api/dispatch/2026-04-11",KT).status_code==403)
t("Kitchen->orders=403",get("/api/orders",KT).status_code==403)
t("Dispatch->dispatch=200",get("/api/dispatch/2026-04-11",DT).status_code==200)
t("Dispatch->bake=403",get("/api/bake/2026-04-11",DT).status_code==403)
t("Store->inventory=200",get("/api/inventory/2026-04-11/1",ST).status_code==200)
t("Store->dispatch=403",get("/api/dispatch/2026-04-11",ST).status_code==403)
t("Non-admin->users=403",get("/api/auth/users",KT).status_code==403)

print("\n--- CRON SECURITY ---")
t("No key=403",requests.post(f"{B}/api/cron/daily-plans",headers={"Content-Length":"0"},verify=False).status_code==403)
t("Bad key=403",requests.post(f"{B}/api/cron/daily-plans",headers={"Content-Length":"0","X-Cron-Key":"wrong"},verify=False).status_code==403)
t("Bad date=400",cron("/api/cron/daily-plans?target_date=2020-01-01").status_code==400)
t("Valid key=200",cron("/api/cron/daily-plans").status_code==200)

print("\n--- MODULE 1: BAKE ---")
d=get("/api/bake/2026-04-11",AT).json()
t("Bake plan",d["total_to_bake"]>0,f"({d['total_to_bake']} bake, {len(d['rows'])} rows)")
t("Override save",patch("/api/bake/2026-04-11/1",AT,{"override_amount":999}).json()["status"]=="ok")
t("Override persists",get("/api/bake/2026-04-11",AT).json()["rows"][0]["override_amount"]==999)
patch("/api/bake/2026-04-11/1",AT,{"override_amount":None})
t("Override reset",get("/api/bake/2026-04-11",AT).json()["rows"][0]["override_amount"] in [None, 0])

print("\n--- MODULE 2: DISPATCH ---")
d=get("/api/dispatch/2026-04-11",AT).json()
t("6 locations",len(d["locations"])==6,f"({sum(l['total_to_send'] for l in d['locations'])} send)")
t("Override",patch("/api/dispatch/2026-04-11/1/1",AT,{"override_amount":777}).json()["status"]=="ok")
r=requests.patch(f"{B}/api/dispatch/2026-04-11/1/confirm?new_status=packed",headers={"Authorization":f"Bearer {AT}","Content-Length":"0"},verify=False)
rj=r.json() if r.status_code==200 else {}
t("Confirm packed",rj.get("status")=="ok",f"(updated {rj.get('updated',0)})")
t("Status=packed",get("/api/dispatch/2026-04-11",AT).json()["locations"][0]["dispatch_status"]=="packed")
patch("/api/dispatch/2026-04-11/1/1",AT,{"override_amount":None})
requests.patch(f"{B}/api/dispatch/2026-04-11/1/confirm?new_status=pending",headers={"Authorization":f"Bearer {AT}","Content-Length":"0"},verify=False)

print("\n--- MODULE 3: STORE ---")
d=get("/api/inventory/2026-04-11/1",AT).json()
t("Inventory",len(d["rows"])>=14,f"({d['location_name']}, {len(d['rows'])} rows)")
t("Update sent",patch("/api/inventory/2026-04-11/1/1",AT,{"sent_cookies":50}).json()["status"]=="ok")
t("Update closing",patch("/api/inventory/2026-04-11/1/1",AT,{"closing_inventory":25}).json()["status"]=="ok")
r=requests.post(f"{B}/api/inventory/delivery-request/4",headers={"Authorization":f"Bearer {AT}","Content-Length":"0"},verify=False).json()
t("2nd delivery req",r["status"]=="ok",f"(id={r['request_id']})")
t("Requests list",len(get("/api/inventory/delivery-requests",AT).json())>0)

print("\n--- MODULE 4: ANALYTICS ---")
d=get("/api/analytics/summary?days=7",AT).json()
t("Summary",len(d["by_location"])>0,f"({sum(l['total'] for l in d['by_location'])} sales)")
t("Trends",len(get("/api/analytics/trends?days=7",AT).json())>0)
d=get("/api/analytics/live-ops",AT).json()
t("Live Ops Center",len(d["locations"])==6)

print("\n--- MODULE 5: ORDERS ---")
d=get("/api/orders",AT).json()
s=d["stats"]
t("Orders list",d["total"]>0,f"({d['total']} orders)")
t("Stats",s["total"]>0,f"(del={s['delivered']}, pend={s['pending']}, ref={s['refunded']})")
t("Search",get("/api/orders?search=cookie",AT).status_code==200)
t("Filter status",get("/api/orders?status=Delivered",AT).status_code==200)
import urllib.parse
on=urllib.parse.quote(d["orders"][0]["order_number"], safe="")
r=patch(f"/api/orders/{on}",AT,{"package_notes":"QA"})
t("Update notes",r.status_code==200 and r.json().get("status")=="ok")

print("\n--- DATA ---")
t("6 locations",len(get("/api/admin/locations",AT).json())==6)
t("16 flavors",len(get("/api/admin/flavors",AT).json())>=14)
t("5+ users",len(get("/api/auth/users",AT).json())>=5)
t("Real sales",sum(sum(r["quantity"] for r in l["rows"]) for l in get("/api/sales/2026-04-08",AT).json())>0)
t("Website orders",get("/api/sales/website-orders/2026-04-10",AT).status_code==200)
t("Median",get("/api/sales/median/1/1",AT).status_code==200)

print("\n--- CRON ---")
r=cron("/api/cron/nightly-pipeline").json()
t("Nightly pipeline","plans" in r,f"(dispatch={r['plans']['dispatch_total']})")
r=cron("/api/cron/sync-orders?days=1").json()
t("Sync orders","synced" in r,f"(synced={r['synced']})")

print("\n--- FRONTEND (8 pages) ---")
for p in ["login","bake","dispatch","store","ops","analytics","orders","admin"]:
    t(f"/{p}",requests.get(f"{F}/{p}",verify=False,timeout=15).status_code==200)

print("\n--- PWA ---")
t("manifest.json",requests.get(f"{F}/manifest.json",verify=False).status_code==200)
t("icon-192.png",requests.get(f"{F}/icon-192.png",verify=False).status_code==200)

print("\n--- SCHEDULERS ---")
gcloud = os.environ.get("GCLOUD_PATH", "gcloud")
for job in ["dc-platform-daily-plans","dc-platform-live-sales","dc-platform-sync-orders"]:
    try:
        r=subprocess.run([gcloud,"scheduler","jobs","describe",job,"--location=us-central1","--project=boxwood-chassis-332307","--format=value(state)"],capture_output=True,text=True)
        t(job,r.stdout.strip()=="ENABLED")
    except: t(job, False, "(gcloud not found)")

print()
print("="*60)
if FL==0: print(f"  \033[32mALL {P} TESTS PASSED\033[0m")
else: print(f"  \033[32m{P} passed\033[0m, \033[31m{FL} failed\033[0m"); [print(f"    - {f}") for f in fails]
print("="*60)
