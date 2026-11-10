
"""
Home Delivery v2 - Multi-City / PIN Code API

Hierarchy:
Platform Super Admin
    -> City Main Admin
        -> Area Admin
            -> Delivery Boys (multiple area assignments)

Legacy order fields, COD, status logs and old sub_admin role are preserved.
"""

from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.core.database import get_db
from app.models.delivery_model import (
    DeliveryArea,
    DeliveryCity,
    DeliveryCityAdmin,
    DeliveryOrder,
    DeliveryOrderStatus,
    DeliveryPaymentMethod,
    DeliveryPaymentStatus,
    DeliveryPincode,
    DeliveryStaff,
    DeliveryStaffArea,
    DeliveryStaffRole,
    DeliveryStatusLog,
)
from app.models.order_model import RestaurantOrder
from app.models.provider_model import Provider
from app.models.user_model import User
from app.schemas.delivery_schema import (
    AssignRequest,
    AreaCreate,
    AreaOut,
    CityAdminCreate,
    CityAdminOut,
    CityCreate,
    CityOut,
    CODCollectRequest,
    DeliveryOrderCreate,
    DeliveryOrderOut,
    PincodeCheckOut,
    PincodeCreate,
    PincodeOut,
    PincodeUpdate,
    ReasonRequest,
    StaffActiveUpdate,
    StaffAreasUpdate,
    StaffCreate,
    StaffOut,
    StatusLogOut,
    StatusUpdateRequest,
)

router = APIRouter(prefix="/delivery", tags=["Home Delivery"])

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
# COMMON HELPERS
# ============================================================

def _norm(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _staff_of(db: Session, user: User) -> DeliveryStaff | None:
    return (
        db.query(DeliveryStaff)
        .filter(
            DeliveryStaff.user_id == user.id,
            DeliveryStaff.is_active.is_(True),
        )
        .first()
    )


def _staff_area_ids(db: Session, staff: DeliveryStaff) -> list[int]:
    ids = [
        row.area_id
        for row in db.query(DeliveryStaffArea)
        .filter(DeliveryStaffArea.staff_id == staff.id)
        .all()
    ]

    if ids:
        return list(dict.fromkeys(ids))

    # Legacy compatibility for old sub_admin / staff records.
    legacy_area = _norm(staff.area)
    if legacy_area:
        areas = (
            db.query(DeliveryArea)
            .filter(DeliveryArea.name.ilike(legacy_area))
            .all()
        )
        return [area.id for area in areas]

    return []


def _staff_area_names(db: Session, staff: DeliveryStaff) -> list[str]:
    ids = _staff_area_ids(db, staff)
    if not ids:
        return [staff.area] if staff.area else []

    return [
        area.name
        for area in db.query(DeliveryArea)
        .filter(DeliveryArea.id.in_(ids))
        .order_by(DeliveryArea.name.asc())
        .all()
    ]


def _commit(db: Session, refresh=None):
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Database save nahi ho paya",
        )

    if refresh is not None:
        db.refresh(refresh)


def _log(
    db: Session,
    order: DeliveryOrder,
    status: str,
    user_id: int | None,
    note: str | None = None,
):
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


def _collect_cod(
    db: Session,
    order: DeliveryOrder,
    user_id: int,
    notes: str | None,
):
    if order.payment_method != DeliveryPaymentMethod.cod:
        raise HTTPException(status_code=400, detail="Ye COD order nahi hai")

    if order.status != S.delivered:
        raise HTTPException(
            status_code=400,
            detail="COD delivery ke baad hi collect hota hai",
        )

    if order.cod_collected:
        raise HTTPException(status_code=409, detail="COD pehle hi collect ho chuka hai")

    order.cod_collected = True
    order.cod_collected_at = _now()
    order.payment_status = DeliveryPaymentStatus.paid

    _log(
        db,
        order,
        "cod_collected",
        user_id,
        notes or f"COD Rs {order.total_amount}",
    )


def _area_ids_for_city(db: Session, city_id: int) -> list[int]:
    return [
        row.id
        for row in db.query(DeliveryArea)
        .filter(DeliveryArea.city_id == city_id)
        .all()
    ]


def _get_area(db: Session, area_id: int) -> DeliveryArea:
    area = db.query(DeliveryArea).filter(DeliveryArea.id == area_id).first()
    if not area:
        raise HTTPException(status_code=404, detail="Area nahi mila")
    return area


def _check_area_scope(actor, area: DeliveryArea):
    if actor.role == "super_admin":
        return

    if actor.role == "city_admin" and area.city_id == actor.city_id:
        return

    if actor.role == "area_admin" and area.id in actor.area_ids:
        return

    raise HTTPException(status_code=403, detail="Is Area ka access nahi hai")


def _staff_out(db: Session, staff: DeliveryStaff) -> StaffOut:
    user = db.query(User).filter(User.id == staff.user_id).first()
    names = _staff_area_names(db, staff)
    ids = _staff_area_ids(db, staff)

    return StaffOut(
        id=staff.id,
        user_id=staff.user_id,
        name=user.name if user else None,
        email=user.email if user else None,
        phone=user.phone if user else None,
        role=staff.role,
        area_ids=ids,
        areas=names,
        is_active=staff.is_active,
    )


# ============================================================
# ACTOR / PERMISSIONS
# ============================================================

@dataclass
class Actor:
    user: User
    role: str
    city_id: int | None = None
    area_ids: list[int] | None = None
    staff: DeliveryStaff | None = None

    @property
    def is_main_admin(self):
        return self.role == "super_admin"


def require_delivery_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Actor:
    # Platform Super Admin
    if current_user.is_admin:
        return Actor(current_user, "super_admin")

    # City Main Admin
    city_admin = (
        db.query(DeliveryCityAdmin)
        .filter(
            DeliveryCityAdmin.user_id == current_user.id,
            DeliveryCityAdmin.is_active.is_(True),
        )
        .first()
    )
    if city_admin:
        return Actor(
            current_user,
            "city_admin",
            city_id=city_admin.city_id,
            area_ids=_area_ids_for_city(db, city_admin.city_id),
        )

    # Area Admin (legacy sub_admin is treated as an Area Admin)
    staff = _staff_of(db, current_user)
    if staff and staff.role in (
        DeliveryStaffRole.area_admin,
        DeliveryStaffRole.sub_admin,
    ):
        area_ids = _staff_area_ids(db, staff)
        if area_ids:
            return Actor(
                current_user,
                "area_admin",
                area_ids=area_ids,
                staff=staff,
            )

    raise HTTPException(
        status_code=403,
        detail="Delivery admin access required",
    )


def require_delivery_boy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeliveryStaff:
    staff = _staff_of(db, current_user)
    if staff and staff.role == DeliveryStaffRole.delivery_boy:
        return staff

    raise HTTPException(status_code=403, detail="Delivery boy access required")


def _order_in_actor_scope(db: Session, actor: Actor, order: DeliveryOrder) -> bool:
    if actor.role == "super_admin":
        return True

    if actor.role == "city_admin":
        return order.city_id == actor.city_id

    if actor.role == "area_admin":
        if order.area_id is not None:
            return order.area_id in (actor.area_ids or [])

        # Old orders without area_id: legacy area-name fallback.
        names = {
            _norm(a.name)
            for a in db.query(DeliveryArea)
            .filter(DeliveryArea.id.in_(actor.area_ids or [-1]))
            .all()
        }
        return _norm(order.area) in names

    return False


def _admin_order(db: Session, actor: Actor, order_id: int) -> DeliveryOrder:
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if not _order_in_actor_scope(db, actor, order):
        raise HTTPException(status_code=403, detail="Ye order aapke jurisdiction ka nahi hai")

    return order


def _boy_order(
    db: Session,
    staff: DeliveryStaff,
    order_id: int,
) -> DeliveryOrder:
    order = (
        db.query(DeliveryOrder)
        .filter(
            DeliveryOrder.id == order_id,
            DeliveryOrder.assigned_to == staff.id,
        )
        .first()
    )

    if not order:
        raise HTTPException(status_code=404, detail="Ye order aapko assign nahi hai")

    # Extra guard: assigned order must also belong to one of the boy's areas.
    area_ids = _staff_area_ids(db, staff)
    if order.area_id is not None and order.area_id not in area_ids:
        raise HTTPException(status_code=403, detail="Ye order aapke assigned Area ka nahi hai")

    return order


# ============================================================
# ROLE / PROFILE
# ============================================================

@router.get("/me")
def delivery_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.is_admin:
        return {"user_id": current_user.id, "role": "super_admin"}

    city_admin = (
        db.query(DeliveryCityAdmin)
        .filter(
            DeliveryCityAdmin.user_id == current_user.id,
            DeliveryCityAdmin.is_active.is_(True),
        )
        .first()
    )
    if city_admin:
        city = db.query(DeliveryCity).filter(
            DeliveryCity.id == city_admin.city_id
        ).first()
        return {
            "user_id": current_user.id,
            "role": "city_admin",
            "city_id": city_admin.city_id,
            "city": city.name if city else None,
        }

    staff = _staff_of(db, current_user)
    if not staff:
        raise HTTPException(status_code=403, detail="Delivery staff access required")

    return {
        "user_id": current_user.id,
        "role": staff.role.value,
        "staff_id": staff.id,
        "area_ids": _staff_area_ids(db, staff),
        "areas": _staff_area_names(db, staff),
    }


# ============================================================
# CITY MANAGEMENT
# ============================================================

@router.post("/admin/cities", response_model=CityOut)
def create_city(
    payload: CityCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can create cities")

    name = payload.name.strip()
    existing = db.query(DeliveryCity).filter(
        DeliveryCity.name.ilike(name)
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="City pehle se maujood hai")

    city = DeliveryCity(name=name, is_active=True)
    db.add(city)
    _commit(db, city)
    return city


@router.get("/admin/cities", response_model=list[CityOut])
def list_cities(
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryCity)

    if actor.role == "city_admin":
        query = query.filter(DeliveryCity.id == actor.city_id)
    elif actor.role == "area_admin":
        city_ids = [
            row.city_id
            for row in db.query(DeliveryArea)
            .filter(DeliveryArea.id.in_(actor.area_ids or [-1]))
            .all()
        ]
        query = query.filter(DeliveryCity.id.in_(city_ids or [-1]))

    return query.order_by(DeliveryCity.name.asc()).all()


# ============================================================
# CITY MAIN ADMIN MANAGEMENT (SUPER ADMIN ONLY)
# ============================================================

@router.post("/admin/city-admins", response_model=CityAdminOut)
def create_city_admin(
    payload: CityAdminCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can appoint City Admin")

    user = db.query(User).filter(
        User.email == payload.email.strip()
    ).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Is email ka user nahi mila. Pehle signup karwayein.",
        )

    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == payload.city_id
    ).first()
    if not city:
        raise HTTPException(status_code=404, detail="City nahi mila")

    existing = db.query(DeliveryCityAdmin).filter(
        DeliveryCityAdmin.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="User pehle se City Admin hai")

    if db.query(DeliveryStaff).filter(DeliveryStaff.user_id == user.id).first():
        raise HTTPException(status_code=409, detail="Ye user pehle se Delivery Staff hai")

    row = DeliveryCityAdmin(
        user_id=user.id,
        city_id=city.id,
        is_active=True,
    )
    db.add(row)
    _commit(db, row)

    return CityAdminOut(
        id=row.id,
        user_id=user.id,
        name=user.name,
        email=user.email,
        city_id=city.id,
        city_name=city.name,
        is_active=row.is_active,
    )


@router.get("/admin/city-admins", response_model=list[CityAdminOut])
def list_city_admins(
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only Super Admin can view City Admin list")

    rows = (
        db.query(DeliveryCityAdmin)
        .order_by(DeliveryCityAdmin.id.asc())
        .all()
    )
    result = []

    for row in rows:
        user = db.query(User).filter(User.id == row.user_id).first()
        city = db.query(DeliveryCity).filter(DeliveryCity.id == row.city_id).first()
        result.append(
            CityAdminOut(
                id=row.id,
                user_id=row.user_id,
                name=user.name if user else None,
                email=user.email if user else None,
                city_id=row.city_id,
                city_name=city.name if city else None,
                is_active=row.is_active,
            )
        )

    return result


# ============================================================
# AREA MANAGEMENT
# ============================================================

@router.post("/admin/areas", response_model=AreaOut)
def create_area(
    payload: AreaCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == payload.city_id,
        DeliveryCity.is_active.is_(True),
    ).first()
    if not city:
        raise HTTPException(status_code=404, detail="Active city nahi mila")

    if actor.role == "area_admin":
        raise HTTPException(status_code=403, detail="Area Admin naya Area create nahi kar sakta")

    if actor.role == "city_admin" and actor.city_id != city.id:
        raise HTTPException(status_code=403, detail="Aap sirf apne city mein Area bana sakte hain")

    name = payload.name.strip()
    existing = db.query(DeliveryArea).filter(
        DeliveryArea.city_id == city.id,
        DeliveryArea.name.ilike(name),
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Is city mein Area pehle se hai")

    area = DeliveryArea(city_id=city.id, name=name, is_active=True)
    db.add(area)
    _commit(db, area)

    return AreaOut(
        id=area.id,
        city_id=area.city_id,
        city_name=city.name,
        name=area.name,
        is_active=area.is_active,
    )


@router.get("/admin/areas", response_model=list[AreaOut])
def list_areas(
    city_id: int | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryArea)

    if actor.role == "city_admin":
        if city_id is not None and city_id != actor.city_id:
            raise HTTPException(status_code=403, detail="Dusre city ka access nahi hai")
        query = query.filter(DeliveryArea.city_id == actor.city_id)

    elif actor.role == "area_admin":
        query = query.filter(DeliveryArea.id.in_(actor.area_ids or [-1]))

    elif city_id is not None:
        query = query.filter(DeliveryArea.city_id == city_id)

    rows = query.order_by(DeliveryArea.name.asc()).all()
    result = []

    for area in rows:
        city = db.query(DeliveryCity).filter(
            DeliveryCity.id == area.city_id
        ).first()
        result.append(
            AreaOut(
                id=area.id,
                city_id=area.city_id,
                city_name=city.name if city else None,
                name=area.name,
                is_active=area.is_active,
            )
        )

    return result


# ============================================================
# PIN CODE MANAGEMENT
# ============================================================

@router.post("/admin/pincodes", response_model=PincodeOut)
def create_pincode(
    payload: PincodeCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    area = _get_area(db, payload.area_id)
    _check_area_scope(actor, area)

    existing = db.query(DeliveryPincode).filter(
        DeliveryPincode.pincode == payload.pincode
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="PIN Code pehle se registered hai")

    row = DeliveryPincode(
        pincode=payload.pincode,
        area_id=area.id,
        # Default schema value is inactive; only activate after coverage verification.
        is_active=payload.is_active,
    )
    db.add(row)
    _commit(db, row)

    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == area.city_id
    ).first()

    return PincodeOut(
        id=row.id,
        pincode=row.pincode,
        area_id=area.id,
        area_name=area.name,
        city_id=area.city_id,
        city_name=city.name if city else None,
        is_active=row.is_active,
    )


@router.get("/admin/pincodes", response_model=list[PincodeOut])
def list_pincodes(
    area_id: int | None = None,
    city_id: int | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryPincode)

    if actor.role == "area_admin":
        query = query.filter(
            DeliveryPincode.area_id.in_(actor.area_ids or [-1])
        )
    elif actor.role == "city_admin":
        city_area_ids = _area_ids_for_city(db, actor.city_id)
        query = query.filter(DeliveryPincode.area_id.in_(city_area_ids or [-1]))
    elif city_id is not None:
        city_area_ids = _area_ids_for_city(db, city_id)
        query = query.filter(DeliveryPincode.area_id.in_(city_area_ids or [-1]))

    if area_id is not None:
        area = _get_area(db, area_id)
        _check_area_scope(actor, area)
        query = query.filter(DeliveryPincode.area_id == area_id)

    rows = query.order_by(DeliveryPincode.pincode.asc()).all()
    result = []

    for row in rows:
        area = db.query(DeliveryArea).filter(
            DeliveryArea.id == row.area_id
        ).first()
        city = (
            db.query(DeliveryCity).filter(
                DeliveryCity.id == area.city_id
            ).first()
            if area else None
        )
        result.append(
            PincodeOut(
                id=row.id,
                pincode=row.pincode,
                area_id=row.area_id,
                area_name=area.name if area else None,
                city_id=area.city_id if area else None,
                city_name=city.name if city else None,
                is_active=row.is_active,
            )
        )

    return result


@router.patch("/admin/pincodes/{pincode_id}", response_model=PincodeOut)
def update_pincode(
    pincode_id: int,
    payload: PincodeUpdate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    row = db.query(DeliveryPincode).filter(
        DeliveryPincode.id == pincode_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="PIN Code nahi mila")

    old_area = _get_area(db, row.area_id)
    _check_area_scope(actor, old_area)

    if payload.area_id is not None:
        new_area = _get_area(db, payload.area_id)
        _check_area_scope(actor, new_area)
        row.area_id = new_area.id

    if payload.is_active is not None:
        row.is_active = payload.is_active

    _commit(db, row)

    area = _get_area(db, row.area_id)
    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == area.city_id
    ).first()

    return PincodeOut(
        id=row.id,
        pincode=row.pincode,
        area_id=area.id,
        area_name=area.name,
        city_id=area.city_id,
        city_name=city.name if city else None,
        is_active=row.is_active,
    )


@router.get("/pincode/{pincode}/check", response_model=PincodeCheckOut)
def check_pincode(
    pincode: str,
    db: Session = Depends(get_db),
):
    if len(pincode) != 6 or not pincode.isdigit():
        raise HTTPException(status_code=422, detail="Valid 6 digit PIN Code bhejein")

    row = (
        db.query(DeliveryPincode)
        .filter(
            DeliveryPincode.pincode == pincode,
            DeliveryPincode.is_active.is_(True),
        )
        .first()
    )

    if not row:
        return PincodeCheckOut(
            pincode=pincode,
            serviceable=False,
            area=None,
            city=None,
        )

    area = db.query(DeliveryArea).filter(
        DeliveryArea.id == row.area_id,
        DeliveryArea.is_active.is_(True),
    ).first()

    if not area:
        return PincodeCheckOut(
            pincode=pincode,
            serviceable=False,
            area=None,
            city=None,
        )

    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == area.city_id,
        DeliveryCity.is_active.is_(True),
    ).first()

    return PincodeCheckOut(
        pincode=pincode,
        serviceable=city is not None,
        area=area.name if city else None,
        city=city.name if city else None,
    )


# ============================================================
# CUSTOMER ORDERS
# ============================================================

@router.post("/orders", response_model=DeliveryOrderOut)
def create_delivery_order(
    payload: DeliveryOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Never trust client-supplied area. Resolve it from an active PIN Code.
    pin = (
        db.query(DeliveryPincode)
        .filter(
            DeliveryPincode.pincode == payload.pincode,
            DeliveryPincode.is_active.is_(True),
        )
        .first()
    )
    if not pin:
        raise HTTPException(
            status_code=400,
            detail="Is PIN Code par abhi delivery service available nahi hai",
        )

    area = db.query(DeliveryArea).filter(
        DeliveryArea.id == pin.area_id,
        DeliveryArea.is_active.is_(True),
    ).first()
    if not area:
        raise HTTPException(status_code=400, detail="Is PIN Code ka Area active nahi hai")

    city = db.query(DeliveryCity).filter(
        DeliveryCity.id == area.city_id,
        DeliveryCity.is_active.is_(True),
    ).first()
    if not city:
        raise HTTPException(status_code=400, detail="Is PIN Code ka City active nahi hai")

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
        pincode=pin.pincode,
        area_id=area.id,
        city_id=city.id,
        area=area.name,  # legacy column maintained
        items_description=payload.items_description,
        notes=payload.notes,
        order_amount=round(float(amount), 2),
        delivery_charge=charge,
        total_amount=round(float(amount) + charge, 2),
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

    city_admin = (
        db.query(DeliveryCityAdmin)
        .filter(
            DeliveryCityAdmin.user_id == user.id,
            DeliveryCityAdmin.is_active.is_(True),
        )
        .first()
    )
    if city_admin:
        return order.city_id == city_admin.city_id

    staff = _staff_of(db, user)
    if not staff:
        return False

    if staff.role in (DeliveryStaffRole.area_admin, DeliveryStaffRole.sub_admin):
        return _order_in_actor_scope(
            db,
            Actor(
                user=user,
                role="area_admin",
                area_ids=_staff_area_ids(db, staff),
                staff=staff,
            ),
            order,
        )

    if staff.role == DeliveryStaffRole.delivery_boy:
        return (
            order.assigned_to == staff.id
            and (
                order.area_id is None
                or order.area_id in _staff_area_ids(db, staff)
            )
        )

    return False


@router.get("/orders/{order_id}", response_model=DeliveryOrderOut)
def get_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.query(DeliveryOrder).filter(
        DeliveryOrder.id == order_id
    ).first()

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
    order = db.query(DeliveryOrder).filter(
        DeliveryOrder.id == order_id
    ).first()

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
    order = db.query(DeliveryOrder).filter(
        DeliveryOrder.id == order_id
    ).first()

    if not order:
        raise HTTPException(status_code=404, detail="Delivery order nahi mila")

    if order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Ye aapka order nahi hai")

    if order.status not in (S.pending, S.accepted):
        raise HTTPException(
            status_code=400,
            detail="Order ab cancel nahi ho sakta. Admin se sampark karein.",
        )

    reason = payload.reason if payload else None
    _change_status(
        db,
        order,
        S.cancelled,
        current_user.id,
        reason or "Customer cancelled",
    )
    order.cancel_reason = reason or "Customer cancelled"
    _commit(db, order)
    return order


# ============================================================
# ADMIN ORDERS
# ============================================================

@router.get("/admin/orders", response_model=list[DeliveryOrderOut])
def admin_list_orders(
    status: DeliveryOrderStatus | None = None,
    area_id: int | None = None,
    city_id: int | None = None,
    area: str | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryOrder)

    if actor.role == "city_admin":
        query = query.filter(DeliveryOrder.city_id == actor.city_id)
    elif actor.role == "area_admin":
        query = query.filter(
            DeliveryOrder.area_id.in_(actor.area_ids or [-1])
        )

    if city_id is not None:
        if actor.role == "city_admin" and city_id != actor.city_id:
            raise HTTPException(status_code=403, detail="Dusre city ka access nahi hai")
        if actor.role == "area_admin":
            allowed_city_ids = [
                a.city_id
                for a in db.query(DeliveryArea)
                .filter(DeliveryArea.id.in_(actor.area_ids or [-1]))
                .all()
            ]
            if city_id not in allowed_city_ids:
                raise HTTPException(status_code=403, detail="Dusre city ka access nahi hai")
        query = query.filter(DeliveryOrder.city_id == city_id)

    if area_id is not None:
        selected_area = _get_area(db, area_id)
        _check_area_scope(actor, selected_area)
        query = query.filter(DeliveryOrder.area_id == area_id)

    if area:
        matching = (
            db.query(DeliveryArea)
            .filter(DeliveryArea.name.ilike(_norm(area)))
            .all()
        )
        matching_ids = [a.id for a in matching]
        if actor.role == "area_admin":
            matching_ids = list(set(matching_ids) & set(actor.area_ids or []))
        if actor.role == "city_admin":
            matching_ids = [
                a.id for a in matching if a.city_id == actor.city_id
            ]
        query = query.filter(DeliveryOrder.area_id.in_(matching_ids or [-1]))

    if status is not None:
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
            DeliveryStaff.is_active.is_(True),
        )
        .first()
    )
    if not boy:
        raise HTTPException(status_code=404, detail="Active delivery boy nahi mila")

    boy_area_ids = _staff_area_ids(db, boy)

    if order.area_id is not None:
        if order.area_id not in boy_area_ids:
            raise HTTPException(
                status_code=400,
                detail="Delivery boy is order ke Area mein assigned nahi hai",
            )
    elif _norm(boy.area) != _norm(order.area):
        raise HTTPException(status_code=400, detail="Delivery boy dusre area ka hai")

    if order.status == S.accepted:
        _change_status(
            db,
            order,
            S.assigned,
            actor.user.id,
            f"Assigned to staff #{boy.id}",
        )
    elif order.status == S.assigned:
        _log(
            db,
            order,
            "reassigned",
            actor.user.id,
            f"Reassigned to staff #{boy.id}",
        )
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
            detail="Yahan sirf picked_up, out_for_delivery, delivered allowed hain",
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
    _change_status(
        db,
        order,
        S.cancelled,
        actor.user.id,
        reason or "Cancelled by admin",
    )
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
# STAFF MANAGEMENT
# ============================================================

@router.post("/admin/staff", response_model=StaffOut)
def admin_create_staff(
    payload: StaffCreate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(
        User.email == payload.email.strip()
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="Is email ka user nahi mila. Pehle app mein signup karwayein.",
        )

    if db.query(DeliveryStaff).filter(
        DeliveryStaff.user_id == user.id
    ).first():
        raise HTTPException(status_code=409, detail="Ye user pehle se staff mein hai")

    if db.query(DeliveryCityAdmin).filter(
        DeliveryCityAdmin.user_id == user.id
    ).first():
        raise HTTPException(status_code=409, detail="Ye user City Admin hai")

    if actor.role == "super_admin":
        pass
    elif actor.role == "city_admin":
        if payload.role != "area_admin":
            raise HTTPException(
                status_code=403,
                detail="City Main Admin sirf Area Admin appoint kar sakta hai",
            )
    elif actor.role == "area_admin":
        if payload.role != "delivery_boy":
            raise HTTPException(
                status_code=403,
                detail="Area Admin sirf Delivery Boy bana sakta hai",
            )
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    area_ids = list(dict.fromkeys(payload.area_ids))
    if not area_ids:
        raise HTTPException(status_code=400, detail="Kam se kam ek Area select karein")

    areas = (
        db.query(DeliveryArea)
        .filter(
            DeliveryArea.id.in_(area_ids),
            DeliveryArea.is_active.is_(True),
        )
        .all()
    )
    if len(areas) != len(area_ids):
        raise HTTPException(status_code=400, detail="Ek ya adhik Area invalid/inactive hain")

    for area in areas:
        _check_area_scope(actor, area)

    if actor.role == "area_admin":
        if any(area.id not in (actor.area_ids or []) for area in areas):
            raise HTTPException(
                status_code=403,
                detail="Aap sirf apne assigned Areas mein Delivery Boy bana sakte hain",
            )

    # Super Admin may appoint staff across cities.
    # City Admin and Area Admin are restricted by _check_area_scope.
    staff = DeliveryStaff(
        user_id=user.id,
        role=DeliveryStaffRole(payload.role),
        area=areas[0].name,  # legacy column
        is_active=True,
        created_by=actor.user.id,
    )
    db.add(staff)
    db.flush()

    for area in areas:
        db.add(DeliveryStaffArea(staff_id=staff.id, area_id=area.id))

    _commit(db, staff)
    return _staff_out(db, staff)


@router.get("/admin/staff", response_model=list[StaffOut])
def admin_list_staff(
    role: DeliveryStaffRole | None = None,
    area_id: int | None = None,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    query = db.query(DeliveryStaff)

    if actor.role == "area_admin":
        query = query.filter(
            DeliveryStaff.role == DeliveryStaffRole.delivery_boy
        )
    elif role is not None:
        query = query.filter(DeliveryStaff.role == role)

    rows = query.order_by(DeliveryStaff.id.asc()).all()
    result = []

    for staff in rows:
        staff_area_ids = _staff_area_ids(db, staff)

        if actor.role == "city_admin":
            allowed = set(actor.area_ids or [])
            if not set(staff_area_ids).intersection(allowed):
                continue
        elif actor.role == "area_admin":
            allowed = set(actor.area_ids or [])
            if not set(staff_area_ids).intersection(allowed):
                continue

        if area_id is not None:
            selected = _get_area(db, area_id)
            _check_area_scope(actor, selected)
            if area_id not in staff_area_ids:
                continue

        result.append(_staff_out(db, staff))

    return result


@router.patch("/admin/staff/{staff_id}/areas", response_model=StaffOut)
def admin_update_staff_areas(
    staff_id: int,
    payload: StaffAreasUpdate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    staff = db.query(DeliveryStaff).filter(
        DeliveryStaff.id == staff_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff nahi mila")

    if actor.role == "area_admin" and staff.role != DeliveryStaffRole.delivery_boy:
        raise HTTPException(status_code=403, detail="Aap sirf Delivery Boy ke Areas badal sakte hain")

    new_ids = list(dict.fromkeys(payload.area_ids))
    areas = (
        db.query(DeliveryArea)
        .filter(
            DeliveryArea.id.in_(new_ids),
            DeliveryArea.is_active.is_(True),
        )
        .all()
    )
    if len(areas) != len(new_ids):
        raise HTTPException(status_code=400, detail="Ek ya adhik Area invalid/inactive hain")

    for area in areas:
        _check_area_scope(actor, area)

    if actor.role == "area_admin":
        if any(a.id not in (actor.area_ids or []) for a in areas):
            raise HTTPException(status_code=403, detail="Aapke assigned Areas ke bahar access nahi hai")

    db.query(DeliveryStaffArea).filter(
        DeliveryStaffArea.staff_id == staff.id
    ).delete(synchronize_session=False)

    for area in areas:
        db.add(DeliveryStaffArea(staff_id=staff.id, area_id=area.id))

    staff.area = areas[0].name
    _commit(db, staff)
    return _staff_out(db, staff)


@router.patch("/admin/staff/{staff_id}/active", response_model=StaffOut)
def admin_set_staff_active(
    staff_id: int,
    payload: StaffActiveUpdate,
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    staff = db.query(DeliveryStaff).filter(
        DeliveryStaff.id == staff_id
    ).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff nahi mila")

    if actor.role == "area_admin" and staff.role != DeliveryStaffRole.delivery_boy:
        raise HTTPException(status_code=403, detail="Aap sirf Delivery Boy ko manage kar sakte hain")

    staff_area_ids = set(_staff_area_ids(db, staff))
    allowed_ids = set(actor.area_ids or [])

    if actor.role in ("city_admin", "area_admin"):
        if not staff_area_ids.intersection(allowed_ids):
            raise HTTPException(status_code=403, detail="Is staff par aapka adhikar nahi hai")

    staff.is_active = payload.is_active
    _commit(db, staff)
    return _staff_out(db, staff)


# ============================================================
# REPORTS / ACTIVITY
# ============================================================

@router.get("/admin/reports/daily")
def admin_daily_report(
    day: date_type | None = Query(None, description="YYYY-MM-DD (IST). Default aaj"),
    area_id: int | None = None,
    city_id: int | None = None,
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

    if actor.role == "city_admin":
        query = query.filter(DeliveryOrder.city_id == actor.city_id)
    elif actor.role == "area_admin":
        query = query.filter(
            DeliveryOrder.area_id.in_(actor.area_ids or [-1])
        )

    if city_id is not None:
        if actor.role == "city_admin" and city_id != actor.city_id:
            raise HTTPException(status_code=403, detail="Dusre city ka access nahi hai")
        if actor.role == "area_admin":
            allowed_city_ids = {
                a.city_id
                for a in db.query(DeliveryArea)
                .filter(DeliveryArea.id.in_(actor.area_ids or [-1]))
                .all()
            }
            if city_id not in allowed_city_ids:
                raise HTTPException(status_code=403, detail="Dusre city ka access nahi hai")
        query = query.filter(DeliveryOrder.city_id == city_id)

    if area_id is not None:
        selected = _get_area(db, area_id)
        _check_area_scope(actor, selected)
        query = query.filter(DeliveryOrder.area_id == area_id)

    if area:
        matching = db.query(DeliveryArea).filter(
            DeliveryArea.name.ilike(_norm(area))
        ).all()
        matching_ids = [a.id for a in matching]
        if actor.role == "area_admin":
            matching_ids = list(set(matching_ids) & set(actor.area_ids or []))
        if actor.role == "city_admin":
            matching_ids = [a.id for a in matching if a.city_id == actor.city_id]
        query = query.filter(DeliveryOrder.area_id.in_(matching_ids or [-1]))

    rows = query.all()
    by_status = {s.value: 0 for s in DeliveryOrderStatus}

    for row in rows:
        by_status[row.status.value] += 1

    delivered = [row for row in rows if row.status == S.delivered]

    cod_query = db.query(DeliveryOrder).filter(
        DeliveryOrder.cod_collected.is_(True),
        DeliveryOrder.cod_collected_at >= start,
        DeliveryOrder.cod_collected_at < end,
    )

    if actor.role == "city_admin":
        cod_query = cod_query.filter(DeliveryOrder.city_id == actor.city_id)
    elif actor.role == "area_admin":
        cod_query = cod_query.filter(
            DeliveryOrder.area_id.in_(actor.area_ids or [-1])
        )

    if area_id is not None:
        cod_query = cod_query.filter(DeliveryOrder.area_id == area_id)
    if city_id is not None:
        cod_query = cod_query.filter(DeliveryOrder.city_id == city_id)

    cod_total = sum(float(row.total_amount) for row in cod_query.all())

    return {
        "date": day.isoformat(),
        "role": actor.role,
        "city_id": actor.city_id,
        "area_ids": actor.area_ids or [],
        "total_orders": len(rows),
        "by_status": by_status,
        "delivered_orders": len(delivered),
        "cancelled_orders": by_status[S.cancelled.value] + by_status[S.rejected.value],
        "delivery_charges_earned": round(
            sum(float(row.delivery_charge) for row in delivered), 2
        ),
        "delivered_value": round(
            sum(float(row.total_amount) for row in delivered), 2
        ),
        "cod_collected_inr": round(cod_total, 2),
        "currency": "INR",
    }


@router.get("/admin/activity", response_model=list[StatusLogOut])
def admin_activity(
    limit: int = Query(50, ge=1, le=200),
    actor: Actor = Depends(require_delivery_admin),
    db: Session = Depends(get_db),
):
    if actor.role != "super_admin":
        raise HTTPException(status_code=403, detail="Sirf Super Admin activity dekh sakta hai")

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
    area_ids = _staff_area_ids(db, staff)
    query = db.query(DeliveryOrder).filter(
        DeliveryOrder.assigned_to == staff.id
    )

    if area_ids:
        query = query.filter(
            (DeliveryOrder.area_id.in_(area_ids))
            | (DeliveryOrder.area_id.is_(None))
        )

    if active_only:
        query = query.filter(
            DeliveryOrder.status.in_([
                S.assigned,
                S.picked_up,
                S.out_for_delivery,
            ])
        )

    return query.order_by(DeliveryOrder.created_at.desc()).all()


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
    _collect_cod(
        db,
        order,
        staff.user_id,
        payload.notes if payload else None,
    )
    _commit(db, order)
    return order
