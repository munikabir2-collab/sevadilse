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

private data class ProviderServiceUi(
    val id: Int,
    val name: String,
    val price: String,
    val capacity: String,
    val totalUnits: String,
    val durationMinutes: String
)

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
    var services by remember { mutableStateOf<List<ProviderServiceUi>>(emptyList()) }

    var loading by remember { mutableStateOf(false) }
    var checking by remember { mutableStateOf(true) }
    var message by remember { mutableStateOf("") }
    var messageIsError by remember { mutableStateOf(false) }

    var showServiceDialog by remember { mutableStateOf(false) }
    var editingService by remember { mutableStateOf<ProviderServiceUi?>(null) }
    var deletingService by remember { mutableStateOf<ProviderServiceUi?>(null) }

    var serviceName by remember { mutableStateOf("") }
    var servicePrice by remember { mutableStateOf("") }
    var serviceCapacity by remember { mutableStateOf("1") }
    var serviceTotalUnits by remember { mutableStateOf("1") }
    var serviceDuration by remember { mutableStateOf("") }

    fun setStatus(text: String, error: Boolean = false) {
        message = text
        messageIsError = error
    }

    fun readServices(json: com.google.gson.JsonObject?): List<ProviderServiceUi> {
        val array = json?.getAsJsonArray("services") ?: return emptyList()
        return array.mapNotNull { element ->
            runCatching {
                val item = element.asJsonObject
                ProviderServiceUi(
                    id = item.get("id")?.asInt ?: return@mapNotNull null,
                    name = item.get("name")?.asString.orEmpty(),
                    price = item.get("price")?.asString
                        ?: item.get("price")?.asDouble?.toString().orEmpty(),
                    capacity = item.get("capacity")?.asInt?.toString() ?: "1",
                    totalUnits = item.get("total_units")?.asInt?.toString() ?: "1",
                    durationMinutes = item.get("duration_minutes")
                        ?.takeUnless { it.isJsonNull }?.asInt?.toString().orEmpty()
                )
            }.getOrNull()
        }
    }

    fun fillProvider(json: com.google.gson.JsonObject) {
        name = json.get("name")?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        category = json.get("category")?.takeUnless { it.isJsonNull }?.asString ?: "hotel"
        city = json.get("city")?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        description = json.get("description")?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        specialization = json.get("specialization")?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        address = json.get("address")?.takeUnless { it.isJsonNull }?.asString.orEmpty()
        services = readServices(json)
    }

    suspend fun loadProvider(id: Int, token: String) {
        checking = true
        try {
            val response = RetrofitClient.api.getProviderRaw(id)
            if (response.isSuccessful) {
                val body = response.body()
                val obj = body?.takeIf { it.isJsonObject }?.asJsonObject
                if (obj != null) {
                    providerId = id
                    fillProvider(obj)
                    setStatus("Provider profile load ho gayi.")
                } else {
                    setStatus("Provider profile ka response valid nahi hai.", true)
                }
            } else {
                setStatus("Provider profile load nahi hui. HTTP ${response.code()}", true)
            }
        } catch (e: Exception) {
            setStatus("Profile load error: ${e.localizedMessage ?: "Request failed"}", true)
        } finally {
            checking = false
        }
    }

    LaunchedEffect(Unit) {
        checking = true
        try {
            val savedProviderId = tokenManager.providerId.first()
            val accessToken = tokenManager.token.first()
            val currentUserId = tokenManager.userId.first()

            if (!accessToken.isNullOrBlank() && savedProviderId != null) {
                loadProvider(savedProviderId, accessToken)
                return@LaunchedEffect
            }

            if (!accessToken.isNullOrBlank() && currentUserId != null) {
                val response = RetrofitClient.api.getProviders(ownerId = currentUserId)
                if (response.isSuccessful) {
                    val profiles = response.body()?.takeIf { it.isJsonArray }?.asJsonArray
                    val existing = profiles?.firstOrNull()?.takeIf { it.isJsonObject }?.asJsonObject
                    val existingId = existing?.get("id")?.takeUnless { it.isJsonNull }?.asInt
                    if (existingId != null) {
                        val admin = tokenManager.isAdmin.first()
                        tokenManager.saveToken(
                            accessToken = accessToken,
                            userId = currentUserId,
                            providerId = existingId,
                            isProvider = true,
                            isAdmin = admin
                        )
                        providerId = existingId
                        loadProvider(existingId, accessToken)
                        return@LaunchedEffect
                    } else {
                        setStatus("Is account ki Provider Profile nahi mili.")
                    }
                } else {
                    setStatus("Provider Profile load nahi hui. HTTP ${response.code()}", true)
                }
            } else {
                setStatus("Login session nahi mila. Dobara login karein.", true)
            }
        } catch (e: Exception) {
            setStatus("Profile load error: ${e.localizedMessage ?: "Request failed"}", true)
        } finally {
            checking = false
        }
    }

    fun saveProviderProfile() {
        scope.launch {
            loading = true
            setStatus("")
            try {
                val token = tokenManager.token.first()
                val userId = tokenManager.userId.first()
                val admin = tokenManager.isAdmin.first()
                if (token.isNullOrBlank() || userId == null) {
                    setStatus("Login session nahi mila. Dobara login karein.", true)
                    return@launch
                }
                if (name.isBlank() || city.isBlank()) {
                    setStatus("Provider Name aur City required hain.", true)
                    return@launch
                }

                val body = JsonObject().apply {
                    addProperty("name", name.trim())
                    addProperty("category", category)
                    addProperty("city", city.trim())
                    addProperty("description", description.trim())
                    addProperty("specialization", specialization.trim())
                    addProperty("address", address.trim())
                }

                val currentId = providerId
                if (currentId == null) {
                    val response = RetrofitClient.api.createProvider(
                        authorization = "Bearer $token",
                        request = body
                    )
                    if (response.isSuccessful) {
                        val result = response.body()
                        val newId = result?.takeIf { it.isJsonObject }
                            ?.asJsonObject?.get("id")?.takeUnless { it.isJsonNull }?.asInt
                        if (newId != null) {
                            tokenManager.saveToken(
                                accessToken = token,
                                userId = userId,
                                providerId = newId,
                                isProvider = true,
                                isAdmin = admin
                            )
                            providerId = newId
                            setStatus("Provider profile create ho gayi. ID: $newId")
                            loadProvider(newId, token)
                        } else {
                            setStatus("Profile create hui, lekin response mein Provider ID nahi mili.", true)
                        }
                    } else {
                        setStatus(
                            when (response.code()) {
                                401 -> "Session expire ho gaya. Dobara login karein."
                                409 -> "Is account ka Provider profile pehle se bana hua hai."
                                422 -> "Details backend schema ke according valid nahi hain."
                                else -> "Server error ${response.code()}: ${response.errorBody()?.string().orEmpty()}"
                            },
                            true
                        )
                    }
                } else {
                    val response = RetrofitClient.api.updateProviderRaw(
                        authorization = "Bearer $token",
                        providerId = currentId,
                        request = body
                    )
                    if (response.isSuccessful) {
                        setStatus("Provider profile successfully update ho gayi.")
                        loadProvider(currentId, token)
                    } else {
                        setStatus(
                            "Profile update nahi hui. HTTP ${response.code()}: ${response.errorBody()?.string().orEmpty()}",
                            true
                        )
                    }
                }
            } catch (e: Exception) {
                setStatus("Error: ${e.localizedMessage ?: "Request failed"}", true)
            } finally {
                loading = false
            }
        }
    }

    fun resetServiceForm(service: ProviderServiceUi?) {
        editingService = service
        serviceName = service?.name.orEmpty()
        servicePrice = service?.price.orEmpty()
        serviceCapacity = service?.capacity ?: "1"
        serviceTotalUnits = service?.totalUnits ?: "1"
        serviceDuration = service?.durationMinutes.orEmpty()
        showServiceDialog = true
    }

    fun saveService() {
        val currentId = providerId
        if (currentId == null) {
            setStatus("Pehle Provider Profile create karein.", true)
            return
        }
        val price = servicePrice.toDoubleOrNull()
        val capacity = serviceCapacity.toIntOrNull()
        val totalUnits = serviceTotalUnits.toIntOrNull()
        val duration = serviceDuration.toIntOrNull()

        if (serviceName.isBlank() || price == null || price < 0 ||
            capacity == null || capacity < 1 || totalUnits == null || totalUnits < 1
        ) {
            setStatus("Service name, valid price, capacity aur total units enter karein.", true)
            return
        }

        scope.launch {
            loading = true
            try {
                val token = tokenManager.token.first()
                if (token.isNullOrBlank()) {
                    setStatus("Login session nahi mila. Dobara login karein.", true)
                    return@launch
                }
                val body = JsonObject().apply {
                    addProperty("name", serviceName.trim())
                    addProperty("price", price)
                    addProperty("capacity", capacity)
                    addProperty("total_units", totalUnits)
                    if (duration != null && duration > 0) {
                        addProperty("duration_minutes", duration)
                    } else {
                        add("duration_minutes", com.google.gson.JsonNull.INSTANCE)
                    }
                }

                val serviceId = editingService?.id
                val response = if (serviceId == null) {
                    RetrofitClient.api.addProviderServiceRaw(
                        authorization = "Bearer $token",
                        providerId = currentId,
                        request = body
                    )
                } else {
                    RetrofitClient.api.updateProviderServiceRaw(
                        authorization = "Bearer $token",
                        providerId = currentId,
                        serviceId = serviceId,
                        request = body
                    )
                }

                if (response.isSuccessful) {
                    showServiceDialog = false
                    setStatus(if (serviceId == null) "Service add ho gayi." else "Service update ho gayi.")
                    loadProvider(currentId, token)
                } else {
                    setStatus(
                        "Service save nahi hui. HTTP ${response.code()}: ${response.errorBody()?.string().orEmpty()}",
                        true
                    )
                }
            } catch (e: Exception) {
                setStatus("Service error: ${e.localizedMessage ?: "Request failed"}", true)
            } finally {
                loading = false
            }
        }
    }

    fun deleteService(service: ProviderServiceUi) {
        val currentId = providerId ?: return
        scope.launch {
            loading = true
            try {
                val token = tokenManager.token.first()
                if (token.isNullOrBlank()) {
                    setStatus("Login session nahi mila. Dobara login karein.", true)
                    return@launch
                }
                val response = RetrofitClient.api.deleteProviderServiceRaw(
                    authorization = "Bearer $token",
                    providerId = currentId,
                    serviceId = service.id
                )
                if (response.isSuccessful) {
                    deletingService = null
                    setStatus("Service delete ho gayi.")
                    loadProvider(currentId, token)
                } else {
                    setStatus(
                        "Service delete nahi hui. HTTP ${response.code()}: ${response.errorBody()?.string().orEmpty()}",
                        true
                    )
                }
            } catch (e: Exception) {
                setStatus("Delete error: ${e.localizedMessage ?: "Request failed"}", true)
            } finally {
                loading = false
            }
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
            if (providerId == null) "Become a Service Provider" else "Manage Provider Profile",
            style = MaterialTheme.typography.headlineSmall
        )
        Text("Apne business ya professional profile ki details yahan manage karein.")

        if (checking) {
            CircularProgressIndicator()
        } else {
            if (providerId != null) {
                Text(
                    "Provider ID: $providerId",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            OutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = { Text("Business / Provider Name *") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Text("Select Category *")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
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
                label = { Text("Description") },
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
                label = { Text("Address") },
                modifier = Modifier.fillMaxWidth()
            )

            Button(
                onClick = { saveProviderProfile() },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(if (providerId == null) "Create Provider Profile" else "Update Provider Profile")
            }

            if (providerId != null) {
                HorizontalDivider()
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("My Services", style = MaterialTheme.typography.titleLarge)
                    TextButton(
                        onClick = { resetServiceForm(null) },
                        enabled = !loading
                    ) {
                        Text("＋ Add Service")
                    }
                }

                if (services.isEmpty()) {
                    Text("Abhi koi service add nahi hai.")
                } else {
                    services.forEach { service ->
                        Card(modifier = Modifier.fillMaxWidth()) {
                            Column(
                                modifier = Modifier.padding(14.dp),
                                verticalArrangement = Arrangement.spacedBy(5.dp)
                            ) {
                                Text(service.name, style = MaterialTheme.typography.titleMedium)
                                Text("Price: ₹${service.price}")
                                Text("Capacity: ${service.capacity} | Total Units: ${service.totalUnits}")
                                if (service.durationMinutes.isNotBlank()) {
                                    Text("Duration: ${service.durationMinutes} minutes")
                                }
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    TextButton(
                                        onClick = { resetServiceForm(service) },
                                        enabled = !loading
                                    ) { Text("Edit") }
                                    TextButton(
                                        onClick = { deletingService = service },
                                        enabled = !loading,
                                        colors = ButtonDefaults.textButtonColors(
                                            contentColor = MaterialTheme.colorScheme.error
                                        )
                                    ) { Text("Delete") }
                                }
                            }
                        }
                    }
                }
            }
        }

        if (message.isNotBlank()) {
            Text(
                message,
                color = if (messageIsError) MaterialTheme.colorScheme.error
                else MaterialTheme.colorScheme.primary
            )
        }

        OutlinedButton(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Back")
        }
    }

    if (showServiceDialog) {
        AlertDialog(
            onDismissRequest = { if (!loading) showServiceDialog = false },
            title = { Text(if (editingService == null) "Add Service" else "Edit Service") },
            text = {
                Column(
                    modifier = Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = serviceName,
                        onValueChange = { serviceName = it },
                        label = { Text("Service Name *") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = servicePrice,
                        onValueChange = { servicePrice = it },
                        label = { Text("Price (₹) *") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = serviceCapacity,
                        onValueChange = { serviceCapacity = it },
                        label = { Text("Capacity *") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = serviceTotalUnits,
                        onValueChange = { serviceTotalUnits = it },
                        label = { Text("Total Units *") },
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = serviceDuration,
                        onValueChange = { serviceDuration = it },
                        label = { Text("Duration (minutes, optional)") },
                        singleLine = true
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = { saveService() }, enabled = !loading) {
                    Text("Save")
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { showServiceDialog = false },
                    enabled = !loading
                ) { Text("Cancel") }
            }
        )
    }

    deletingService?.let { service ->
        AlertDialog(
            onDismissRequest = { deletingService = null },
            title = { Text("Delete Service?") },
            text = { Text("Kya aap '${service.name}' service delete karna chahte hain?") },
            confirmButton = {
                TextButton(
                    onClick = { deleteService(service) },
                    enabled = !loading,
                    colors = ButtonDefaults.textButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) { Text("Delete") }
            },
            dismissButton = {
                TextButton(onClick = { deletingService = null }) { Text("Cancel") }
            }
        )
    }
}
