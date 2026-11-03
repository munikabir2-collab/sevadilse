package com.example.servicehub

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonArray
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import retrofit2.Response


/* ============================================================
   SMALL HELPERS
   ============================================================ */

private fun JsonElement?.asArr(): JsonArray =
    if (this != null && this.isJsonArray) this.asJsonArray else JsonArray()

private fun JsonArray.objects(): List<JsonObject> =
    this.mapNotNull { if (it.isJsonObject) it.asJsonObject else null }

private fun JsonObject.text(key: String): String =
    if (has(key) && !get(key).isJsonNull) get(key).asString else ""

private fun errText(r: Response<*>): String {
    val body = try {
        r.errorBody()?.string()?.take(250) ?: ""
    } catch (_: Exception) {
        ""
    }
    return "Error ${r.code()}: $body"
}

private suspend fun currentProviderId(tokenManager: TokenManager): Int? =
    tokenManager.providerId.first()?.toString()?.toIntOrNull()

@Composable
private fun Field(
    label: String,
    value: String,
    onChange: (String) -> Unit,
    numeric: Boolean = false
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(
            keyboardType = if (numeric) KeyboardType.Number else KeyboardType.Text
        ),
        modifier = Modifier
            .fillMaxWidth()
            .padding(top = 8.dp)
    )
}

@Composable
private fun ScreenHeader(title: String, subtitle: String) {
    Text(
        text = title,
        style = MaterialTheme.typography.headlineSmall,
        fontWeight = FontWeight.Bold
    )
    Text(
        text = subtitle,
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(top = 4.dp, bottom = 12.dp)
    )
}


/* ============================================================
   SERVICES
   GET  providers/{id}               -> services list
   POST providers/{id}/services      -> add service (token needed)
   ============================================================ */

@Composable
fun ServicesScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()

    var services by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var saving by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var reload by remember { mutableStateOf(0) }

    var name by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var capacity by remember { mutableStateOf("1") }
    var duration by remember { mutableStateOf("") }
    var units by remember { mutableStateOf("1") }

    LaunchedEffect(reload) {
        loading = true
        try {
            val pid = currentProviderId(tokenManager)
            if (pid == null) {
                message = "Provider ID nahi mila. Logout karke dobara login karein."
            } else {
                val r = RetrofitClient.api.getProviderRaw(pid)
                if (r.isSuccessful) {
                    val obj = r.body()
                    services =
                        if (obj != null && obj.isJsonObject)
                            obj.asJsonObject.get("services").asArr().objects()
                        else emptyList()
                } else {
                    message = errText(r)
                }
            }
        } catch (e: Exception) {
            message = "Network error: ${e.message ?: ""}"
        }
        loading = false
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {

        item {
            Spacer(Modifier.height(12.dp))
            ScreenHeader("🛎️ Services", "Aapki listed services")
        }

        if (loading) {
            item { CircularProgressIndicator(Modifier.size(28.dp)) }
        } else if (services.isEmpty()) {
            item { Text("Abhi koi service nahi hai. Neeche se jodein.") }
        }

        items(services) { s ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text(
                        s.text("name"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text("₹${s.text("price")}  •  capacity ${s.text("capacity")}  •  units ${s.text("total_units")}")
                    if (s.text("duration_minutes").isNotBlank()) {
                        Text("Duration: ${s.text("duration_minutes")} min")
                    }
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text("Nayi service jodein", fontWeight = FontWeight.Bold)
                    Field("Naam *", name, { name = it })
                    Field("Price (₹) *", price, { price = it }, numeric = true)
                    Field("Capacity", capacity, { capacity = it }, numeric = true)
                    Field("Duration (minutes, optional)", duration, { duration = it }, numeric = true)
                    Field("Total units", units, { units = it }, numeric = true)

                    Button(
                        onClick = {
                            val p = price.toDoubleOrNull()
                            if (name.isBlank() || p == null) {
                                message = "Naam aur sahi price zaroori hai."
                                return@Button
                            }
                            scope.launch {
                                saving = true
                                message = ""
                                try {
                                    val pid = currentProviderId(tokenManager)
                                    val token = tokenManager.token.first()
                                    if (pid == null || token.isNullOrBlank()) {
                                        message = "Login dobara karein."
                                    } else {
                                        val body = JsonObject().apply {
                                            addProperty("name", name.trim())
                                            addProperty("price", p)
                                            capacity.toIntOrNull()?.let { addProperty("capacity", it) }
                                            duration.toIntOrNull()?.let { addProperty("duration_minutes", it) }
                                            units.toIntOrNull()?.let { addProperty("total_units", it) }
                                        }
                                        val r = RetrofitClient.api.addProviderServiceRaw(
                                            "Bearer $token", pid, body
                                        )
                                        if (r.isSuccessful) {
                                            message = "Service add ho gayi."
                                            name = ""
                                            price = ""
                                            duration = ""
                                            reload++
                                        } else {
                                            message = errText(r)
                                        }
                                    }
                                } catch (e: Exception) {
                                    message = "Network error: ${e.message ?: ""}"
                                }
                                saving = false
                            }
                        },
                        enabled = !saving,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                    ) {
                        Text(if (saving) "Saving..." else "Add service")
                    }
                }
            }
        }

        if (message.isNotBlank()) {
            item { Text(message, color = MaterialTheme.colorScheme.primary) }
        }

        item {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
            ) { Text("← Back to Dashboard") }
        }
    }
}


/* ============================================================
   HOTEL ROOMS
   GET    hotels/{provider_id}/rooms
   POST   hotels/{provider_id}/rooms
   PATCH  hotels/rooms/{room_id}
   DELETE hotels/rooms/{room_id}
   ============================================================ */

@Composable
fun HotelRoomsScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()

    var rooms by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var saving by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var reload by remember { mutableStateOf(0) }

    var name by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var capacity by remember { mutableStateOf("2") }
    var units by remember { mutableStateOf("1") }

    // edit dialog state
    var editing by remember { mutableStateOf<JsonObject?>(null) }
    var eName by remember { mutableStateOf("") }
    var ePrice by remember { mutableStateOf("") }
    var eCapacity by remember { mutableStateOf("") }
    var eUnits by remember { mutableStateOf("") }

    LaunchedEffect(reload) {
        loading = true
        try {
            val pid = currentProviderId(tokenManager)
            if (pid == null) {
                message = "Provider ID nahi mila. Logout karke dobara login karein."
            } else {
                val r = RetrofitClient.api.getHotelRooms(pid)
                if (r.isSuccessful) {
                    rooms = r.body().asArr().objects()
                } else {
                    message = errText(r)
                }
            }
        } catch (e: Exception) {
            message = "Network error: ${e.message ?: ""}"
        }
        loading = false
    }

    if (editing != null) {
        AlertDialog(
            onDismissRequest = { editing = null },
            title = { Text("Room edit karein") },
            text = {
                Column {
                    Field("Naam", eName, { eName = it })
                    Field("Price (₹)", ePrice, { ePrice = it }, numeric = true)
                    Field("Capacity", eCapacity, { eCapacity = it }, numeric = true)
                    Field("Total units", eUnits, { eUnits = it }, numeric = true)
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val id = editing?.text("id")?.toIntOrNull()
                    editing = null
                    if (id != null) {
                        scope.launch {
                            try {
                                val body = JsonObject().apply {
                                    if (eName.isNotBlank()) addProperty("name", eName.trim())
                                    ePrice.toDoubleOrNull()?.let { addProperty("price", it) }
                                    eCapacity.toIntOrNull()?.let { addProperty("capacity", it) }
                                    eUnits.toIntOrNull()?.let { addProperty("total_units", it) }
                                }
                                val r = RetrofitClient.api.updateHotelRoom(id, body)
                                message = if (r.isSuccessful) "Room update ho gaya." else errText(r)
                                if (r.isSuccessful) reload++
                            } catch (e: Exception) {
                                message = "Network error: ${e.message ?: ""}"
                            }
                        }
                    }
                }) { Text("Save") }
            },
            dismissButton = {
                TextButton(onClick = { editing = null }) { Text("Cancel") }
            }
        )
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {

        item {
            Spacer(Modifier.height(12.dp))
            ScreenHeader("🏨 Hotel Rooms", "Aapke hotel ke rooms")
        }

        if (loading) {
            item { CircularProgressIndicator(Modifier.size(28.dp)) }
        } else if (rooms.isEmpty()) {
            item { Text("Abhi koi room nahi hai. Neeche se jodein.") }
        }

        items(rooms) { r ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text(
                        r.text("name"),
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                    Text("₹${r.text("price")}  •  guests ${r.text("capacity")}  •  rooms ${r.text("total_units")}")

                    Row(
                        modifier = Modifier.padding(top = 8.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedButton(onClick = {
                            eName = r.text("name")
                            ePrice = r.text("price")
                            eCapacity = r.text("capacity")
                            eUnits = r.text("total_units")
                            editing = r
                        }) { Text("Edit") }

                        TextButton(onClick = {
                            val id = r.text("id").toIntOrNull()
                            if (id != null) {
                                scope.launch {
                                    try {
                                        val res = RetrofitClient.api.deleteHotelRoom(id)
                                        message =
                                            if (res.isSuccessful) "Room delete ho gaya." else errText(res)
                                        if (res.isSuccessful) reload++
                                    } catch (e: Exception) {
                                        message = "Network error: ${e.message ?: ""}"
                                    }
                                }
                            }
                        }) { Text("Delete") }
                    }
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text("Naya room jodein", fontWeight = FontWeight.Bold)
                    Field("Room ka naam *", name, { name = it })
                    Field("Price per night (₹) *", price, { price = it }, numeric = true)
                    Field("Guests capacity", capacity, { capacity = it }, numeric = true)
                    Field("Kitne rooms (units)", units, { units = it }, numeric = true)

                    Button(
                        onClick = {
                            val p = price.toDoubleOrNull()
                            if (name.isBlank() || p == null) {
                                message = "Naam aur sahi price zaroori hai."
                                return@Button
                            }
                            scope.launch {
                                saving = true
                                message = ""
                                try {
                                    val pid = currentProviderId(tokenManager)
                                    if (pid == null) {
                                        message = "Login dobara karein."
                                    } else {
                                        val body = JsonObject().apply {
                                            addProperty("name", name.trim())
                                            addProperty("price", p)
                                            capacity.toIntOrNull()?.let { addProperty("capacity", it) }
                                            units.toIntOrNull()?.let { addProperty("total_units", it) }
                                        }
                                        val r = RetrofitClient.api.createHotelRoom(pid, body)
                                        if (r.isSuccessful) {
                                            message = "Room add ho gaya."
                                            name = ""
                                            price = ""
                                            reload++
                                        } else {
                                            message = errText(r)
                                        }
                                    }
                                } catch (e: Exception) {
                                    message = "Network error: ${e.message ?: ""}"
                                }
                                saving = false
                            }
                        },
                        enabled = !saving,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                    ) {
                        Text(if (saving) "Saving..." else "Add room")
                    }
                }
            }
        }

        if (message.isNotBlank()) {
            item { Text(message, color = MaterialTheme.colorScheme.primary) }
        }

        item {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
            ) { Text("← Back to Dashboard") }
        }
    }
}


/* ============================================================
   DOCTOR SLOTS (Appointments)
   GET  doctors/{provider_id}/slots
   POST doctors/{provider_id}/slots   {service_id, start_time, end_time}
   service_id aapki Services list se aata hai.
   ============================================================ */

@Composable
fun DoctorSlotsScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()

    var slots by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var services by remember { mutableStateOf<List<JsonObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var saving by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var reload by remember { mutableStateOf(0) }

    var serviceId by remember { mutableStateOf("") }
    var start by remember { mutableStateOf("") }
    var end by remember { mutableStateOf("") }

    LaunchedEffect(reload) {
        loading = true
        try {
            val pid = currentProviderId(tokenManager)
            if (pid == null) {
                message = "Provider ID nahi mila. Logout karke dobara login karein."
            } else {
                val rs = RetrofitClient.api.getDoctorSlots(pid)
                if (rs.isSuccessful) slots = rs.body().asArr().objects()
                else message = errText(rs)

                val rp = RetrofitClient.api.getProviderRaw(pid)
                if (rp.isSuccessful) {
                    val obj = rp.body()
                    services =
                        if (obj != null && obj.isJsonObject)
                            obj.asJsonObject.get("services").asArr().objects()
                        else emptyList()
                    if (serviceId.isBlank() && services.size == 1) {
                        serviceId = services[0].text("id")
                    }
                }
            }
        } catch (e: Exception) {
            message = "Network error: ${e.message ?: ""}"
        }
        loading = false
    }

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {

        item {
            Spacer(Modifier.height(12.dp))
            ScreenHeader("🩺 Appointment Slots", "Aapke available time slots")
        }

        if (loading) {
            item { CircularProgressIndicator(Modifier.size(28.dp)) }
        } else if (slots.isEmpty()) {
            item { Text("Abhi koi slot nahi hai. Neeche se jodein.") }
        }

        items(slots) { s ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text(
                        "${s.text("start_time")}  →  ${s.text("end_time")}",
                        fontWeight = FontWeight.Bold
                    )
                    Text("Service #${s.text("service_id")}")
                    Text(
                        if (s.text("is_available") == "true") "✅ Available" else "⛔ Booked",
                        color = MaterialTheme.colorScheme.primary
                    )
                }
            }
        }

        item {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(Modifier.padding(14.dp)) {
                    Text("Naya slot jodein", fontWeight = FontWeight.Bold)

                    if (services.isEmpty()) {
                        Text(
                            "Pehle Services mein ek service jodein (slot ek service se juda hota hai).",
                            color = MaterialTheme.colorScheme.error,
                            modifier = Modifier.padding(top = 6.dp)
                        )
                    } else {
                        Text(
                            "Service chunein (ID likhein): " +
                                    services.joinToString { "${it.text("id")}=${it.text("name")}" },
                            style = MaterialTheme.typography.bodySmall,
                            modifier = Modifier.padding(top = 6.dp)
                        )
                    }

                    Field("Service ID *", serviceId, { serviceId = it }, numeric = true)
                    Field("Start (2026-11-05T10:00:00) *", start, { start = it })
                    Field("End (2026-11-05T10:30:00) *", end, { end = it })

                    Button(
                        onClick = {
                            val sid = serviceId.toIntOrNull()
                            if (sid == null || start.isBlank() || end.isBlank()) {
                                message = "Service ID, start aur end time zaroori hain."
                                return@Button
                            }
                            scope.launch {
                                saving = true
                                message = ""
                                try {
                                    val pid = currentProviderId(tokenManager)
                                    if (pid == null) {
                                        message = "Login dobara karein."
                                    } else {
                                        val body = JsonObject().apply {
                                            addProperty("service_id", sid)
                                            addProperty("start_time", start.trim())
                                            addProperty("end_time", end.trim())
                                        }
                                        val r = RetrofitClient.api.createDoctorSlot(pid, body)
                                        if (r.isSuccessful) {
                                            message = "Slot add ho gaya."
                                            start = ""
                                            end = ""
                                            reload++
                                        } else {
                                            message = errText(r)
                                        }
                                    }
                                } catch (e: Exception) {
                                    message = "Network error: ${e.message ?: ""}"
                                }
                                saving = false
                            }
                        },
                        enabled = !saving,
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                    ) {
                        Text(if (saving) "Saving..." else "Add slot")
                    }
                }
            }
        }

        if (message.isNotBlank()) {
            item { Text(message, color = MaterialTheme.colorScheme.primary) }
        }

        item {
            OutlinedButton(
                onClick = onBack,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
            ) { Text("← Back to Dashboard") }
        }
    }
}