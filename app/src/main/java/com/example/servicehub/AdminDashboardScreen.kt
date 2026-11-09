
package com.example.servicehub

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.unit.sp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import com.google.gson.JsonObject
import java.text.NumberFormat
import java.util.Locale
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

private data class AdminDashboardStats(
    val totalUsers: Int,
    val totalProviderUsers: Int,
    val totalProviders: Int,
    val totalBookings: Int,
    val totalRestaurantOrders: Int,
    val paidTransactions: Int,
    val paidRevenue: Double,
    val platformCommission: Double,
    val providerEarnings: Double
)

private data class AdminSection(
    val icon: String,
    val title: String,
    val description: String
)

private fun JsonObject.intOrZero(key: String): Int {
    val value = get(key) ?: return 0
    return if (value.isJsonNull) 0 else value.asInt
}

private fun JsonObject.doubleOrZero(key: String): Double {
    val value = get(key) ?: return 0.0
    return if (value.isJsonNull) 0.0 else value.asDouble
}

private fun formatInr(amount: Double): String {
    return NumberFormat.getCurrencyInstance(Locale("en", "IN"))
        .format(amount)
}

@Composable
fun AdminDashboardScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    onSectionClick: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    var stats by remember { mutableStateOf<AdminDashboardStats?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    suspend fun loadStats() {
        isLoading = true
        errorMessage = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                errorMessage = "Login session nahi mila. Dobara login karein."
                stats = null
                return
            }

            val response = RetrofitClient.api.getAdminDashboardStats(
                authorization = "Bearer $token"
            )

            if (response.isSuccessful) {
                val json = response.body()?.asJsonObject

                if (json == null) {
                    errorMessage = "Server se dashboard data nahi mila."
                    stats = null
                } else {
                    stats = AdminDashboardStats(
                        totalUsers = json.intOrZero("total_users"),
                        totalProviderUsers = json.intOrZero("total_provider_users"),
                        totalProviders = json.intOrZero("total_providers"),
                        totalBookings = json.intOrZero("total_bookings"),
                        totalRestaurantOrders = json.intOrZero("total_restaurant_orders"),
                        paidTransactions = json.intOrZero("paid_transactions"),
                        paidRevenue = json.doubleOrZero("paid_revenue_inr"),
                        platformCommission = json.doubleOrZero("platform_commission_inr"),
                        providerEarnings = json.doubleOrZero("provider_earnings_inr")
                    )
                }
            } else {
                errorMessage = when (response.code()) {
                    401 -> "Session expire ho gaya. Dobara login karein."
                    403 -> "Admin permission nahi hai. Admin account se login karein."
                    else -> "Dashboard load failed: HTTP ${response.code()}"
                }
                stats = null
            }
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message ?: "Please try again"}"
        } finally {
            isLoading = false
        }
    }

    LaunchedEffect(tokenManager) {
        loadStats()
    }

    val sections = listOf(
        AdminSection("US", "User Management", "Manage customer accounts and users"),
        AdminSection("PV", "Provider Management", "Hotels, restaurants and doctors"),
        AdminSection("BK", "Booking Management", "Appointments and customer bookings"),
        AdminSection("RO", "Restaurant Orders", "View and manage restaurant orders"),
        AdminSection("₹", "Payments", "Online payments, COD and transactions"),
        AdminSection("PO", "Provider Payouts", "Payout onboarding and account status"),
        AdminSection("AN", "Reports & Analytics", "Revenue, commission and earnings"),
        AdminSection("⚙", "Admin Settings", "Platform administration")
    )

    Column(
        modifier = modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        // Dashboard header
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text(
                    text = "SERVICEHUB  /  ADMIN",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "Admin Dashboard",
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Text(
                    text = "Manage your platform, users and business operations.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = "ADMINISTRATOR",
                    style = MaterialTheme.typography.labelSmall,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }
        }

        // Overview heading and refresh
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Platform Overview",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold
                )
                Text(
                    text = "Live dashboard statistics",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }

            OutlinedButton(
                onClick = { scope.launch { loadStats() } },
                enabled = !isLoading
            ) {
                Text("↻ Refresh")
            }
        }

        // Loading state
        if (isLoading && stats == null) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp)
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    CircularProgressIndicator()
                    Spacer(modifier = Modifier.height(12.dp))
                    Text("Loading admin statistics...")
                }
            }
        }

        // Error state
        if (errorMessage.isNotBlank()) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.errorContainer
                )
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = errorMessage,
                        color = MaterialTheme.colorScheme.onErrorContainer
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedButton(
                        onClick = { scope.launch { loadStats() } },
                        enabled = !isLoading
                    ) {
                        Text("Try Again")
                    }
                }
            }
        }

        // Statistics cards
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            AdminMetricCard(
                title = "Total Users",
                value = stats?.totalUsers?.toString() ?: "0",
                icon = "US",
                modifier = Modifier.weight(1f)
            )
            AdminMetricCard(
                title = "Provider Users",
                value = stats?.totalProviderUsers?.toString() ?: "0",
                icon = "PV",
                modifier = Modifier.weight(1f)
            )
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            AdminMetricCard(
                title = "Total Providers",
                value = stats?.totalProviders?.toString() ?: "0",
                icon = "PR",
                modifier = Modifier.weight(1f)
            )
            AdminMetricCard(
                title = "Bookings",
                value = stats?.totalBookings?.toString() ?: "0",
                icon = "BK",
                modifier = Modifier.weight(1f)
            )
        }

        // Financial overview
        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                text = "Financial Overview",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(20.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.secondaryContainer
                )
            ) {
                Column(
                    modifier = Modifier.padding(18.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "Payment & Earnings",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSecondaryContainer
                    )

                    Spacer(modifier = Modifier.height(2.dp))

                    AdminInfoRow(
                        "Paid Revenue",
                        stats?.let { formatInr(it.paidRevenue) } ?: formatInr(0.0)
                    )
                    AdminInfoRow(
                        "Platform Commission",
                        stats?.let { formatInr(it.platformCommission) } ?: formatInr(0.0)
                    )
                    AdminInfoRow(
                        "Provider Earnings",
                        stats?.let { formatInr(it.providerEarnings) } ?: formatInr(0.0)
                    )
                    AdminInfoRow(
                        "Paid Transactions",
                        stats?.paidTransactions?.toString() ?: "0"
                    )
                    AdminInfoRow(
                        "Restaurant Orders",
                        stats?.totalRestaurantOrders?.toString() ?: "0"
                    )
                }
            }
        }

        // Administration modules
        Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text(
                text = "Administration Modules",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            Text(
                text = "Select a module to manage your platform",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            sections.chunked(2).forEach { sectionRow ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    sectionRow.forEach { section ->
                        AdminModuleCard(
                            section = section,
                            modifier = Modifier.weight(1f),
                            onClick = { onSectionClick(section.title) }
                        )
                    }

                    if (sectionRow.size == 1) {
                        Spacer(modifier = Modifier.weight(1f))
                    }
                }
            }
        }

        Button(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(14.dp)
        ) {
            Text("Back")
        }

        Spacer(modifier = Modifier.height(12.dp))
    }
}

@Composable
private fun AdminMetricCard(
    title: String,
    value: String,
    icon: String,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = icon,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )

            Text(
                text = value,
                fontSize = 27.sp,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )

            Text(
                text = title,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onPrimaryContainer
            )
        }
    }
}

@Composable
private fun AdminModuleCard(
    section: AdminSection,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    Card(
        modifier = modifier
            .clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            Card(
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {
                Text(
                    text = section.icon,
                    modifier = Modifier.padding(
                        horizontal = 12.dp,
                        vertical = 9.dp
                    ),
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.primary
                )
            }

            Text(
                text = section.title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.Bold
            )

            Text(
                text = section.description,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Text(
                text = "Open  →",
                style = MaterialTheme.typography.labelMedium,
                fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.primary
            )
        }
    }
}

@Composable
private fun AdminInfoRow(
    title: String,
    value: String
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = title,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSecondaryContainer
        )

        Spacer(modifier = Modifier.width(8.dp))

        Text(
            text = value,
            fontWeight = FontWeight.SemiBold,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSecondaryContainer
        )
    }
}
@Composable
fun AdminModuleLandingScreen(
    title: String,
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    var items by remember(title) {
        mutableStateOf<List<JsonObject>>(emptyList())
    }
    var total by remember(title) {
        mutableStateOf(0)
    }
    var isLoading by remember(title) {
        mutableStateOf(true)
    }
    var errorMessage by remember(title) {
        mutableStateOf("")
    }

    val scope = rememberCoroutineScope()

    val resource = when (title) {
        "User Management" -> "users"
        "Provider Management" -> "provider-management"
        "Booking Management" -> "bookings"
        "Restaurant Orders" -> "orders"
        "Payments" -> "payments"
        "Reports & Analytics" -> "earnings"
        else -> null
    }

    suspend fun loadData() {
        if (resource == null) {
            errorMessage = when (title) {
                "Provider Payouts" ->
                    "Payout listing API abhi available nahi hai."
                "Admin Settings" ->
                    "Admin Settings API abhi connect nahi hai."
                else ->
                    "Is module ka API available nahi hai."
            }
            isLoading = false
            return
        }

        isLoading = true
        errorMessage = ""

        try {
            val token = tokenManager.token.first()

            if (token.isNullOrBlank()) {
                errorMessage = "Login session nahi mila. Dobara login karein."
                items = emptyList()
                total = 0
                return
            }

            val response = RetrofitClient.api.getAdminList(
                authorization = "Bearer $token",
                resource = resource,
                limit = 30,
                offset = 0
            )

            if (response.isSuccessful) {
                val json = response.body()?.asJsonObject

                if (json == null) {
                    errorMessage = "Server se valid data nahi mila."
                    items = emptyList()
                    total = 0
                } else {
                    total = json.get("total")?.asInt ?: 0

                    val array = json.get("items")?.asJsonArray

                    items = array?.mapNotNull {
                        if (it.isJsonObject) it.asJsonObject else null
                    } ?: emptyList()
                }
            } else {
                errorMessage = when (response.code()) {
                    401 -> "Session expire ho gaya. Dobara login karein."
                    403 -> "Admin permission nahi hai."
                    404 -> "Backend API endpoint nahi mila."
                    else -> "Data load failed: HTTP ${response.code()}"
                }
                items = emptyList()
                total = 0
            }
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message ?: "Please try again"}"
            items = emptyList()
            total = 0
        } finally {
            isLoading = false
        }
    }

    LaunchedEffect(title, tokenManager) {
        loadData()
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
            text = title,
            style = MaterialTheme.typography.headlineSmall,
            fontWeight = FontWeight.Bold
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Button(
                onClick = onBack,
                modifier = Modifier.weight(1f)
            ) {
                Text("Back")
            }

            OutlinedButton(
                onClick = {
                    scope.launch { loadData() }
                },
                enabled = !isLoading,
                modifier = Modifier.weight(1f)
            ) {
                Text("Refresh")
            }
        }

        if (resource != null) {
            Text(
                text = "Total records: $total",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
        }

        if (isLoading) {
            CircularProgressIndicator()
            Text("Loading $title...")
        }

        if (errorMessage.isNotBlank()) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.error,
                style = MaterialTheme.typography.bodyMedium
            )

            Button(
                onClick = {
                    scope.launch { loadData() }
                }
            ) {
                Text("Try Again")
            }
        }

        if (!isLoading && errorMessage.isBlank() && resource != null) {
            if (items.isEmpty()) {
                Text("Abhi koi record available nahi hai.")
            }

            items.forEachIndexed { index, item ->
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    colors = CardDefaults.cardColors(
                        containerColor = MaterialTheme.colorScheme.surface
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "Record ${index + 1}",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )

                        item.entrySet().forEach { entry ->
                            val value = if (
                                entry.value.isJsonNull
                            ) {
                                "—"
                            } else {
                                entry.value.toString()
                                    .removeSurrounding("\"")
                            }

                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = entry.key
                                        .replace("_", " "),
                                    fontWeight = FontWeight.Medium,
                                    modifier = Modifier.weight(1f)
                                )

                                Text(
                                    text = value,
                                    modifier = Modifier.weight(1f)
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}