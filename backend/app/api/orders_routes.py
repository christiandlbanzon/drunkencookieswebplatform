"""Shopify Order Manager API endpoints."""

import math
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.database import get_db
from app.models.shopify_order import ShopifyOrder
from app.auth.dependencies import get_current_user, require_module
from app.schemas.orders import OrderResponse, OrderUpdate, OrderListResponse

router = APIRouter()


@router.get("", response_model=OrderListResponse)
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=10, le=100),
    status: str | None = None,
    search: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    special_only: bool = False,
    refunded_only: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_module("sales")),
):
    query = db.query(ShopifyOrder)

    if status:
        query = query.filter(ShopifyOrder.delivery_status == status)
    if search:
        term = f"%{search}%"
        query = query.filter(
            or_(
                ShopifyOrder.order_number.ilike(term),
                ShopifyOrder.customer_name.ilike(term),
                ShopifyOrder.email.ilike(term),
            )
        )
    if date_from:
        query = query.filter(ShopifyOrder.order_date >= date_from)
    if date_to:
        query = query.filter(ShopifyOrder.order_date <= date_to)
    if special_only:
        query = query.filter(ShopifyOrder.is_special_request.is_(True))
    if refunded_only:
        query = query.filter(ShopifyOrder.refund_status == "Yes")

    total = query.count()

    # Stats
    all_q = db.query(ShopifyOrder)
    if date_from:
        all_q = all_q.filter(ShopifyOrder.order_date >= date_from)
    if date_to:
        all_q = all_q.filter(ShopifyOrder.order_date <= date_to)

    stats = {
        "total": all_q.count(),
        "pending": all_q.filter(ShopifyOrder.delivery_status == "Pending").count(),
        "in_transit": all_q.filter(ShopifyOrder.delivery_status.in_(["In Transit", "Out for Delivery"])).count(),
        "delivered": all_q.filter(ShopifyOrder.delivery_status == "Delivered").count(),
        "refunded": all_q.filter(ShopifyOrder.refund_status == "Yes").count(),
        "special": all_q.filter(ShopifyOrder.is_special_request.is_(True)).count(),
    }

    orders = (
        query.order_by(ShopifyOrder.order_date.desc(), ShopifyOrder.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return OrderListResponse(
        orders=[OrderResponse.model_validate(o) for o in orders],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 1,
        stats=stats,
    )


@router.get("/{order_number}", response_model=OrderResponse)
def get_order(
    order_number: str,
    db: Session = Depends(get_db),
    _=Depends(require_module("sales")),
):
    order = db.query(ShopifyOrder).filter(ShopifyOrder.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_number}")
def update_order(
    order_number: str,
    body: OrderUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_module("sales")),
):
    order = db.query(ShopifyOrder).filter(ShopifyOrder.order_number == order_number).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    if body.package_notes is not None:
        order.package_notes = body.package_notes
    if body.feedback is not None:
        order.feedback = body.feedback
    if body.endorsement is not None:
        order.endorsement = body.endorsement
    db.commit()
    return {"status": "ok"}
