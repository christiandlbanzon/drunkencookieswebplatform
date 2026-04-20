"""Notifications API — in-app alerts for operational events."""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.database import get_db
from app.models.notification import Notification
from app.models.user import User
from app.auth.dependencies import get_current_user

router = APIRouter()


@router.get("")
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List notifications relevant to the current user (by role or user_id)."""
    # Keep notifications for 14 days
    cutoff = datetime.utcnow() - timedelta(days=14)

    # Admin sees everything; everyone else sees their own + role-targeted + broadcast
    if user.role == "admin":
        q = db.query(Notification).filter(Notification.created_at >= cutoff)
    else:
        q = db.query(Notification).filter(
            Notification.created_at >= cutoff,
            or_(
                Notification.target_user_id == user.id,
                Notification.target_role == user.role,
                and_(Notification.target_role.is_(None), Notification.target_user_id.is_(None)),
            ),
        )
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    rows = q.order_by(Notification.created_at.desc()).limit(limit).all()
    return [
        {
            "id": n.id,
            "kind": n.kind,
            "severity": n.severity,
            "title": n.title,
            "body": n.body,
            "link_url": n.link_url,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in rows
    ]


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """How many unread notifications for the current user."""
    cutoff = datetime.utcnow() - timedelta(days=14)
    base = db.query(Notification).filter(
        Notification.created_at >= cutoff,
        Notification.is_read.is_(False),
    )
    if user.role != "admin":
        base = base.filter(
            or_(
                Notification.target_user_id == user.id,
                Notification.target_role == user.role,
                and_(Notification.target_role.is_(None), Notification.target_user_id.is_(None)),
            )
        )
    return {"unread": base.count()}


@router.post("/{notif_id}/read")
def mark_read(
    notif_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    n = db.query(Notification).filter(Notification.id == notif_id).first()
    if n:
        n.is_read = True
        db.commit()
    return {"status": "ok"}


@router.post("/read-all")
def mark_all_read(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Mark all notifications targeted at this user/role as read."""
    (
        db.query(Notification)
        .filter(
            Notification.is_read.is_(False),
            or_(
                Notification.target_user_id == user.id,
                Notification.target_role == user.role,
            ),
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {"status": "ok"}


def create_notification(
    db: Session,
    kind: str,
    title: str,
    body: str = None,
    severity: str = "info",
    target_role: str = None,
    target_user_id: int = None,
    link_url: str = None,
):
    """Helper for other services to create notifications."""
    n = Notification(
        kind=kind,
        title=title,
        body=body,
        severity=severity,
        target_role=target_role,
        target_user_id=target_user_id,
        link_url=link_url,
    )
    db.add(n)
    db.commit()
    return n
