package com.example.servicehub.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.example.servicehub.data.LoginRequest
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.local.TokenManager
import kotlinx.coroutines.launch

@Composable
fun LoginScreen(
    tokenManager: TokenManager,
    onLoginSuccess: (Boolean, Boolean) -> Unit
) {

    var email by remember {
        mutableStateOf("")
    }

    var password by remember {
        mutableStateOf("")
    }

    var errorMessage by remember {
        mutableStateOf("")
    }

    var isLoading by remember {
        mutableStateOf(false)
    }

    val scope = rememberCoroutineScope()

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(
                MaterialTheme.colorScheme.background
            ),
        contentAlignment = Alignment.Center
    ) {

        Card(
            modifier = Modifier
                .fillMaxWidth()
                .padding(20.dp),
            shape = RoundedCornerShape(28.dp),
            colors = CardDefaults.cardColors(
                containerColor =
                    MaterialTheme.colorScheme.surface
            ),
            elevation = CardDefaults.cardElevation(
                defaultElevation = 6.dp
            )
        ) {

            Column(
                modifier = Modifier.padding(24.dp),
                horizontalAlignment =
                    Alignment.CenterHorizontally
            ) {

                Box(
                    modifier = Modifier
                        .size(76.dp)
                        .background(
                            MaterialTheme.colorScheme.primary,
                            CircleShape
                        ),
                    contentAlignment = Alignment.Center
                ) {

                    Text(
                        text = "S",
                        color =
                            MaterialTheme.colorScheme.onPrimary,
                        style =
                            MaterialTheme.typography.displaySmall,
                        fontWeight = FontWeight.Bold
                    )
                }

                Text(
                    text = "ServiceHub",
                    style =
                        MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(top = 16.dp)
                )

                Text(
                    text = "Provider Portal",
                    style =
                        MaterialTheme.typography.titleMedium,
                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp)
                )

                Text(
                    text =
                        "Manage your services, bookings and customers",
                    style =
                        MaterialTheme.typography.bodyMedium,
                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(
                        top = 8.dp,
                        bottom = 24.dp
                    )
                )

                OutlinedTextField(
                    value = email,
                    onValueChange = {
                        email = it
                        errorMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Email address")
                    },
                    placeholder = {
                        Text("Enter your email")
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Email
                    ),
                    shape = RoundedCornerShape(16.dp)
                )

                Spacer(
                    modifier = Modifier.height(14.dp)
                )

                OutlinedTextField(
                    value = password,
                    onValueChange = {
                        password = it
                        errorMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Password")
                    },
                    placeholder = {
                        Text("Enter your password")
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    visualTransformation =
                        PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Password
                    ),
                    shape = RoundedCornerShape(16.dp)
                )

                Spacer(
                    modifier = Modifier.height(22.dp)
                )

                Button(
                    onClick = {

                        if (email.isBlank() ||
                            password.isBlank()
                        ) {

                            errorMessage =
                                "Email aur password enter kijiye"

                            return@Button
                        }

                        scope.launch {

                            isLoading = true
                            errorMessage = ""

                            try {

                                val response =
                                    RetrofitClient.api.login(
                                        LoginRequest(
                                            email = email.trim(),
                                            password = password
                                        )
                                    )

                                if (response.isSuccessful) {

                                    val data =
                                        response.body()

                                    if (data != null) {

                                        /*
                                         * Login response se:
                                         *
                                         * userId     -> logged-in user
                                         * providerId -> provider listing
                                         * isProvider -> provider account
                                         * isAdmin    -> admin account
                                         */

                                        tokenManager.saveToken(
                                            accessToken =
                                                data.accessToken,

                                            userId =
                                                data.userId,

                                            providerId =
                                                data.providerId,

                                            isProvider =
                                                data.isProvider,

                                            isAdmin =
                                                data.isAdmin
                                        )

                                        onLoginSuccess(
                                            data.isProvider,
                                            data.isAdmin
                                        )

                                    } else {

                                        errorMessage =
                                            "Server ne empty response diya"
                                    }

                                } else {

                                    errorMessage =
                                        when (response.code()) {

                                            400 ->
                                                "Invalid login request"

                                            401 ->
                                                "Email ya password galat hai"

                                            403 ->
                                                "Access denied"

                                            404 ->
                                                "Login API nahi mili"

                                            500 ->
                                                "Server error"

                                            else ->
                                                "Login failed: ${response.code()}"
                                        }
                                }

                            } catch (e: Exception) {

                                errorMessage =
                                    "Backend se connection nahi ho pa raha.\n${e.message}"

                            } finally {

                                isLoading = false
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    enabled = !isLoading,
                    shape = RoundedCornerShape(16.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor =
                            MaterialTheme.colorScheme.primary
                    )
                ) {

                    if (isLoading) {

                        CircularProgressIndicator(
                            modifier = Modifier.size(24.dp),
                            color =
                                MaterialTheme.colorScheme.onPrimary,
                            strokeWidth = 2.dp
                        )

                    } else {

                        Text(
                            text = "Sign In",
                            fontWeight = FontWeight.Bold
                        )
                    }
                }

                if (errorMessage.isNotBlank()) {

                    Text(
                        text = errorMessage,
                        color =
                            MaterialTheme.colorScheme.error,
                        style =
                            MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(
                            top = 14.dp
                        )
                    )
                }

                TextButton(
                    onClick = {

                        if (!isLoading) {

                            errorMessage =
                                "Signup screen next step mein add karenge"
                        }
                    },
                    enabled = !isLoading,
                    modifier = Modifier.padding(top = 8.dp)
                ) {

                    Text("Create new account")
                }
            }
        }
    }
}