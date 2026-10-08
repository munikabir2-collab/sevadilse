from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.provider_model import Provider, ProviderCategory
from app.models.service_model import Service
from app.models.booking_model import Booking, BookingStatus
from app.schemas.hotel_schema import (
    HotelRoomCreate,
    HotelRoomUpdate,
    HotelRoomOut,
    HotelBookingCreate,
    HotelBookingOut,
)


router = APIRouter(
    prefix="/hotels",
    tags=["Hotel Rooms"],
)


def get_hotel(provider_id: int, db: Session):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id)
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Hotel provider nahi mila",
        )

    if provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=400,
            detail="Ye provider hotel nahi hai",
        )

    return provider


# =========================================================
# CREATE HOTEL ROOM
# =========================================================

@router.post(
    "/{provider_id}/rooms",
    response_model=HotelRoomOut,
)
def create_hotel_room(
    provider_id: int,
    room: HotelRoomCreate,
    db: Session = Depends(get_db),
):
    get_hotel(provider_id, db)

    new_room = Service(
        provider_id=provider_id,
        name=room.name,
        price=room.price,
        capacity=room.capacity,
        duration_minutes=None,
        total_units=room.total_units,
    )

    db.add(new_room)
    db.commit()
    db.refresh(new_room)

    return new_room


# =========================================================
# LIST HOTEL ROOMS
# =========================================================

@router.get(
    "/{provider_id}/rooms",
    response_model=list[HotelRoomOut],
)
def list_hotel_rooms(
    provider_id: int,
    db: Session = Depends(get_db),
):
    get_hotel(provider_id, db)

    rooms = (
        db.query(Service)
        .filter(Service.provider_id == provider_id)
        .all()
    )

    return rooms


# =========================================================
# GET SINGLE HOTEL ROOM
# =========================================================

@router.get(
    "/rooms/{room_id}",
    response_model=HotelRoomOut,
)
def get_hotel_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    room = (
        db.query(Service)
        .filter(Service.id == room_id)
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Hotel room nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == room.provider_id)
        .first()
    )

    if not provider or provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=400,
            detail="Ye service hotel room nahi hai",
        )

    return room


# =========================================================
# UPDATE HOTEL ROOM
# =========================================================

@router.patch(
    "/rooms/{room_id}",
    response_model=HotelRoomOut,
)
def update_hotel_room(
    room_id: int,
    room_data: HotelRoomUpdate,
    db: Session = Depends(get_db),
):
    room = (
        db.query(Service)
        .filter(Service.id == room_id)
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Hotel room nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == room.provider_id)
        .first()
    )

    if not provider or provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=400,
            detail="Ye service hotel room nahi hai",
        )

    if room_data.name is not None:
        room.name = room_data.name

    if room_data.price is not None:
        room.price = room_data.price

    if room_data.capacity is not None:
        room.capacity = room_data.capacity

    if room_data.total_units is not None:
        room.total_units = room_data.total_units

    db.commit()
    db.refresh(room)

    return room


# =========================================================
# DELETE HOTEL ROOM
# =========================================================

@router.delete("/rooms/{room_id}")
def delete_hotel_room(
    room_id: int,
    db: Session = Depends(get_db),
):
    room = (
        db.query(Service)
        .filter(Service.id == room_id)
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Hotel room nahi mila",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == room.provider_id)
        .first()
    )

    if not provider or provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=400,
            detail="Ye service hotel room nahi hai",
        )

    existing_booking = (
        db.query(Booking)
        .filter(
            Booking.service_id == room_id,
            Booking.status.in_(
                [
                    BookingStatus.pending,
                    BookingStatus.confirmed,
                ]
            ),
        )
        .first()
    )

    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail="Is room ke active bookings hain, room delete nahi kiya ja sakta",
        )

    db.delete(room)
    db.commit()

    return {
        "message": "Hotel room delete ho gaya",
        "room_id": room_id,
    }


# =========================================================
# HOTEL BOOKING
# =========================================================

hotel_booking_router = APIRouter(
    prefix="/hotel-bookings",
    tags=["Hotel Bookings"],
)


@hotel_booking_router.post(
    "/",
    response_model=HotelBookingOut,
)
def create_hotel_booking(
    booking_data: HotelBookingCreate,
    db: Session = Depends(get_db),
):
    if booking_data.check_out <= booking_data.check_in:
        raise HTTPException(
            status_code=400,
            detail="Check-out, check-in ke baad hona chahiye",
        )

    provider = (
        db.query(Provider)
        .filter(
            Provider.id == booking_data.provider_id,
            Provider.category == ProviderCategory.hotel,
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=404,
            detail="Hotel nahi mila",
        )

    room = (
        db.query(Service)
        .filter(
            Service.id == booking_data.service_id,
            Service.provider_id == booking_data.provider_id,
        )
        .first()
    )

    if not room:
        raise HTTPException(
            status_code=404,
            detail="Hotel room nahi mila",
        )

    if booking_data.guests > room.capacity:
        raise HTTPException(
            status_code=400,
            detail=f"Is room ki maximum capacity {room.capacity} guests hai",
        )

    # Overlapping active bookings
    overlapping = (
        db.query(Booking)
        .filter(
            Booking.service_id == room.id,
            Booking.status.in_(
                [
                    BookingStatus.pending,
                    BookingStatus.confirmed,
                ]
            ),
            Booking.start_time < booking_data.check_out,
            Booking.end_time > booking_data.check_in,
        )
        .count()
    )

    if overlapping >= room.total_units:
        raise HTTPException(
            status_code=409,
            detail="Selected dates par room available nahi hai",
        )

    # Number of nights
    nights = (
        booking_data.check_out.date()
        - booking_data.check_in.date()
    ).days

    if nights <= 0:
        raise HTTPException(
            status_code=400,
            detail="Minimum 1 night booking required hai",
        )

    total_price = room.price * nights

    new_booking = Booking(
        user_id=booking_data.user_id,
        provider_id=booking_data.provider_id,
        service_id=booking_data.service_id,
        start_time=booking_data.check_in,
        end_time=booking_data.check_out,
        guests=booking_data.guests,
        total_price=total_price,
        status=BookingStatus.pending,
    )

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


# =========================================================
# LIST USER HOTEL BOOKINGS
# =========================================================

@hotel_booking_router.get(
    "/user/{user_id}",
    response_model=list[HotelBookingOut],
)
def list_user_hotel_bookings(
    user_id: int,
    db: Session = Depends(get_db),
):
    bookings = (
        db.query(Booking)
        .join(Service, Booking.service_id == Service.id)
        .filter(
            Booking.user_id == user_id,
            Service.provider_id == Booking.provider_id,
        )
        .join(
            Provider,
            Provider.id == Booking.provider_id,
        )
        .filter(
            Provider.category == ProviderCategory.hotel
        )
        .order_by(Booking.start_time.desc())
        .all()
    )

    return bookings


# =========================================================
# GET HOTEL BOOKING
# =========================================================

@hotel_booking_router.get(
    "/{booking_id}",
    response_model=HotelBookingOut,
)
def get_hotel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Hotel booking nahi mili",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == booking.provider_id)
        .first()
    )

    if not provider or provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel booking nahi mili",
        )

    return booking


# =========================================================
# CANCEL HOTEL BOOKING
# =========================================================

@hotel_booking_router.patch(
    "/{booking_id}/cancel",
    response_model=HotelBookingOut,
)
def cancel_hotel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Hotel booking nahi mili",
        )

    provider = (
        db.query(Provider)
        .filter(Provider.id == booking.provider_id)
        .first()
    )

    if not provider or provider.category != ProviderCategory.hotel:
        raise HTTPException(
            status_code=404,
            detail="Hotel booking nahi mili",
        )

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Booking already cancelled hai",
        )

    if booking.status == BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Completed booking cancel nahi ho sakti",
        )

    booking.status = BookingStatus.cancelled

    db.commit()
    db.refresh(booking)

    return booking