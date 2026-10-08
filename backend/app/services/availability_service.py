from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.booking_model import Booking, BookingStatus
from app.models.service_model import Service


def is_available(
    db: Session, service_id: int, start_time: datetime, end_time: datetime
) -> bool:
    """
    Check karta hai ki is service (room/table/doctor-slot) ke paas is time range
    me enough free units hain ya nahi. Overlapping bookings count karke
    total_units se compare karta hai.
    """
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        return False

    # Is time range se overlap karne wali saari active bookings nikaalo
    overlapping = (
        db.query(Booking)
        .filter(
            Booking.service_id == service_id,
            Booking.status.in_([BookingStatus.pending, BookingStatus.confirmed]),
            and_(Booking.start_time < end_time, Booking.end_time > start_time),
        )
        .count()
    )

    return overlapping < service.total_units
