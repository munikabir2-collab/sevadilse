
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.menu_item_model import MenuItem
from app.models.provider_model import Provider, ProviderCategory
from app.schemas.menu_schema import (
    MenuItemCreate,
    MenuItemUpdate,
    MenuItemOut,
)

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurant Menu"],
)


def check_restaurant_access(
    provider: Provider,
    current_user,
):
    if provider.category != ProviderCategory.restaurant:
        raise HTTPException(
            status_code=400,
            detail="Ye provider restaurant nahi hai",
        )

    if (
        provider.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="Is restaurant ka menu manage karne ki permission nahi hai",
        )


@router.post(
    "/{provider_id}/menu",
    response_model=MenuItemOut,
)
def create_menu_item(
    provider_id: int,
    item: MenuItemCreate,
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
            detail="Restaurant provider nahi mila",
        )

    check_restaurant_access(provider, current_user)

    db_item = MenuItem(
        provider_id=provider_id,
        **item.model_dump(),
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


@router.get(
    "/{provider_id}/menu",
    response_model=list[MenuItemOut],
)
def list_menu(
    provider_id: int,
    category: str | None = None,
    available_only: bool = False,
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
            detail="Restaurant provider nahi mila",
        )

    if provider.category != ProviderCategory.restaurant:
        raise HTTPException(
            status_code=400,
            detail="Ye provider restaurant nahi hai",
        )

    query = db.query(MenuItem).filter(
        MenuItem.provider_id == provider_id
    )

    if category:
        query = query.filter(
            MenuItem.category.ilike(f"%{category}%")
        )

    if available_only:
        query = query.filter(
            MenuItem.is_available.is_(True)
        )

    return query.order_by(
        MenuItem.category,
        MenuItem.name,
    ).all()


@router.get(
    "/menu/{item_id}",
    response_model=MenuItemOut,
)
def get_menu_item(
    item_id: int,
    db: Session = Depends(get_db),
):
    item = (
        db.query(MenuItem)
        .filter(MenuItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Menu item nahi mila",
        )

    return item


@router.patch(
    "/menu/{item_id}",
    response_model=MenuItemOut,
)
def update_menu_item(
    item_id: int,
    data: MenuItemUpdate,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(MenuItem)
        .filter(MenuItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Menu item nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == item.provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Restaurant provider nahi mila",
        )

    check_restaurant_access(provider, current_user)

    updates = data.model_dump(exclude_unset=True)

    for key, value in updates.items():
        setattr(item, key, value)

    db.commit()
    db.refresh(item)

    return item


@router.delete("/menu/{item_id}")
def delete_menu_item(
    item_id: int,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = (
        db.query(MenuItem)
        .filter(MenuItem.id == item_id)
        .first()
    )

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Menu item nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == item.provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Restaurant provider nahi mila",
        )

    check_restaurant_access(provider, current_user)

    db.delete(item)
    db.commit()

    return {
        "message": "Menu item delete ho gaya",
        "item_id": item_id,
    }
