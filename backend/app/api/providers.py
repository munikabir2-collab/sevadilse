
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.booking_model import Booking
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.provider_model import Provider, ProviderCategory
from app.models.service_model import Service


from app.schemas.provider_schema import (
    ProviderCreate,
    ProviderOut,
    ProviderDetailOut,
    ProviderUpdate,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
)

router = APIRouter(prefix="/providers", tags=["Providers"])


# ============================================================
# CREATE PROVIDER - JWT AUTHENTICATED
# ============================================================

@router.post("/", response_model=ProviderOut)
def create_provider(
    provider: ProviderCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check whether this user already has a provider profile
    existing_provider = (
        db.query(Provider)
        .filter(Provider.owner_id == current_user.id)
        .first()
    )

    if existing_provider:
        raise HTTPException(
            status_code=409,
            detail="Is account ka Provider profile pehle se bana hua hai",
        )

    # Create provider using authenticated user's ID
    db_provider = Provider(
        owner_id=current_user.id,
        **provider.model_dump(),
    )

    # Update role and create provider in the same transaction
    current_user.is_provider = True
    db.add(db_provider)

    try:
        db.commit()
        db.refresh(db_provider)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Provider profile create nahi ho paya",
        )

    return db_provider


# ============================================================
# LIST PROVIDERS
# ============================================================

@router.get("/", response_model=list[ProviderOut])
def list_providers(
    category: ProviderCategory | None = None,
    city: str | None = None,
    search: str | None = Query(None, description="Naam me search karo"),
    owner_id: int | None = Query(None, description="Sirf is owner ki listings"),
    db: Session = Depends(get_db),
):
    query = db.query(Provider)

    if category:
        query = query.filter(Provider.category == category)

    if city:
        query = query.filter(Provider.city.ilike(f"%{city}%"))

    if search:
        query = query.filter(Provider.name.ilike(f"%{search}%"))

    if owner_id is not None:
        query = query.filter(Provider.owner_id == owner_id)

    return query.order_by(Provider.avg_rating.desc()).all()


# ============================================================
# GET PROVIDER
# ============================================================

@router.get("/{provider_id}", response_model=ProviderDetailOut)
def get_provider(
    provider_id: int,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider nahi mila",
        )

    return provider


# ============================================================
# ADD SERVICE - OWNER OR ADMIN ONLY
# ============================================================

@router.post("/{provider_id}/services", response_model=ServiceOut)
def add_service(
    provider_id: int,
    service: ServiceCreate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Provider nahi mila",
        )

    # Only provider owner or admin can add services
    if (
        provider.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Is Provider ki service add karne ki permission nahi hai",
        )

    db_service = Service(
        provider_id=provider_id,
        **service.model_dump(),
    )

    db.add(db_service)

    try:
        db.commit()
        db.refresh(db_service)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Service add nahi ho payi",
        )

    return db_service



# ============================================================
# PROVIDER PROFILE UPDATE
# ============================================================

@router.patch("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: int,
    payload: ProviderUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider nahi mila")

    if provider.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="Update data required")

    for field in ("name", "category", "city"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=400,
                detail=f"{field} empty nahi ho sakta",
            )

    for key, value in updates.items():
        setattr(provider, key, value)

    try:
        db.commit()
        db.refresh(provider)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Provider update failed")

    return provider


# ============================================================
# SERVICE UPDATE
# ============================================================

@router.patch("/{provider_id}/services/{service_id}", response_model=ServiceOut)
def update_provider_service(
    provider_id: int,
    service_id: int,
    payload: ServiceUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider nahi mila")

    if provider.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider_id,
        )
        .first()
    )

    if not service:
        raise HTTPException(status_code=404, detail="Service nahi mili")

    updates = payload.model_dump(exclude_unset=True)

    if not updates:
        raise HTTPException(status_code=400, detail="Update data required")

    for field in ("name", "price", "capacity", "total_units"):
        if field in updates and updates[field] is None:
            raise HTTPException(
                status_code=400,
                detail=f"{field} empty nahi ho sakta",
            )

    for key, value in updates.items():
        setattr(service, key, value)

    try:
        db.commit()
        db.refresh(service)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Service update failed")

    return service


# ============================================================
# SERVICE DELETE
# ============================================================

@router.delete("/{provider_id}/services/{service_id}")
def delete_provider_service(
    provider_id: int,
    service_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(status_code=404, detail="Provider nahi mila")

    if provider.owner_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Permission denied")

    service = (
        db.query(Service)
        .filter(
            Service.id == service_id,
            Service.provider_id == provider_id,
        )
        .first()
    )

    if not service:
        raise HTTPException(status_code=404, detail="Service nahi mili")

    existing_booking = (
        db.query(Booking)
        .filter(Booking.service_id == service_id)
        .first()
    )

    if existing_booking:
        raise HTTPException(
            status_code=409,
            detail="Is service par booking history hai. Service delete nahi kar sakte.",
        )

    try:
        db.delete(service)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Service delete failed")

    return {
        "message": "Service delete ho gayi",
        "service_id": service_id,
    }
