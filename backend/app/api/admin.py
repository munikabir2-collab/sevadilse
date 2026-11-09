
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Body, status
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from app.models.provider_earning_model import ProviderEarning
from app.core.database import get_db
from app.api.auth import get_current_user
from decimal import Decimal
from pydantic import BaseModel, Field
from app.models.admin_settings_model import AdminSettings
from app.models.user_model import User
from app.models.provider_model import Provider
from app.models.booking_model import Booking
from app.models.order_model import RestaurantOrder
from app.models.payment_model import Payment, PaymentStatus


router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ============================================================
# ADMIN AUTHORIZATION
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
    return {
        field: _admin_plain(getattr(obj, field, None))
        for field in fields
    }


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
        "items": [
            _admin_row(row, fields)
            for row in rows
        ],
    }


# ============================================================
# ADMIN DASHBOARD STATISTICS
# ============================================================

@router.get("/dashboard/stats")
def get_admin_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(_admin_require),
):
    total_users = (
        db.query(func.count(User.id)).scalar() or 0
    )

    total_provider_users = (
        db.query(func.count(User.id))
        .filter(User.is_provider.is_(True))
        .scalar() or 0
    )

    total_providers = (
        db.query(func.count(Provider.id)).scalar() or 0
    )

    total_bookings = (
        db.query(func.count(Booking.id)).scalar() or 0
    )

    total_restaurant_orders = (
        db.query(func.count(RestaurantOrder.id)).scalar() or 0
    )

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
# ADMIN USERS
# ============================================================

@router.get("/users")
def admin_list_users(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        User,
        User.id,
        [
            "id",
            "name",
            "email",
            "phone",
            "is_provider",
            "is_admin",
            "is_active",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN PROVIDERS - BASIC LIST
# ============================================================

@router.get("/providers")
def admin_list_providers(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        Provider,
        Provider.id,
        [
            "id",
            "owner_id",
            "name",
            "category",
            "city",
            "address",
            "avg_rating",
            "total_reviews",
            "verification_status",
            "is_active",
            "rejection_reason",
            "verified_at",
            "verified_by",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN BOOKINGS
# ============================================================

@router.get("/bookings")
def admin_list_bookings(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        Booking,
        Booking.id,
        [
            "id",
            "user_id",
            "provider_id",
            "service_id",
            "start_time",
            "end_time",
            "guests",
            "total_price",
            "status",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN RESTAURANT ORDERS
# ============================================================

@router.get("/orders")
def admin_list_orders(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        RestaurantOrder,
        RestaurantOrder.id,
        [
            "id",
            "user_id",
            "provider_id",
            "table_id",
            "order_type",
            "status",
            "payment_status",
            "grand_total",
            "created_at",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN PAYMENTS
# ============================================================

@router.get("/payments")
def admin_list_payments(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        Payment,
        Payment.id,
        [
            "id",
            "user_id",
            "provider_id",
            "entity_type",
            "entity_id",
            "payment_method",
            "amount",
            "currency",
            "status",
            "commission_amount",
            "provider_amount",
            "created_at",
            "paid_at",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN PROVIDER EARNINGS
# ============================================================

@router.get("/earnings")
def admin_list_provider_earnings(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    return _admin_paged(
        db,
        ProviderEarning,
        ProviderEarning.id,
        [
            "id",
            "provider_id",
            "payment_id",
            "gross_amount",
            "commission_percent",
            "commission_amount",
            "provider_amount",
            "currency",
            "status",
            "settlement_reference",
            "created_at",
            "settled_at",
        ],
        limit,
        offset,
    )


# ============================================================
# ADMIN CUSTOMER MANAGEMENT
# ============================================================

def _admin_get_customer_or_404(
    customer_id: int,
    db: Session,
):
    customer = (
        db.query(User)
        .filter(
            User.id == customer_id,
            User.is_provider.isnot(True),
            User.is_admin.isnot(True),
        )
        .first()
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

    return customer


@router.get("/customers")
def admin_list_customers(
    search: str | None = Query(None, max_length=100),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    query = db.query(User).filter(
        User.is_provider.isnot(True),
        User.is_admin.isnot(True),
    )

    if search and search.strip():
        search_value = f"%{search.strip()}%"

        query = query.filter(
            or_(
                User.name.ilike(search_value),
                User.email.ilike(search_value),
                User.phone.ilike(search_value),
            )
        )

    total = query.count()

    customers = (
        query
        .order_by(User.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            _admin_row(
                customer,
                [
                    "id",
                    "name",
                    "email",
                    "phone",
                    "is_provider",
                    "is_admin",
                    "is_active",
                ],
            )
            for customer in customers
        ],
    }


@router.get("/customers/{customer_id}")
def admin_get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    customer = _admin_get_customer_or_404(
        customer_id,
        db,
    )

    return _admin_row(
        customer,
        [
            "id",
            "name",
            "email",
            "phone",
            "is_provider",
            "is_admin",
            "is_active",
        ],
    )


@router.patch("/customers/{customer_id}/status")
def admin_update_customer_status(
    customer_id: int,
    is_active: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    customer = _admin_get_customer_or_404(
        customer_id,
        db,
    )

    customer.is_active = is_active

    db.commit()
    db.refresh(customer)

    return {
        "message": (
            "Customer activated successfully"
            if is_active
            else "Customer deactivated successfully"
        ),
        "customer": _admin_row(
            customer,
            [
                "id",
                "name",
                "email",
                "phone",
                "is_active",
            ],
        ),
    }


# ============================================================
# ADMIN PROVIDER MANAGEMENT - SEARCH + FILTER + PAGINATION
# ============================================================

@router.get("/provider-management")
def admin_provider_management(
    search: str | None = Query(None, max_length=100),
    category: str | None = Query(None),
    city: str | None = Query(None),
    verification_status: str | None = Query(None),
    is_active: bool | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(_admin_require),
    db: Session = Depends(get_db),
):
    query = (
        db.query(Provider, User)
        .join(User, Provider.owner_id == User.id)
    )

    if search and search.strip():
        term = f"%{search.strip()}%"

        query = query.filter(
            or_(
                Provider.name.ilike(term),
                Provider.city.ilike(term),
                User.name.ilike(term),
                User.email.ilike(term),
                User.phone.ilike(term),
            )
        )

    if category:
        allowed_categories = [
            "hotel",
            "restaurant",
            "doctor",
        ]

        if category not in allowed_categories:
            raise HTTPException(
                status_code=400,
                detail="Invalid provider category",
            )

        query = query.filter(
            Provider.category == category
        )

    if city and city.strip():
        query = query.filter(
            Provider.city.ilike(f"%{city.strip()}%")
        )

    if verification_status:
        allowed_statuses = [
            "pending",
            "approved",
            "rejected",
        ]

        if verification_status not in allowed_statuses:
            raise HTTPException(
                status_code=400,
                detail="Invalid verification status",
            )

        query = query.filter(
            Provider.verification_status == verification_status
        )

    if is_active is not None:
        query = query.filter(
            Provider.is_active.is_(is_active)
        )

    total = query.count()

    rows = (
        query
        .order_by(Provider.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = []

    for provider, owner in rows:
        items.append({
            "id": provider.id,
            "owner_id": provider.owner_id,
            "owner_name": owner.name,
            "owner_email": owner.email,
            "owner_phone": owner.phone,
            "owner_active": owner.is_active,

            "name": provider.name,
            "category": _admin_plain(provider.category),
            "description": provider.description,
            "specialization": provider.specialization,

            "city": provider.city,
            "address": provider.address,
            "latitude": provider.latitude,
            "longitude": provider.longitude,

            "avg_rating": provider.avg_rating,
            "total_reviews": provider.total_reviews,

            "verification_status": provider.verification_status,
            "is_active": provider.is_active,
            "rejection_reason": provider.rejection_reason,
            "verified_at": _admin_plain(provider.verified_at),
            "verified_by": provider.verified_by,
        })

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


# ============================================================
# ADMIN PROVIDER DETAILS
# ============================================================

@router.get("/provider-management/{provider_id}")
def admin_provider_details(
    provider_id: int,
    current_user: User = Depends(_admin_require),
    db: Session = Depends(get_db),
):
    result = (
        db.query(Provider, User)
        .join(User, Provider.owner_id == User.id)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    provider, owner = result

    services = []

    for service in provider.services:
        services.append({
            "id": service.id,
            "name": service.name,
            "price": service.price,
            "capacity": service.capacity,
            "duration_minutes": service.duration_minutes,
            "total_units": service.total_units,
        })

    return {
        "id": provider.id,
        "owner_id": provider.owner_id,

        "owner_name": owner.name,
        "owner_email": owner.email,
        "owner_phone": owner.phone,
        "owner_active": owner.is_active,

        "name": provider.name,
        "category": _admin_plain(provider.category),
        "description": provider.description,
        "specialization": provider.specialization,

        "city": provider.city,
        "address": provider.address,
        "latitude": provider.latitude,
        "longitude": provider.longitude,

        "avg_rating": provider.avg_rating,
        "total_reviews": provider.total_reviews,

        "verification_status": provider.verification_status,
        "is_active": provider.is_active,
        "rejection_reason": provider.rejection_reason,
        "verified_at": _admin_plain(provider.verified_at),
        "verified_by": provider.verified_by,

        "services": services,
    }


# ============================================================
# ADMIN PROVIDER LOOKUP
# ============================================================

def _admin_get_provider_or_404(
    provider_id: int,
    db: Session,
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if provider is None:
        raise HTTPException(
            status_code=404,
            detail="Provider not found",
        )

    return provider


# ============================================================
# ADMIN PROVIDER APPROVE / REJECT / PENDING
# ============================================================

@router.patch("/provider-management/{provider_id}/verification")
def admin_update_provider_verification(
    provider_id: int,
    verification_status: str = Body(...),
    rejection_reason: str | None = Body(None),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    allowed_statuses = [
        "pending",
        "approved",
        "rejected",
    ]

    if verification_status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Status must be pending, approved or rejected",
        )

    provider = _admin_get_provider_or_404(
        provider_id,
        db,
    )

    if verification_status == "rejected":
        if not rejection_reason or not rejection_reason.strip():
            raise HTTPException(
                status_code=400,
                detail="Rejection reason is required",
            )

        provider.rejection_reason = rejection_reason.strip()

    else:
        provider.rejection_reason = None

    provider.verification_status = verification_status

    if verification_status in ["approved", "rejected"]:
        provider.verified_at = datetime.now(timezone.utc)
        provider.verified_by = admin.id
    else:
        provider.verified_at = None
        provider.verified_by = None

    try:
        db.commit()
        db.refresh(provider)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Provider verification update failed",
        )

    return {
        "message": f"Provider {verification_status} successfully",
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "verification_status": provider.verification_status,
            "rejection_reason": provider.rejection_reason,
            "verified_at": _admin_plain(provider.verified_at),
            "verified_by": provider.verified_by,
            "is_active": provider.is_active,
        },
    }


# ============================================================
# ADMIN PROVIDER SUSPEND / RESTORE
# ============================================================

@router.patch("/provider-management/{provider_id}/status")
def admin_update_provider_status(
    provider_id: int,
    is_active: bool = Body(..., embed=True),
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    provider = _admin_get_provider_or_404(
        provider_id,
        db,
    )

    provider.is_active = is_active

    try:
        db.commit()
        db.refresh(provider)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Provider status update failed",
        )

    return {
        "message": (
            "Provider restored successfully"
            if is_active
            else "Provider suspended successfully"
        ),
        "provider": {
            "id": provider.id,
            "name": provider.name,
            "is_active": provider.is_active,
            "verification_status": provider.verification_status,
        },
    }

# ============================================================
# ADMIN SETTINGS
# ============================================================

class AdminSettingsUpdate(BaseModel):
    platform_name: str | None = Field(default=None, min_length=1, max_length=150)
    support_email: str | None = Field(default=None, max_length=255)
    support_phone: str | None = Field(default=None, max_length=30)

    customer_registration_enabled: bool | None = None
    provider_registration_enabled: bool | None = None
    booking_enabled: bool | None = None
    maintenance_mode: bool | None = None

    platform_commission_percent: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
    )


def _admin_get_settings(db: Session):
    settings = (
        db.query(AdminSettings)
        .filter(AdminSettings.id == 1)
        .first()
    )

    if settings is None:
        settings = AdminSettings(id=1)
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def _admin_settings_response(settings):
    return _admin_row(
        settings,
        [
            "id",
            "platform_name",
            "support_email",
            "support_phone",
            "customer_registration_enabled",
            "provider_registration_enabled",
            "booking_enabled",
            "maintenance_mode",
            "platform_commission_percent",
            "updated_at",
        ],
    )


@router.get("/settings")
def admin_get_settings(
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    settings = _admin_get_settings(db)

    return _admin_settings_response(settings)


@router.patch("/settings")
def admin_update_settings(
    payload: AdminSettingsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(_admin_require),
):
    settings = _admin_get_settings(db)

    updates = payload.dict(exclude_unset=True)

    for key, value in updates.items():
        if value is None and key not in ["support_email", "support_phone"]:
            raise HTTPException(
                status_code=400,
                detail=f"{key} cannot be null",
            )

        setattr(settings, key, value)

    try:
        db.commit()
        db.refresh(settings)

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Admin settings update failed",
        )

    return {
        "message": "Admin settings updated successfully",
        "settings": _admin_settings_response(settings),
    }
