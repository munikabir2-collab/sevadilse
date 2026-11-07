from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user_model import User
from app.models.provider_model import Provider
from app.models.booking_model import Booking, BookingStatus
from app.models.service_model import Service
from app.schemas.booking_schema import (
    BookingCreate,
    BookingOut,
    BookingStatusUpdate,
)
from app.services.availability_service import is_available


router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ============================================================
# CUSTOMER: CREATE BOOKING
# ============================================================

@router.post("/", response_model=BookingOut)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = (
        db.query(Service)
        .filter(Service.id == booking.service_id)
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Service nahi mili",
        )

    if booking.end_time <= booking.start_time:
        raise HTTPException(
            status_code=400,
            detail="End time, start time ke baad honi chahiye",
        )

    if booking.guests < 1:
        raise HTTPException(
            status_code=400,
            detail="Guests kam se kam 1 hone chahiye",
        )

    if not is_available(
        db,
        booking.service_id,
        booking.start_time,
        booking.end_time,
    ):
        raise HTTPException(
            status_code=409,
            detail="Is time slot ke liye availability nahi hai",
        )

    db_booking = Booking(
        # User ID JWT se li ja rahi hai.
        # Request body ka user_id ignore kiya ja raha hai.
        user_id=current_user.id,
        provider_id=service.provider_id,
        service_id=service.id,
        start_time=booking.start_time,
        end_time=booking.end_time,
        guests=booking.guests,
        total_price=service.price,
        status=BookingStatus.pending,
    )

    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)

    return db_booking


# ============================================================
# CUSTOMER: LIST OWN BOOKINGS
# ============================================================

@router.get("/user/{user_id}", response_model=list[BookingOut])
def list_user_bookings(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Aap dusre user ki bookings nahi dekh sakte",
        )

    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.start_time.desc())
        .all()
    )


# ============================================================
# CUSTOMER: CANCEL OWN BOOKING
# ============================================================

@router.patch("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.user_id == current_user.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking nahi mili",
        )

    if booking.status not in {
        BookingStatus.pending,
        BookingStatus.confirmed,
    }:
        raise HTTPException(
            status_code=400,
            detail="Is booking ko ab cancel nahi kiya ja sakta",
        )

    booking.status = BookingStatus.cancelled

    db.commit()
    db.refresh(booking)

    return booking


# ============================================================
# PROVIDER: GET OWN BOOKINGS
# ============================================================

@router.get("/provider/me", response_model=list[BookingOut])
def list_provider_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_provider:
        raise HTTPException(
            status_code=403,
            detail="Provider access required",
        )

    # Ek owner ke multiple provider profiles ho sakte hain.
    providers = (
        db.query(Provider)
        .filter(Provider.owner_id == current_user.id)
        .all()
    )

    provider_ids = [provider.id for provider in providers]

    if not provider_ids:
        raise HTTPException(
            status_code=404,
            detail="Provider profile nahi mila",
        )

    return (
        db.query(Booking)
        .filter(Booking.provider_id.in_(provider_ids))
        .order_by(Booking.start_time.desc())
        .all()
    )


# ============================================================
# PROVIDER: UPDATE BOOKING STATUS
# ============================================================

@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_provider_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user.is_provider:
        raise HTTPException(
            status_code=403,
            detail="Provider access required",
        )

    providers = (
        db.query(Provider)
        .filter(Provider.owner_id == current_user.id)
        .all()
    )

    provider_ids = [provider.id for provider in providers]

    if not provider_ids:
        raise HTTPException(
            status_code=404,
            detail="Provider profile nahi mila",
        )

    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.provider_id.in_(provider_ids),
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking nahi mili",
        )

    # Valid status transitions:
    # pending -> confirmed / cancelled
    # confirmed -> completed / cancelled

    allowed_transitions = {
        BookingStatus.pending: {
            BookingStatus.confirmed,
            BookingStatus.cancelled,
        },
        BookingStatus.confirmed: {
            BookingStatus.completed,
            BookingStatus.cancelled,
        },
    }

    allowed = allowed_transitions.get(booking.status, set())

    if payload.status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid booking status transition: "
                f"{booking.status.value} -> {payload.status.value}"
            ),
        )

    booking.status = payload.status

    db.commit()
    db.refresh(booking)

    return booking
