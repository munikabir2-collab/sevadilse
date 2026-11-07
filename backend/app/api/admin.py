from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.api.auth import get_current_user

from app.models.user_model import User
from app.models.provider_model import Provider
from app.models.booking_model import Booking
from app.models.order_model import RestaurantOrder
from app.models.payment_model import Payment, PaymentStatus


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/dashboard/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Admin-only access
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    # User statistics
    total_users = (
        db.query(func.count(User.id))
        .scalar() or 0
    )

    total_provider_users = (
        db.query(func.count(User.id))
        .filter(User.is_provider.is_(True))
        .scalar() or 0
    )

    total_providers = (
        db.query(func.count(Provider.id))
        .scalar() or 0
    )

    # Booking statistics
    total_bookings = (
        db.query(func.count(Booking.id))
        .scalar() or 0
    )

    total_restaurant_orders = (
        db.query(func.count(RestaurantOrder.id))
        .scalar() or 0
    )

    # Only successfully paid INR transactions
    paid_filter = (
        Payment.status == PaymentStatus.paid,
        Payment.currency == "INR",
    )

    paid_transactions = (
        db.query(func.count(Payment.id))
        .filter(*paid_filter)
        .scalar() or 0
    )

    paid_revenue = (
        db.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(*paid_filter)
        .scalar() or 0.0
    )

    platform_commission = (
        db.query(func.coalesce(func.sum(Payment.commission_amount), 0.0))
        .filter(*paid_filter)
        .scalar() or 0.0
    )

    provider_earnings = (
        db.query(func.coalesce(func.sum(Payment.provider_amount), 0.0))
        .filter(*paid_filter)
        .scalar() or 0.0
    )

    return {
        "total_users": total_users,
        "total_provider_users": total_provider_users,
        "total_providers": total_providers,
        "total_bookings": total_bookings,
        "total_restaurant_orders": total_restaurant_orders,
        "paid_transactions": paid_transactions,
        "paid_revenue_inr": round(float(paid_revenue), 2),
        "platform_commission_inr": round(float(platform_commission), 2),
        "provider_earnings_inr": round(float(provider_earnings), 2),
        "currency": "INR",
    }

# ============================================================
# ADMIN LIST ENDPOINTS - READ ONLY
# ============================================================

def _admin_require(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


def _admin_plain(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _admin_row(obj, fields):
    return {field: _admin_plain(getattr(obj, field, None)) for field in fields}


def _admin_paged(db, model, order_col, fields, limit, offset):
    total = db.query(model).count()
    rows = (
        db.query(model)
        .order_by(order_col.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_admin_row(row, fields) for row in rows],
    }


@router.get("/users")
def admin_list_users(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db, User, User.id,
        ["id", "name", "email", "phone", "is_provider", "is_admin"],
        limit, offset,
    )


@router.get("/providers")
def admin_list_providers(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db, Provider, Provider.id,
        ["id", "owner_id", "name", "category", "city", "address",
         "avg_rating", "total_reviews"],
        limit, offset,
    )


@router.get("/bookings")
def admin_list_bookings(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db, Booking, Booking.id,
        ["id", "user_id", "provider_id", "service_id", "start_time",
         "end_time", "guests", "total_price", "status"],
        limit, offset,
    )


@router.get("/orders")
def admin_list_orders(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db, RestaurantOrder, RestaurantOrder.id,
        ["id", "user_id", "provider_id", "table_id", "order_type",
         "status", "payment_status", "grand_total", "created_at"],
        limit, offset,
    )


@router.get("/payments")
def admin_list_payments(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db, Payment, Payment.id,
        ["id", "user_id", "provider_id", "entity_type", "entity_id",
         "payment_method", "amount", "currency", "status",
         "commission_amount", "provider_amount", "created_at", "paid_at"],
        limit, offset,
    )


