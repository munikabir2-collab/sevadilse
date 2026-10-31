package com.example.servicehub

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.BookingResponse
import com.example.servicehub.data.BookingStatusUpdateRequest
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@Composable
fun MyBookingsScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var bookings by remember { mutableStateOf<List<BookingResponse>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var updatingId by remember { mutableStateOf<Int?>(null) }
    var message by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    suspend fun loadBookings() {
        isLoading = true
        message = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                message = "Login required. Please login again."
                bookings = emptyList()
                return
            }

            val response = RetrofitClient.api.getMyBookings("Bearer $token")

            if (response.isSuccessful) {
                bookings = response.body() ?: emptyList()
            } else {
                message = "Bookings load failed: HTTP ${response.code()}"
            }
        } catch (e: Exception) {
            message = "Network error: ${e.message ?: "Please try again"}"
        } finally {
            isLoading = false
        }
    }

    suspend fun changeStatus(bookingId: Int, status: String) {
        updatingId = bookingId
        message = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                message = "Login required"
                return
            }

            val response = RetrofitClient.api.updateBookingStatus(
                authorization = "Bearer $token",
                bookingId = bookingId,
                request = BookingStatusUpdateRequest(status = status)
            )

            if (response.isSuccessful) {
                message = "Booking #$bookingId updated: $status"
                loadBookings()
            } else {
                message = "Status update failed: HTTP ${response.code()}"
            }
        } catch (e: Exception) {
            message = "Update error: ${e.message ?: "Please try again"}"
        } finally {
            updatingId = null
        }
    }

    LaunchedEffect(Unit) {
        loadBookings()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(
            text = "My Bookings",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Spacer(modifier = Modifier.height(12.dp))

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("← Dashboard")
            }

            Button(
                onClick = {
                    scope.launch { loadBookings() }
                },
                enabled = !isLoading,
                modifier = Modifier.weight(1f)
            ) {
                Text("Refresh")
            }
        }

        if (message.isNotBlank()) {
            Text(
                text = message,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(vertical = 10.dp)
            )
        }

        when {
            isLoading -> {
                CircularProgressIndicator(
                    modifier = Modifier.padding(24.dp)
                )
            }

            bookings.isEmpty() -> {
                Text(
                    text = "No bookings found.",
                    modifier = Modifier.padding(top = 24.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(bookings, key = { it.id }) { booking ->
                        Card(
                            modifier = Modifier.fillMaxWidth(),
                            shape = RoundedCornerShape(18.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = MaterialTheme.colorScheme.surfaceVariant
                            )
                        ) {
                            Column(
                                modifier = Modifier.padding(16.dp)
                            ) {
                                Text(
                                    text = "Booking #${booking.id}",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )

                                Text("Service ID: ${booking.serviceId}")
                                Text("Start: ${booking.startTime}")
                                Text("End: ${booking.endTime}")
                                Text("Guests: ${booking.guests}")
                                Text("Price: ${booking.totalPrice}")

                                Text(
                                    text = "Status: ${booking.status}",
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 6.dp)
                                )

                                Spacer(modifier = Modifier.height(10.dp))

                                if (updatingId == booking.id) {
                                    CircularProgressIndicator()
                                } else {
                                    when (booking.status.lowercase()) {
                                        "pending" -> {
                                            Row(
                                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                                            ) {
                                                Button(
                                                    onClick = {
                                                        scope.launch {
                                                            changeStatus(booking.id, "confirmed")
                                                        }
                                                    }
                                                ) {
                                                    Text("Confirm")
                                                }

                                                OutlinedButton(
                                                    onClick = {
                                                        scope.launch {
                                                            changeStatus(booking.id, "cancelled")
                                                        }
                                                    }
                                                ) {
                                                    Text("Cancel")
                                                }
                                            }
                                        }

                                        "confirmed" -> {
                                            Row(
                                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                                            ) {
                                                Button(
                                                    onClick = {
                                                        scope.launch {
                                                            changeStatus(booking.id, "completed")
                                                        }
                                                    }
                                                ) {
                                                    Text("Complete")
                                                }

                                                OutlinedButton(
                                                    onClick = {
                                                        scope.launch {
                                                            changeStatus(booking.id, "cancelled")
                                                        }
                                                    }
                                                ) {
                                                    Text("Cancel")
                                                }
                                            }
                                        }

                                        else -> {
                                            Text(
                                                text = "No further status actions available.",
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
