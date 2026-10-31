package com.example.servicehub.data

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val email: String,
    val password: String
)

data class TokenResponse(
    @SerializedName("access_token")
    val accessToken: String,

    @SerializedName("token_type")
    val tokenType: String,

    @SerializedName("user_id")
    val userId: Int,

    @SerializedName("provider_id")
    val providerId: Int?,

    @SerializedName("is_provider")
    val isProvider: Boolean,

    @SerializedName("is_admin")
    val isAdmin: Boolean
)

data class UserCreate(
    val name: String,
    val email: String,
    val password: String,
    val phone: String?,

    @SerializedName("is_provider")
    val isProvider: Boolean = false
)

data class UserOut(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String?,

    @SerializedName("is_provider")
    val isProvider: Boolean,

    @SerializedName("is_admin")
    val isAdmin: Boolean
)

data class UserResponse(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String?,

    @SerializedName("is_provider")
    val isProvider: Boolean,

    @SerializedName("is_admin")
    val isAdmin: Boolean
)
data class ServiceCreateRequest(
    val name: String,
    val price: Double,
    val capacity: Int = 1,

    @SerializedName("duration_minutes")
    val durationMinutes: Int? = null,

    @SerializedName("total_units")
    val totalUnits: Int = 1
)

data class ServiceResponse(
    val id: Int,
    val name: String,
    val price: Double,
    val capacity: Int,

    @SerializedName("duration_minutes")
    val durationMinutes: Int?,

    @SerializedName("total_units")
    val totalUnits: Int
)

data class ProviderDetailResponse(
    val id: Int,
    val name: String,
    val category: String,
    val city: String,
    val services: List<ServiceResponse> = emptyList()
)