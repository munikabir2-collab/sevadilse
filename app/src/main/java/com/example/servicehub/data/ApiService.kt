package com.example.servicehub.data

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PATCH
import retrofit2.http.Path

interface ApiService {

    @POST("auth/login")
    suspend fun login(
        @Body request: LoginRequest
    ): Response<TokenResponse>

    @POST("auth/signup")
    suspend fun signup(
        @Body request: UserCreate
    ): Response<UserOut>

    @GET("auth/me")
    suspend fun getCurrentUser(
        @Header("Authorization") authorization: String
    ): Response<UserResponse>

    // Provider details aur uski services load karna
    @GET("providers/{provider_id}")
    suspend fun getProvider(
        @Path("provider_id") providerId: Int
    ): Response<ProviderDetailResponse>

    // Provider ki nayi service add karna
    @POST("providers/{provider_id}/services")
    suspend fun addProviderService(
        @Header("Authorization") authorization: String,
        @Path("provider_id") providerId: Int,
        @Body request: ServiceCreateRequest
    ): Response<ServiceResponse>

    @GET("provider-payouts/onboarding/status")
    suspend fun getPayoutOnboardingStatus(
        @Header("Authorization") authorization: String
    ): Response<PayoutOnboardingStatus>

    @GET("provider-payouts/me")
    suspend fun getMyPayoutProfile(
        @Header("Authorization") authorization: String
    ): Response<ProviderPayoutProfile>

    // Provider ki apni bookings load karna
    @GET("bookings/provider/me")
    suspend fun getMyBookings(
        @Header("Authorization") authorization: String
    ): Response<List<BookingResponse>>

    // Provider booking ka status update karna
    @PATCH("bookings/{booking_id}/status")
    suspend fun updateBookingStatus(
        @Header("Authorization") authorization: String,
        @Path("booking_id") bookingId: Int,
        @Body request: BookingStatusUpdateRequest
    ): Response<BookingResponse>
}
