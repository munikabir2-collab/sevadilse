import os
import logging
import hashlib
import hmac
import json
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.orm import Session

from app.core.database import get_db

from app.models.user_model import User
from app.models.provider_model import Provider
from app.models.provider_payout_model import (
    ProviderPayoutProfile,
    PayoutAccountStatus,
)

from app.schemas.provider_payout_schema import (
    ProviderPayoutSetupRequest,
    StakeholderCreateRequest,
    RouteProductRequest,
    SettlementBankRequest,
    ProviderPayoutProfileOut,
    ProviderPayoutStatusUpdate,
)

from app.api.auth import get_current_user


# ============================================================
# ENV
# ============================================================

load_dotenv()


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/provider-payouts",
    tags=["Provider Payouts"],
)

logger = logging.getLogger(__name__)


# ============================================================
# RAZORPAY CONFIG
# ============================================================

RAZORPAY_KEY_ID = os.getenv(
    "RAZORPAY_KEY_ID",
    "",
).strip()

RAZORPAY_KEY_SECRET = os.getenv(
    "RAZORPAY_KEY_SECRET",
    "",
).strip()

RAZORPAY_BASE_URL = "https://api.razorpay.com/v2"

RAZORPAY_WEBHOOK_SECRET = os.getenv(
    "RAZORPAY_WEBHOOK_SECRET",
    "",
).strip()


# ============================================================
# RAZORPAY HELPERS
# ============================================================

def check_razorpay_config():
    """
    Razorpay credentials configured hain ya nahi check karta hai.
    """

    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "Razorpay configuration missing. "
                "RAZORPAY_KEY_ID aur RAZORPAY_KEY_SECRET "
                ".env file me set karein."
            ),
        )


def razorpay_request(
    method: str,
    endpoint: str,
    payload: Dict[str, Any] | None = None,
):
    """
    Razorpay API helper.

    IMPORTANT:
    - Secret credentials logs me print nahi hote.
    - Request body logs me print nahi hota.
    """

    check_razorpay_config()

    url = f"{RAZORPAY_BASE_URL}{endpoint}"

    try:
        response = requests.request(
            method=method,
            url=url,
            auth=(
                RAZORPAY_KEY_ID,
                RAZORPAY_KEY_SECRET,
            ),
            json=payload,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    except requests.RequestException as exc:
        logger.exception(
            "Razorpay API connection failed"
        )

        raise HTTPException(
            status_code=502,
            detail=(
                "Razorpay API se connection failed. "
                "Network/firewall ya Razorpay API availability check karein."
            ),
        ) from exc

    try:
        data = response.json()

    except ValueError:
        data = {
            "raw_response": response.text,
        }

    if response.status_code >= 400:

        logger.error(
            "Razorpay API failed: method=%s endpoint=%s status=%s",
            method,
            endpoint,
            response.status_code,
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": "Razorpay API request failed.",
                "razorpay_status": response.status_code,
                "razorpay_response": data,
            },
        )

    return data


# ============================================================
# PROVIDER HELPERS
# ============================================================

def require_provider(
    current_user: User,
    db: Session,
) -> Provider:

    provider = (
        db.query(Provider)
        .filter(
            Provider.owner_id == current_user.id
        )
        .first()
    )

    if not provider:
        raise HTTPException(
            status_code=403,
            detail=(
                "Current user ke liye provider account nahi mila."
            ),
        )

    return provider


def get_profile(
    provider_id: int,
    db: Session,
) -> ProviderPayoutProfile:

    profile = (
        db.query(ProviderPayoutProfile)
        .filter(
            ProviderPayoutProfile.provider_id
            == provider_id
        )
        .first()
    )

    if not profile:
        raise HTTPException(
            status_code=404,
            detail=(
                "Provider payout profile nahi mila. "
                "Pehle Linked Account setup karein."
            ),
        )

    return profile


# ============================================================
# 1. CREATE RAZORPAY LINKED ACCOUNT
# ============================================================

@router.post(
    "/setup",
    response_model=ProviderPayoutProfileOut,
)
def setup_provider_payout_account(
    payload: ProviderPayoutSetupRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    existing = (
        db.query(ProviderPayoutProfile)
        .filter(
            ProviderPayoutProfile.provider_id
            == provider.id
        )
        .first()
    )

    # Already linked account exists.
    if existing and existing.razorpay_account_id:
        return existing

    account_payload = {
        "email": payload.email,
        "phone": payload.phone or current_user.phone,
        "type": "route",
        "legal_business_name": payload.legal_business_name,
        "business_type": payload.business_type,
        "contact_name": payload.contact_name,
        "profile": {
            "category": payload.business_category,
            "subcategory": payload.business_subcategory,
            "addresses": {
                "registered": {
                    "street1": payload.street1,
                    "street2": payload.street2,
                    "city": payload.city,
                    "state": payload.state,
                    "postal_code": payload.postal_code,
                    "country": payload.country,
                }
            },
        },
    }

    if payload.pan or payload.gst:

        account_payload["legal_info"] = {}

        if payload.pan:
            account_payload["legal_info"]["pan"] = payload.pan

        if payload.gst:
            account_payload["legal_info"]["gst"] = payload.gst

    razorpay_data = razorpay_request(
        "POST",
        "/accounts",
        account_payload,
    )

    razorpay_account_id = razorpay_data.get("id")

    if not razorpay_account_id:
        raise HTTPException(
            status_code=502,
            detail=(
                "Razorpay response me Linked Account ID nahi mila."
            ),
        )

    if existing:

        profile = existing

        profile.razorpay_account_id = razorpay_account_id

        profile.razorpay_stakeholder_id = None
        profile.razorpay_product_id = None

        profile.status = PayoutAccountStatus.pending
        profile.payouts_enabled = False
        profile.bank_submitted = False
        profile.razorpay_activation_status = None

    else:

        profile = ProviderPayoutProfile(
            provider_id=provider.id,
            razorpay_account_id=razorpay_account_id,
            status=PayoutAccountStatus.pending,
            payouts_enabled=False,
            bank_submitted=False,
            razorpay_activation_status=None,
        )

        db.add(profile)

    db.commit()
    db.refresh(profile)

    logger.info(
        "Razorpay Linked Account created for provider_id=%s",
        provider.id,
    )

    return profile


# ============================================================
# 2. CREATE STAKEHOLDER / KYC
# ============================================================

@router.post(
    "/stakeholder",
    response_model=ProviderPayoutProfileOut,
)
def create_provider_stakeholder(
    payload: StakeholderCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = get_profile(
        provider.id,
        db,
    )

    if not profile.razorpay_account_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Pehle /provider-payouts/setup "
                "call karke Linked Account create karein."
            ),
        )

    if profile.razorpay_stakeholder_id:
        return profile

    stakeholder_payload = {
        "name": payload.name,
        "addresses": {
            "residential": {
                "street": payload.street,
                "city": payload.city,
                "state": payload.state,
                "postal_code": payload.postal_code,
                "country": payload.country,
            }
        },
        "kyc": {
            "pan": payload.pan,
        },
    }

    endpoint = (
        f"/accounts/"
        f"{profile.razorpay_account_id}"
        f"/stakeholders"
    )

    razorpay_data = razorpay_request(
        "POST",
        endpoint,
        stakeholder_payload,
    )

    stakeholder_id = razorpay_data.get("id")

    if not stakeholder_id:
        raise HTTPException(
            status_code=502,
            detail=(
                "Razorpay response me Stakeholder ID nahi mila."
            ),
        )

    profile.razorpay_stakeholder_id = stakeholder_id

    db.commit()
    db.refresh(profile)

    logger.info(
        "Razorpay Stakeholder created for provider_id=%s",
        provider.id,
    )

    return profile
# ============================================================
# 3. REQUEST ROUTE PRODUCT
# ============================================================

@router.post(
    "/route-product",
    response_model=ProviderPayoutProfileOut,
)
def request_route_product(
    payload: RouteProductRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = get_profile(
        provider.id,
        db,
    )

    if not profile.razorpay_account_id:
        raise HTTPException(
            status_code=400,
            detail="Linked Account pehle create karein.",
        )

    if not profile.razorpay_stakeholder_id:
        raise HTTPException(
            status_code=400,
            detail="Stakeholder pehle create karein.",
        )

    if profile.razorpay_product_id:
        return profile

    if not payload.tnc_accepted:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provider ko Razorpay Route Terms & Conditions "
                "accept karna hoga."
            ),
        )

    endpoint = (
        f"/accounts/"
        f"{profile.razorpay_account_id}"
        f"/products"
    )

    product_payload = {
        "product_name": "route",
        "tnc_accepted": True,
    }

    razorpay_data = razorpay_request(
        "POST",
        endpoint,
        product_payload,
    )

    product_id = razorpay_data.get("id")

    if not product_id:
        raise HTTPException(
            status_code=502,
            detail=(
                "Razorpay response me Product ID nahi mila."
            ),
        )

    profile.razorpay_product_id = product_id

    db.commit()
    db.refresh(profile)

    logger.info(
        "Razorpay Route Product created for provider_id=%s",
        provider.id,
    )

    return profile


# ============================================================
# 4. CONFIGURE BANK / SETTLEMENT
# ============================================================

@router.patch(
    "/bank",
    response_model=ProviderPayoutProfileOut,
)
def configure_settlement_bank(
    payload: SettlementBankRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = get_profile(
        provider.id,
        db,
    )

    if not profile.razorpay_account_id:
        raise HTTPException(
            status_code=400,
            detail="Linked Account pehle create karein.",
        )

    if not profile.razorpay_product_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Route Product Configuration "
                "pehle request karein."
            ),
        )

    if not payload.tnc_accepted:
        raise HTTPException(
            status_code=400,
            detail=(
                "Razorpay Route Terms & Conditions "
                "accept karna required hai."
            ),
        )

    endpoint = (
        f"/accounts/"
        f"{profile.razorpay_account_id}"
        f"/products/"
        f"{profile.razorpay_product_id}"
    )

    bank_payload = {
        "settlements": {
            "account_number": payload.account_number,
            "ifsc_code": payload.ifsc_code,
            "beneficiary_name": payload.beneficiary_name,
        },
        "tnc_accepted": True,
    }

    # Razorpay API successful hone par hi bank submitted mark karein.
    razorpay_request(
        "PATCH",
        endpoint,
        bank_payload,
    )

    profile.bank_submitted = True
    profile.razorpay_activation_status = None
    profile.status = PayoutAccountStatus.pending
    profile.payouts_enabled = False

    db.commit()
    db.refresh(profile)

    logger.info(
        "Settlement bank submitted for provider_id=%s",
        provider.id,
    )

    return profile


# ============================================================
# 5. ONBOARDING STATUS
# ============================================================

@router.get("/onboarding/status")
def get_onboarding_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = (
        db.query(ProviderPayoutProfile)
        .filter(
            ProviderPayoutProfile.provider_id == provider.id
        )
        .first()
    )

    # Payout onboarding abhi start nahi hua hai.
    if not profile:
        return {
            "provider_id": provider.id,
            "payout_profile_id": None,

            "linked_account": {
                "completed": False,
                "id": None,
            },

            "stakeholder": {
                "completed": False,
                "id": None,
            },

            "route_product": {
                "completed": False,
                "id": None,
            },

            "bank": {
                "completed": False,
            },

            "verification": {
                "completed": False,
                "status": "not_started",
                "activation_status": None,
                "payouts_enabled": False,
            },

            "next_step": "linked_account",
            "ready_for_payout": False,
        }

    linked_account_ready = bool(
        profile.razorpay_account_id
    )

    stakeholder_ready = bool(
        profile.razorpay_stakeholder_id
    )

    route_product_ready = bool(
        profile.razorpay_product_id
    )

    bank_ready = bool(
        profile.bank_submitted
    )

    verification_complete = (
        profile.status == PayoutAccountStatus.active
        and profile.payouts_enabled
    )

    # Next onboarding step.
    if verification_complete:
        next_step = "completed"

    elif not linked_account_ready:
        next_step = "linked_account"

    elif not stakeholder_ready:
        next_step = "stakeholder"

    elif not route_product_ready:
        next_step = "route_product"

    elif not bank_ready:
        next_step = "bank"

    else:
        next_step = "verification"

    return {
        "provider_id": provider.id,
        "payout_profile_id": profile.id,

        "linked_account": {
            "completed": linked_account_ready,
            "id": profile.razorpay_account_id,
        },

        "stakeholder": {
            "completed": stakeholder_ready,
            "id": profile.razorpay_stakeholder_id,
        },

        "route_product": {
            "completed": route_product_ready,
            "id": profile.razorpay_product_id,
        },

        "bank": {
            "completed": bank_ready,
        },

        "verification": {
            "completed": verification_complete,
            "status": profile.status.value,
            "activation_status": profile.razorpay_activation_status,
            "payouts_enabled": profile.payouts_enabled,
        },

        "next_step": next_step,
        "ready_for_payout": verification_complete,
    }


# ============================================================
# 6. FETCH RAZORPAY LINKED ACCOUNT
# ============================================================

@router.get(
    "/razorpay-account",
)
def fetch_razorpay_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = get_profile(
        provider.id,
        db,
    )

    if not profile.razorpay_account_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "Razorpay Linked Account setup nahi hua."
            ),
        )

    endpoint = (
        f"/accounts/"
        f"{profile.razorpay_account_id}"
    )

    return razorpay_request(
        "GET",
        endpoint,
    )


# ============================================================
# 7. FETCH ROUTE PRODUCT
# ============================================================

@router.get(
    "/razorpay-product",
)
def fetch_razorpay_product(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    profile = get_profile(
        provider.id,
        db,
    )

    if not profile.razorpay_account_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "Razorpay Linked Account setup nahi hua."
            ),
        )

    if not profile.razorpay_product_id:
        raise HTTPException(
            status_code=404,
            detail=(
                "Razorpay Route Product setup nahi hua."
            ),
        )

    endpoint = (
        f"/accounts/"
        f"{profile.razorpay_account_id}"
        f"/products/"
        f"{profile.razorpay_product_id}"
    )

    return razorpay_request(
        "GET",
        endpoint,
    )


# ============================================================
# 8. GET MY PAYOUT PROFILE
# ============================================================

@router.get(
    "/me",
    response_model=ProviderPayoutProfileOut,
)
def get_my_payout_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    return get_profile(
        provider.id,
        db,
    )


# ============================================================
# 9. GET LOCAL PAYOUT STATUS
# ============================================================

@router.get(
    "/status",
    response_model=ProviderPayoutProfileOut,
)
def get_my_payout_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    provider = require_provider(
        current_user,
        db,
    )

    return get_profile(
        provider.id,
        db,
    )


# ============================================================
# 10. ADMIN STATUS UPDATE
# ============================================================

@router.patch(
    "/admin/{provider_id}/status",
    response_model=ProviderPayoutProfileOut,
)
def update_provider_payout_status(
    provider_id: int,
    payload: ProviderPayoutStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    if not current_user.is_admin:
        raise HTTPException(
            status_code=403,
            detail=(
                "Sirf admin provider payout status "
                "update kar sakta hai."
            ),
        )

    profile = get_profile(
        provider_id,
        db,
    )

    profile.status = PayoutAccountStatus(
        payload.status
    )

    profile.payouts_enabled = (
        payload.payouts_enabled
    )

    db.commit()
    db.refresh(profile)

    return profile
# ============================================================
# 11. RAZORPAY ROUTE WEBHOOK
# ============================================================

@router.post("/webhook/razorpay")
async def razorpay_route_webhook(
    request: Request,
    x_razorpay_signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
    db: Session = Depends(get_db),
):
    """
    Razorpay Route activation webhook.

    IMPORTANT:
    - Signature raw request body se verify hota hai.
    - Webhook activation ko local payout approval se alag rakha gaya hai.
    - Payouts admin approval ke bina enable nahi honge.
    """

    if not RAZORPAY_WEBHOOK_SECRET:
        logger.error("Razorpay webhook secret is not configured")
        raise HTTPException(
            status_code=503,
            detail="Razorpay webhook configuration missing.",
        )

    if not x_razorpay_signature:
        raise HTTPException(
            status_code=400,
            detail="Razorpay webhook signature missing.",
        )

    raw_body = await request.body()

    expected_signature = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        x_razorpay_signature.strip(),
    ):
        logger.warning("Razorpay webhook signature verification failed")
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook signature.",
        )

    try:
        event_data = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid Razorpay webhook JSON payload.",
        )

    event_name = event_data.get("event")
    supported_events = {
        "product.route.under_review": "under_review",
        "product.route.needs_clarification": "needs_clarification",
        "product.route.activated": "activated",
    }

    activation_status = supported_events.get(event_name)

    # Other Razorpay events are acknowledged and ignored.
    if activation_status is None:
        return {
            "status": "ignored",
            "event": event_name,
        }

    payload = event_data.get("payload") or {}
    merchant_product = payload.get("merchant_product") or {}
    product_entity = merchant_product.get("entity") or {}

    account_id = (
        event_data.get("account_id")
        or product_entity.get("merchant_id")
    )
    product_id = product_entity.get("id")

    if not account_id:
        logger.warning(
            "Razorpay Route webhook has no account_id; event=%s",
            event_name,
        )
        return {
            "status": "ignored",
            "reason": "account_id_missing",
        }

    profile = (
        db.query(ProviderPayoutProfile)
        .filter(
            ProviderPayoutProfile.razorpay_account_id == account_id
        )
        .first()
    )

    if not profile:
        logger.warning(
            "Razorpay Route webhook account not found locally; account_id=%s",
            account_id,
        )
        return {
            "status": "ignored",
            "reason": "linked_account_not_found",
        }

    # Do not apply an old/stale product event to a newer product.
    if (
        product_id
        and profile.razorpay_product_id
        and product_id != profile.razorpay_product_id
    ):
        logger.warning(
            "Razorpay Route webhook product mismatch for provider_id=%s",
            profile.provider_id,
        )
        return {
            "status": "ignored",
            "reason": "route_product_id_mismatch",
        }

    profile.razorpay_activation_status = activation_status

    if activation_status in {
        "under_review",
        "needs_clarification",
    }:
        # Review/clarification state must never permit payouts.
        profile.status = PayoutAccountStatus.pending
        profile.payouts_enabled = False

    # On "activated", record Razorpay's activation only.
    # Local payout status remains subject to the existing admin approval.
    db.commit()
    db.refresh(profile)

    requirements = (
        (merchant_product.get("data") or {}).get("requirements") or []
    )

    logger.info(
        "Razorpay Route webhook processed: event=%s provider_id=%s "
        "activation_status=%s requirements_count=%s",
        event_name,
        profile.provider_id,
        activation_status,
        len(requirements),
    )

    return {
        "status": "processed",
        "event": event_name,
        "provider_id": profile.provider_id,
        "activation_status": profile.razorpay_activation_status,
        "local_payout_status": profile.status.value,
        "payouts_enabled": profile.payouts_enabled,
        "requirements_count": len(requirements),
    }