package com.example.servicehub.data

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {

    // =========================
    // AUTH
    // =========================

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

    // =========================
    // PROVIDERS
    // =========================

    @POST("providers/")
    suspend fun createProvider(
        @Header("Authorization") authorization: String,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("providers/")
    suspend fun getProviders(
        @Query("category") category: String? = null,
        @Query("city") city: String? = null,
        @Query("search") search: String? = null,
        @Query("owner_id") ownerId: Int? = null
    ): Response<JsonElement>

    @GET("providers/{provider_id}")
    suspend fun getProvider(
        @Path("provider_id") providerId: Int
    ): Response<ProviderDetailResponse>

    @POST("providers/{provider_id}/services")
    suspend fun addProviderService(
        @Header("Authorization") authorization: String,
        @Path("provider_id") providerId: Int,
        @Body request: ServiceCreateRequest
    ): Response<ServiceResponse>

    // =========================
    // BOOKINGS
    // =========================

    @POST("bookings/")
    suspend fun createBooking(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("bookings/user/{user_id}")
    suspend fun getUserBookings(
        @Path("user_id") userId: Int
    ): Response<JsonElement>

    @PATCH("bookings/{booking_id}/cancel")
    suspend fun cancelBooking(
        @Path("booking_id") bookingId: Int
    ): Response<JsonElement>

    @GET("bookings/provider/me")
    suspend fun getMyBookings(
        @Header("Authorization") authorization: String
    ): Response<List<BookingResponse>>

    @PATCH("bookings/{booking_id}/status")
    suspend fun updateBookingStatus(
        @Header("Authorization") authorization: String,
        @Path("booking_id") bookingId: Int,
        @Body request: BookingStatusUpdateRequest
    ): Response<BookingResponse>

    // =========================
    // RESTAURANT TABLES
    // =========================

    @POST("restaurants/{provider_id}/tables")
    suspend fun createRestaurantTable(
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("restaurants/{provider_id}/tables")
    suspend fun getRestaurantTables(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    @GET("restaurants/tables/{table_id}")
    suspend fun getRestaurantTable(
        @Path("table_id") tableId: Int
    ): Response<JsonElement>

    @PATCH("restaurants/tables/{table_id}")
    suspend fun updateRestaurantTable(
        @Path("table_id") tableId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @DELETE("restaurants/tables/{table_id}")
    suspend fun deleteRestaurantTable(
        @Path("table_id") tableId: Int
    ): Response<JsonElement>

    // =========================
    // RESTAURANT MENU
    // =========================

    @POST("restaurants/{provider_id}/menu")
    suspend fun createMenuItem(
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("restaurants/{provider_id}/menu")
    suspend fun getRestaurantMenu(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    @GET("restaurants/menu/{item_id}")
    suspend fun getMenuItem(
        @Path("item_id") itemId: Int
    ): Response<JsonElement>

    @PATCH("restaurants/menu/{item_id}")
    suspend fun updateMenuItem(
        @Path("item_id") itemId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @DELETE("restaurants/menu/{item_id}")
    suspend fun deleteMenuItem(
        @Path("item_id") itemId: Int
    ): Response<JsonElement>

    // =========================
    // FOOD ORDERS
    // =========================

    @POST("orders/")
    suspend fun createFoodOrder(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("orders/user/{user_id}")
    suspend fun getUserFoodOrders(
        @Path("user_id") userId: Int
    ): Response<JsonElement>

    @GET("orders/{order_id}")
    suspend fun getFoodOrder(
        @Path("order_id") orderId: Int
    ): Response<JsonElement>

    @PATCH("orders/{order_id}/status")
    suspend fun updateFoodOrderStatus(
        @Path("order_id") orderId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @PATCH("orders/{order_id}/cancel")
    suspend fun cancelFoodOrder(
        @Path("order_id") orderId: Int
    ): Response<JsonElement>

    // =========================
    // RESTAURANT BILLS
    // =========================

    @POST("bills/")
    suspend fun createRestaurantBill(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("bills/{bill_id}")
    suspend fun getRestaurantBill(
        @Path("bill_id") billId: Int
    ): Response<JsonElement>

    @GET("bills/order/{order_id}")
    suspend fun getBillByOrder(
        @Path("order_id") orderId: Int
    ): Response<JsonElement>

    @PATCH("bills/{bill_id}/payment-status")
    suspend fun updateBillPaymentStatus(
        @Path("bill_id") billId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    // =========================
    // HOTEL ROOMS
    // =========================

    @POST("hotels/{provider_id}/rooms")
    suspend fun createHotelRoom(
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("hotels/{provider_id}/rooms")
    suspend fun getHotelRooms(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    @GET("hotels/rooms/{room_id}")
    suspend fun getHotelRoom(
        @Path("room_id") roomId: Int
    ): Response<JsonElement>

    @PATCH("hotels/rooms/{room_id}")
    suspend fun updateHotelRoom(
        @Path("room_id") roomId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @DELETE("hotels/rooms/{room_id}")
    suspend fun deleteHotelRoom(
        @Path("room_id") roomId: Int
    ): Response<JsonElement>

    // =========================
    // HOTEL BOOKINGS
    // =========================

    @POST("hotel-bookings/")
    suspend fun createHotelBooking(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("hotel-bookings/user/{user_id}")
    suspend fun getUserHotelBookings(
        @Path("user_id") userId: Int
    ): Response<JsonElement>

    @GET("hotel-bookings/{booking_id}")
    suspend fun getHotelBooking(
        @Path("booking_id") bookingId: Int
    ): Response<JsonElement>

    @PATCH("hotel-bookings/{booking_id}/cancel")
    suspend fun cancelHotelBooking(
        @Path("booking_id") bookingId: Int
    ): Response<JsonElement>

    // =========================
    // DOCTORS
    // =========================

    @POST("doctors/{provider_id}/profile")
    suspend fun updateDoctorProfile(
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("doctors/")
    suspend fun getDoctors(): Response<JsonElement>

    @GET("doctors/{provider_id}")
    suspend fun getDoctor(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    // =========================
    // DOCTOR SLOTS
    // =========================

    @POST("doctors/{provider_id}/slots")
    suspend fun createDoctorSlot(
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("doctors/{provider_id}/slots")
    suspend fun getDoctorSlots(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    // =========================
    // APPOINTMENTS
    // =========================

    @POST("appointments/")
    suspend fun createAppointment(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("appointments/user/{user_id}")
    suspend fun getUserAppointments(
        @Path("user_id") userId: Int
    ): Response<JsonElement>

    @GET("appointments/{appointment_id}")
    suspend fun getAppointment(
        @Path("appointment_id") appointmentId: Int
    ): Response<JsonElement>

    @PATCH("appointments/{appointment_id}/cancel")
    suspend fun cancelAppointment(
        @Path("appointment_id") appointmentId: Int
    ): Response<JsonElement>

    // =========================
    // REVIEWS
    // =========================

    @POST("reviews/")
    suspend fun createReview(
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("reviews/provider/{provider_id}")
    suspend fun getProviderReviews(
        @Path("provider_id") providerId: Int
    ): Response<JsonElement>

    // =========================
    // PAYMENTS
    // =========================

    @POST("payments/create-order")
    suspend fun createPaymentOrder(
        @Body request: JsonObject
    ): Response<JsonElement>

    @POST("payments/verify")
    suspend fun verifyPayment(
        @Body request: JsonObject
    ): Response<JsonElement>

    @POST("payments/{payment_id}/cod-collect")
    suspend fun collectCashOnDelivery(
        @Path("payment_id") paymentId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("payments/{payment_id}")
    suspend fun getPayment(
        @Path("payment_id") paymentId: Int
    ): Response<JsonElement>

    // =========================
    // PROVIDER PAYOUTS
    // =========================

    @POST("provider-payouts/setup")
    suspend fun setupProviderPayout(
        @Header("Authorization") authorization: String,
        @Body request: JsonObject
    ): Response<JsonElement>

    @POST("provider-payouts/stakeholder")
    suspend fun createPayoutStakeholder(
        @Header("Authorization") authorization: String,
        @Body request: JsonObject
    ): Response<JsonElement>

    @POST("provider-payouts/route-product")
    suspend fun createPayoutRouteProduct(
        @Header("Authorization") authorization: String,
        @Body request: JsonObject
    ): Response<JsonElement>

    @PATCH("provider-payouts/bank")
    suspend fun updatePayoutBank(
        @Header("Authorization") authorization: String,
        @Body request: JsonObject
    ): Response<JsonElement>

    @GET("provider-payouts/onboarding/status")
    suspend fun getPayoutOnboardingStatus(
        @Header("Authorization") authorization: String
    ): Response<PayoutOnboardingStatus>

    @GET("provider-payouts/razorpay-account")
    suspend fun getRazorpayAccount(
        @Header("Authorization") authorization: String
    ): Response<JsonElement>

    @GET("provider-payouts/razorpay-product")
    suspend fun getRazorpayProduct(
        @Header("Authorization") authorization: String
    ): Response<JsonElement>

    @GET("provider-payouts/me")
    suspend fun getMyPayoutProfile(
        @Header("Authorization") authorization: String
    ): Response<ProviderPayoutProfile>

    @GET("provider-payouts/status")
    suspend fun getProviderPayoutStatus(
        @Header("Authorization") authorization: String
    ): Response<JsonElement>

    @PATCH("provider-payouts/admin/{provider_id}/status")
    suspend fun updateProviderPayoutStatusByAdmin(
        @Header("Authorization") authorization: String,
        @Path("provider_id") providerId: Int,
        @Body request: JsonObject
    ): Response<JsonElement>

    // =========================
    // ADMIN
    // =========================

    @GET("admin/dashboard/stats")
    suspend fun getAdminDashboardStats(
        @Header("Authorization") authorization: String
    ): Response<JsonElement>
}