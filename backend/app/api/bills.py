from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.bill_model import (
    RestaurantBill,
    BillPaymentStatus,
)
from app.models.order_model import (
    RestaurantOrder,
    PaymentStatus,
)
from app.schemas.bill_schema import (
    BillCreate,
    BillOut,
    BillPaymentStatusUpdate,
)

router = APIRouter(
    prefix="/bills",
    tags=["Restaurant Bills"],
)


@router.post(
    "/",
    response_model=BillOut,
)
def create_bill(
    data: BillCreate,
    db: Session = Depends(get_db),
):
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.id == data.order_id)
        .first()
    )

    if not order:
        raise HTTPException(
            status_code=404,
            detail="Order nahi mila",
        )

    existing = (
        db.query(RestaurantBill)
        .filter(RestaurantBill.order_id == data.order_id)
        .first()
    )

    if existing:
        return existing

    bill = RestaurantBill(
        order_id=order.id,
        subtotal=order.subtotal,
        discount=order.discount,
        gst=order.gst,
        service_charge=order.service_charge,
        grand_total=order.grand_total,
        payment_status=BillPaymentStatus.pending,
    )

    db.add(bill)
    db.commit()
    db.refresh(bill)

    return bill


@router.get(
    "/{bill_id}",
    response_model=BillOut,
)
def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
):
    bill = (
        db.query(RestaurantBill)
        .filter(RestaurantBill.id == bill_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill nahi mili",
        )

    return bill


@router.get(
    "/order/{order_id}",
    response_model=BillOut,
)
def get_order_bill(
    order_id: int,
    db: Session = Depends(get_db),
):
    bill = (
        db.query(RestaurantBill)
        .filter(RestaurantBill.order_id == order_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Is order ki bill nahi mili",
        )

    return bill


@router.patch(
    "/{bill_id}/payment-status",
    response_model=BillOut,
)
def update_bill_payment_status(
    bill_id: int,
    data: BillPaymentStatusUpdate,
    db: Session = Depends(get_db),
):
    bill = (
        db.query(RestaurantBill)
        .filter(RestaurantBill.id == bill_id)
        .first()
    )

    if not bill:
        raise HTTPException(
            status_code=404,
            detail="Bill nahi mili",
        )

    bill.payment_status = data.payment_status

    if data.payment_status == BillPaymentStatus.paid:
        bill.paid_at = datetime.now(timezone.utc)

    # Order ka payment status bhi sync karo
    order = (
        db.query(RestaurantOrder)
        .filter(RestaurantOrder.id == bill.order_id)
        .first()
    )

    if order:
        mapping = {
            BillPaymentStatus.pending: PaymentStatus.pending,
            BillPaymentStatus.paid: PaymentStatus.paid,
            BillPaymentStatus.failed: PaymentStatus.failed,
            BillPaymentStatus.refunded: PaymentStatus.refunded,
        }

        order.payment_status = mapping[data.payment_status]

    db.commit()
    db.refresh(bill)

    return bill