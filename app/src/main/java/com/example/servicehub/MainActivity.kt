@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.servicehub
import com.example.servicehub.ui.SignupScreen
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.UserResponse
import com.example.servicehub.data.local.TokenManager
import com.example.servicehub.ui.LoginScreen
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch


class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val tokenManager = TokenManager(this)

        setContent {

            val appScope = rememberCoroutineScope()

            MaterialTheme {

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {

                    var isCheckingLogin by remember { mutableStateOf(true) }
                    var isLoggedIn by remember { mutableStateOf(false) }
                    var isProvider by remember { mutableStateOf(false) }
                    var isAdmin by remember { mutableStateOf(false) }
                    var currentUser by remember { mutableStateOf<UserResponse?>(null) }
                    var showSignup by remember { mutableStateOf(false) }
                    // -----------------------------------------
                    // CHECK SAVED LOGIN SESSION
                    // -----------------------------------------

                    LaunchedEffect(Unit) {

                        val savedToken = tokenManager.token.first()

                        if (!savedToken.isNullOrBlank()) {

                            try {

                                val response =
                                    RetrofitClient.api.getCurrentUser("Bearer $savedToken")

                                val user = response.body()

                                if (
                                    response.isSuccessful &&
                                    user != null &&
                                    (user.isProvider || user.isAdmin)
                                ) {
                                    currentUser = user
                                    isProvider = user.isProvider
                                    isAdmin = user.isAdmin
                                    isLoggedIn = true
                                } else {
                                    tokenManager.clear()
                                    currentUser = null
                                    isProvider = false
                                    isAdmin = false
                                    isLoggedIn = false
                                }

                            } catch (_: Exception) {

                                // Temporary backend/network failure.
                                // Use saved role only for offline access.
                                isProvider = tokenManager.isProvider.first()
                                isAdmin = tokenManager.isAdmin.first()
                                isLoggedIn = isProvider || isAdmin
                            }
                        }

                        isCheckingLogin = false
                    }

                    // -----------------------------------------
                    // MAIN SCREEN
                    // -----------------------------------------

                    when {

                        showSignup && !isLoggedIn -> {
                            SignupScreen(
                                onSignupSuccess = { showSignup = false },
                                onBackToLogin = { showSignup = false }
                            )
                        }


                        isCheckingLogin -> {
                            LoadingScreen()
                        }

                        !isLoggedIn -> {

                            LoginScreen(
                                tokenManager = tokenManager,

                                onLoginSuccess = { provider, admin ->

                                    appScope.launch {

                                        isCheckingLogin = true

                                        isProvider = provider
                                        isAdmin = admin

                                        if (!provider && !admin) {
                                            tokenManager.clear()
                                            currentUser = null
                                            isLoggedIn = false
                                            isCheckingLogin = false
                                            return@launch
                                        }

                                        try {

                                            val savedToken = tokenManager.token.first()

                                            if (savedToken.isNullOrBlank()) {

                                                tokenManager.clear()
                                                currentUser = null
                                                isLoggedIn = false

                                            } else {

                                                val response =
                                                    RetrofitClient.api.getCurrentUser(
                                                        "Bearer $savedToken"
                                                    )

                                                val user = response.body()

                                                if (
                                                    response.isSuccessful &&
                                                    user != null &&
                                                    (user.isProvider || user.isAdmin)
                                                ) {
                                                    currentUser = user
                                                    isProvider = user.isProvider
                                                    isAdmin = user.isAdmin
                                                    isLoggedIn = true
                                                } else {
                                                    tokenManager.clear()
                                                    currentUser = null
                                                    isProvider = false
                                                    isAdmin = false
                                                    isLoggedIn = false
                                                }
                                            }

                                        } catch (_: Exception) {

                                            // Login response confirmed the role.
                                            // Keep session during temporary outage.
                                            isLoggedIn = provider || admin
                                        }

                                        isCheckingLogin = false
                                    }
                                },
                                onCreateAccount = { showSignup = true }
                            )
                        }

                        else -> {

                            ProviderDashboard(
                                user = currentUser,
                                isProvider = isProvider,
                                isAdmin = isAdmin,
                                tokenManager = tokenManager,

                                onUserUpdated = { updatedUser ->
                                    if (updatedUser != null) {
                                        currentUser = updatedUser
                                        isProvider = updatedUser.isProvider
                                        isAdmin = updatedUser.isAdmin
                                    }
                                },

                                onLogout = {
                                    appScope.launch {
                                        tokenManager.clear()
                                        isLoggedIn = false
                                        currentUser = null
                                        isProvider = false
                                        isAdmin = false
                                    }
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}


/* ============================================================
   LOADING SCREEN
   ============================================================ */

@Composable
private fun LoadingScreen() {

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(MaterialTheme.colorScheme.background),
        contentAlignment = Alignment.Center
    ) {

        Column(horizontalAlignment = Alignment.CenterHorizontally) {

            CircularProgressIndicator(modifier = Modifier.size(48.dp))

            Spacer(modifier = Modifier.height(18.dp))

            Text(
                text = "ServiceHub loading...",
                style = MaterialTheme.typography.titleMedium
            )

            Text(
                text = "Connecting to backend",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 6.dp)
            )
        }
    }
}


/* ============================================================
   MODELS
   ============================================================ */

private data class DashboardItem(
    val title: String,
    val subtitle: String,
    val emoji: String
)

private data class BottomNavigationItem(
    val route: String,
    val label: String,
    val emoji: String
)


/* ============================================================
   PROVIDER DASHBOARD
   ============================================================ */

@Composable
private fun ProviderDashboard(
    user: UserResponse?,
    isProvider: Boolean,
    isAdmin: Boolean,
    tokenManager: TokenManager,
    onUserUpdated: (UserResponse?) -> Unit,
    onLogout: () -> Unit
) {

    var selectedItem by remember { mutableStateOf("Dashboard") }

    // FIX: Phone Back button -> module screen se Dashboard par wapas.
    // Dashboard par Back dabane par app normal tarah band hoga.
    BackHandler(enabled = selectedItem != "Dashboard") {
        selectedItem = "Dashboard"
    }

    var isRefreshing by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }

    val scope = rememberCoroutineScope()

    val dashboardItems = buildList {

        add(DashboardItem("Orders", "Manage customer orders", "📦"))
        add(DashboardItem("Bookings", "View customer bookings", "📅"))
        add(DashboardItem("Hotels", "Hotel bookings", "🏨"))
        add(DashboardItem("Appointments", "Doctor appointments", "🩺"))
        add(DashboardItem("Services", "Manage services", "🛎️"))
        add(DashboardItem("Payments", "Payments and earnings", "💰"))
        add(DashboardItem("Profile", "Provider profile", "👤"))
        add(DashboardItem("Settings", "Application settings", "⚙️"))

        if (isAdmin) {
            add(DashboardItem("Admin", "Administration", "🛡️"))
        }
    }

    val navigationItems = listOf(
        BottomNavigationItem("Dashboard", "Home", "🏠"),
        BottomNavigationItem("Orders", "Orders", "📦"),
        BottomNavigationItem("Bookings", "Bookings", "📅"),
        BottomNavigationItem("Profile", "Profile", "👤")
    )

    Scaffold(

        topBar = {

            TopAppBar(

                title = {

                    Column {

                        Text(
                            text = "ServiceHub",
                            fontWeight = FontWeight.Bold
                        )

                        Text(
                            text = when {
                                isAdmin -> "Admin Panel"
                                isProvider -> "Provider Panel"
                                else -> "User Panel"
                            },
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                },

                actions = {

                    IconButton(
                        onClick = {

                            if (!isRefreshing) {

                                scope.launch {

                                    isRefreshing = true
                                    message = ""

                                    try {

                                        val token = tokenManager.token.first()

                                        if (!token.isNullOrBlank()) {

                                            val response =
                                                RetrofitClient.api.getCurrentUser(
                                                    "Bearer $token"
                                                )

                                            val updatedUser = response.body()

                                            if (
                                                response.isSuccessful &&
                                                updatedUser != null &&
                                                (updatedUser.isProvider || updatedUser.isAdmin)
                                            ) {
                                                onUserUpdated(updatedUser)
                                                message = "Profile refreshed"
                                            } else {
                                                message = "Session expired. Please login again."
                                            }

                                        } else {
                                            message = "Login required"
                                        }

                                    } catch (e: Exception) {

                                        message =
                                            "Refresh failed: ${e.message ?: "Network error"}"

                                    } finally {
                                        isRefreshing = false
                                    }
                                }
                            }
                        }
                    ) {

                        if (isRefreshing) {

                            CircularProgressIndicator(
                                modifier = Modifier.size(22.dp),
                                strokeWidth = 2.dp
                            )

                        } else {

                            Text(
                                text = "↻",
                                style = MaterialTheme.typography.headlineSmall
                            )
                        }
                    }
                },

                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },

        bottomBar = {

            NavigationBar(
                containerColor = MaterialTheme.colorScheme.surface,
                tonalElevation = 8.dp
            ) {

                navigationItems.forEach { item ->

                    NavigationBarItem(
                        selected = selectedItem == item.route,
                        onClick = {
                            selectedItem = item.route
                            message = ""
                        },
                        icon = {
                            Text(
                                text = item.emoji,
                                style = MaterialTheme.typography.titleLarge
                            )
                        },
                        label = { Text(item.label) },
                        alwaysShowLabel = true
                    )
                }
            }
        }

    ) { paddingValues ->

        val backToDashboard = { selectedItem = "Dashboard" }

        when (selectedItem) {

            "Dashboard" -> DashboardHome(
                user = user,
                isProvider = isProvider,
                isAdmin = isAdmin,
                items = dashboardItems,
                message = message,
                onItemClick = { item ->
                    selectedItem = item
                    message = ""
                },
                onLogout = onLogout,
                modifier = Modifier.padding(paddingValues)
            )

            "Orders" -> ModuleScreen(
                title = "Orders",
                emoji = "📦",
                description = "Manage your customer orders.",
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Bookings" -> MyBookingsScreen(
                tokenManager = tokenManager,
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Hotels" -> ModuleScreen(
                title = "Hotel Bookings",
                emoji = "🏨",
                description = "Manage hotel booking requests.",
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Appointments" -> ModuleScreen(
                title = "Appointments",
                emoji = "🩺",
                description = "Manage doctor appointments.",
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Services" -> ModuleScreen(
                title = "Services",
                emoji = "🛎️",
                description = "Manage your listed services.",
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Payments" -> PayoutStatusScreen(
                tokenManager = tokenManager,
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Profile" -> ProfileScreen(
                user = user,
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )

            "Settings" -> ModuleScreen(
                title = "Settings",
                emoji = "⚙️",
                description = "Manage your application settings.",
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )
            "Admin" -> AdminDashboardScreen(
                onBack = backToDashboard,
                modifier = Modifier.padding(paddingValues)
            )
        }
    }
}


/* ============================================================
   DASHBOARD HOME
   ============================================================ */

@Composable
private fun DashboardHome(
    user: UserResponse?,
    isProvider: Boolean,
    isAdmin: Boolean,
    items: List<DashboardItem>,
    message: String,
    onItemClick: (String) -> Unit,
    onLogout: () -> Unit,
    modifier: Modifier = Modifier
) {

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {

        item {

            Spacer(modifier = Modifier.height(8.dp))

            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(24.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer
                )
            ) {

                Row(
                    modifier = Modifier.padding(20.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {

                    Box(
                        modifier = Modifier
                            .size(58.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primary),
                        contentAlignment = Alignment.Center
                    ) {

                        Text(
                            text = user?.name
                                ?.firstOrNull()
                                ?.uppercase()
                                ?: "S",
                            color = MaterialTheme.colorScheme.onPrimary,
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold
                        )
                    }

                    Spacer(modifier = Modifier.width(14.dp))

                    Column(modifier = Modifier.weight(1f)) {

                        Text(
                            text = "Welcome back 👋",
                            style = MaterialTheme.typography.labelLarge
                        )

                        Text(
                            text = user?.name ?: "Service Provider",
                            style = MaterialTheme.typography.titleLarge,
                            fontWeight = FontWeight.Bold
                        )

                        Text(
                            text = user?.email ?: "",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }
                }
            }
        }

        item {

            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {

                StatCard(
                    title = "Account",
                    value = when {
                        isAdmin -> "Admin"
                        isProvider -> "Provider"
                        else -> "User"
                    },
                    emoji = "✓",
                    modifier = Modifier.weight(1f)
                )

                StatCard(
                    title = "Status",
                    value = "Active",
                    emoji = "●",
                    modifier = Modifier.weight(1f)
                )
            }
        }

        item {

            Text(
                text = "Quick Actions",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
        }

        item {

            LazyVerticalGrid(
                columns = GridCells.Fixed(2),
                modifier = Modifier.height(
                    if (items.size <= 4) 330.dp else 620.dp
                ),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
                userScrollEnabled = false
            ) {

                items(items) { item ->

                    DashboardCard(
                        item = item,
                        onClick = { onItemClick(item.title) }
                    )
                }
            }
        }

        if (message.isNotBlank()) {

            item {

                Text(
                    text = message,
                    color = MaterialTheme.colorScheme.primary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        }

        item {

            OutlinedButton(
                onClick = onLogout,
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 20.dp)
            ) {
                Text("Logout")
            }
        }
    }
}


/* ============================================================
   STAT CARD
   ============================================================ */

@Composable
private fun StatCard(
    title: String,
    value: String,
    emoji: String,
    modifier: Modifier = Modifier
) {

    Card(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp)
    ) {

        Column(modifier = Modifier.padding(16.dp)) {

            Text(
                text = emoji,
                style = MaterialTheme.typography.titleLarge
            )

            Text(
                text = title,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp)
            )

            Text(
                text = value,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
        }
    }
}


/* ============================================================
   DASHBOARD CARD
   ============================================================ */

@Composable
private fun DashboardCard(
    item: DashboardItem,
    onClick: () -> Unit
) {

    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant
        )
    ) {

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalArrangement = Arrangement.Center
        ) {

            Text(
                text = item.emoji,
                style = MaterialTheme.typography.headlineMedium
            )

            Text(
                text = item.title,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(top = 10.dp)
            )

            Text(
                text = item.subtitle,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp)
            )
        }
    }
}


/* ============================================================
   MODULE SCREEN
   ============================================================ */

@Composable
private fun ModuleScreen(
    title: String,
    emoji: String,
    description: String,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {

        Text(
            text = emoji,
            style = MaterialTheme.typography.displaySmall
        )

        Text(
            text = title,
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 12.dp)
        )

        Text(
            text = description,
            textAlign = TextAlign.Center,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 12.dp, bottom = 24.dp)
        )

        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(20.dp)
        ) {

            Column(modifier = Modifier.padding(20.dp)) {

                Text(
                    text = "Backend integration",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.Bold
                )

                Text(
                    text = "This module is ready for ServiceHub API integration.",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 8.dp)
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("← Back to Dashboard")
        }
    }
}


/* ============================================================
   PROFILE
   ============================================================ */

@Composable
private fun ProfileScreen(
    user: UserResponse?,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {

    Column(
        modifier = modifier
            .fillMaxSize()
            .padding(20.dp)
    ) {

        Text(
            text = "👤",
            style = MaterialTheme.typography.displaySmall
        )

        Text(
            text = "My Profile",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 10.dp)
        )

        Spacer(modifier = Modifier.height(20.dp))

        ProfileRow(title = "Name", value = user?.name ?: "-")
        ProfileRow(title = "Email", value = user?.email ?: "-")
        ProfileRow(title = "Phone", value = user?.phone ?: "-")
        ProfileRow(
            title = "Provider",
            value = if (user?.isProvider == true) "Yes" else "No"
        )
        ProfileRow(
            title = "Admin",
            value = if (user?.isAdmin == true) "Yes" else "No"
        )

        Spacer(modifier = Modifier.height(24.dp))

        Button(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("← Back to Dashboard")
        }
    }
}


/* ============================================================
   PROFILE ROW
   ============================================================ */

@Composable
private fun ProfileRow(
    title: String,
    value: String
) {

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 10.dp)
    ) {

        Text(
            text = title,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        Text(
            text = value,
            style = MaterialTheme.typography.bodyLarge,
            fontWeight = FontWeight.Medium,
            modifier = Modifier.padding(top = 3.dp)
        )

        Divider(modifier = Modifier.padding(top = 10.dp))
    }
}


