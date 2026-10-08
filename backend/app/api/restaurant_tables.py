from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.provider_model import Provider, ProviderCategory
from app.models.restaurant_table_model import RestaurantTable, TableStatus
from app.schemas.restaurant_table_schema import (
    RestaurantTableCreate,
    RestaurantTableUpdate,
    RestaurantTableOut,
)

router = APIRouter(
    prefix="/restaurants",
    tags=["Restaurant Tables"],
)


@router.post(
    "/{provider_id}/tables",
    response_model=RestaurantTableOut,
)
def create_table(
    provider_id: int,
    table: RestaurantTableCreate,
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

    if table.capacity < 1:
        raise HTTPException(
            status_code=400,
            detail="Table capacity kam se kam 1 honi chahiye",
        )

    existing = (
        db.query(RestaurantTable)
        .filter(
            RestaurantTable.provider_id == provider_id,
            RestaurantTable.table_number == table.table_number,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Ye table number pehle se exist karta hai",
        )

    db_table = RestaurantTable(
        provider_id=provider_id,
        table_number=table.table_number,
        capacity=table.capacity,
        description=table.description,
        status=TableStatus.available,
    )

    db.add(db_table)
    db.commit()
    db.refresh(db_table)

    return db_table


@router.get(
    "/{provider_id}/tables",
    response_model=list[RestaurantTableOut],
)
def list_tables(
    provider_id: int,
    status: TableStatus | None = None,
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

    query = db.query(RestaurantTable).filter(
        RestaurantTable.provider_id == provider_id
    )

    if status:
        query = query.filter(
            RestaurantTable.status == status
        )

    return query.order_by(RestaurantTable.table_number).all()


@router.get(
    "/tables/{table_id}",
    response_model=RestaurantTableOut,
)
def get_table(
    table_id: int,
    db: Session = Depends(get_db),
):
    table = (
        db.query(RestaurantTable)
        .filter(RestaurantTable.id == table_id)
        .first()
    )

    if not table:
        raise HTTPException(
            status_code=404,
            detail="Table nahi mili",
        )

    return table


@router.patch(
    "/tables/{table_id}",
    response_model=RestaurantTableOut,
)
def update_table(
    table_id: int,
    data: RestaurantTableUpdate,
    db: Session = Depends(get_db),
):
    table = (
        db.query(RestaurantTable)
        .filter(RestaurantTable.id == table_id)
        .first()
    )

    if not table:
        raise HTTPException(
            status_code=404,
            detail="Table nahi mili",
        )

    updates = data.model_dump(exclude_unset=True)

    if "capacity" in updates and updates["capacity"] < 1:
        raise HTTPException(
            status_code=400,
            detail="Table capacity kam se kam 1 honi chahiye",
        )

    if "table_number" in updates:
        existing = (
            db.query(RestaurantTable)
            .filter(
                RestaurantTable.provider_id == table.provider_id,
                RestaurantTable.table_number == updates["table_number"],
                RestaurantTable.id != table_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="Ye table number pehle se exist karta hai",
            )

    for key, value in updates.items():
        setattr(table, key, value)

    db.commit()
    db.refresh(table)

    return table


@router.delete(
    "/tables/{table_id}",
)
def delete_table(
    table_id: int,
    db: Session = Depends(get_db),
):
    table = (
        db.query(RestaurantTable)
        .filter(RestaurantTable.id == table_id)
        .first()
    )

    if not table:
        raise HTTPException(
            status_code=404,
            detail="Table nahi mili",
        )

    db.delete(table)
    db.commit()

    return {
        "message": "Restaurant table delete ho gayi",
        "table_id": table_id,
    }
