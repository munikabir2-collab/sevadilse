
package com.example.servicehub

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProviderSetupScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf("") }
    var city by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var specialization by remember { mutableStateOf("") }
    var address by remember { mutableStateOf("") }

    var category by remember { mutableStateOf("hotel") }
    var providerId by remember { mutableStateOf<Int?>(null) }

    var loading by remember { mutableStateOf(false) }
    var checking by remember { mutableStateOf(true) }
    var message by remember { mutableStateOf("") }

   LaunchedEffect(Unit) {
    checking = true

    try {
        // Saved provider ID pehle check karein
        val savedProviderId = tokenManager.providerId.first()

        if (savedProviderId != null) {
            providerId = savedProviderId
        } else {
            // Login user details
            val accessToken = tokenManager.token.first()
            val currentUserId = tokenManager.userId.first()
            val admin = tokenManager.isAdmin.first()

            if (!accessToken.isNullOrBlank() && currentUserId != null) {

                // Backend se existing provider profile search karein
                val response = RetrofitClient.api.getProviders(
                    ownerId = currentUserId
                )

                if (response.isSuccessful) {
                    val profiles = response.body()?.asJsonArray

                    val existingProfile = profiles?.firstOrNull()

                    val existingId = existingProfile
                        ?.asJsonObject
                        ?.get("id")
                        ?.asInt

                    if (existingId != null) {

                        // Existing Provider ID save karein
                        tokenManager.saveToken(
                            accessToken = accessToken,
                            userId = currentUserId,
                            providerId = existingId,
                            isProvider = true,
                            isAdmin = admin
                        )

                        providerId = existingId
                        message = "Existing Provider Profile load ho gayi."
                    } else {
                        message = "Is account ki Provider Profile nahi mili."
                    }
                } else {
                    message = "Provider Profile load nahi hui. HTTP ${response.code()}"
                }
            } else {
                message = "Login session nahi mila. Dobara login karein."
            }
        }
    } catch (e: Exception) {
        message = "Profile load error: ${e.message}"
    } finally {
        checking = false
    }
}

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(
            "Provider Setup",
            style = MaterialTheme.typography.headlineMedium
        )

        Text(
            "Apne business ya professional profile ki details enter karein."
        )

        if (checking) {
            CircularProgressIndicator()
            return@Column
        }

        if (providerId != null) {
            Text(
                "Provider profile pehle se bana hua hai.",
                color = MaterialTheme.colorScheme.primary
            )

            Text("Provider ID: $providerId")

            Text(
                "Profile editing ke liye backend mein abhi update API available nahi hai."
            )

            Button(
                onClick = onBack,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Back to Dashboard")
            }

            return@Column
        }

        OutlinedTextField(
            value = name,
            onValueChange = { name = it },
            label = { Text("Business / Provider Name *") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        Text("Select Category *")

        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            listOf("hotel", "restaurant", "doctor").forEach { item ->
                FilterChip(
                    selected = category == item,
                    onClick = { category = item },
                    label = { Text(item.replaceFirstChar { it.uppercase() }) }
                )
            }
        }

        OutlinedTextField(
            value = city,
            onValueChange = { city = it },
            label = { Text("City *") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )

        OutlinedTextField(
            value = description,
            onValueChange = { description = it },
            label = { Text("Description (Optional)") },
            modifier = Modifier.fillMaxWidth()
        )

        if (category == "doctor") {
            OutlinedTextField(
                value = specialization,
                onValueChange = { specialization = it },
                label = { Text("Specialization") },
                modifier = Modifier.fillMaxWidth()
            )
        }

        OutlinedTextField(
            value = address,
            onValueChange = { address = it },
            label = { Text("Address (Optional)") },
            modifier = Modifier.fillMaxWidth()
        )

        if (message.isNotBlank()) {
            Text(
                message,
                color = MaterialTheme.colorScheme.error
            )
        }

        Button(
            onClick = {
                if (name.isBlank() || city.isBlank()) {
                    message = "Name aur City required hain."
                    return@Button
                }

                scope.launch {
                    loading = true
                    message = ""

                    try {
                        val token = tokenManager.token.first()
                        val userId = tokenManager.userId.first()
                        val admin = tokenManager.isAdmin.first()

                        if (token.isNullOrBlank() || userId == null) {
                            message = "Login session nahi mila. Dobara login karein."
                            loading = false
                            return@launch
                        }

                        val body = JsonObject().apply {
                            addProperty("name", name.trim())
                            addProperty("category", category)
                            addProperty("city", city.trim())

                            if (description.isNotBlank()) {
                                addProperty("description", description.trim())
                            }

                            if (category == "doctor" && specialization.isNotBlank()) {
                                addProperty("specialization", specialization.trim())
                            }

                            if (address.isNotBlank()) {
                                addProperty("address", address.trim())
                            }
                        }

                        val response = RetrofitClient.api.createProvider(
                            authorization = "Bearer $token",
                            request = body
                        )

                        if (response.isSuccessful) {
                            val result = response.body()

                            val newId = result
                                ?.takeIf { it.isJsonObject }
                                ?.asJsonObject
                                ?.get("id")
                                ?.takeIf { it.isJsonPrimitive }
                                ?.asInt

                            if (newId != null) {
                                tokenManager.saveToken(
                                    accessToken = token,
                                    userId = userId,
                                    providerId = newId,
                                    isProvider = true,
                                    isAdmin = admin
                                )

                                providerId = newId
                                message = "Provider profile successfully create ho gaya. ID: $newId"
                            } else {
                                message = "Profile create hua, lekin response mein Provider ID nahi mili. Login response verify karein."
                            }
                        } else {
                            message = when (response.code()) {
                                401 -> "Session expire ho gaya. Dobara login karein."
                                409 -> "Is account ka Provider profile pehle se bana hua hai. Login response mein provider_id verify karein."
                                422 -> "Kuch details backend schema ke according valid nahi hain."
                                else -> "Server error ${response.code()}: ${response.errorBody()?.string().orEmpty()}"
                            }
                        }
                    } catch (e: Exception) {
                        message = "Error: ${e.localizedMessage ?: "Request failed"}"
                    } finally {
                        loading = false
                    }
                }
            },
            enabled = !loading,
            modifier = Modifier.fillMaxWidth()
        ) {
            if (loading) {
                CircularProgressIndicator(
                    modifier = Modifier.size(20.dp),
                    strokeWidth = 2.dp
                )
            } else {
                Text("Create Provider Profile")
            }
        }

        OutlinedButton(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Back to Dashboard")
        }
    }
}
