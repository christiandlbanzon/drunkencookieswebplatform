from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from passlib.context import CryptContext

from app.database import get_db
from app.models.location import Location
from app.models.flavor import Flavor
from app.models.par_settings import ParSettings
from app.models.daily_sales import DailySales
from app.models.user import User
from app.auth.dependencies import require_role
from app.auth.roles import Role
from app.schemas.admin import (
    LocationResponse, FlavorResponse, FlavorUpdate, FlavorCreate,
    ParSettingsResponse, ParSettingsUpdate,
    UserResponse, UserCreate, UserUpdate,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter()


@router.get("/locations", response_model=list[LocationResponse])
def list_locations(db: Session = Depends(get_db), _=Depends(require_role(Role.ADMIN, Role.OPS_MANAGER))):
    return db.query(Location).order_by(Location.sort_order).all()


@router.get("/flavors", response_model=list[FlavorResponse])
def list_flavors(db: Session = Depends(get_db), _=Depends(require_role(Role.ADMIN, Role.OPS_MANAGER))):
    return db.query(Flavor).order_by(Flavor.sort_order).all()


@router.patch("/flavors/{flavor_id}")
def update_flavor(
    flavor_id: int,
    body: FlavorUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    """
    Update a flavor's name, active status, etc.
    Use this when launching a new flavor (e.g., activating slot I)
    or retiring one (deactivating K).
    """
    flavor = db.query(Flavor).filter(Flavor.id == flavor_id).first()
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    if body.name is not None:
        flavor.name = body.name
    if body.is_active is not None:
        flavor.is_active = body.is_active
    if body.is_core is not None:
        flavor.is_core = body.is_core
    db.commit()
    return {"status": "ok", "flavor": {"id": flavor.id, "code": flavor.code, "name": flavor.name, "is_active": flavor.is_active}}


@router.delete("/flavors/{flavor_id}/sales-history")
def clear_flavor_sales(
    flavor_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    """
    Clear all historical sales data for a flavor.
    Use when a flavor slot is reassigned (e.g., Guava Crumble -> Linzer Cake)
    so old sales don't pollute the new flavor's median.
    """
    flavor = db.query(Flavor).filter(Flavor.id == flavor_id).first()
    if not flavor:
        raise HTTPException(status_code=404, detail="Flavor not found")
    deleted = db.query(DailySales).filter(DailySales.flavor_id == flavor_id).delete()
    db.commit()
    return {"status": "ok", "flavor_id": flavor_id, "flavor_name": flavor.name, "records_deleted": deleted}


@router.get("/par-settings/{location_id}", response_model=list[ParSettingsResponse])
def get_par_settings(
    location_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    return (
        db.query(ParSettings)
        .filter(ParSettings.location_id == location_id)
        .order_by(ParSettings.effective_date.desc())
        .limit(30)
        .all()
    )


@router.put("/par-settings/{location_id}/{effective_date}")
def upsert_par_settings(
    location_id: int,
    effective_date: date,
    body: ParSettingsUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    existing = (
        db.query(ParSettings)
        .filter(ParSettings.location_id == location_id, ParSettings.effective_date == effective_date)
        .first()
    )
    if existing:
        if body.reduction_pct is not None:
            existing.reduction_pct = body.reduction_pct
        if body.minimum_par is not None:
            existing.minimum_par = body.minimum_par
        if body.median_weeks is not None:
            existing.median_weeks = body.median_weeks
    else:
        existing = ParSettings(
            location_id=location_id,
            effective_date=effective_date,
            reduction_pct=body.reduction_pct or 0.0,
            minimum_par=body.minimum_par or 10,
            median_weeks=body.median_weeks or 4,
        )
        db.add(existing)

    db.commit()
    return {"status": "ok"}


@router.post("/flavors", response_model=FlavorResponse)
def create_flavor(
    body: FlavorCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    """Create a brand-new flavor slot."""
    if db.query(Flavor).filter(Flavor.code == body.code).first():
        raise HTTPException(status_code=400, detail=f"Flavor code '{body.code}' already exists")
    flavor = Flavor(
        code=body.code, name=body.name, sort_order=body.sort_order,
        is_core=body.is_core, is_active=body.is_active, category=body.category,
    )
    db.add(flavor)
    db.commit()
    db.refresh(flavor)
    return flavor


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db), _=Depends(require_role(Role.ADMIN))):
    return db.query(User).order_by(User.id).all()


@router.post("/users", response_model=UserResponse)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    valid_roles = {r.value for r in Role}
    if body.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {sorted(valid_roles)}")
    user = User(
        username=body.username,
        password_hash=pwd_context.hash(body.password),
        display_name=body.display_name,
        role=body.role,
        location_id=body.location_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.role is not None:
        valid_roles = {r.value for r in Role}
        if body.role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Role must be one of: {sorted(valid_roles)}")
        user.role = body.role
    if body.location_id is not None:
        user.location_id = body.location_id if body.location_id != 0 else None
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password:
        user.password_hash = pwd_context.hash(body.password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.username == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete the admin user")
    db.delete(user)
    db.commit()
    return {"status": "ok"}


@router.get("/transition-status")
def transition_status(
    target_date: date | None = None,
    db: Session = Depends(get_db),
    _=Depends(require_role(Role.ADMIN, Role.OPS_MANAGER)),
):
    """
    Show how many flavor/location pairs are ready to switch from sheet to DB.
    Phase 1: log-only. Once 100% are ready and drift is low, we flip the switch.
    """
    from app.services.transition_tracker import get_transition_status
    if target_date is None:
        target_date = date.today()
    return get_transition_status(db, target_date)
