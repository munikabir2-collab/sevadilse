# ============================================================
# SERVICEHUB PAYMENT CONFIGURATION
# ============================================================

PLATFORM_COMMISSION_PERCENT = 5.0
PROVIDER_SHARE_PERCENT = 95.0


def calculate_payment_split(amount: float):
    """
    Customer ke total payment ko:
    5% ServiceHub commission
    95% Provider earning
    mein divide karta hai.
    """

    if amount < 0:
        raise ValueError("Amount negative nahi ho sakta.")

    commission = round(
        amount * PLATFORM_COMMISSION_PERCENT / 100,
        2,
    )

    provider_amount = round(
        amount - commission,
        2,
    )

    return {
        "gross_amount": round(amount, 2),
        "commission_percent": PLATFORM_COMMISSION_PERCENT,
        "commission_amount": commission,
        "provider_percent": PROVIDER_SHARE_PERCENT,
        "provider_amount": provider_amount,
    }