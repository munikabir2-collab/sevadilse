# ServiceHub Backend

Ek unified FastAPI backend jo **Hotels, Restaurants, aur Doctors** — teeno ki
bookings ek hi system se handle karta hai.

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env          # .env me DB credentials set karo

uvicorn app.main:app --reload
```

Swagger docs: `http://127.0.0.1:8000/docs`

## Core concept

Teeno categories alag dikhti hain lekin same pattern follow karti hain:

| | Hotel | Restaurant | Doctor |
|---|---|---|---|
| Provider | Hotel | Restaurant | Clinic |
| Service (bookable unit) | Room type | Table type | Consultation slot |
| Booking | Check-in → check-out | Date + time + guests | Date + time |

## API flow (example)

```
1. POST /auth/signup                         → user banao
2. POST /providers/?owner_id=1                → hotel/restaurant/clinic banao (category set karo)
3. POST /providers/{id}/services               → room/table/slot type add karo (price, capacity)
4. GET  /providers/?category=hotel&city=Delhi   → search/filter
5. POST /bookings/                              → book karo (availability auto-check hoti hai)
6. PATCH /bookings/{id}/cancel                   → cancel karo
7. POST /reviews/ (booking status=completed hone ke baad hi)
```

## Abhi tak bana hua

- [x] Folder structure + models (User, Provider, Service, Booking, Review)
- [x] `/auth/signup`
- [x] `/providers` — create, list (category/city/search filter), detail
- [x] `/providers/{id}/services` — room/table/slot add karna
- [x] `/bookings` — create (double-booking rokta hai), list, cancel
- [x] `/reviews` — sirf completed booking par (fake review rokne ke liye)
- [ ] `/auth/login` (JWT) — abhi `owner_id`/`user_id` manually pass karna padta hai
- [ ] Payment integration
- [ ] Image upload (provider photos, menu, doctor profile)
- [ ] Notifications (booking confirm/cancel SMS/email)
