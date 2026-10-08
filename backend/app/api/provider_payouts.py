import os
import logging
from typing import Any, Dict

import requests
from dotenv import load_dotenv

from fastapi import APIRouter, Depends, HTTPException
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

# Project ke .env ko load karega.
# Isse uvicorn ke through application start hone par bhi
# Razorpay credentials available rahenge.
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

        profile.razorpay_account_id = (
            razorpay_account_id
        )

        profile.status = (
            PayoutAccountStatus.pending
        )

        profile.payouts_enabled = False

    else:

        profile = ProviderPayoutProfile(
            provider_id=provider.id,
            razorpay_account_id=razorpay_account_id,
            status=PayoutAccountStatus.pending,
            payouts_enabled=False,
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

    razorpay_request(
        "PATCH",
        endpoint,
        bank_payload,
    )

    # IMPORTANT:
    # Bank details submit hone ke baad Razorpay
    # verification/KYC complete hone ka wait ho sakta hai.

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

@router.get(
    "/onboarding/status",
)
def get_onboarding_status(
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

    linked_account_ready = bool(
        profile.razorpay_account_id
    )

    stakeholder_ready = bool(
        profile.razorpay_stakeholder_id
    )

    route_product_ready = bool(
        profile.razorpay_product_id
    )

    bank_submitted = (
        route_product_ready
    )

    verification_complete = (
        profile.status == PayoutAccountStatus.active
        and profile.payouts_enabled
    )

    if verification_complete:
        next_step = "completed"

    elif not linked_account_ready:
        next_step = "linked_account"

    elif not stakeholder_ready:
        next_step = "stakeholder"

    elif not route_product_ready:
        next_step = "route_product"

    elif not bank_submitted:
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
            "completed": bank_submitted,
        },

        "verification": {
            "completed": verification_complete,
            "status": profile.status.value,
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