# ServiceHub React Frontend

Responsive React + Vite frontend for the ServiceHub FastAPI API.

## Run locally (Windows PowerShell)

```powershell
cd F:\sevadilse\frontend
Copy-Item .env.example .env
notepad .env
npm install
npm run dev
```

In `.env`, set `VITE_API_BASE_URL` to the public Render backend URL, e.g.
`https://your-service-name.onrender.com` (do not use `127.0.0.1`, `localhost`, or `/docs`).
Set `VITE_RAZORPAY_KEY_ID` to the Razorpay **public Key ID** only. Never put a Razorpay Key Secret or database URL in React.

Build check:

```powershell
npm run build
```

## Included screens

- Home/dashboard with categories
- Signup and login (Bearer token)
- Providers and doctors directory
- Service bookings, hotel bookings, doctor appointments
- Restaurant menus and orders
- My bookings, orders and appointments
- Provider workspace for creating services, hotel rooms, doctor profiles and slots
- Payment order creation and Razorpay Checkout script loading

## API notes

The app calls the endpoints shown in the supplied OpenAPI documentation. Since only endpoint names (not every schema field) were supplied, request payloads are reasonable defaults and are isolated in `src/api.js` / page forms. If the backend schema requires different fields, use `/openapi.json` on the live Render URL and adjust the relevant payload. Auth responses support common `access_token` and `token` shapes.

Razorpay checkout needs a configured public Key ID and a backend endpoint that returns the Razorpay `order_id`. The server must verify payment signatures through `/payments/verify`; do not mark an order paid only in frontend code.
