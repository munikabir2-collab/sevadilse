from typing import Optional

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    EmailStr,
)


# ============================================================
# 1. LINKED ACCOUNT SETUP
# ============================================================

class ProviderPayoutSetupRequest(BaseModel):
    legal_business_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )

    email: EmailStr

    phone: Optional[str] = Field(
        default=None,
        max_length=30,
    )

    contact_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    business_type: str = Field(
        default="individual",
        min_length=2,
        max_length=50,
    )

    business_category: str = Field(
        default="services",
        min_length=2,
        max_length=100,
    )

    business_subcategory: str = Field(
        default="other",
        min_length=2,
        max_length=100,
    )

    street1: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )

    street2: Optional[str] = Field(
        default=None,
        max_length=200,
    )

    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    postal_code: str = Field(
        ...,
        min_length=4,
        max_length=12,
    )

    country: str = Field(
        default="IN",
        min_length=2,
        max_length=2,
    )

    # Razorpay ko bheja jayega.
    # ServiceHub DB me store nahi kiya ja raha.
    pan: Optional[str] = Field(
        default=None,
        max_length=20,
    )

    gst: Optional[str] = Field(
        default=None,
        max_length=30,
    )


# ============================================================
# 2. STAKEHOLDER / KYC
# ============================================================

class StakeholderCreateRequest(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    street: str = Field(
        ...,
        min_length=2,
        max_length=200,
    )

    city: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    state: str = Field(
        ...,
        min_length=2,
        max_length=100,
    )

    postal_code: str = Field(
        ...,
        min_length=4,
        max_length=12,
    )

    country: str = Field(
        default="IN",
        min_length=2,
        max_length=2,
    )

    pan: str = Field(
        ...,
        min_length=10,
        max_length=20,
    )


# ============================================================
# 3. ROUTE PRODUCT
# ============================================================

class RouteProductRequest(BaseModel):
    tnc_accepted: bool = Field(
        ...,
        description=(
            "Provider ne Razorpay Route "
            "Terms & Conditions accept kiye hain."
        ),
    )


# ============================================================
# 4. BANK / SETTLEMENT
# ============================================================

class SettlementBankRequest(BaseModel):
    account_number: str = Field(
        ...,
        min_length=6,
        max_length=30,
    )

    ifsc_code: str = Field(
        ...,
        min_length=4,
        max_length=20,
    )

    beneficiary_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
    )

    tnc_accepted: bool = Field(
        ...,
        description=(
            "Provider ne Razorpay Route "
            "Terms & Conditions accept kiye hain."
        ),
    )


# ============================================================
# 5. PAYOUT PROFILE RESPONSE
# ============================================================

class ProviderPayoutProfileOut(BaseModel):
    id: int
    provider_id: int

    razorpay_account_id: Optional[str] = None

    razorpay_stakeholder_id: Optional[str] = None

    razorpay_product_id: Optional[str] = None

    status: str

    payouts_enabled: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# ============================================================
# 6. ADMIN STATUS UPDATE
# ============================================================

class ProviderPayoutStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(pending|active|suspended)$",
    )

    payouts_enabled: bool = False


# ============================================================
# 7. ONBOARDING STEP
# ============================================================

class PayoutOnboardingStep(BaseModel):
    completed: bool

    id: Optional[str] = None


# ============================================================
# 8. BANK ONBOARDING STEP
# ============================================================

class PayoutBankOnboardingStep(BaseModel):
    completed: bool


# ============================================================
# 9. VERIFICATION STATUS
# ============================================================

class PayoutVerificationStatus(BaseModel):
    completed: bool

    status: str

    payouts_enabled: bool


# ============================================================
# 10. COMPLETE ONBOARDING STATUS
# ============================================================

class ProviderPayoutOnboardingStatusOut(BaseModel):
    provider_id: int

    payout_profile_id: int

    linked_account: PayoutOnboardingStep

    stakeholder: PayoutOnboardingStep

    route_product: PayoutOnboardingStep

    bank: PayoutBankOnboardingStep

    verification: PayoutVerificationStatus

    next_step: str

    ready_for_payout: bool