package com.example.servicehub

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
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
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

/**
 * Admin module -> backend resource.
 * Backend: GET /admin/{users|providers|bookings|orders|payments}
 */
private fun adminResource(title: String): String? = when (title) {
    "User Management" -> "users"
    "Provider Management" -> "providers"
    "Booking Management" -> "bookings"
    "Restaurant Orders" -> "orders"
    "Payments" -> "payments"
    else -> null
}

@Composable
fun AdminListScreen(
    tokenManager: TokenManager,
    title: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val resource = adminResource(title)
    val scope = rememberCoroutineScope()
    val pageSize = 30

    var items by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var total by remember { mutableStateOf(0) }
    var loading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }

    fun load(reset: Boolean) {
        if (resource == null) return
        scope.launch {
            loading = true
            message = ""
            try {
                val token = tokenManager.token.first()
                if (token.isNullOrBlank()) {
                    message = "Login dobara karein."
                } else {
                    val start = if (reset) 0 else items.size
                    val r = RetrofitClient.api.getAdminList(
                        "Bearer $token", resource, pageSize, start
                    )
                    if (r.isSuccessful) {
                        val body = r.body()
                        if (body != null && body.isJsonObject) {
                            val obj = body.asJsonObject
                            val arr: JsonArray =
                                if (obj.get("items")?.isJsonArray == true) obj.getAsJsonArray("items")
                                else JsonArray()
                            val page = arr.mapNotNull {
                                if (it.isJsonObject) it.asJsonObject else null
                            }
                            total = obj.get("total")?.takeIf { !it.isJsonNull }?.asInt ?: page.size
                            items = if (reset) page else items + page
                        }
                    } else {
                        message = when (r.code()) {
                            401 -> "Session expire ho gaya. Dobara login karein."
                            403 -> "Admin permission nahi hai. Admin account se login karein."
                            404 -> "Ye endpoint server par abhi deploy nahi hua."
                            else -> "Error ${r.code()}"
                        }
                    }
                }
            } catch (e: Exception) {
                message = "Network error: ${e.message ?: ""}"
            }
            loading = false
        }
    }

    LaunchedEffect(title) {
        items = emptyList()
        total = 0
        load(true)
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {

        item {
            Spacer(Modifier.height(12.dp))
            Text(
                text = title,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold
            )
            if (resource != null) {
                Text(
                    text = "Total: $total",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp, bottom = 8.dp)
                )
                OutlinedButton(onClick = { load(true) }) { Text("↻ Refresh") }
            }
        }

        if (resource == null) {
            item {
                Text(
                    "$title ke liye abhi backend list endpoint nahi hai. " +
                            "Payout status ke liye Payments (provider) screen use karein."
                )
            }
        }

        if (loading) {
            item { CircularProgressIndicator(Modifier.size(28.dp)) }
        } else if (resource != null && items.isEmpty() && message.isBlank()) {
            item { Text("Koi record nahi mila.") }
        }

        items(items) { o ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(14.dp)
            ) {
                Column(Modifier.padding(12.dp)) {
                    for ((key, value) in o.entrySet()) {
                        val text = when {
                            value.isJsonNull -> "-"
                            value.isJsonPrimitive -> value.asString
                            else -> value.toString()
                        }
                        Text("$key: $text", style = MaterialTheme.typography.bodyMedium)
                    }
                }
            }
        }

        if (!loading && items.isNotEmpty() && items.size < total) {
            item {
                Button(
                    onClick = { load(false) },
                    modifier = Modifier.fillMaxWidth()
                ) { Text("Aur dikhayein (${items.size}/$total)") }
            }
        }

        if (message.isNotBlank()) {
            item { Text(message, color = MaterialTheme.colorScheme.error) }
        }

        item {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
            ) { Text("← Back") }
        }
    }
}