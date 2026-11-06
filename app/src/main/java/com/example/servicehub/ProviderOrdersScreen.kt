
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
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private data class ProviderOrderItem(
    val id: Int,
    val userId: Int,
    val tableId: Int?,
    val orderType: String,
    val status: String,
    val paymentStatus: String,
    val subtotal: String,
    val discount: String,
    val gst: String,
    val serviceCharge: String,
    val grandTotal: String,
    val specialInstructions: String,
    val createdAt: String,
    val items: List<String>
)

private fun JsonElement.readString(key: String): String {
    return try {
        if (isJsonObject && !asJsonObject.get(key).isJsonNull) {
            asJsonObject.get(key).asString
        } else {
            ""
        }
    } catch (e: Exception) {
        ""
    }
}

private fun JsonElement.readInt(key: String): Int {
    return readString(key).toIntOrNull() ?: 0
}

private fun JsonElement.readNullableInt(key: String): Int? {
    return try {
        val value = asJsonObject.get(key)
        if (value == null || value.isJsonNull) null else value.asInt
    } catch (e: Exception) {
        null
    }
}

private fun parseProviderOrders(element: JsonElement?): List<ProviderOrderItem> {
    if (element == null || !element.isJsonArray) return emptyList()

    return element.asJsonArray.mapNotNull { json ->
        try {
            if (!json.isJsonObject) return@mapNotNull null

            val orderItems = try {
                json.asJsonObject.get("items")
                    ?.takeIf { it.isJsonArray }
                    ?.asJsonArray
                    ?.map { item ->
                        val menuId = item.readInt("menu_item_id")
                        val quantity = item.readInt("quantity")
                        val unitPrice = item.readString("unit_price")
                        val totalPrice = item.readString("total_price")

                        "Menu #$menuId | Qty: $quantity | Unit: ₹$unitPrice | Total: ₹$totalPrice"
                    } ?: emptyList()
            } catch (e: Exception) {
                emptyList()
            }

            ProviderOrderItem(
                id = json.readInt("id"),
                userId = json.readInt("user_id"),
                tableId = json.readNullableInt("table_id"),
                orderType = json.readString("order_type"),
                status = json.readString("status"),
                paymentStatus = json.readString("payment_status"),
                subtotal = json.readString("subtotal"),
                discount = json.readString("discount"),
                gst = json.readString("gst"),
                serviceCharge = json.readString("service_charge"),
                grandTotal = json.readString("grand_total"),
                specialInstructions = json.readString("special_instructions"),
                createdAt = json.readString("created_at"),
                items = orderItems
            )
        } catch (e: Exception) {
            null
        }
    }
}

@Composable
fun ProviderOrdersScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var orders by remember {
        mutableStateOf<List<ProviderOrderItem>>(emptyList())
    }

    var isLoading by remember { mutableStateOf(true) }
    var updatingId by remember { mutableStateOf<Int?>(null) }
    var message by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    suspend fun loadOrders() {
        isLoading = true
        message = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                message = "Login required. Please login again."
                orders = emptyList()
                return
            }

            val response = RetrofitClient.api.getProviderFoodOrders(
                authorization = "Bearer $token"
            )

            if (response.isSuccessful) {
                orders = parseProviderOrders(response.body())
            } else {
                message = "Orders load failed: HTTP ${response.code()}"
            }

        } catch (e: Exception) {
            message = "Network error: ${e.message ?: "Please try again"}"
        } finally {
            isLoading = false
        }
    }

    suspend fun changeOrderStatus(orderId: Int, newStatus: String) {
        updatingId = orderId
        message = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                message = "Login required"
                return
            }

            val request = JsonObject().apply {
                addProperty("status", newStatus)
            }

            val response = RetrofitClient.api.updateFoodOrderStatus(
                authorization = "Bearer $token",
                orderId = orderId,
                request = request
            )

            if (response.isSuccessful) {
                message = "Order #$orderId updated: $newStatus"
                loadOrders()
            } else {
                val error = response.errorBody()?.string()
                message = "Update failed: HTTP ${response.code()} ${error ?: ""}"
            }

        } catch (e: Exception) {
            message = "Update error: ${e.message ?: "Please try again"}"
        } finally {
            updatingId = null
        }
    }

    LaunchedEffect(Unit) {
        loadOrders()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        Text(
            text = "Provider Orders",
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
                    scope.launch { loadOrders() }
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

            orders.isEmpty() -> {
                Text(
                    text = "No restaurant orders found.",
                    modifier = Modifier.padding(top = 24.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            else -> {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    items(orders, key = { it.id }) { order ->

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
                                    text = "Order #${order.id}",
                                    style = MaterialTheme.typography.titleLarge,
                                    fontWeight = FontWeight.Bold
                                )

                                Text("Customer ID: ${order.userId}")
                                Text("Order Type: ${order.orderType}")

                                order.tableId?.let {
                                    Text("Table ID: $it")
                                }

                                Text(
                                    text = "Status: ${order.status.uppercase()}",
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary,
                                    modifier = Modifier.padding(top = 8.dp)
                                )

                                Text("Payment: ${order.paymentStatus}")

                                Spacer(modifier = Modifier.height(8.dp))

                                Text(
                                    text = "Order Items",
                                    fontWeight = FontWeight.Bold
                                )

                                if (order.items.isEmpty()) {
                                    Text("No item details available.")
                                } else {
                                    order.items.forEach {
                                        Text(it)
                                    }
                                }

                                Spacer(modifier = Modifier.height(8.dp))

                                Text("Subtotal: ₹${order.subtotal}")
                                Text("Discount: ₹${order.discount}")
                                Text("GST: ₹${order.gst}")
                                Text("Service Charge: ₹${order.serviceCharge}")

                                Text(
                                    text = "Grand Total: ₹${order.grandTotal}",
                                    style = MaterialTheme.typography.titleMedium,
                                    fontWeight = FontWeight.Bold
                                )

                                if (order.specialInstructions.isNotBlank()) {
                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text("Instructions: ${order.specialInstructions}")
                                }

                                Text(
                                    text = "Created: ${order.createdAt}",
                                    style = MaterialTheme.typography.bodySmall
                                )

                                Spacer(modifier = Modifier.height(12.dp))

                                if (updatingId == order.id) {
                                    CircularProgressIndicator()
                                } else {
                                    when (order.status.lowercase()) {

                                        "pending" -> {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        changeOrderStatus(order.id, "accepted")
                                                    }
                                                }
                                            ) {
                                                Text("Accept Order")
                                            }
                                        }

                                        "accepted" -> {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        changeOrderStatus(order.id, "preparing")
                                                    }
                                                }
                                            ) {
                                                Text("Start Preparing")
                                            }
                                        }

                                        "preparing" -> {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        changeOrderStatus(order.id, "ready")
                                                    }
                                                }
                                            ) {
                                                Text("Mark Ready")
                                            }
                                        }

                                        "ready" -> {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        changeOrderStatus(order.id, "served")
                                                    }
                                                }
                                            ) {
                                                Text("Mark Served")
                                            }
                                        }

                                        "served" -> {
                                            Button(
                                                onClick = {
                                                    scope.launch {
                                                        changeOrderStatus(order.id, "completed")
                                                    }
                                                }
                                            ) {
                                                Text("Complete Order")
                                            }
                                        }

                                        "completed" -> {
                                            Text(
                                                text = "Order completed.",
                                                color = MaterialTheme.colorScheme.primary
                                            )
                                        }

                                        "cancelled" -> {
                                            Text(
                                                text = "Order cancelled.",
                                                color = MaterialTheme.colorScheme.error
                                            )
                                        }

                                        else -> {
                                            Text("No status action available.")
                                        }
                                    }

                                    if (
                                        order.status.lowercase() !in
                                        listOf("completed", "cancelled") &&
                                        order.paymentStatus.lowercase() != "paid"
                                    ) {
                                        Spacer(modifier = Modifier.height(6.dp))

                                        OutlinedButton(
                                            onClick = {
                                                scope.launch {
                                                    changeOrderStatus(order.id, "cancelled")
                                                }
                                            }
                                        ) {
                                            Text("Cancel Order")
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
