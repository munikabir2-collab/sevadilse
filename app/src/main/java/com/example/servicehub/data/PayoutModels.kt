package com.example.servicehub.data

import com.google.gson.annotations.SerializedName

data class PayoutOnboardingStatus(
    @SerializedName("provider_id")
    val providerId: Int,

    @SerializedName("payout_profile_id")
    val payoutProfileId: Int,

    @SerializedName("linked_account")
    val linkedAccount: PayoutStep,

    val stakeholder: PayoutStep,

    @SerializedName("route_product")
    val routeProduct: PayoutStep,

    val bank: PayoutBankStep,

    val verification: PayoutVerification,

    @SerializedName("next_step")
    val nextStep: String,

    @SerializedName("ready_for_payout")
    val readyForPayout: Boolean
)

data class PayoutStep(
    val completed: Boolean,
    val id: String? = null
)

data class PayoutBankStep(
    val completed: Boolean
)

data class PayoutVerification(
    val completed: Boolean,
    val status: String,
    @SerializedName("payouts_enabled")
    val payoutsEnabled: Boolean
)

data class ProviderPayoutProfile(
    val id: Int,
    @SerializedName("provider_id")
    val providerId: Int,
    @SerializedName("razorpay_account_id")
    val razorpayAccountId: String?,
    @SerializedName("razorpay_stakeholder_id")
    val razorpayStakeholderId: String?,
    @SerializedName("razorpay_product_id")
    val razorpayProductId: String?,
    val status: String,
    @SerializedName("payouts_enabled")
    val payoutsEnabled: Boolean
)
