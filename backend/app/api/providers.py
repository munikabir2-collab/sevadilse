from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.provider_model import Provider, ProviderCategory
from app.models.service_model import Service
from app.schemas.provider_schema import (
    ProviderCreate,
    ProviderOut,
    ProviderDetailOut,
    ServiceCreate,
    ServiceOut,
)

router = APIRouter(prefix="/providers", tags=["Providers"])


@router.post("/", response_model=ProviderOut)
def create_provider(
    provider: ProviderCreate, owner_id: int, db: Session = Depends(get_db)
):
    # owner_id abhi query param hai — /auth/login (JWT) bante hi token se milega
    db_provider = Provider(owner_id=owner_id, **provider.model_dump())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


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
    if owner_id:
        query = query.filter(Provider.owner_id == owner_id)
    return query.order_by(Provider.avg_rating.desc()).all()


@router.get("/{provider_id}", response_model=ProviderDetailOut)
def get_provider(provider_id: int, db: Session = Depends(get_db)):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider nahi mila")
    return provider


@router.post("/{provider_id}/services", response_model=ServiceOut)
def add_service(
    provider_id: int, service: ServiceCreate, db: Session = Depends(get_db)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider nahi mila")

    db_service = Service(provider_id=provider_id, **service.model_dump())
    db.add(db_service)
    db.commit()
    db.refresh(db_service)
    return db_service
