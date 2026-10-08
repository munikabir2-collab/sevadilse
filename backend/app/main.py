from dotenv import load_dotenv

# ============================================================
# LOAD ENVIRONMENT VARIABLES FIRST
# ============================================================

# .env ko application ke baaki modules import hone se
# pehle load karna important hai.
load_dotenv()


# ============================================================
# FASTAPI
# ============================================================

from fastapi import FastAPI


# ============================================================
# DATABASE
# ============================================================

from app.core.database import Base, engine


# ============================================================
# API ROUTERS
# ============================================================

from app.api import (
    auth,
    providers,
    bookings,
    reviews,
    restaurant_tables,
    menu,
    orders,
    bills,
    hotels,
    doctors,
    payments,
    provider_payouts,
)


# ============================================================
# MODELS
# ============================================================

from app.models import (
    user_model,
    provider_model,
    service_model,
    booking_model,
    review_model,
    restaurant_table_model,
    menu_item_model,
    order_model,
    bill_model,
    doctor_slot_model,
    payment_model,
    provider_payout_model,
    provider_earning_model,
)


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="ServiceHub Backend",
    description=(
        "Hotel, restaurant aur doctor bookings "
        "ke liye ek unified backend"
    ),
    version="0.5.0",
)


# ============================================================
# AUTH
# ============================================================

app.include_router(auth.router)


# ============================================================
# PROVIDERS
# ============================================================

app.include_router(providers.router)


# ============================================================
# BOOKINGS
# ============================================================

app.include_router(bookings.router)


# ============================================================
# REVIEWS
# ============================================================

app.include_router(reviews.router)


# ============================================================
# RESTAURANT
# ============================================================

app.include_router(restaurant_tables.router)
app.include_router(menu.router)
app.include_router(orders.router)
app.include_router(bills.router)


# ============================================================
# PROVIDER PAYOUTS / RAZORPAY ROUTE
# ============================================================

app.include_router(provider_payouts.router)


# ============================================================
# HOTEL
# ============================================================

app.include_router(hotels.router)
app.include_router(hotels.hotel_booking_router)


# ============================================================
# DOCTOR
# ============================================================

app.include_router(doctors.doctor_router)
app.include_router(doctors.appointment_router)


# ============================================================
# PAYMENTS
# ============================================================

app.include_router(payments.router)


# ============================================================
# DATABASE TABLE CREATION
# ============================================================

@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "ServiceHub backend chal raha hai 🚀"
    }