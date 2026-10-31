package com.example.servicehub

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import kotlinx.coroutines.launch

@Composable
fun PayoutStatusScreen(
    tokenManager: TokenManager,
    onBack: () -> Unit,
    modifier: Modifier = Modifier
) {
    val token by tokenManager.token.collectAsStateWithLifecycle(initialValue = null)
    val providerId by tokenManager.providerId.collectAsStateWithLifecycle(initialValue = null)
    val scope = rememberCoroutineScope()

    var loading by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf("") }
    var payoutStatus by remember {
        mutableStateOf<com.example.servicehub.data.PayoutOnboardingStatus?>(null)
    }

    suspend fun loadPayoutStatus() {
        val currentToken = token

        if (currentToken.isNullOrBlank()) {
            message = "Login session nahi mila. Dobara login karein."
            return
        }

        loading = true
        message = ""

        try {
            val response = RetrofitClient.api.getPayoutOnboardingStatus(
                authorization = "Bearer $currentToken"
            )

            if (response.isSuccessful) {
                payoutStatus = response.body()
                if (payoutStatus == null) {
                    message = "Backend se payout status empty mila."
                }
            } else {
                message = "Payout status load nahi hua. HTTP ${response.code()}"
            }
        } catch (e: Exception) {
            message = e.message ?: "Network error"
        } finally {
            loading = false
        }
    }

    LaunchedEffect(token, providerId) {
        if (!token.isNullOrBlank() && providerId != null) {
            loadPayoutStatus()
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
            text = "💰 Payout Status",
            style = MaterialTheme.typography.headlineMedium,
            fontWeight = FontWeight.Bold
        )

        Text(
            text = "Apne provider payout setup aur verification ka status dekhein.",
            style = MaterialTheme.typography.bodyMedium
        )

        if (providerId == null) {
            Text(
                text = "Provider ID nahi mila. Provider account se login karein.",
                color = MaterialTheme.colorScheme.error
            )
        } else {
            Text(
                text = "Provider ID: $providerId",
                style = MaterialTheme.typography.labelLarge
            )
        }

        HorizontalDivider()

        if (loading) {
            CircularProgressIndicator()
            Text("Payout status load ho raha hai...")
        }

        if (message.isNotBlank()) {
            Text(
                text = message,
                color = MaterialTheme.colorScheme.error
            )
        }

        payoutStatus?.let { status ->
            Text(
                text = "Onboarding Checklist",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            StatusRow("Linked Account", status.linkedAccount.completed)
            StatusRow("Stakeholder", status.stakeholder.completed)
            StatusRow("Route Product", status.routeProduct.completed)
            StatusRow("Bank Details", status.bank.completed)

            HorizontalDivider()

            Text(
                text = "Verification",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            Text("Verification Status: ${status.verification.status}")
            StatusRow("Verification Completed", status.verification.completed)
            StatusRow("Payouts Enabled", status.verification.payoutsEnabled)

            HorizontalDivider()

            Text(
                text = "Payout Readiness",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )

            StatusRow("Ready for Payout", status.readyForPayout)

            Text("Next Step: ${status.nextStep}")
            Text("Payout Profile ID: ${status.payoutProfileId}")

            if (status.readyForPayout) {
                Text(
                    text = "Payout setup complete hai.",
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
            } else {
                Text(
                    text = "Payout activation ke liye onboarding/verification complete hona baaki hai.",
                    color = MaterialTheme.colorScheme.error
                )
            }
        }

        OutlinedButton(
            onClick = {
                scope.launch { loadPayoutStatus() }
            },
            enabled = !loading && !token.isNullOrBlank(),
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("Refresh Status")
        }

        OutlinedButton(
            onClick = onBack,
            modifier = Modifier.fillMaxWidth()
        ) {
            Text("← Back to Dashboard")
        }
    }
}

@Composable
private fun StatusRow(
    label: String,
    completed: Boolean
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 5.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(label)
        Text(
            text = if (completed) "Completed" else "Pending",
            color = if (completed)
                MaterialTheme.colorScheme.primary
            else
                MaterialTheme.colorScheme.error,
            fontWeight = FontWeight.Bold
        )
    }
}
