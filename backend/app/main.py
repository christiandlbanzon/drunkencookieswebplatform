"""
Drunken Cookies Operations Platform — FastAPI entrypoint.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api.router import api_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = get_settings()

app = FastAPI(
    title="Drunken Cookies Operations Platform",
    version="1.0.0",
    description="Unified operations platform for kitchen, dispatch, and store management.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.on_event("startup")
def check_production_config():
    """Warn loudly if the app is running with insecure default config."""
    logger = logging.getLogger(__name__)
    warnings = []
    if settings.JWT_SECRET == "change-me-in-production":
        warnings.append("JWT_SECRET is still the default! Set a strong random secret.")
    if not settings.CRON_API_KEY:
        warnings.append("CRON_API_KEY is not set. Using JWT_SECRET as fallback (insecure).")
    if warnings:
        logger.warning("=" * 70)
        for w in warnings:
            logger.warning(f"SECURITY: {w}")
        logger.warning("=" * 70)


@app.on_event("startup")
def run_migrations():
    """Add new columns/tables on startup if they don't exist yet (safe to re-run)."""
    from app.database import engine, Base
    from sqlalchemy import text, inspect
    # Register the notification model so create_all picks it up
    from app.models import notification as _notification_module  # noqa: F401
    logger = logging.getLogger(__name__)
    try:
        inspector = inspect(engine)
        existing_cols = {col["name"] for col in inspector.get_columns("inventory")}
        new_cols = {
            "expired": "INTEGER DEFAULT 0",
            "flawed": "INTEGER DEFAULT 0",
            "used_as_display": "INTEGER DEFAULT 0",
            "given_away": "INTEGER DEFAULT 0",
            "production_waste": "INTEGER DEFAULT 0",
        }
        with engine.begin() as conn:
            for col_name, col_type in new_cols.items():
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE inventory ADD COLUMN {col_name} {col_type}"))
                    logger.info(f"Added column inventory.{col_name}")

        # Create notifications table if missing
        existing_tables = set(inspector.get_table_names())
        if "notifications" not in existing_tables:
            Base.metadata.tables["notifications"].create(bind=engine)
            logger.info("Created table notifications")
    except Exception as e:
        logger.warning(f"Migration check failed (non-fatal): {e}")


@app.get("/health")
def health_check():
    """Health check — returns ok if service is running."""
    from app.database import engine
    try:
        with engine.connect() as conn:
            conn.execute(conn.connection.cursor().execute("SELECT 1") if False else __import__("sqlalchemy").text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    return {"status": "ok", "service": "drunken-cookies-platform", "database": db_status}
