package com.example.servicehub

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
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
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonArray
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private data class DeliveryStaffItem(
    val id: Int,
    val name: String,
    val email: String,
    val phone: String,
    val role: String,
    val area: String,
    val isActive: Boolean
)

private fun JsonArray.toDeliveryStaffList(): List<DeliveryStaffItem> {
    return mapNotNull { element ->
        if (!element.isJsonObject) {
            return@mapNotNull null
        }

        val item = element.asJsonObject

        fun stringValue(key: String): String {
            val value = item.get(key) ?: return ""
            return if (value.isJsonNull) "" else value.asString
        }

        DeliveryStaffItem(
            id = item.get("id")?.takeUnless { it.isJsonNull }?.asInt ?: 0,
            name = stringValue("name"),
            email = stringValue("email"),
            phone = stringValue("phone"),
            role = stringValue("role"),
            area = stringValue("area"),
            isActive = item.get("is_active")
                ?.takeUnless { it.isJsonNull }?.asBoolean ?: false
        )
    }
}

private fun deliveryStaffError(code: Int): String {
    return when (code) {
        401 -> "Session expire ho gaya. Dobara login karein."
        403 -> "Admin permission nahi hai."
        404 -> "Is email ka customer account nahi mila. Pehle user se signup karwayein."
        409 -> "Yeh user pehle se Delivery Staff ke roop mein registered hai."
        422 -> "Email, role ya area ki details valid nahi hain."
        else -> "Request failed: HTTP $code"
    }
}

@Composable
fun DeliveryStaffScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var email by remember { mutableStateOf("") }
    var area by remember { mutableStateOf("") }
    var selectedRole by remember { mutableStateOf("delivery_boy") }

    var staffList by remember { mutableStateOf<List<DeliveryStaffItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isSaving by remember { mutableStateOf(false) }
    var updatingStaffId by remember { mutableStateOf<Int?>(null) }

    var errorMessage by remember { mutableStateOf("") }
    var successMessage by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    suspend fun loadStaff() {
        isLoading = true
        errorMessage = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                errorMessage = "Login session nahi mila. Dobara login karein."
                staffList = emptyList()
                return
            }

            val response = RetrofitClient.api.getDeliveryStaff(
                authorization = "Bearer $token"
            )

            if (response.isSuccessful) {
                val array = response.body()?.asJsonArray

                if (array == null) {
                    errorMessage = "Server se valid staff list nahi mili."
                    staffList = emptyList()
                } else {
                    staffList = array.toDeliveryStaffList()
                }
            } else {
                errorMessage = deliveryStaffError(response.code())
                staffList = emptyList()
            }
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message ?: "Please try again"}"
            staffList = emptyList()
        } finally {
            isLoading = false
        }
    }

    suspend fun registerStaff() {
        errorMessage = ""
        successMessage = ""

        if (email.isBlank() || !email.contains("@")) {
            errorMessage = "Valid registered customer email enter karein."
            return
        }

        if (area.isBlank()) {
            errorMessage = "Staff ka area enter karna zaroori hai."
            return
        }

        isSaving = true

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                errorMessage = "Login session nahi mila. Dobara login karein."
                return
            }

            val request = JsonObject().apply {
                addProperty("email", email.trim())
                addProperty("role", selectedRole)
                addProperty("area", area.trim())
            }

            val response = RetrofitClient.api.createDeliveryStaff(
                authorization = "Bearer $token",
                request = request
            )

            if (response.isSuccessful) {
                email = ""
                successMessage = "Delivery Staff successfully register ho gaya."
                loadStaff()
                successMessage = "Delivery Staff successfully register ho gaya."
            } else {
                errorMessage = deliveryStaffError(response.code())
            }
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message ?: "Please try again"}"
        } finally {
            isSaving = false
        }
    }

    suspend fun changeStaffStatus(staff: DeliveryStaffItem) {
        errorMessage = ""
        successMessage = ""
        updatingStaffId = staff.id

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                errorMessage = "Login session nahi mila. Dobara login karein."
                return
            }

            val request = JsonObject().apply {
                addProperty("is_active", !staff.isActive)
            }

            val response = RetrofitClient.api.updateDeliveryStaffActive(
                authorization = "Bearer $token",
                staffId = staff.id,
                request = request
            )

            if (response.isSuccessful) {
                successMessage = if (staff.isActive) {
                    "Staff account inactive kar diya gaya."
                } else {
                    "Staff account active kar diya gaya."
                }
                loadStaff()
            } else {
                errorMessage = deliveryStaffError(response.code())
            }
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message ?: "Please try again"}"
        } finally {
            updatingStaffId = null
        }
    }

    LaunchedEffect(tokenManager) {
        loadStaff()
    }

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text(
            text = "Delivery Staff Management",
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Text(
            text = "Register delivery boys and sub-admins, and manage their access.",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        OutlinedButton(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("← Back to Admin")
        }

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(18.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.surface
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Text(
                    text = "Register New Staff",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "User ka account pehle Customer App mein isi email se registered hona chahiye.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Registered Customer Email") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                OutlinedTextField(
                    value = area,
                    onValueChange = { area = it },
                    label = { Text("Assigned Area") },
                    placeholder = { Text("Example: Kankarbagh") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )

                Text(
                    text = "Select Staff Role",
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.SemiBold
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    if (selectedRole == "delivery_boy") {
                        Button(
                            onClick = { selectedRole = "delivery_boy" },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Delivery Boy")
                        }
                    } else {
                        OutlinedButton(
                            onClick = { selectedRole = "delivery_boy" },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Delivery Boy")
                        }
                    }

                    if (selectedRole == "sub_admin") {
                        Button(
                            onClick = { selectedRole = "sub_admin" },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Sub-admin")
                        }
                    } else {
                        OutlinedButton(
                            onClick = { selectedRole = "sub_admin" },
                            modifier = Modifier.weight(1f)
                        ) {
                            Text("Sub-admin")
                        }
                    }
                }

                Text(
                    text = if (selectedRole == "delivery_boy") {
                        "Delivery Boy: Assigned area ke delivery orders handle karega."
                    } else {
                        "Sub-admin: Apne assigned area ke delivery boys aur orders manage karega."
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )

                Button(
                    onClick = { scope.launch { registerStaff() } },
                    enabled = !isSaving,
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    if (isSaving) {
                        CircularProgressIndicator(
                            modifier = Modifier.width(18.dp),
                            strokeWidth = 2.dp
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }

                    Text(if (isSaving) "Registering..." else "Register Staff")
                }
            }
        }

        if (errorMessage.isNotBlank()) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Text(
                    text = errorMessage,
                    modifier = Modifier.padding(14.dp),
                    color = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        }

        if (successMessage.isNotBlank()) {
            Text(
                text = successMessage,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.SemiBold
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Registered Staff",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Total: ${staffList.size}",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            OutlinedButton(
                onClick = { scope.launch { loadStaff() } },
                enabled = !isLoading && !isSaving && updatingStaffId == null
            ) {
                Text("↻ Refresh")
            }
        }

        if (isLoading) {
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                CircularProgressIndicator()
                Spacer(modifier = Modifier.height(8.dp))
                Text("Loading delivery staff...")
            }
        } else if (staffList.isEmpty() && errorMessage.isBlank()) {
            Text(
                text = "Abhi koi Delivery Staff registered nahi hai.",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        staffList.forEach { staff ->
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        text = staff.name.ifBlank { staff.email.ifBlank { "Staff #${staff.id}" } },
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )

                    if (staff.email.isNotBlank()) {
                        Text("Email: ${staff.email}")
                    }

                    if (staff.phone.isNotBlank()) {
                        Text("Phone: ${staff.phone}")
                    }

                    Text(
                        text = "Role: ${
                            when (staff.role) {
                                "delivery_boy" -> "Delivery Boy"
                                "sub_admin" -> "Sub-admin"
                                else -> staff.role
                            }
                        }"
                    )

                    Text("Area: ${staff.area}")

                    Text(
                        text = if (staff.isActive) "Status: ACTIVE" else "Status: INACTIVE",
                        color = if (staff.isActive) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.error
                        },
                        fontWeight = FontWeight.Bold
                    )

                    OutlinedButton(
                        onClick = {
                            scope.launch { changeStaffStatus(staff) }
                        },
                        enabled = updatingStaffId == null && !isSaving,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        if (updatingStaffId == staff.id) {
                            CircularProgressIndicator(
                                modifier = Modifier.width(18.dp),
                                strokeWidth = 2.dp
                            )
                            Spacer(modifier = Modifier.width(8.dp))
                        }

                        Text(
                            when {
                                updatingStaffId == staff.id -> "Updating..."
                                staff.isActive -> "Deactivate Staff"
                                else -> "Activate Staff"
                            }
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(12.dp))
    }
}