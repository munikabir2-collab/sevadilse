from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.models.provider_model import (
    Provider,
    ProviderCategory,
)

from app.models.service_model import Service

from app.models.doctor_slot_model import DoctorSlot

from app.models.booking_model import (
    Booking,
    BookingStatus,
)

from app.schemas.doctor_schema import (
    DoctorProfileUpdate,
    DoctorOut,
    DoctorSlotCreate,
    DoctorSlotUpdate,
    DoctorSlotOut,
    AppointmentCreate,
    AppointmentOut,
)


doctor_router = APIRouter(
    prefix="/doctors",
    tags=["Doctors"],
)

appointment_router = APIRouter(
    prefix="/appointments",
    tags=["Appointments"],
)


# =========================================================
# HELPER
# =========================================================

def get_doctor(
    provider_id: int,
    db: Session,
):
    doctor = (
        db.query(Provider)
        .filter(
            Provider.id == provider_id,
            Provider.category == ProviderCategory.doctor,
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor nahi mila",
        )

    return doctor


# =========================================================
# DOCTOR PROFILE
# =========================================================

@doctor_router.post(
    "/{provider_id}/profile",
    response_model=DoctorOut,
)
def update_doctor_profile(
    provider_id: int,
    profile: DoctorProfileUpdate,
    db: Session = Depends(get_db),
):
    doctor = get_doctor(provider_id, db)

    if profile.name is not None:
        doctor.name = profile.name

    if profile.specialization is not None:
        doctor.specialization = profile.specialization

    if profile.description is not None:
        doctor.description = profile.description

    if profile.city is not None:
        doctor.city = profile.city

    if profile.address is not None:
        doctor.address = profile.address

    if profile.latitude is not None:
        doctor.latitude = profile.latitude

    if profile.longitude is not None:
        doctor.longitude = profile.longitude

    db.commit()
    db.refresh(doctor)

    return doctor


@doctor_router.get(
    "/",
    response_model=list[DoctorOut],
)
def list_doctors(
    city: str | None = None,
    specialization: str | None = None,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Provider)
        .filter(
            Provider.category == ProviderCategory.doctor
        )
    )

    if city:
        query = query.filter(
            Provider.city.ilike(f"%{city}%")
        )

    if specialization:
        query = query.filter(
            Provider.specialization.ilike(
                f"%{specialization}%"
            )
        )

    return query.order_by(
        Provider.avg_rating.desc()
    ).all()


@doctor_router.get(
    "/{provider_id}",
    response_model=DoctorOut,
)
def get_doctor_profile(
    provider_id: int,
    db: Session = Depends(get_db),
):
    return get_doctor(provider_id, db)


# =========================================================
# DOCTOR SLOTS
# =========================================================

@doctor_router.post(
    "/{provider_id}/slots",
    response_model=DoctorSlotOut,
)
def create_doctor_slot(
    provider_id: int,
    slot_data: DoctorSlotCreate,
    db: Session = Depends(get_db),
):
    doctor = get_doctor(provider_id, db)

    if slot_data.end_time <= slot_data.start_time:
        raise HTTPException(
            status_code=400,
            detail="Slot ka end time start time ke baad hona chahiye",
        )

    service = (
        db.query(Service)
        .filter(
            Service.id == slot_data.service_id,
            Service.provider_id == doctor.id,
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Doctor service nahi mili",
        )

    # Duration validation
    if service.duration_minutes:
        actual_minutes = int(
            (
                slot_data.end_time
                - slot_data.start_time
            ).total_seconds() / 60
        )

        if actual_minutes != service.duration_minutes:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Slot duration {service.duration_minutes} "
                    f"minutes honi chahiye"
                ),
            )

    # Existing overlapping slot
    overlapping_slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.provider_id == doctor.id,
            DoctorSlot.start_time < slot_data.end_time,
            DoctorSlot.end_time > slot_data.start_time,
        )
        .first()
    )

    if overlapping_slot:
        raise HTTPException(
            status_code=409,
            detail="Doctor ke liye is time par slot already maujood hai",
        )

    new_slot = DoctorSlot(
        provider_id=doctor.id,
        service_id=service.id,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time,
        is_available=True,
    )

    db.add(new_slot)
    db.commit()
    db.refresh(new_slot)

    return new_slot


@doctor_router.get(
    "/{provider_id}/slots",
    response_model=list[DoctorSlotOut],
)
def list_doctor_slots(
    provider_id: int,
    available_only: bool = True,
    db: Session = Depends(get_db),
):
    get_doctor(provider_id, db)

    query = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.provider_id == provider_id
        )
    )

    if available_only:
        query = query.filter(
            DoctorSlot.is_available.is_(True)
        )

    return query.order_by(
        DoctorSlot.start_time
    ).all()


# =========================================================
# APPOINTMENTS
# =========================================================

@appointment_router.post(
    "/",
    response_model=AppointmentOut,
)
def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
):
    doctor = get_doctor(
        appointment_data.provider_id,
        db,
    )

    slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.id == appointment_data.slot_id,
            DoctorSlot.provider_id == doctor.id,
        )
        .first()
    )

    if not slot:
        raise HTTPException(
            status_code=404,
            detail="Doctor slot nahi mila",
        )

    if not slot.is_available:
        raise HTTPException(
            status_code=409,
            detail="Ye doctor slot already booked hai",
        )

    if slot.service_id != appointment_data.service_id:
        raise HTTPException(
            status_code=400,
            detail="Slot aur service match nahi karte",
        )

    service = (
        db.query(Service)
        .filter(
            Service.id == appointment_data.service_id,
            Service.provider_id == doctor.id,
        )
        .first()
    )

    if not service:
        raise HTTPException(
            status_code=404,
            detail="Doctor service nahi mili",
        )

    # User ke same slot par duplicate booking check
    existing_booking = (
        db.query(Booking)
        .filter(
            Booking.service_id == service.id,
            Booking.start_time == slot.start_time,
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
        slot.is_available = False

        db.commit()

        raise HTTPException(
            status_code=409,
            detail="Ye doctor slot already booked hai",
        )

    new_booking = Booking(
        user_id=appointment_data.user_id,
        provider_id=doctor.id,
        service_id=service.id,
        start_time=slot.start_time,
        end_time=slot.end_time,
        guests=1,
        total_price=service.price,
        status=BookingStatus.pending,
    )

    slot.is_available = False

    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return new_booking


@appointment_router.get(
    "/user/{user_id}",
    response_model=list[AppointmentOut],
)
def list_user_appointments(
    user_id: int,
    db: Session = Depends(get_db),
):
    appointments = (
        db.query(Booking)
        .join(
            Provider,
            Provider.id == Booking.provider_id,
        )
        .filter(
            Booking.user_id == user_id,
            Provider.category == ProviderCategory.doctor,
        )
        .order_by(
            Booking.start_time.desc()
        )
        .all()
    )

    return appointments


@appointment_router.get(
    "/{appointment_id}",
    response_model=AppointmentOut,
)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
):
    appointment = (
        db.query(Booking)
        .filter(
            Booking.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment nahi mili",
        )

    doctor = (
        db.query(Provider)
        .filter(
            Provider.id == appointment.provider_id,
            Provider.category == ProviderCategory.doctor,
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor appointment nahi mili",
        )

    return appointment


@appointment_router.patch(
    "/{appointment_id}/cancel",
    response_model=AppointmentOut,
)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
):
    appointment = (
        db.query(Booking)
        .filter(
            Booking.id == appointment_id
        )
        .first()
    )

    if not appointment:
        raise HTTPException(
            status_code=404,
            detail="Appointment nahi mili",
        )

    doctor = (
        db.query(Provider)
        .filter(
            Provider.id == appointment.provider_id,
            Provider.category == ProviderCategory.doctor,
        )
        .first()
    )

    if not doctor:
        raise HTTPException(
            status_code=404,
            detail="Doctor appointment nahi mili",
        )

    if appointment.status == BookingStatus.cancelled:
        raise HTTPException(
            status_code=400,
            detail="Appointment already cancelled hai",
        )

    if appointment.status == BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Completed appointment cancel nahi ho sakti",
        )

    appointment.status = BookingStatus.cancelled

    # Corresponding slot ko dobara available karein
    slot = (
        db.query(DoctorSlot)
        .filter(
            DoctorSlot.provider_id == appointment.provider_id,
            DoctorSlot.service_id == appointment.service_id,
            DoctorSlot.start_time == appointment.start_time,
            DoctorSlot.end_time == appointment.end_time,
        )
        .first()
    )

    if slot:
        slot.is_available = True

    db.commit()
    db.refresh(appointment)

    return appointment