
package com.example.servicehub.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.material3.Checkbox
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
import com.example.servicehub.data.RetrofitClient
import com.example.servicehub.data.UserCreate
import kotlinx.coroutines.launch


@Composable
fun SignupScreen(
    onSignupSuccess: () -> Unit,
    onBackToLogin: () -> Unit
) {

    var name by remember {
        mutableStateOf("")
    }

    var email by remember {
        mutableStateOf("")
    }

    var phone by remember {
        mutableStateOf("")
    }

    var password by remember {
        mutableStateOf("")
    }

    var confirmPassword by remember {
        mutableStateOf("")
    }

    var isProvider by remember {
        mutableStateOf(true)
    }

    var errorMessage by remember {
        mutableStateOf("")
    }

    var successMessage by remember {
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

                // ====================================================
                // LOGO
                // ====================================================

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


                // ====================================================
                // TITLE
                // ====================================================

                Text(
                    text = "Create Account",
                    style =
                        MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(
                        top = 16.dp
                    )
                )

                Text(
                    text = "ServiceHub Provider Portal",
                    style =
                        MaterialTheme.typography.titleMedium,
                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(
                        top = 4.dp
                    )
                )

                Text(
                    text =
                        "Create your account to manage services, bookings and customers",
                    style =
                        MaterialTheme.typography.bodyMedium,
                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(
                        top = 8.dp,
                        bottom = 24.dp
                    )
                )


                // ====================================================
                // NAME
                // ====================================================

                OutlinedTextField(
                    value = name,
                    onValueChange = {
                        name = it
                        errorMessage = ""
                        successMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Full name")
                    },
                    placeholder = {
                        Text("Enter your name")
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Text
                    ),
                    shape = RoundedCornerShape(16.dp)
                )


                Spacer(
                    modifier = Modifier.height(12.dp)
                )


                // ====================================================
                // EMAIL
                // ====================================================

                OutlinedTextField(
                    value = email,
                    onValueChange = {
                        email = it
                        errorMessage = ""
                        successMessage = ""
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
                    modifier = Modifier.height(12.dp)
                )


                // ====================================================
                // PHONE
                // ====================================================

                OutlinedTextField(
                    value = phone,
                    onValueChange = {
                        phone = it
                        errorMessage = ""
                        successMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Phone number")
                    },
                    placeholder = {
                        Text("Enter phone number")
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Phone
                    ),
                    shape = RoundedCornerShape(16.dp)
                )


                Spacer(
                    modifier = Modifier.height(12.dp)
                )


                // ====================================================
                // PASSWORD
                // ====================================================

                OutlinedTextField(
                    value = password,
                    onValueChange = {
                        password = it
                        errorMessage = ""
                        successMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Password")
                    },
                    placeholder = {
                        Text("Create a password")
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
                    modifier = Modifier.height(12.dp)
                )


                // ====================================================
                // CONFIRM PASSWORD
                // ====================================================

                OutlinedTextField(
                    value = confirmPassword,
                    onValueChange = {
                        confirmPassword = it
                        errorMessage = ""
                        successMessage = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                    label = {
                        Text("Confirm password")
                    },
                    placeholder = {
                        Text("Enter password again")
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
                    modifier = Modifier.height(12.dp)
                )


                // ====================================================
                // PROVIDER CHECKBOX
                // ====================================================

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment =
                        Alignment.CenterVertically
                ) {

                    Checkbox(
                        checked = isProvider,
                        onCheckedChange = {
                            isProvider = it
                            errorMessage = ""
                        },
                        enabled = !isLoading
                    )

                    Text(
                        text = "I am a service provider",
                        fontWeight = FontWeight.Medium
                    )
                }


                Text(
                    text =
                        "Provider account se aap apni services aur bookings manage kar sakte hain.",
                    style =
                        MaterialTheme.typography.bodySmall,
                    color =
                        MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(
                            start = 12.dp,
                            end = 12.dp
                        )
                )


                Spacer(
                    modifier = Modifier.height(22.dp)
                )


                // ====================================================
                // CREATE ACCOUNT BUTTON
                // ====================================================

                Button(
                    onClick = {

                        // --------------------------------------------
                        // BASIC VALIDATION
                        // --------------------------------------------

                        when {

                            name.isBlank() -> {

                                errorMessage =
                                    "Name enter kijiye"
                            }

                            email.isBlank() -> {

                                errorMessage =
                                    "Email enter kijiye"
                            }

                            password.isBlank() -> {

                                errorMessage =
                                    "Password enter kijiye"
                            }

                            password.length < 6 -> {

                                errorMessage =
                                    "Password kam se kam 6 characters ka hona chahiye"
                            }

                            confirmPassword.isBlank() -> {

                                errorMessage =
                                    "Confirm password enter kijiye"
                            }

                            password != confirmPassword -> {

                                errorMessage =
                                    "Password aur confirm password same nahi hain"
                            }

                            else -> {

                                scope.launch {

                                    isLoading = true
                                    errorMessage = ""
                                    successMessage = ""

                                    try {

                                        // --------------------------------
                                        // BACKEND SIGNUP API
                                        // --------------------------------

                                        val response =
                                            RetrofitClient.api.signup(
                                                UserCreate(
                                                    name =
                                                        name.trim(),

                                                    email =
                                                        email.trim(),

                                                    password =
                                                        password,

                                                    phone =
                                                        phone
                                                            .trim()
                                                            .ifBlank {
                                                                null
                                                            },

                                                    isProvider =
                                                        isProvider
                                                )
                                            )


                                        // --------------------------------
                                        // SUCCESS
                                        // --------------------------------

                                        if (response.isSuccessful) {

                                            successMessage =
                                                "Account successfully create ho gaya."

                                            /*
                                             * Backend signup token return
                                             * nahi karta.
                                             *
                                             * Isliye signup ke baad
                                             * Login screen par jayenge.
                                             */

                                            onSignupSuccess()

                                        } else {

                                            // ----------------------------
                                            // ERROR
                                            // ----------------------------

                                            errorMessage =
                                                when (
                                                    response.code()
                                                ) {

                                                    400 ->
                                                        "Ye email pehle se registered hai"

                                                    401 ->
                                                        "Signup authorization failed"

                                                    422 ->
                                                        "Please sabhi details sahi format mein enter kijiye"

                                                    500 ->
                                                        "Server error. Thodi der baad try kijiye"

                                                    else ->
                                                        "Signup failed: ${response.code()}"
                                                }
                                        }

                                    } catch (e: Exception) {

                                        errorMessage =
                                            "Backend se connection nahi ho pa raha.\n${e.message}"

                                    } finally {

                                        isLoading = false
                                    }
                                }
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
                            text = "Create Account",
                            fontWeight = FontWeight.Bold
                        )
                    }
                }


                // ====================================================
                // SUCCESS MESSAGE
                // ====================================================

                if (successMessage.isNotBlank()) {

                    Text(
                        text = successMessage,
                        color =
                            MaterialTheme.colorScheme.primary,
                        style =
                            MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(
                            top = 14.dp
                        )
                    )
                }


                // ====================================================
                // ERROR MESSAGE
                // ====================================================

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


                // ====================================================
                // BACK TO LOGIN
                // ====================================================

                TextButton(
                    onClick = {

                        if (!isLoading) {
                            onBackToLogin()
                        }
                    },
                    enabled = !isLoading,
                    modifier = Modifier.padding(
                        top = 8.dp
                    )
                ) {

                    Text(
                        text =
                            "Already have an account? Sign In"
                    )
                }
            }
        }
    }
}
