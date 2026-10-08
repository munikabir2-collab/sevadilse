from datetime import datetime

from pydantic import BaseModel

from app.models.bill_model import BillPaymentStatus


class BillCreate(BaseModel):
    order_id: int


class BillOut(BaseModel):
    id: int
    order_id: int
    subtotal: float
    discount: float
    gst: float
    service_charge: float
    grand_total: float
    payment_status: BillPaymentStatus
    created_at: datetime
    paid_at: datetime | None

    class Config:
        from_attributes = True


class BillPaymentStatusUpdate(BaseModel):
    payment_status: BillPaymentStatus