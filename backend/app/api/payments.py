import os
import hmac
import hashlib

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from pydantic import BaseModel, Field

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.api.auth import get_current_user

from app.models.user_model import User

from app.models.payment_model import (
    Payment,
    PaymentStatus as GatewayPaymentStatus,
    PaymentMethod,
    PaymentEntityType,
)

from app.models.provider_model import Provider

from app.models.order_model import (
    RestaurantOrder,
    PaymentStatus as OrderPaymentStatus,
)

from app.models.bill_model import (
    RestaurantBill,
    BillPaymentStatus,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
)


# ============================================================
# CONFIG
# ============================================================

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID",
    "",
)

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET",
    "",
)

PLATFORM_COMMISSION_PERCENT = 5.0


# ============================================================
# REQUEST SCHEMAS
# ============================================================

class CreatePaymentRequest(BaseModel):

    entity_type: PaymentEntityType

    entity_id: int = Field(
        gt=0
    )

    amount: float = Field(
        gt=0
    )

    provider_id: int | None = Field(
        default=None,
        gt=0,
    )

    payment_method: PaymentMethod = (
        PaymentMethod.online
    )


class VerifyPaymentRequest(BaseModel):

    payment_id: int = Field(
        gt=0
    )

    razorpay_order_id: str

    razorpay_payment_id: str

    razorpay_signature: str


class CODCollectRequest(BaseModel):

    notes: str | None = None


# ============================================================
# RAZORPAY CLIENT
# ============================================================

def get_razorpay_client():

    if not RAZORPAY_KEY_ID:

        raise HTTPException(
            status_code=500,
            detail=(
                "RAZORPAY_KEY_ID configured nahi hai"
            ),
        )

    if not RAZORPAY_KEY_SECRET:

        raise HTTPException(
            status_code=500,
            detail=(
                "RAZORPAY_KEY_SECRET configured nahi hai"
            ),
        )

    try:

        import razorpay

    except ImportError:

        raise HTTPException(
            status_code=500,
            detail=(
                "razorpay package installed nahi hai"
            ),
        )

    return razorpay.Client(
        auth=(
            RAZORPAY_KEY_ID,
            RAZORPAY_KEY_SECRET,
        )
    )


# ============================================================
# PROVIDER / ADMIN CHECK
# ============================================================

def require_provider_or_admin(
    current_user: User,
):
    if not (
        current_user.is_provider
        or current_user.is_admin
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Sirf provider ya admin "
                "ye action kar sakta hai"
            ),
        )

    return current_user


# ============================================================
# CREATE PAYMENT
# ============================================================

@router.post("/create-order")
def create_payment_order(
    payment_data: CreatePaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    amount = round(
        float(payment_data.amount),
        2,
    )

    # --------------------------------------------------------
    # PROVIDER VALIDATION
    # --------------------------------------------------------

    provider = None

    if payment_data.provider_id:

        provider = (
            db.query(Provider)
            .filter(
                Provider.id
                == payment_data.provider_id
            )
            .first()
        )

        if not provider:

            raise HTTPException(
                status_code=404,
                detail="Provider nahi mila",
            )

    # --------------------------------------------------------
    # COMMISSION
    # --------------------------------------------------------

    commission_amount = round(
        amount
        * PLATFORM_COMMISSION_PERCENT
        / 100,
        2,
    )

    provider_amount = round(
        amount - commission_amount,
        2,
    )

    # --------------------------------------------------------
    # COD
    # --------------------------------------------------------

    if (
        payment_data.payment_method
        == PaymentMethod.cod
    ):

        payment = Payment(

            user_id=current_user.id,

            provider_id=(
                payment_data.provider_id
            ),

            entity_type=(
                payment_data.entity_type
            ),

            entity_id=(
                payment_data.entity_id
            ),

            payment_method=(
                PaymentMethod.cod
            ),

            amount=amount,

            currency="INR",

            commission_percent=(
                PLATFORM_COMMISSION_PERCENT
            ),

            commission_amount=(
                commission_amount
            ),

            provider_amount=(
                provider_amount
            ),

            status=(
                GatewayPaymentStatus.pending
            ),
        )

        db.add(payment)

        db.commit()

        db.refresh(payment)

        return {

            "success": True,

            "message": (
                "COD order successfully create ho gaya"
            ),

            "payment_id": payment.id,

            "payment_method": "cod",

            "status": payment.status.value,

            "billing": {

                "amount": amount,

                "commission_percent": (
                    PLATFORM_COMMISSION_PERCENT
                ),

                "servicehub_commission": (
                    commission_amount
                ),

                "provider_amount": (
                    provider_amount
                ),
            },
        }

    # --------------------------------------------------------
    # ONLINE PAYMENT
    # --------------------------------------------------------

    razorpay_amount = int(
        round(amount * 100)
    )

    client = get_razorpay_client()

    try:

        razorpay_order = client.order.create(
            {
                "amount": razorpay_amount,
                "currency": "INR",
                "receipt": (
                    f"servicehub_"
                    f"{current_user.id}_"
                    f"{payment_data.entity_type.value}_"
                    f"{payment_data.entity_id}"
                ),
            }
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "Razorpay order create failed: "
                f"{str(exc)}"
            ),
        )

    payment = Payment(

        user_id=current_user.id,

        provider_id=(
            payment_data.provider_id
        ),

        entity_type=(
            payment_data.entity_type
        ),

        entity_id=(
            payment_data.entity_id
        ),

        payment_method=(
            PaymentMethod.online
        ),

        amount=amount,

        currency="INR",

        commission_percent=(
            PLATFORM_COMMISSION_PERCENT
        ),

        commission_amount=(
            commission_amount
        ),

        provider_amount=(
            provider_amount
        ),

        status=(
            GatewayPaymentStatus.created
        ),

        razorpay_order_id=(
            razorpay_order["id"]
        ),
    )

    db.add(payment)

    db.commit()

    db.refresh(payment)

    return {

        "success": True,

        "message": (
            "Razorpay order successfully create ho gaya"
        ),

        "payment_id": payment.id,

        "payment_method": "online",

        "razorpay": {

            "key_id": RAZORPAY_KEY_ID,

            "order_id": (
                razorpay_order["id"]
            ),

            "amount": razorpay_amount,

            "currency": "INR",
        },

        "billing": {

            "amount": amount,

            "commission_percent": (
                PLATFORM_COMMISSION_PERCENT
            ),

            "servicehub_commission": (
                commission_amount
            ),

            "provider_amount": (
                provider_amount
            ),
        },
    }


# ============================================================
# VERIFY ONLINE PAYMENT
# ============================================================

@router.post("/verify")
def verify_payment(
    payment_data: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.id
            == payment_data.payment_id,

            Payment.user_id
            == current_user.id,
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment record nahi mila",
        )

    if (
        payment.payment_method
        != PaymentMethod.online
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Ye online payment nahi hai"
            ),
        )

    # --------------------------------------------------------
    # ALREADY PAID
    # --------------------------------------------------------

    if (
        payment.status
        == GatewayPaymentStatus.paid
    ):

        return {

            "success": True,

            "message": (
                "Payment already verified hai"
            ),

            "payment_id": payment.id,

            "status": payment.status.value,
        }

    # --------------------------------------------------------
    # ORDER ID CHECK
    # --------------------------------------------------------

    if (
        payment.razorpay_order_id
        != payment_data.razorpay_order_id
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Razorpay order ID match nahi karta"
            ),
        )

    # --------------------------------------------------------
    # SIGNATURE
    # --------------------------------------------------------

    if not RAZORPAY_KEY_SECRET:

        raise HTTPException(
            status_code=500,
            detail=(
                "Razorpay secret key configured nahi hai"
            ),
        )

    generated_signature = hmac.new(

        RAZORPAY_KEY_SECRET.encode(
            "utf-8"
        ),

        (
            payment_data.razorpay_order_id
            + "|"
            + payment_data.razorpay_payment_id
        ).encode("utf-8"),

        hashlib.sha256,

    ).hexdigest()

    if not hmac.compare_digest(
        generated_signature,
        payment_data.razorpay_signature,
    ):

        payment.status = (
            GatewayPaymentStatus.failed
        )

        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid Razorpay payment signature"
            ),
        )

    # --------------------------------------------------------
    # SUCCESS
    # --------------------------------------------------------

    payment.razorpay_payment_id = (
        payment_data.razorpay_payment_id
    )

    payment.razorpay_signature = (
        payment_data.razorpay_signature
    )

    payment.status = (
        GatewayPaymentStatus.paid
    )

    payment.paid_at = (
        datetime.now(timezone.utc)
    )

    # --------------------------------------------------------
    # RESTAURANT ORDER
    # --------------------------------------------------------

    if (
        payment.entity_type
        == PaymentEntityType.restaurant_order
    ):

        order = (
            db.query(RestaurantOrder)
            .filter(
                RestaurantOrder.id
                == payment.entity_id
            )
            .first()
        )

        if order:

            order.payment_status = (
                OrderPaymentStatus.paid
            )

            bill = (
                db.query(RestaurantBill)
                .filter(
                    RestaurantBill.order_id
                    == order.id
                )
                .first()
            )

            if bill:

                bill.payment_status = (
                    BillPaymentStatus.paid
                )

                bill.paid_at = (
                    datetime.now(timezone.utc)
                )

    db.commit()

    db.refresh(payment)

    return {

        "success": True,

        "message": (
            "Payment successfully verified"
        ),

        "payment": {

            "id": payment.id,

            "status": payment.status.value,

            "amount": payment.amount,

            "currency": payment.currency,
        },

        "settlement": {

            "commission_percent": (
                payment.commission_percent
            ),

            "servicehub_commission": (
                payment.commission_amount
            ),

            "provider_amount": (
                payment.provider_amount
            ),
        },
    }


# ============================================================
# COD COLLECT
# ============================================================

@router.post("/{payment_id}/cod-collect")
def collect_cod_payment(
    payment_id: int,

    cod_data: CODCollectRequest,

    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user),
):

    require_provider_or_admin(
        current_user
    )

    # --------------------------------------------------------
    # PAYMENT
    # --------------------------------------------------------

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment nahi mila",
        )

    # --------------------------------------------------------
    # COD CHECK
    # --------------------------------------------------------

    if (
        payment.payment_method
        != PaymentMethod.cod
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Ye COD payment nahi hai"
            ),
        )

    # --------------------------------------------------------
    # PROVIDER OWNERSHIP
    # --------------------------------------------------------

    if not current_user.is_admin:

        provider = (
            db.query(Provider)
            .filter(
                Provider.id
                == payment.provider_id
            )
            .first()
        )

        if not provider:

            raise HTTPException(
                status_code=404,
                detail="Provider nahi mila",
            )

        if (
            provider.owner_id
            != current_user.id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "Aap is provider ka COD "
                    "payment collect nahi kar sakte"
                ),
            )

    # --------------------------------------------------------
    # ALREADY COLLECTED
    # --------------------------------------------------------

    if (
        payment.status
        == GatewayPaymentStatus.paid
    ):

        return {

            "success": True,

            "message": (
                "COD payment already collected hai"
            ),

            "payment_id": payment.id,

            "status": payment.status.value,
        }

    # --------------------------------------------------------
    # MARK COLLECTED
    # --------------------------------------------------------

    payment.status = (
        GatewayPaymentStatus.paid
    )

    payment.paid_at = (
        datetime.now(timezone.utc)
    )

    payment.cod_collected_at = (
        datetime.now(timezone.utc)
    )

    payment.cod_collected_by = (
        current_user.id
    )

    payment.cod_notes = (
        cod_data.notes
    )

    # --------------------------------------------------------
    # RESTAURANT ORDER
    # --------------------------------------------------------

    if (
        payment.entity_type
        == PaymentEntityType.restaurant_order
    ):

        order = (
            db.query(RestaurantOrder)
            .filter(
                RestaurantOrder.id
                == payment.entity_id
            )
            .first()
        )

        if order:

            order.payment_status = (
                OrderPaymentStatus.paid
            )

            bill = (
                db.query(RestaurantBill)
                .filter(
                    RestaurantBill.order_id
                    == order.id
                )
                .first()
            )

            if bill:

                bill.payment_status = (
                    BillPaymentStatus.paid
                )

                bill.paid_at = (
                    datetime.now(timezone.utc)
                )

    db.commit()

    db.refresh(payment)

    return {

        "success": True,

        "message": (
            "COD payment successfully collected"
        ),

        "payment": {

            "id": payment.id,

            "status": payment.status.value,

            "payment_method": (
                payment.payment_method.value
            ),

            "amount": payment.amount,

            "cod_collected_by": (
                payment.cod_collected_by
            ),

            "cod_collected_at": (
                payment.cod_collected_at
            ),
        },

        "settlement": {

            "gross_amount": (
                payment.amount
            ),

            "servicehub_commission": (
                payment.commission_amount
            ),

            "provider_amount": (
                payment.provider_amount
            ),
        },
    }


# ============================================================
# GET PAYMENT
# ============================================================

@router.get("/{payment_id}")
def get_payment(
    payment_id: int,

    db: Session = Depends(get_db),

    current_user: User = Depends(get_current_user),
):

    payment = (
        db.query(Payment)
        .filter(
            Payment.id == payment_id
        )
        .first()
    )

    if not payment:

        raise HTTPException(
            status_code=404,
            detail="Payment nahi mila",
        )

    # --------------------------------------------------------
    # CUSTOMER OWNER
    # --------------------------------------------------------

    if (
        payment.user_id
        != current_user.id
        and not current_user.is_admin
    ):

        # Provider apna payment dekh sakta hai
        if current_user.is_provider:

            provider = (
                db.query(Provider)
                .filter(
                    Provider.id
                    == payment.provider_id
                )
                .first()
            )

            if (
                not provider
                or provider.owner_id
                != current_user.id
            ):

                raise HTTPException(
                    status_code=403,
                    detail="Access denied",
                )

        else:

            raise HTTPException(
                status_code=403,
                detail="Access denied",
            )

    return {

        "id": payment.id,

        "user_id": payment.user_id,

        "provider_id": payment.provider_id,

        "entity_type": (
            payment.entity_type.value
        ),

        "entity_id": payment.entity_id,

        "payment_method": (
            payment.payment_method.value
        ),

        "amount": payment.amount,

        "currency": payment.currency,

        "commission_percent": (
            payment.commission_percent
        ),

        "commission_amount": (
            payment.commission_amount
        ),

        "provider_amount": (
            payment.provider_amount
        ),

        "status": (
            payment.status.value
        ),

        "razorpay_order_id": (
            payment.razorpay_order_id
        ),

        "razorpay_payment_id": (
            payment.razorpay_payment_id
        ),

        "created_at": payment.created_at,

        "paid_at": payment.paid_at,

        "cod_collected_at": (
            payment.cod_collected_at
        ),

        "cod_collected_by": (
            payment.cod_collected_by
        ),

        "cod_notes": payment.cod_notes,
    }