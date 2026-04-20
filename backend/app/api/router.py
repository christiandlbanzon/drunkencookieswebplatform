from fastapi import APIRouter
from app.api.auth_routes import router as auth_router
from app.api.sales_routes import router as sales_router
from app.api.dispatch_routes import router as dispatch_router
from app.api.bake_routes import router as bake_router
from app.api.inventory_routes import router as inventory_router
from app.api.admin_routes import router as admin_router
from app.api.cron_routes import router as cron_router
from app.api.analytics_routes import router as analytics_router
from app.api.orders_routes import router as orders_router
from app.api.notifications_routes import router as notifications_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(sales_router, prefix="/sales", tags=["Sales"])
api_router.include_router(dispatch_router, prefix="/dispatch", tags=["Dispatch"])
api_router.include_router(bake_router, prefix="/bake", tags=["Bake"])
api_router.include_router(inventory_router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(admin_router, prefix="/admin", tags=["Admin"])
api_router.include_router(cron_router, prefix="/cron", tags=["Cron"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(orders_router, prefix="/orders", tags=["Orders"])
api_router.include_router(notifications_router, prefix="/notifications", tags=["Notifications"])
