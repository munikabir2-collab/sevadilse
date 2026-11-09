"""
Home Delivery module - API  (prefix: /delivery)

Roles
-----
- Customer       : koi bhi logged-in user (order dena, dekhna, cancel)
- Sub-admin      : DeliveryStaff(role=sub_admin)  -> sirf apne AREA ke orders
- Delivery boy   : DeliveryStaff(role=delivery_boy) -> sirf apne assigned orders
- Main admin     : users.is_admin = True -> sab kuch, staff banana, reports, activity

Status flow
-----------
pending -> accepted -> assigned -> picked_up -> out_for_delivery -> delivered
(pending/accepted/assigned se cancelled, pending se rejected)
"""

from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.delivery_model import (
    DeliveryOrder,
    DeliveryOrderStatus,
    DeliveryPaymentMethod,
    DeliveryPaymentStatus,
    DeliveryStaff,
    DeliveryStaffRole,
    DeliveryStatusLog,
)
from app.models.order_model import RestaurantOrder
from app.models.provider_model import Provider
from app.models.user_model import User
from app.schemas.delivery_schema import (
    AssignRequest,
    CODCollectRequest,
    DeliveryOrderCreate,
    DeliveryOrderOut,
    ReasonRequest,
    StaffActiveUpdate,
    StaffCreate,
    StaffOut,
    StatusLogOut,
    StatusUpdateRequest,
)

router = APIRouter(prefix="/delivery", tags=["Home Delivery"])

# Flat delivery charge (₹). Baad mein area-wise / distance-wise kar sakte hain.
DEFAULT_DELIVERY_CHARGE = 30.0

IST = timezone(timedelta(hours=5, minutes=30))

S = DeliveryOrderStatus

ALLOWED_TRANSITIONS = {
    S.pending: {S.accepted, S.rejected, S.cancelled},
    S.accepted: {S.assigned, S.cancelled},
    S.assigned: {S.picked_up, S.cancelled},
    S.picked_up: {S.out_for_delivery},
    S.out_for_delivery: {S.delivered},
}

BOY_ALLOWED = {S.picked_up, S.out_for_delivery, S.delivered}


# ============================================================
# HELPERS
# ============================================================

def _norm(area: str | None) -> str:
    return " ".join((area or "").strip().lower().split())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _staff_of(db: Session, user: User) -> DeliveryStaff | None:
    return (
        db.query(DeliveryStaff)
        .filter(
            DeliveryStaff.user_id == user.id,
            DeliveryStaff.is_active == True,  # noqa: E712
        )
        .first()
    )


@dataclass
class Actor:
    user: User
    is_main_admin: bool
    area: str | None
    staff: DeliveryStaff | None


def require_delivery_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Actor:
    if current_user.is_admin:
        return Actor(current_user, True, None, None)

    staff = _staff_of(db, current_user)
    if staff and staff.role == DeliveryStaffRole.sub_admin:
        return Actor(current_user, False, staff.area, staff)

    raise HTTPException(
        status_code=403,
        detail="Delivery sub-admin ya admin access required",
    )


def require_delivery_boy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeliveryStaff:
    staff = _staff_of(db, current_user)
    if staff and staff.role == DeliveryStaffRole.delivery_boy:
        return staff

    raise HTTPException(status_code=403, detail="Delivery boy access required")


def _log(db: Session, order: DeliveryOrder, status: str, user_id: int | None, note: str | None = None):
    db.add(
        DeliveryStatusLog(
            order_id=order.id,
            status=status,
            changed_by=user_id,
            note=note,
        )
    )


def _change_status(
    db: Session,
    order: DeliveryOrder,
    new_status: DeliveryOrderStatus,
    user_id: int,
    note: str | None = None,
):
    allowed = ALLOWED_TRANSITIONS.get(order.status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"{order.status.value} se {new_status.value} nahi ho sakta",
        )

    order.status = new_status

    if new_status == S.delivered:
        order.delivered_at = _now()

    _log(db, order, new_status.value, user_id, note)


def _commit(db: Session, order: DeliveryOrder | None = None):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database save nahi ho paya")

    if order is not None:
        db.refresh(order)


def _admin_order(db: Session, actor: Actor, order_id: int) -> DeliveryOrder:
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if not actor.is_main_admin and order.area != actor.area:
        raise HTTPException(status_code=403, detail="Ye order aapke area ka nahi hai")

    return order


def _collect_cod(db: Session, order: DeliveryOrder, user_id: int, notes: str | None):
    if order.payment_method != DeliveryPaymentMethod.cod:
        raise HTTPException(status_code=400, detail="Ye COD order nahi hai")

    if order.status != S.delivered:
        raise HTTPException(status_code=400, detail="COD delivery ke baad hi collect hota hai")

    if order.cod_collected:
        raise HTTPException(status_code=409, detail="COD pehle hi collect ho chuka hai")

    order.cod_collected = True
    order.cod_collected_at = _now()
    order.payment_status = DeliveryPaymentStatus.paid

    _log(db, order, "cod_collected", user_id, notes or f"COD Rs {order.total_amount}")


def _staff_out(db: Session, staff: DeliveryStaff) -> StaffOut:
    user = db.query(User).filter(User.id == staff.user_id).first()
    return StaffOut(
        id=staff.id,
        user_id=staff.user_id,
        name=user.name if user else None,
        email=user.email if user else None,
        phone=user.phone if user else None,
        role=staff.role,
        area=staff.area,
        is_active=staff.is_active,
    )


# ============================================================
# WHO AM I (app ko role batata hai)
# ============================================================

@router.get("/me")
def delivery_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    staff = _staff_of(db, current_user)

    if not staff or staff.role != DeliveryStaffRole.delivery_boy:
        raise HTTPException(
            status_code=403,
            detail="Access denied. Registered active delivery boy only.",
        )

    return {
        "user_id": current_user.id,
        "role": "delivery_boy",
        "area": staff.area,
        "staff_id": staff.id,
    }


# ============================================================
# CUSTOMER
# ============================================================

@router.post("/orders", response_model=DeliveryOrderOut)
def create_delivery_order(
    payload: DeliveryOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    area = _norm(payload.area)
    if not area:
        raise HTTPException(status_code=400, detail="Area zaroori hai")

    provider_id = payload.provider_id
    amount = payload.order_amount

    if payload.restaurant_order_id is not None:
        ro = (
            db.query(RestaurantOrder)
            .filter(RestaurantOrder.id == payload.restaurant_order_id)
            .first()
        )
        if not ro:
            raise HTTPException(status_code=404, detail="Restaurant order nahi mila")

        if ro.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Ye aapka order nahi hai")

        duplicate = (
            db.query(DeliveryOrder)
            .filter(
                DeliveryOrder.restaurant_order_id == ro.id,
                DeliveryOrder.status.notin_([S.cancelled, S.rejected]),
            )
            .first()
        )
        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="Is order ki delivery pehle se request ho chuki hai",
            )

        provider_id = ro.provider_id
        amount = float(ro.grand_total)

    elif provider_id is not None:
        if not db.query(Provider).filter(Provider.id == provider_id).first():
            raise HTTPException(status_code=404, detail="Provider nahi mila")

    if amount is None:
        raise HTTPException(status_code=400, detail="order_amount zaroori hai")

    charge = DEFAULT_DELIVERY_CHARGE

    order = DeliveryOrder(
        user_id=current_user.id,
        provider_id=provider_id,
        restaurant_order_id=payload.restaurant_order_id,
        customer_name=payload.customer_name.strip(),
        customer_phone=payload.customer_phone.strip(),
        address=payload.address.strip(),
        landmark=payload.landmark,
        area=area,
        items_description=payload.items_description,
        notes=payload.notes,
        order_amount=round(amount, 2),
        delivery_charge=charge,
        total_amount=round(amount + charge, 2),
        payment_method=payload.payment_method,
        payment_status=DeliveryPaymentStatus.pending,
        status=S.pending,
    )

    db.add(order)
    db.flush()
    _log(db, order, S.pending.value, current_user.id, "Order placed")
    _commit(db, order)

    return order


@router.get("/orders/my", response_model=list[DeliveryOrderOut])
def my_delivery_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.user_id == current_user.id)
        .order_by(DeliveryOrder.created_at.desc())
        .all()
    )


def _can_view(db: Session, user: User, order: DeliveryOrder) -> bool:
    if user.is_admin or order.user_id == user.id:
        return True

    staff = _staff_of(db, user)
    if not staff:
        return False

    if staff.role == DeliveryStaffRole.sub_admin:
        return staff.area == order.area

    return order.assigned_to == staff.id


@router.get("/orders/{order_id}", response_model=DeliveryOrderOut)
def get_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if not _can_view(db, current_user, order):
        raise HTTPException(status_code=403, detail="Is order ko dekhne ki permission nahi hai")

    return order


@router.get("/orders/{order_id}/timeline", response_model=list[StatusLogOut])
def delivery_timeline(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if not _can_view(db, current_user, order):
        raise HTTPException(status_code=403, detail="Is order ko dekhne ki permission nahi hai")

    return (
        db.query(DeliveryStatusLog)
        .filter(DeliveryStatusLog.order_id == order_id)
        .order_by(DeliveryStatusLog.id.asc())
        .all()
    )


@router.patch("/orders/{order_id}/cancel", response_model=DeliveryOrderOut)
def customer_cancel(
    order_id: int,
    payload: ReasonRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ye aapka order nahi hai")

    if order.status not in (S.pending, S.accepted):
        raise HTTPException(
            status_code=400,
            detail="Order ab cancel nahi ho sakta. Sub-admin se sampark karein.",
        )

    reason = payload.reason if payload else None
    _change_status(db, order, S.cancelled, current_user.id, reason or "Customer cancelled")
    order.cancel_reason = reason or "Customer cancelled"
    _commit(db, order)

    return order


# ============================================================
# SUB-ADMIN / MAIN ADMIN  - ORDERS
# ============================================================

@router.get("/admin/orders", response_model=list[DeliveryOrderOut])
def admin_list_orders(
    status: DeliveryOrderStatus | None = None,
    area: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryOrder)

    if not actor.is_main_admin:
        query = query.filter(DeliveryOrder.area == actor.area)
    elif area:
        query = query.filter(DeliveryOrder.area == _norm(area))

    if status:
        query = query.filter(DeliveryOrder.status == status)

    return (
        query.order_by(DeliveryOrder.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.patch("/admin/orders/{order_id}/accept", response_model=DeliveryOrderOut)
def admin_accept(
    order_id: int,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)
    _change_status(db, order, S.accepted, actor.user.id, "Accepted")
    _commit(db, order)
    return order


@router.patch("/admin/orders/{order_id}/reject", response_model=DeliveryOrderOut)
def admin_reject(
    order_id: int,
    payload: ReasonRequest | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)
    reason = payload.reason if payload else None
    _change_status(db, order, S.rejected, actor.user.id, reason or "Rejected")
    order.cancel_reason = reason or "Rejected"
    _commit(db, order)
    return order


@router.patch("/admin/orders/{order_id}/assign", response_model=DeliveryOrderOut)
def admin_assign(
    order_id: int,
    payload: AssignRequest,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)

    boy = (
        db.query(DeliveryStaff)
        .filter(
            DeliveryStaff.id == payload.staff_id,
            DeliveryStaff.role == DeliveryStaffRole.delivery_boy,
            DeliveryStaff.is_active == True,  # noqa: E712
        )
        .first()
    )

    if not boy:
        raise HTTPException(status_code=404, detail="Active delivery boy nahi mila")

    if boy.area != order.area:
        raise HTTPException(status_code=400, detail="Delivery boy dusre area ka hai")

    if order.status == S.accepted:
        _change_status(db, order, S.assigned, actor.user.id, f"Assigned to staff #{boy.id}")
    elif order.status == S.assigned:
        _log(db, order, "reassigned", actor.user.id, f"Reassigned to staff #{boy.id}")
    else:
        raise HTTPException(
            status_code=400,
            detail="Assign sirf accepted ya assigned order par ho sakta hai",
        )

    order.assigned_to = boy.id
    _commit(db, order)
    return order


@router.patch("/admin/orders/{order_id}/status", response_model=DeliveryOrderOut)
def admin_update_status(
    order_id: int,
    payload: StatusUpdateRequest,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)

    if payload.status not in BOY_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail="Yahan sirf picked_up, out_for_delivery, delivered allowed hain. "
                   "accept/reject/assign/cancel ke alag endpoints hain.",
        )

    _change_status(db, order, payload.status, actor.user.id, payload.note)
    _commit(db, order)
    return order


@router.patch("/admin/orders/{order_id}/cancel", response_model=DeliveryOrderOut)
def admin_cancel(
    order_id: int,
    payload: ReasonRequest | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)
    reason = payload.reason if payload else None
    _change_status(db, order, S.cancelled, actor.user.id, reason or "Cancelled by admin")
    order.cancel_reason = reason or "Cancelled by admin"
    _commit(db, order)
    return order


@router.patch("/admin/orders/{order_id}/collect-cod", response_model=DeliveryOrderOut)
def admin_collect_cod(
    order_id: int,
    payload: CODCollectRequest | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    order = _admin_order(db, actor, order_id)
    _collect_cod(db, order, actor.user.id, payload.notes if payload else None)
    _commit(db, order)
    return order


# ============================================================
# SUB-ADMIN / MAIN ADMIN  - STAFF
# ============================================================

@router.post("/admin/staff", response_model=StaffOut)
def admin_create_staff(
    payload: StaffCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.email == payload.email.strip())
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Is email ka user nahi mila. Pehle app mein signup karwayein.",
        )

    if db.query(DeliveryStaff).filter(DeliveryStaff.user_id == user.id).first():
        raise HTTPException(status_code=409, detail="Ye user pehle se staff mein hai")

    if actor.is_main_admin:
        area = _norm(payload.area)
        if not area:
            raise HTTPException(status_code=400, detail="Staff ka area zaroori hai")
    else:
        # sub-admin sirf apne area ke delivery boy bana sakta hai
        if payload.role != DeliveryStaffRole.delivery_boy:
            raise HTTPException(
                status_code=403,
                detail="Sub-admin sirf delivery boy bana sakta hai",
            )
        area = actor.area

    staff = DeliveryStaff(
        user_id=user.id,
        role=payload.role,
        area=area,
        is_active=True,
        created_by=actor.user.id,
    )

    db.add(staff)
    _commit(db)
    db.refresh(staff)

    return _staff_out(db, staff)


@router.get("/admin/staff", response_model=list[StaffOut])
def admin_list_staff(
    role: DeliveryStaffRole | None = None,
    area: str | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryStaff)

    if not actor.is_main_admin:
        query = query.filter(
            DeliveryStaff.area == actor.area,
            DeliveryStaff.role == DeliveryStaffRole.delivery_boy,
        )
    else:
        if area:
            query = query.filter(DeliveryStaff.area == _norm(area))
        if role:
            query = query.filter(DeliveryStaff.role == role)

    rows = query.order_by(DeliveryStaff.id.asc()).all()
    return [_staff_out(db, s) for s in rows]


@router.patch("/admin/staff/{staff_id}/active", response_model=StaffOut)
def admin_set_staff_active(
    staff_id: int,
    payload: StaffActiveUpdate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    staff = db.query(DeliveryStaff).filter(DeliveryStaff.id == staff_id).first()

    if not staff:
        raise HTTPException(status_code=404, detail="Staff nahi mila")

    if not actor.is_main_admin:
        if staff.area != actor.area or staff.role != DeliveryStaffRole.delivery_boy:
            raise HTTPException(status_code=403, detail="Is staff par aapka adhikar nahi hai")

    staff.is_active = payload.is_active
    _commit(db)
    db.refresh(staff)

    return _staff_out(db, staff)


# ============================================================
# REPORTS / ACTIVITY
# ============================================================

@router.get("/admin/reports/daily")
def admin_daily_report(
    day: date_type | None = Query(None, description="YYYY-MM-DD (IST). Default aaj"),
    area: str | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    day = day or datetime.now(IST).date()

    start = datetime.combine(day, time.min, tzinfo=IST)
    end = start + timedelta(days=1)

    query = db.query(DeliveryOrder).filter(
        DeliveryOrder.created_at >= start,
        DeliveryOrder.created_at < end,
    )

    if not actor.is_main_admin:
        query = query.filter(DeliveryOrder.area == actor.area)
    elif area:
        query = query.filter(DeliveryOrder.area == _norm(area))

    rows = query.all()

    by_status = {s.value: 0 for s in DeliveryOrderStatus}
    for r in rows:
        by_status[r.status.value] += 1

    delivered = [r for r in rows if r.status == S.delivered]

    cod_query = db.query(DeliveryOrder).filter(
        DeliveryOrder.cod_collected == True,  # noqa: E712
        DeliveryOrder.cod_collected_at >= start,
        DeliveryOrder.cod_collected_at < end,
    )
    if not actor.is_main_admin:
        cod_query = cod_query.filter(DeliveryOrder.area == actor.area)
    elif area:
        cod_query = cod_query.filter(DeliveryOrder.area == _norm(area))

    cod_total = sum(float(r.total_amount) for r in cod_query.all())

    return {
        "date": day.isoformat(),
        "area": actor.area if not actor.is_main_admin else (_norm(area) or "all"),
        "total_orders": len(rows),
        "by_status": by_status,
        "delivered_orders": len(delivered),
        "cancelled_orders": by_status[S.cancelled.value] + by_status[S.rejected.value],
        "delivery_charges_earned": round(sum(float(r.delivery_charge) for r in delivered), 2),
        "delivered_value": round(sum(float(r.total_amount) for r in delivered), 2),
        "cod_collected_inr": round(cod_total, 2),
        "currency": "INR",
    }


@router.get("/admin/activity", response_model=list[StatusLogOut])
def admin_activity(
    limit: int = Query(50, ge=1, le=200),
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    if not actor.is_main_admin:
        raise HTTPException(status_code=403, detail="Sirf main admin activity dekh sakta hai")

    return (
        db.query(DeliveryStatusLog)
        .order_by(DeliveryStatusLog.id.desc())
        .limit(limit)
        .all()
    )


# ============================================================
# DELIVERY BOY
# ============================================================

@router.get("/boy/orders", response_model=list[DeliveryOrderOut])
def boy_orders(
    active_only: bool = True,
    staff: DeliveryStaff = Depends(require_delivery_boy),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryOrder).filter(DeliveryOrder.assigned_to == staff.id)

    if active_only:
        query = query.filter(
            DeliveryOrder.status.in_([S.assigned, S.picked_up, S.out_for_delivery])
        )

    return query.order_by(DeliveryOrder.created_at.desc()).all()


def _boy_order(db: Session, staff: DeliveryStaff, order_id: int) -> DeliveryOrder:
    order = (
        db.query(DeliveryOrder)
        .filter(DeliveryOrder.id == order_id, DeliveryOrder.assigned_to == staff.id)
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Ye order aapko assign nahi hai")

    return order


@router.patch("/boy/orders/{order_id}/status", response_model=DeliveryOrderOut)
def boy_update_status(
    order_id: int,
    payload: StatusUpdateRequest,
    staff: DeliveryStaff = Depends(require_delivery_boy),
    db: Session = Depends(get_db),
):
    order = _boy_order(db, staff, order_id)

    if payload.status not in BOY_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail="Sirf picked_up, out_for_delivery, delivered allowed hain",
        )

    _change_status(db, order, payload.status, staff.user_id, payload.note)
    _commit(db, order)
    return order


@router.patch("/boy/orders/{order_id}/collect-cod", response_model=DeliveryOrderOut)
def boy_collect_cod(
    order_id: int,
    payload: CODCollectRequest | None = None,
    staff: DeliveryStaff = Depends(require_delivery_boy),
    db: Session = Depends(get_db),
):
    order = _boy_order(db, staff, order_id)
    _collect_cod(db, order, staff.user_id, payload.notes if payload else None)
    _commit(db, order)
    return order
