
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user_model import User
from app.models.menu_item_model import MenuItem
from app.models.order_model import (
    RestaurantOrder,
    RestaurantOrderItem,
    OrderStatus,
    OrderType,
)
from app.models.provider_model import Provider, ProviderCategory
from app.models.restaurant_table_model import RestaurantTable
from app.schemas.order_schema import (
    OrderCreate,
    OrderOut,
    OrderStatusUpdate,
)

router = APIRouter(
    prefix="/orders",
    tags=["Food Orders"],
)


# ---------------------------------------------------------
# Helper: check whether current user can manage restaurant
# ---------------------------------------------------------
def require_provider_or_admin(
    current_user: User,
    provider: Provider,
):
    if current_user.is_admin:
        return

    if not current_user.is_provider:
        raise HTTPException(
            status_code=403,
            detail="Sirf restaurant provider ya admin ye action kar sakta hai",
        )

    if provider.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Aap is restaurant ke owner nahi hain",
        )


# ---------------------------------------------------------
# CREATE ORDER
# ---------------------------------------------------------
@router.post(
    "/",
    response_model=OrderOut,
)
def create_order(
    order: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == order.provider_id)
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
            detail="Food order sirf restaurant ke liye hai",
        )

    if not order.items:
        raise HTTPException(
            status_code=400,
            detail="Order me kam se kam ek item hona chahiye",
        )

    # -----------------------------------------------------
    # Dine-in table validation
    # -----------------------------------------------------
    if order.order_type == OrderType.dine_in:
        if not order.table_id:
            raise HTTPException(
                status_code=400,
                detail="Dine-in order ke liye table_id zaroori hai",
            )

        table = (
            db.query(RestaurantTable)
            .filter(
                RestaurantTable.id == order.table_id,
                RestaurantTable.provider_id == order.provider_id,
            )
            .first()
        )

        if not table:
            raise HTTPException(
                status_code=404,
                detail="Restaurant table nahi mili",
            )

    # -----------------------------------------------------
    # Calculate order
    # -----------------------------------------------------
    subtotal = 0.0
    order_items = []

    for requested_item in order.items:

        if requested_item.quantity <= 0:
            raise HTTPException(
                status_code=400,
                detail="Item quantity 0 se greater honi chahiye",
            )

        menu_item = (
            db.query(MenuItem)
            .filter(
                MenuItem.id == requested_item.menu_item_id,
                MenuItem.provider_id == order.provider_id,
            )
            .first()
        )

        if not menu_item:
            raise HTTPException(
                status_code=404,
                detail=f"Menu item {requested_item.menu_item_id} nahi mila",
            )

        if not menu_item.is_available:
            raise HTTPException(
                status_code=400,
                detail=f"{menu_item.name} abhi available nahi hai",
            )

        total_price = menu_item.price * requested_item.quantity
        subtotal += total_price

        order_items.append(
            RestaurantOrderItem(
                menu_item_id=menu_item.id,
                quantity=requested_item.quantity,
                unit_price=menu_item.price,
                total_price=total_price,
            )
        )

    # -----------------------------------------------------
    # Discount / GST / Service Charge
    # -----------------------------------------------------
    discount = min(order.discount, subtotal)

    taxable_amount = subtotal - discount

    gst = taxable_amount * order.gst_percent / 100

    service_charge = (
        taxable_amount * order.service_charge_percent / 100
    )

    grand_total = (
        taxable_amount
        + gst
        + service_charge
    )

    # -----------------------------------------------------
    # IMPORTANT:
    # user_id request body se nahi,
    # JWT logged-in user se liya ja raha hai.
    # -----------------------------------------------------
    db_order = RestaurantOrder(
        user_id=current_user.id,
        provider_id=order.provider_id,
        table_id=order.table_id,
        order_type=order.order_type,
        status=OrderStatus.pending,
        subtotal=round(subtotal, 2),
        discount=round(discount, 2),
        gst=round(gst, 2),
        service_charge=round(service_charge, 2),
        grand_total=round(grand_total, 2),
        special_instructions=order.special_instructions,
    )

    db.add(db_order)
    db.flush()

    for item in order_items:
        item.order_id = db_order.id
        db.add(item)

    db.commit()
    db.refresh(db_order)

    return db_order


# ---------------------------------------------------------
# LIST CURRENT USER ORDERS
# ---------------------------------------------------------
@router.get(
    "/user/{user_id}",
    response_model=list[OrderOut],
)
def list_user_orders(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # User sirf apne orders dekh sakta hai.
    # Admin kisi bhi user ke orders dekh sakta hai.
    if not current_user.is_admin and user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Aap doosre user ke orders access nahi kar sakte",
        )

    return (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.user_id == user_id)
        .order_by(RestaurantOrder.created_at.desc())
        .all()
    )


# ---------------------------------------------------------
# GET SINGLE ORDER
# ---------------------------------------------------------
@router.get(
    "/{order_id}",
    response_model=OrderOut,
)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order nahi mila",
        )

    # Customer apna order dekh sakta hai.
    # Provider apne restaurant ka order dekh sakta hai.
    # Admin sab dekh sakta hai.
    if not current_user.is_admin:

        if order.user_id == current_user.id:
            return order

        provider = (
            db.query(Provider)
            .filter(Provider.id == order.provider_id)
            .first()
        )

        if not provider or provider.owner_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Aap is order ko access nahi kar sakte",
            )

    return order


# ---------------------------------------------------------
# UPDATE ORDER STATUS
# Provider owner / Admin only
# ---------------------------------------------------------
@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
)
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == order.provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Restaurant provider nahi mila",
        )

    # Provider owner / Admin only
    require_provider_or_admin(
        current_user,
        provider,
    )

    if order.status == OrderStatus.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Cancelled order ka status change nahi kar sakte",
        )

    if (
        data.status == OrderStatus.cancelled
        and order.payment_status.value == "paid"
    ):
        raise HTTPException(
            status_code=400,
            detail="Paid order ko pehle refund process karein",
        )

    order.status = data.status

    db.commit()
    db.refresh(order)

    return order


# ---------------------------------------------------------
# CANCEL ORDER
# Customer owner / Admin
# ---------------------------------------------------------
@router.patch(
    "/{order_id}/cancel",
    response_model=OrderOut,
)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.id == order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order nahi mila",
        )

    # Customer sirf apna order cancel kar sakta hai.
    # Admin kisi bhi order ko cancel kar sakta hai.
    if not current_user.is_admin and order.user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Aap doosre user ka order cancel nahi kar sakte",
        )

    if order.status in [
        OrderStatus.completed,
        OrderStatus.served,
        OrderStatus.cancelled,
    ]:
        raise HTTPException(
            status_code=400,
            detail="Is order ko ab cancel nahi kiya ja sakta",
        )

    # Paid order ko direct cancel nahi karna.
    if order.payment_status.value == "paid":
        raise HTTPException(
            status_code=400,
            detail="Paid order ko cancel karne se pehle refund process karein",
        )

    order.status = OrderStatus.cancelled

    db.commit()
    db.refresh(order)

    return order

