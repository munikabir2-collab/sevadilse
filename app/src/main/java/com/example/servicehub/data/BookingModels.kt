package com.example.servicehub.data

import com.google.gson.annotations.SerializedName

data class BookingResponse(
    val id: Int,

    @SerializedName("user_id")
    val userId: Int,

    @SerializedName("provider_id")
    val providerId: Int,

    @SerializedName("service_id")
    val serviceId: Int,

    @SerializedName("start_time")
    val startTime: String,

    @SerializedName("end_time")
    val endTime: String,

    val guests: Int,

    @SerializedName("total_price")
    val totalPrice: Double,

    val status: String
)

data class BookingStatusUpdateRequest(
    val status: String
)
