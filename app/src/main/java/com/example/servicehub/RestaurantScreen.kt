package com.example.servicehub

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonElement
import com.google.gson.JsonObject
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private data class RestaurantMenuItem(
    val id: Int,
    val name: String,
    val category: String,
    val description: String,
    val price: Double,
    val available: Boolean
)

private data class RestaurantTableItem(
    val id: Int,
    val number: String,
    val capacity: Int,
    val status: String,
    val description: String
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun RestaurantScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit
) {
    val scope = rememberCoroutineScope()

    var providerId by remember { mutableStateOf<Int?>(null) }
    var authToken by remember { mutableStateOf<String?>(null) }

    var selectedTab by remember { mutableStateOf(0) }
    var menuItems by remember { mutableStateOf<List<RestaurantMenuItem>>(emptyList()) }
    var tables by remember { mutableStateOf<List<RestaurantTableItem>>(emptyList()) }

    var loading by remember { mutableStateOf(true) }
    var saving by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf("") }
    var infoMessage by remember { mutableStateOf("") }

    var showMenuDialog by remember { mutableStateOf(false) }
    var editingMenu by remember { mutableStateOf<RestaurantMenuItem?>(null) }

    var showTableDialog by remember { mutableStateOf(false) }
    var editingTable by remember { mutableStateOf<RestaurantTableItem?>(null) }

    var deleteMenu by remember { mutableStateOf<RestaurantMenuItem?>(null) }
    var deleteTable by remember { mutableStateOf<RestaurantTableItem?>(null) }

    BackHandler(onBack = onBack)

    fun parseMenu(element: JsonElement): List<RestaurantMenuItem> {
        if (!element.isJsonArray) return emptyList()

        return element.asJsonArray.mapNotNull { item ->
            if (!item.isJsonObject) return@mapNotNull null

            val obj = item.asJsonObject

            RestaurantMenuItem(
                id = obj.get("id")?.asInt ?: return@mapNotNull null,
                name = obj.get("name")?.asString ?: "",
                category = obj.get("category")?.takeUnless { it.isJsonNull }?.asString ?: "",
                description = obj.get("description")?.takeUnless { it.isJsonNull }?.asString ?: "",
                price = obj.get("price")?.asDouble ?: 0.0,
                available = obj.get("is_available")?.asBoolean ?: true
            )
        }
    }

    fun parseTables(element: JsonElement): List<RestaurantTableItem> {
        if (!element.isJsonArray) return emptyList()

        return element.asJsonArray.mapNotNull { item ->
            if (!item.isJsonObject) return@mapNotNull null

            val obj = item.asJsonObject

            RestaurantTableItem(
                id = obj.get("id")?.asInt ?: return@mapNotNull null,
                number = obj.get("table_number")?.asString ?: "",
                capacity = obj.get("capacity")?.asInt ?: 2,
                status = obj.get("status")?.asString ?: "available",
                description = obj.get("description")?.takeUnless { it.isJsonNull }?.asString ?: ""
            )
        }
    }

    fun loadData() {
        scope.launch {
            loading = true
            errorMessage = ""

            try {
                val savedToken = tokenManager.token.first()
                val savedProviderId = tokenManager.providerId.first()

                if (savedToken.isNullOrBlank()) {
                    errorMessage = "Login session नहीं मिला। दोबारा login करें।"
                    loading = false
                    return@launch
                }

                if (savedProviderId == null) {
                    errorMessage = "Provider ID नहीं मिली। Provider account से login करें।"
                    loading = false
                    return@launch
                }

                authToken = "Bearer $savedToken"
                providerId = savedProviderId

                val menuResponse =
                    RetrofitClient.api.getRestaurantMenu(savedProviderId)

                val tableResponse =
                    RetrofitClient.api.getRestaurantTables(savedProviderId)

                if (menuResponse.isSuccessful) {
                    menuItems = menuResponse.body()?.let { parseMenu(it) } ?: emptyList()
                } else {
                    errorMessage = "Menu load नहीं हुआ: ${menuResponse.code()}"
                }

                if (tableResponse.isSuccessful) {
                    tables = tableResponse.body()?.let { parseTables(it) } ?: emptyList()
                } else {
                    errorMessage = "Tables load नहीं हुए: ${tableResponse.code()}"
                }

            } catch (e: Exception) {
                errorMessage = e.message ?: "Data load करने में समस्या हुई।"
            }

            loading = false
        }
    }

    fun saveMenu(
        item: RestaurantMenuItem?,
        name: String,
        category: String,
        description: String,
        price: String,
        available: Boolean
    ) {
        val id = providerId
        val authorization = authToken

        if (id == null || authorization == null) {
            errorMessage = "Provider या login जानकारी उपलब्ध नहीं है।"
            return
        }

        val parsedPrice = price.toDoubleOrNull()
        if (name.isBlank() || parsedPrice == null || parsedPrice <= 0) {
            errorMessage = "सही नाम और कीमत भरें।"
            return
        }

        scope.launch {
            saving = true
            errorMessage = ""

            try {
                val request = JsonObject().apply {
                    addProperty("name", name.trim())
                    addProperty("category", category.trim().ifBlank { null })
                    addProperty("description", description.trim().ifBlank { null })
                    addProperty("price", parsedPrice)
                    addProperty("is_available", available)
                }

                val response = if (item == null) {
                    RetrofitClient.api.createMenuItem(authorization, id, request)
                } else {
                    RetrofitClient.api.updateMenuItem(authorization, item.id, request)
                }

                if (response.isSuccessful) {
                    showMenuDialog = false
                    editingMenu = null
                    infoMessage = if (item == null) "Menu item जोड़ा गया।" else "Menu item अपडेट हुआ।"
                    loadData()
                } else {
                    errorMessage = "Menu save नहीं हुआ: ${response.code()} ${response.errorBody()?.string().orEmpty()}"
                }
            } catch (e: Exception) {
                errorMessage = e.message ?: "Menu save करने में समस्या हुई।"
            }

            saving = false
        }
    }

    fun saveTable(
        item: RestaurantTableItem?,
        number: String,
        capacity: String,
        status: String,
        description: String
    ) {
        val id = providerId
        val authorization = authToken

        if (id == null || authorization == null) {
            errorMessage = "Provider या login जानकारी उपलब्ध नहीं है।"
            return
        }

        val parsedCapacity = capacity.toIntOrNull()
        if (number.isBlank() || parsedCapacity == null || parsedCapacity < 1) {
            errorMessage = "Table number और सही capacity भरें।"
            return
        }

        scope.launch {
            saving = true
            errorMessage = ""

            try {
                val request = JsonObject().apply {
                    addProperty("table_number", number.trim())
                    addProperty("capacity", parsedCapacity)
                    addProperty("description", description.trim().ifBlank { null })

                    if (item != null) {
                        addProperty("status", status)
                    }
                }

                val response = if (item == null) {
                    RetrofitClient.api.createRestaurantTable(authorization, id, request)
                } else {
                    RetrofitClient.api.updateRestaurantTable(authorization, item.id, request)
                }

                if (response.isSuccessful) {
                    showTableDialog = false
                    editingTable = null
                    infoMessage = if (item == null) "Table जोड़ी गई।" else "Table अपडेट हुई।"
                    loadData()
                } else {
                    errorMessage = "Table save नहीं हुई: ${response.code()} ${response.errorBody()?.string().orEmpty()}"
                }
            } catch (e: Exception) {
                errorMessage = e.message ?: "Table save करने में समस्या हुई।"
            }

            saving = false
        }
    }

    fun removeMenu(item: RestaurantMenuItem) {
        val authorization = authToken ?: return

        scope.launch {
            saving = true
            try {
                val response =
                    RetrofitClient.api.deleteMenuItem(authorization, item.id)

                if (response.isSuccessful) {
                    deleteMenu = null
                    infoMessage = "Menu item delete हुआ।"
                    loadData()
                } else {
                    errorMessage = "Delete नहीं हुआ: ${response.code()} ${response.errorBody()?.string().orEmpty()}"
                }
            } catch (e: Exception) {
                errorMessage = e.message ?: "Delete करने में समस्या हुई।"
            }
            saving = false
        }
    }

    fun removeTable(item: RestaurantTableItem) {
        val authorization = authToken ?: return

        scope.launch {
            saving = true
            try {
                val response =
                    RetrofitClient.api.deleteRestaurantTable(authorization, item.id)

                if (response.isSuccessful) {
                    deleteTable = null
                    infoMessage = "Table delete हुई।"
                    loadData()
                } else {
                    errorMessage = "Delete नहीं हुआ: ${response.code()} ${response.errorBody()?.string().orEmpty()}"
                }
            } catch (e: Exception) {
                errorMessage = e.message ?: "Delete करने में समस्या हुई।"
            }
            saving = false
        }
    }

    LaunchedEffect(Unit) {
        loadData()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Restaurant Dashboard") },
                navigationIcon = {
                    TextButton(onClick = onBack) {
                        Text("Back")
                    }
                },
                actions = {
                    TextButton(onClick = { loadData() }) {
                        Text("Refresh")
                    }
                }
            )
        }
    ) { padding ->

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(12.dp)
        ) {

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Button(
                    onClick = { selectedTab = 0 },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Menu (${menuItems.size})")
                }

                Button(
                    onClick = { selectedTab = 1 },
                    modifier = Modifier.weight(1f)
                ) {
                    Text("Tables (${tables.size})")
                }
            }

            Spacer(Modifier.height(12.dp))

            if (errorMessage.isNotBlank()) {
                Text(
                    text = errorMessage,
                    color = MaterialTheme.colorScheme.error
                )
                Spacer(Modifier.height(8.dp))
            }

            if (infoMessage.isNotBlank()) {
                Text(
                    text = infoMessage,
                    color = MaterialTheme.colorScheme.primary
                )
                Spacer(Modifier.height(8.dp))
            }

            if (loading) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    CircularProgressIndicator()
                }
            } else if (selectedTab == 0) {

                Button(
                    onClick = {
                        editingMenu = null
                        showMenuDialog = true
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("+ Add Menu Item")
                }

                Spacer(Modifier.height(8.dp))

                if (menuItems.isEmpty()) {
                    Text("अभी कोई Menu Item उपलब्ध नहीं है।")
                }

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(menuItems, key = { it.id }) { item ->
                        Card(
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                Text(
                                    item.name,
                                    style = MaterialTheme.typography.titleMedium
                                )

                                Text("Category: ${item.category.ifBlank { "Other" }}")
                                Text("Price: ₹${item.price}")
                                Text("Description: ${item.description.ifBlank { "—" }}")
                                Text(if (item.available) "Available" else "Unavailable")

                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedButton(
                                        onClick = {
                                            editingMenu = item
                                            showMenuDialog = true
                                        }
                                    ) {
                                        Text("Edit")
                                    }

                                    OutlinedButton(
                                        onClick = { deleteMenu = item }
                                    ) {
                                        Text("Delete")
                                    }
                                }
                            }
                        }
                    }
                }

            } else {

                Button(
                    onClick = {
                        editingTable = null
                        showTableDialog = true
                    },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("+ Add Table")
                }

                Spacer(Modifier.height(8.dp))

                if (tables.isEmpty()) {
                    Text("अभी कोई Table उपलब्ध नहीं है।")
                }

                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(tables, key = { it.id }) { item ->
                        Card(
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(Modifier.padding(12.dp)) {
                                Text(
                                    "Table ${item.number}",
                                    style = MaterialTheme.typography.titleMedium
                                )

                                Text("Capacity: ${item.capacity}")
                                Text("Status: ${item.status}")
                                Text("Description: ${item.description.ifBlank { "—" }}")

                                Row(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    OutlinedButton(
                                        onClick = {
                                            editingTable = item
                                            showTableDialog = true
                                        }
                                    ) {
                                        Text("Edit")
                                    }

                                    OutlinedButton(
                                        onClick = { deleteTable = item }
                                    ) {
                                        Text("Delete")
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showMenuDialog) {
        MenuEditorDialog(
            item = editingMenu,
            saving = saving,
            onDismiss = {
                showMenuDialog = false
                editingMenu = null
            },
            onSave = { name, category, description, price, available ->
                saveMenu(editingMenu, name, category, description, price, available)
            }
        )
    }

    if (showTableDialog) {
        TableEditorDialog(
            item = editingTable,
            saving = saving,
            onDismiss = {
                showTableDialog = false
                editingTable = null
            },
            onSave = { number, capacity, status, description ->
                saveTable(editingTable, number, capacity, status, description)
            }
        )
    }

    deleteMenu?.let { item ->
        AlertDialog(
            onDismissRequest = { deleteMenu = null },
            title = { Text("Delete Menu Item?") },
            text = { Text("क्या आप '${item.name}' को delete करना चाहते हैं?") },
            confirmButton = {
                TextButton(onClick = { removeMenu(item) }) {
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteMenu = null }) {
                    Text("Cancel")
                }
            }
        )
    }

    deleteTable?.let { item ->
        AlertDialog(
            onDismissRequest = { deleteTable = null },
            title = { Text("Delete Table?") },
            text = { Text("क्या आप Table ${item.number} को delete करना चाहते हैं?") },
            confirmButton = {
                TextButton(onClick = { removeTable(item) }) {
                    Text("Delete")
                }
            },
            dismissButton = {
                TextButton(onClick = { deleteTable = null }) {
                    Text("Cancel")
                }
            }
        )
    }
}

@Composable
private fun MenuEditorDialog(
    item: RestaurantMenuItem?,
    saving: Boolean,
    onDismiss: () -> Unit,
    onSave: (String, String, String, String, Boolean) -> Unit
) {
    var name by remember(item?.id) { mutableStateOf(item?.name ?: "") }
    var category by remember(item?.id) { mutableStateOf(item?.category ?: "") }
    var description by remember(item?.id) { mutableStateOf(item?.description ?: "") }
    var price by remember(item?.id) { mutableStateOf(item?.price?.toString() ?: "") }
    var available by remember(item?.id) { mutableStateOf(item?.available ?: true) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (item == null) "Add Menu Item" else "Edit Menu Item") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(name, { name = it }, label = { Text("Name") })
                OutlinedTextField(category, { category = it }, label = { Text("Category") })
                OutlinedTextField(description, { description = it }, label = { Text("Description") })
                OutlinedTextField(price, { price = it }, label = { Text("Price") })
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Available")
                    Spacer(Modifier.width(12.dp))
                    Switch(checked = available, onCheckedChange = { available = it })
                }
            }
        },
        confirmButton = {
            TextButton(
                enabled = !saving,
                onClick = { onSave(name, category, description, price, available) }
            ) {
                Text(if (saving) "Saving..." else "Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}

@Composable
private fun TableEditorDialog(
    item: RestaurantTableItem?,
    saving: Boolean,
    onDismiss: () -> Unit,
    onSave: (String, String, String, String) -> Unit
) {
    var number by remember(item?.id) { mutableStateOf(item?.number ?: "") }
    var capacity by remember(item?.id) { mutableStateOf(item?.capacity?.toString() ?: "2") }
    var status by remember(item?.id) { mutableStateOf(item?.status ?: "available") }
    var description by remember(item?.id) { mutableStateOf(item?.description ?: "") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(if (item == null) "Add Table" else "Edit Table") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(number, { number = it }, label = { Text("Table Number") })
                OutlinedTextField(capacity, { capacity = it }, label = { Text("Capacity") })
                OutlinedTextField(description, { description = it }, label = { Text("Description") })

                if (item != null) {
                    Text("Table Status")
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        listOf("available", "occupied", "inactive").forEach { value ->
                            FilterChip(
                                selected = status == value,
                                onClick = { status = value },
                                label = { Text(value) }
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(
                enabled = !saving,
                onClick = { onSave(number, capacity, status, description) }
            ) {
                Text(if (saving) "Saving..." else "Save")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}