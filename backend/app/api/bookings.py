from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.booking_model import Booking, BookingStatus
from app.models.service_model import Service
from app.schemas.booking_schema import BookingCreate, BookingOut
from app.services.availability_service import is_available

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingOut)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == booking.service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service nahi mila")

    if booking.end_time <= booking.start_time:
        raise HTTPException(status_code=400, detail="end_time, start_time ke baad honi chahiye")

    if not is_available(db, booking.service_id, booking.start_time, booking.end_time):
        raise HTTPException(
            status_code=409,
            detail="Is time slot ke liye availability nahi hai",
        )

    # Simple pricing: hotel jaise duration-based ho to price * nights/hours nikaal sakte ho,
    # abhi ke liye flat service price use kar rahe hain
    db_booking = Booking(
        user_id=booking.user_id,
        provider_id=service.provider_id,
        service_id=booking.service_id,
        start_time=booking.start_time,
        end_time=booking.end_time,
        guests=booking.guests,
        total_price=service.price,
        status=BookingStatus.confirmed,
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@router.get("/user/{user_id}", response_model=list[BookingOut])
def list_user_bookings(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.start_time.desc())
        .all()
    )


@router.patch("/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nahi mili")

    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)
    return booking
