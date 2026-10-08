from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.booking_model import Booking, BookingStatus
from app.models.review_model import Review
from app.models.provider_model import Provider
from app.schemas.review_schema import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewOut)
def create_review(review: ReviewCreate, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == review.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking nahi mili")
    if booking.user_id != review.user_id:
        raise HTTPException(status_code=403, detail="Ye booking tumhari nahi hai")
    if booking.status != BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="Sirf completed booking par hi review de sakte ho (fake review rokne ke liye)",
        )

    existing = db.query(Review).filter(Review.booking_id == review.booking_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Is booking par pehle se review hai")

    db_review = Review(
        user_id=review.user_id,
        provider_id=booking.provider_id,
        booking_id=review.booking_id,
        rating=review.rating,
        comment=review.comment,
    )
    db.add(db_review)

    # Provider ka average rating update karo
    provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()
    provider.total_reviews += 1
    provider.avg_rating = (
        (provider.avg_rating * (provider.total_reviews - 1)) + review.rating
    ) / provider.total_reviews

    db.commit()
    db.refresh(db_review)
    return db_review


@router.get("/provider/{provider_id}", response_model=list[ReviewOut])
def list_provider_reviews(provider_id: int, db: Session = Depends(get_db)):
    return (
        db.query(Review)
        .filter(Review.provider_id == provider_id)
        .order_by(Review.created_at.desc())
        .all()
    )
